from fastapi import FastAPI, UploadFile, File, HTTPException
from PyPDF2 import PdfReader
from docx import Document
from dotenv import load_dotenv
import google.generativeai as genai
import os
import io
import requests
import json
import re
import mysql.connector

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI(title="Smart Resume Analyzer MCP Server")

# ---- Helper functions ----
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")

def extract_text_from_docx(file):
    try:
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"DOCX extraction failed: {str(e)}")

def analyze_with_gemini(text: str):
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    prompt = f"""
    You are a resume parsing assistant. Strictly return output in raw JSON format (no explanations or text).
    Example:
    {{
      "skills": ["Python", "TensorFlow", "FastAPI"],
      "education": "B.Tech in Computer Science",
      "experience": "2 years as ML Engineer"
    }}

    Analyze this resume and output JSON only:
    Resume Text:
    {text[:10000]}
    """
    response = model.generate_content(prompt)
    return response.text

def clean_json_response(text: str):
    """Extract valid JSON object from Gemini output."""
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            raise ValueError("Gemini output contains invalid JSON format.")
    raise ValueError("No valid JSON found in Gemini response.")

def notify_n8n(email, skills, experience):
    try:
        n8n_url = os.getenv("N8N_WEBHOOK_URL")
        payload = {
            "email": email,
            "skills": skills,
            "experience": experience,
            "rapidapi_key": os.getenv("RAPIDAPI_KEY")
        }
        response = requests.post(n8n_url, json=payload)
        response.raise_for_status()
        print("✅ Data sent to n8n successfully!")
    except Exception as e:
        print(f"❌ Failed to notify n8n: {e}")


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER1"),
        password=os.getenv("DB_PASSWORD1"),
        database=os.getenv("DB_NAME1")
    )

@app.post("/analyze_resume")
async def analyze_resume(file: UploadFile = File(...)):
    filename = file.filename.lower()
    content = await file.read()
    text = ""

    if filename.endswith(".pdf"):
        text = extract_text_from_pdf(io.BytesIO(content))
    elif filename.endswith(".docx"):
        text = extract_text_from_docx(io.BytesIO(content))
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use PDF or DOCX.")

    try:
        result = analyze_with_gemini(text)
        parsed = clean_json_response(result)

        
        skills = parsed.get("skills", [])
        experience = parsed.get("experience", "")
        email = "user@example.com"  

       
        notify_n8n(email, skills, experience)

        return {
            "filename": filename,
            "skills": skills,
            "experience": experience,
            "status": "✅ Data sent to n8n successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini analysis failed: {str(e)}")


@app.post("/store_jobs")
async def store_jobs(data: dict):
    """Store job data received from n8n or any other service into MySQL."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO jobs (title, company, location, salary, job_url, skills, experience)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            data.get("title"),
            data.get("company"),
            data.get("location"),
            data.get("salary"),
            data.get("job_url"),
            ",".join(data.get("skills", [])),
            data.get("experience")
        ))
        conn.commit()
        cursor.close()
        conn.close()

        return {"status": "success", "message": "✅ Job stored successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB insert failed: {e}")

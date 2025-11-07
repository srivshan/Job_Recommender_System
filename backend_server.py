from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
import aiofiles
import os
import requests
from dotenv import load_dotenv

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


latest_data = {}


load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@app.post("/upload_resume")
async def upload_resume(file: UploadFile = File(...)):
    
    try:
        save_path = os.path.join(UPLOAD_DIR, file.filename)
        async with aiofiles.open(save_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)

        n8n_url = os.getenv("N8N_WEBHOOK_URL")  
        payload = {"file_name": file.filename, "file_path": save_path}
        n8n_response = requests.post(n8n_url, json=payload)

        if n8n_response.status_code != 200:
            return {"error": f"Failed to trigger N8N workflow: {n8n_response.text}"}

        return {"message": f"✅ Resume '{file.filename}' uploaded successfully and sent to N8N."}

    except Exception as e:
        return {"error": str(e)}

@app.post("/save_jobs")
async def save_jobs(request: Request):
    
    global latest_data
    data = await request.json()
    latest_data = data  

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        jobs = data.get("jobs", [])
        if not jobs:
            return {"message": "No jobs found in request"}

        for job in jobs:
            title = job.get("title", "N/A")
            company = job.get("company", "N/A")
            location = job.get("location", "N/A")
            url = job.get("url", "")

            cursor.execute(
                """
                INSERT INTO job_data (title, company, location, url)
                VALUES (%s, %s, %s, %s)
                """,
                (title, company, location, url)
            )

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": f"✅ {len(jobs)} jobs saved successfully in database"}

    except Exception as e:
        return {"error": str(e)}


@app.get("/get_latest_jobs")
def get_latest_jobs():
    
    if not latest_data:
        return {"message": "No recent job data available"}
    return latest_data

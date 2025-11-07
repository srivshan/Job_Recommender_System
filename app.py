import streamlit as st
import requests
import os
from dotenv import load_dotenv


load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL1")

st.set_page_config(page_title="Smart Job Recommender System", page_icon="💼", layout="wide")
st.title("💼 Smart Job Recommender System")
st.markdown("---")
analyze_url = os.getenv("analyze")

st.subheader("📁 Upload Your Resume")

uploaded_file = st.file_uploader("Upload your Resume (PDF or DOCX)", type=["pdf", "docx"])
if uploaded_file:
    st.info("Uploading resume to backend and triggering workflow...")
    try:
        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        response = requests.post(analyze_url, files=files)

        if response.status_code == 200:
            st.success("✅ Resume uploaded and sent to n8n successfully!")
        else:
            st.error(f"❌ Backend upload failed: {response.text}")
    except Exception as e:
        st.error(f"⚠️ Error sending file to backend: {e}")


st.markdown("---")
st.subheader("🔔 Latest Job Recommendations")

if st.button("🔄 Refresh Latest Jobs"):
    try:
        response = requests.get(f"{BACKEND_URL}/get_latest_jobs")
        if response.status_code == 200:
            latest_data = response.json()
            jobs = latest_data.get("jobs", [])

            if jobs:
                st.success(f"✅ Showing latest {len(jobs)} jobs received from backend")
                for job in jobs[:10]:
                    st.markdown(f"### {job.get('title', 'N/A')}")
                    st.markdown(f"**Company:** {job.get('company', 'Unknown')}")
                    st.markdown(f"**Location:** {job.get('location', 'N/A')}")
                    if "url" in job:
                        st.markdown(f"[🔗 Apply Here]({job.get('url', '#')})")
                    st.write("---")
            else:
                st.warning("No latest jobs available.")
        else:
            st.error(f"❌ Backend error: {response.text}")
    except Exception as e:
        st.error(f"⚠️ Error fetching jobs: {e}")

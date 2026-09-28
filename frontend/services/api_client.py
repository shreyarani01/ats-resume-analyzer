from typing import Any, Dict, List
import requests
import streamlit as st

DEFAULT_BACKEND_URL = "https://ats-resume-analyzer-o66g.onrender.com"


def _backend_url() -> str:
    """Safely fetch backend URL from Streamlit secrets or environment variables with fallback."""
    # Check top-level secret key first (e.g., BACKEND_URL = "...")
    if "BACKEND_URL" in st.secrets:
        return str(st.secrets["BACKEND_URL"]).rstrip("/")
    
    # Check nested secret key (e.g., [backend] url = "...")
    try:
        return str(st.secrets["backend"]["url"]).rstrip("/")
    except (KeyError, AttributeError, TypeError):
        pass

    return DEFAULT_BACKEND_URL.rstrip("/")


def _auth_headers(access_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def health_check() -> Dict[str, Any]:
    # Increased timeout to 60s to account for Render free tier cold starts
    response = requests.get(f"{_backend_url()}/api/v1/health", timeout=60)
    response.raise_for_status()
    return response.json()


def analyze_resume(
    resume_file,
    access_token: str,
    job_description: str = "",
) -> Dict[str, Any]:
    files = {
        "resume": (resume_file.name, resume_file.getvalue(), resume_file.type),
    }
    # Sanitize job_description so empty string doesn't break route parameters
    data = {"job_description": job_description if job_description.strip() else ""}
    
    response = requests.post(
        f"{_backend_url()}/api/v1/analyze-resume",
        files=files,
        data=data,
        headers=_auth_headers(access_token),
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def get_history(access_token: str) -> List[Dict[str, Any]]:
    response = requests.get(
        f"{_backend_url()}/api/v1/history",
        headers=_auth_headers(access_token),
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def delete_history_entry(analysis_id: str, access_token: str) -> None:
    response = requests.delete(
        f"{_backend_url()}/api/v1/history/{analysis_id}",
        headers=_auth_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()


def generate_pdf(analysis_data: Dict[str, Any], access_token: str) -> bytes:
    response = requests.post(
        f"{_backend_url()}/api/v1/generate-pdf",
        json=analysis_data,
        headers=_auth_headers(access_token),
        timeout=60,
    )
    response.raise_for_status()
    return response.content


def get_history_pdf(analysis_id: str, access_token: str) -> bytes:
    response = requests.get(
        f"{_backend_url()}/api/v1/history/{analysis_id}/pdf",
        headers=_auth_headers(access_token),
        timeout=60,
    )
    response.raise_for_status()
    return response.content
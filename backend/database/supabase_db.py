import logging
import json
import httpx
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from backend.core.config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger("ats_resume_scorer")

# Shared client with reasonable timeouts to avoid blocking during network latency
_client = httpx.AsyncClient(timeout=10.0)


def _get_headers() -> Optional[Dict[str, str]]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively converts model objects (like Pydantic models) or non-standard types into JSON serializable types without double stringification."""
    if hasattr(obj, "model_dump"):
        return _sanitize_for_json(obj.model_dump())
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(i) for i in obj]
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return obj


async def save_analysis(
    user_id: str, filename: str, analysis_result: Dict[str, Any]
) -> Optional[str]:
    headers = _get_headers()
    if not headers:
        logger.error("Supabase credentials not set.")
        return None

    serializable_result = _sanitize_for_json(analysis_result)

    doc = {
        "user_id": user_id,
        "filename": filename,
        "ats_score": serializable_result.get("ats_score", 0),
        "keyword_match": serializable_result.get("keyword_match", 0),
        "missing_keywords": serializable_result.get("missing_keywords", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_result": serializable_result,
    }

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"

    try:
        response = await _client.post(url, headers=headers, json=doc)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            inserted_id = str(data[0].get("id"))
            logger.info(f"Saved analysis for user {user_id}: {inserted_id}")
            return inserted_id
        return None
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"Supabase HTTP error saving analysis: {exc.response.status_code} - {exc.response.text}"
        )
        return None
    except Exception as exc:
        logger.error(f"Failed to save analysis to Supabase: {exc}")
        return None


async def get_user_history(user_id: str) -> List[Dict[str, Any]]:
    headers = _get_headers()
    if not headers:
        logger.error("Supabase credentials not set.")
        return []

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"

    try:
        response = await _client.get(
            url,
            headers=headers,
            params={"user_id": f"eq.{user_id}", "order": "created_at.desc"},
        )
        response.raise_for_status()
        docs = response.json()

        results = []
        for doc in docs:
            analysis_data = doc.get("analysis_result", {})
            results.append(
                {
                    "id": str(doc.get("id")),
                    "filename": doc.get("filename", "resume"),
                    "resume_name": doc.get("filename", "resume"),
                    "job_title": analysis_data.get("job_title", "Unspecified Position"),
                    "ats_score": doc.get("ats_score", 0),
                    "keyword_match": doc.get("keyword_match", 0),
                    "missing_keywords": doc.get("missing_keywords", []),
                    "date": doc.get("created_at", ""),
                    "created_at": doc.get("created_at", ""),
                    "analysis_result": analysis_data,
                }
            )
        return results
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"Supabase HTTP error fetching history: {exc.response.status_code} - {exc.response.text}"
        )
        return []
    except Exception as exc:
        logger.error(f"Failed to fetch history from Supabase: {exc}")
        return []


async def delete_analysis(analysis_id: str, user_id: str) -> bool:
    headers = _get_headers()
    if not headers:
        logger.error("Supabase credentials not set.")
        return False

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"

    try:
        response = await _client.delete(
            url,
            headers=headers,
            params={"id": f"eq.{analysis_id}", "user_id": f"eq.{user_id}"},
        )
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"Supabase HTTP error deleting analysis {analysis_id}: {exc.response.status_code} - {exc.response.text}"
        )
        return False
    except Exception as exc:
        logger.error(f"Failed to delete analysis {analysis_id}: {exc}")
        return False
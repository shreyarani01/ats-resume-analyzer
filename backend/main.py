import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import httpx
import numpy as np

load_dotenv()
import puremagic

def validate_and_extract_file(file_bytes: bytes, filename: str):
    try:
        # puremagic checks magic numbers purely in Python without libmagic1
        exts = puremagic.from_string(file_bytes)
        # Check if detected extension matches pdf or office docs
    except puremagic.PureError:
        # Fallback to extension check if magic headers are ambiguous
        if filename.lower().endswith(('.pdf', '.docx', '.doc')):
            pass
        else:
            raise ValueError("Unsupported or corrupted file format.")
from backend.api.routes import router
from backend.core.config import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    SENTENCE_TRANSFORMER_MODEL,
    SPACY_MODEL_PRIMARY,
    SPACY_MODEL_SECONDARY,
)

logger = logging.getLogger("ats_resume_scorer")

# Hugging Face Free API setup to replace local PyTorch/SentenceTransformers
HF_TOKEN = os.getenv("HF_TOKEN")
model_identifier = SENTENCE_TRANSFORMER_MODEL.split('/')[-1] if '/' in SENTENCE_TRANSFORMER_MODEL else SENTENCE_TRANSFORMER_MODEL
HF_API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{SENTENCE_TRANSFORMER_MODEL}"

# Live Streamlit App URL for OAuth redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://pubnp3sbcbnnwu.streamlit.app").rstrip("/")

class HuggingFaceEmbedder:
    """Lightweight API client for embeddings matching SentenceTransformer output structure."""
    def __init__(self, model_url: str, token: str | None = None):
        self.model_url = model_url
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def encode(self, sentences, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True):
        is_single = isinstance(sentences, str)
        if is_single:
            sentences = [sentences]

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self.model_url,
                headers=self.headers,
                json={"inputs": sentences, "options": {"wait_for_model": True}},
            )
            response.raise_for_status()
            data = response.json()

        arr = np.array(data)
        if convert_to_numpy:
            if normalize_embeddings:
                norm = np.linalg.norm(arr, axis=-1, keepdims=True)
                norm[norm == 0] = 1e-12
                arr = arr / norm
            return arr[0] if is_single else arr
        return data


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting ATS Resume Analyser API.......")
    import spacy

    primary_model = (SPACY_MODEL_PRIMARY or "en_core_web_sm").strip('\'"')
    secondary_model = (SPACY_MODEL_SECONDARY or "en_core_web_sm").strip('\'"')

    logger.info(f"Loading spaCy NLP model: {primary_model}")

    try:
        app.state.nlp = spacy.load(primary_model)
        logger.info(f"Loaded {primary_model}")
    except OSError:
        logger.warning(f"{primary_model} not found - falling back to {secondary_model}")
        try:
            app.state.nlp = spacy.load(secondary_model)
            logger.info(f"Loaded {secondary_model} (fallback)")
        except OSError:
            logger.warning("Fallback model failed. Defaulting to 'en_core_web_sm'")
            app.state.nlp = spacy.load("en_core_web_sm")

    logger.info(f"Connecting to Hugging Face Embedder: {SENTENCE_TRANSFORMER_MODEL}")
    app.state.embedder = HuggingFaceEmbedder(HF_API_URL, HF_TOKEN)
    logger.info("Embedder ready via Hugging Face API")

    logger.info("ALL models loaded. API is ready to serve requests")

    yield

    logger.info("shutting down the api!!")


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Fix CORS Settings for Browser Fetch Requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "online", "message": "ATS Resume Analyzer API is running!"}


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Catch OAuth callback parameters and redirect back to Streamlit UI."""
    query_params = str(request.query_params)
    redirect_url = (
        f"{FRONTEND_URL}?{query_params}"
        if query_params
        else FRONTEND_URL
    )
    return RedirectResponse(url=redirect_url)


app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
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
# Clean model name if passed as a full repo or path
model_identifier = SENTENCE_TRANSFORMER_MODEL.split('/')[-1] if '/' in SENTENCE_TRANSFORMER_MODEL else SENTENCE_TRANSFORMER_MODEL
HF_API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{SENTENCE_TRANSFORMER_MODEL}"

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

        # Format array into numpy array matching sentence-transformers format
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

    # Clean model strings to strip accidental quotes like '"en_core_web_sm'
    primary_model = (SPACY_MODEL_PRIMARY or "en_core_web_sm").strip('\'"')
    secondary_model = (SPACY_MODEL_SECONDARY or "en_core_web_sm").strip('\'"')

    logger.info(f"Loading spaCy NLP model: {primary_model}")

    try:
        app.state.nlp = spacy.load(primary_model)
        logger.info(f"Loaded {primary_model}")
    except OSError:
        logger.warning(
            f"{primary_model} not found - falling back to {secondary_model}"
        )
        try:
            app.state.nlp = spacy.load(secondary_model)
            logger.info(f"Loaded {secondary_model} (fallback)")
        except OSError:
            logger.warning("Fallback model failed. Defaulting to 'en_core_web_sm'")
            app.state.nlp = spacy.load("en_core_web_sm")

    # Lightweight embedder initialization
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

# Fix CORS Settings: Disable allow_credentials when wildcard '*' origins are used
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
        f"http://localhost:8501?{query_params}"
        if query_params
        else "http://localhost:8501"
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
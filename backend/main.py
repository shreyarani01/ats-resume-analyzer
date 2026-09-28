import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import httpx

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
HF_API_URL = f"https://api-inference.huggingface.co/models/{SENTENCE_TRANSFORMER_MODEL}"

class HuggingFaceEmbedder:
    """Lightweight API client for embeddings (uses ~0 MB RAM)."""
    def __init__(self, model_url: str, token: str | None = None):
        self.model_url = model_url
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def encode(self, sentences, show_progress_bar=False):
        if isinstance(sentences, str):
            sentences = [sentences]
            
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self.model_url,
                headers=self.headers,
                json={"inputs": sentences, "options": {"wait_for_model": True}},
            )
            response.raise_for_status()
            return response.json()


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
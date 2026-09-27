import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting ATS Resume Analyser API.......")
    logger.info(f"Loading spaCy NLP model: {SPACY_MODEL_PRIMARY}")
    import spacy

    try:
        app.state.nlp = spacy.load(SPACY_MODEL_PRIMARY)
        logger.info(f"Loaded {SPACY_MODEL_PRIMARY}")
    except OSError:
        logger.warning(
            f"{SPACY_MODEL_PRIMARY} not found - falling back to {SPACY_MODEL_SECONDARY}"
        )
        app.state.nlp = spacy.load(SPACY_MODEL_SECONDARY)
        logger.info(f"Loaded {SPACY_MODEL_SECONDARY}(fallback)")

    logger.info(f"Loading SentenceTransformer: {SENTENCE_TRANSFORMER_MODEL}")
    from sentence_transformers import SentenceTransformer

    app.state.embedder = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    logger.info(f"Loaded {SENTENCE_TRANSFORMER_MODEL}")

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
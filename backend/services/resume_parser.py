import os
import io
import logging
from typing import Dict, Any, Optional

import pdfplumber
import docx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

logger = logging.getLogger("ats_resume_scorer")

class FileParsingError(Exception):
    """Raised when text extraction from a file fails."""
    pass


class FileValidationError(Exception):
    """Raised when file type or file content validation fails."""
    pass
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber with pypdf fallback."""
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}. Trying pypdf fallback...")
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as fallback_err:
            logger.error(f"pypdf fallback failed: {fallback_err}")
            raise ValueError("Could not parse PDF content.")

    if not text.strip():
        raise ValueError("PDF file appears to be empty or contains scanned images without selectable text.")
    return text.strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX file using python-docx."""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        full_text = [para.text for para in doc.paragraphs if para.text.strip()]
        text = "\n".join(full_text)
        if not text.strip():
            raise ValueError("DOCX file contains no readable text.")
        return text.strip()
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        raise ValueError("Could not parse DOCX content.")


def validate_and_extract_text(file_bytes: bytes, filename: str) -> str:
    """Validate file extension and extract text without python-magic dependency."""
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith((".docx", ".doc")):
        return extract_text_from_docx(file_bytes)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a PDF or DOCX file."
        )
# 3. Main parser entry point expected by routes
def parse_resume_file(file_bytes: bytes, filename: str) -> str:
    """Validate extension and extract resume text cleanly without libmagic/python-magic."""
    if not file_bytes:
        raise FileValidationError("Uploaded file is empty.")

    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith((".docx", ".doc")):
        return extract_text_from_docx(file_bytes)
    else:
        raise FileValidationError("Unsupported file format. Please upload a PDF or DOCX file.")

@router.post("/analyze-resume")
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: Optional[str] = Form(""),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Analyze resume endpoint."""
    try:
        contents = await resume.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Extract text cleanly without python-magic
        extracted_text = validate_and_extract_text(contents, resume.filename)

        # Proceed with spaCy / Hugging Face analysis pipeline...
        return {
            "filename": resume.filename,
            "status": "success",
            "extracted_text_length": len(extracted_text),
            # Add your ATS scoring logic here
        }

    except ValueError as ve:
        raise HTTPException(status_code=422, detail=f"Could not read or parse the resume: {str(ve)}")
    except Exception as e:
        logger.error(f"Error processing resume: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal processing error: {str(e)}")
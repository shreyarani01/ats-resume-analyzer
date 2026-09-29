import io
import logging
from typing import Any, Dict, Tuple

import docx
import pdfplumber

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
            raise FileParsingError(
                f"Could not parse PDF content: {fallback_err}"
            )

    if not text.strip():
        raise FileParsingError(
            "PDF file appears to be empty or contains scanned images without selectable text."
        )
    return text.strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX file using python-docx."""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        full_text = [para.text for para in doc.paragraphs if para.text.strip()]
        text = "\n".join(full_text)
        if not text.strip():
            raise FileParsingError("DOCX file contains no readable text.")
        return text.strip()
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        raise FileParsingError(f"Could not parse DOCX content: {e}")


def parse_resume_file(file_bytes: bytes, filename: str) -> Tuple[str, Dict[str, Any], str]:
    """Validate extension and return 3 items: (extracted_text, metadata, file_extension)."""
    if not file_bytes:
        raise FileValidationError("Uploaded file is empty.")

    filename_lower = filename.lower()
    ext = filename_lower.rsplit(".", 1)[-1] if "." in filename_lower else ""
    
    if filename_lower.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith((".docx", ".doc")):
        text = extract_text_from_docx(file_bytes)
    else:
        raise FileValidationError("Unsupported file format. Please upload a PDF or DOCX file.")

    metadata = {
        "filename": filename,
        "size_bytes": len(file_bytes),
        "extension": ext
    }

    # Returns 3 items (text, metadata, extension) to match callers expecting 3 values
    return text, metadata, ext
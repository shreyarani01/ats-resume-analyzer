import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from backend.services.resume_parser import (
    FileParsingError,
    FileValidationError,
    parse_resume_file,
)

logger = logging.getLogger("ats_resume_scorer")

router = APIRouter(prefix="/api/v1", tags=["resume"])


@router.post("/parse-resume")
async def parse_resume_endpoint(file: UploadFile = File(...)):
    """Upload and parse a resume file (PDF or DOCX)."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded or filename is missing.",
        )

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise FileValidationError("Uploaded file is empty.")

        # Safely unpack EXACTLY 2 values (extracted_text, metadata)
        extracted_text, metadata = parse_resume_file(file_bytes, file.filename)

        return {
            "status": "success",
            "text": extracted_text,
            "metadata": metadata,
        }

    except (FileParsingError, FileValidationError) as err:
        logger.warning(f"File parsing error for {file.filename}: {err}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read or parse the resume: {str(err)}",
        )
    except Exception as err:
        logger.error(f"Unexpected error parsing resume {file.filename}: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the file: {str(err)}",
        )
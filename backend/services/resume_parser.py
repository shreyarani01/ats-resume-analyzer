import io
import logging
from typing import Any, Dict, Optional, Tuple

import docx
import pdfplumber
import PyPDF2
import puremagic

from backend.core.config import (
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    SUPPORTED_MIME_TYPES,
)
from backend.utils.file_utils import (
    FileParsingError,
    FileUploadError,
    TextExtractionError,
    log_error,
    log_info,
    log_warning,
    with_fallback,
)

logger = logging.getLogger("ats_resume_scorer")


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


def validate_resume_file(file_data: bytes, filename: str) -> Tuple[bool, str, Optional[str]]:
    """Validate file size and type cleanly, returning a guaranteed 3-element tuple."""
    file_size_bytes = len(file_data)

    if file_size_bytes == 0:
        return False, "Uploaded file is empty. Please check the file and try again.", None

    if file_size_bytes > MAX_FILE_SIZE_BYTES:
        size_mb = file_size_bytes / (1024 * 1024)
        return (
            False,
            f"File size ({size_mb:.2f} MB) exceeds maximum of {MAX_FILE_SIZE_MB} MB. "
            "Please upload a smaller file or compress your resume.",
            None,
        )

    filename_lower = filename.lower()
    file_type = None

    # Detect file type using puremagic with extension fallback
    try:
        matches = puremagic.from_string(file_data)
        if matches:
            detected_exts = [m[0].lower() for m in matches if m[0]]
            if ".pdf" in detected_exts:
                file_type = "pdf"
            elif ".docx" in detected_exts:
                file_type = "docx"
            elif ".doc" in detected_exts:
                file_type = "doc"
    except puremagic.PureError:
        logger.warning(f"puremagic failed for {filename}, falling back to file extension.")

    # Extension fallback
    if not file_type:
        if filename_lower.endswith(".pdf"):
            file_type = "pdf"
        elif filename_lower.endswith(".docx"):
            file_type = "docx"
        elif filename_lower.endswith(".doc"):
            file_type = "doc"

    if not file_type:
        return (
            False,
            "Unsupported file type. Please upload a PDF or DOCX file.",
            None,
        )

    return True, "", file_type


def _extract_pdf_hyperlinks(file_data: bytes) -> str:
    urls = []
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_data))
        for page in reader.pages:
            if "/Annots" not in page:
                continue
            for annot_ref in page["/Annots"]:
                try:
                    annot = annot_ref.get_object()
                    if annot.get("/Subtype") != "/Link":
                        continue
                    action = annot.get("/A", {})
                    uri = action.get("/URI", "")
                    if uri and isinstance(uri, (str, bytes)):
                        if isinstance(uri, bytes):
                            uri = uri.decode("utf-8", errors="ignore")
                        uri = uri.strip()
                        if uri.startswith("http"):
                            urls.append(uri)
                except Exception:
                    pass
    except Exception:
        pass
    return "\n".join(urls)


def _extract_pdf_with_pdfplumber(file_data: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(file_data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    if not text.strip():
        raise TextExtractionError(
            "pdfplumber extracted no text",
            user_message="No text could be extracted from the PDF.",
        )

    hyperlinks = _extract_pdf_hyperlinks(file_data)
    if hyperlinks:
        text = text.strip() + "\n" + hyperlinks

    return text.strip()


def _extract_pdf_with_pypdf2(file_data: bytes) -> str:
    text = ""
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    if not text.strip():
        raise TextExtractionError(
            "PyPDF2 extracted no text",
            user_message="No text could be extracted from the PDF.",
        )

    hyperlinks = _extract_pdf_hyperlinks(file_data)
    if hyperlinks:
        text = text.strip() + "\n" + hyperlinks

    return text.strip()


def extract_text_from_pdf(file_data: bytes) -> str:
    try:
        result, used_fallback = with_fallback(
            _extract_pdf_with_pdfplumber,
            _extract_pdf_with_pypdf2,
            file_data,
            log_fallback=True,
        )

        if used_fallback:
            log_info(
                "PDF EXTRACTION succeeded using the PyPDF2 fallback",
                context="resume_parser",
            )
        return result

    except Exception as e:
        log_error(e, context="extract_text_from_pdf")
        raise FileParsingError(
            "Failed to extract text from PDF using both pdfplumber and PyPDF2. "
            "The PDF may be corrupted, password-protected, or contain only scanned images. "
            "Please ensure it contains selectable text."
        ) from e


def extract_text_from_docx(file_data: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_data))
        text_parts = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_parts.append(cell.text)

        text = "\n".join(text_parts)

        if not text.strip():
            raise FileParsingError(
                "No text could be extracted from the document. "
                "The document may be empty or corrupted."
            )

        try:
            for rel in doc.part.rels.values():
                if "hyperlink" in rel.reltype.lower():
                    url = rel._target
                    if isinstance(url, str) and url.startswith("http"):
                        text += "\n" + url
        except Exception:
            pass

        log_info(f"Extracted {len(text)} chars from DOCX", context="resume_parser")
        return text.strip()

    except FileParsingError:
        raise

    except Exception as e:
        log_error(e, context="extract_text_from_docx")
        raise FileParsingError(
            "Failed to extract text from DOCX. "
            "The document may be corrupted or in an unsupported format. "
            "Please try re-saving or converting to PDF."
        ) from e


def extract_text_from_doc(file_data: bytes) -> str:
    raise FileParsingError(
        "Legacy .doc format is not supported. "
        "Please convert your document to .docx or .pdf and try again."
    )


def extract_text(file_data: bytes, file_type: str) -> str:
    if file_type == "pdf":
        return extract_text_from_pdf(file_data)
    elif file_type == "docx":
        return extract_text_from_docx(file_data)
    elif file_type == "doc":
        return extract_text_from_doc(file_data)
    else:
        raise FileValidationError(
            f"Invalid file type: {file_type}. Supported types are: pdf, docx, and doc"
        )


def parse_resume_file(file_data: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
    log_info(f"Parsing file: {filename}", context="parse_resume_file")

    # Phase 01: Validate file using renamed function
    try:
        is_valid, error_msg, file_type = validate_resume_file(file_data, filename)
        if not is_valid:
            log_warning(f"Validation failed for file {filename}", context="parse_resume_file")
            raise FileValidationError(error_msg)

    except FileValidationError:
        raise

    except Exception as e:
        log_error(e, context="parse_resume_file_validation")
        raise FileValidationError(
            "Could not validate the uploaded file. Please ensure it is a valid PDF or DOCX."
        ) from e

    # Phase 02: Extract text from file
    try:
        text = extract_text(file_data, file_type)
        log_info(f"Extracted {len(text)} chars from {filename}", context="parse_resume_file")

    except FileParsingError:
        raise

    except Exception as e:
        log_error(e, context="parse_resume_file_extraction")
        raise FileParsingError(
            "An unexpected error occurred while processing the file. "
            "Please try again or contact support if the problem persists."
        ) from e

    metadata = {
        "filename": filename,
        "file_type": file_type,
        "file_size_bytes": len(file_data),
        "text_length": len(text),
        "success": True,
    }

    return text, metadata
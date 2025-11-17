"""
Document upload endpoint for MVP_0.
Accepts PDF, TXT files, or pasted text content.
"""

import uuid
from datetime import datetime
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import pdfplumber
from PyPDF2 import PdfReader

from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

# In-memory session storage (no database for hackathon MVP_0)
# In production, use Redis or database
sessions = {}


class UploadResponse(BaseModel):
    session_id: str
    filename: Optional[str]
    text_length: int
    text_preview: str
    created_at: str


class TextUploadRequest(BaseModel):
    text: str
    title: Optional[str] = "Pasted Text"


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(None), text_content: Optional[str] = Form(None)):
    """
    Upload a document (PDF, TXT) or paste text directly.

    Returns:
        - session_id: Unique identifier for this upload session
        - text_preview: First 500 characters of extracted text
        - text_length: Total character count
    """

    try:
        extracted_text = ""
        filename = None

        # Case 1: File upload (PDF or TXT)
        if file:
            filename = file.filename
            file_content = await file.read()

            # Handle PDF files
            if filename.lower().endswith('.pdf'):
                logger.info("extracting_pdf", filename=filename)
                extracted_text = extract_text_from_pdf(file_content)

            # Handle TXT files
            elif filename.lower().endswith('.txt'):
                logger.info("extracting_txt", filename=filename)
                extracted_text = file_content.decode('utf-8', errors='ignore')

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type. Please upload PDF or TXT files."
                )

        # Case 2: Pasted text
        elif text_content:
            logger.info("processing_pasted_text")
            extracted_text = text_content.strip()
            filename = "Pasted Text"

        else:
            raise HTTPException(
                status_code=400,
                detail="Please provide either a file or text content"
            )

        # Validate extracted text
        if not extracted_text or len(extracted_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Document is too short or empty. Please provide at least 50 characters."
            )

        # Create session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            'text': extracted_text,
            'filename': filename,
            'created_at': datetime.now(),
            'text_length': len(extracted_text)
        }

        logger.info(
            "document_uploaded",
            session_id=session_id,
            filename=filename,
            text_length=len(extracted_text)
        )

        return UploadResponse(
            session_id=session_id,
            filename=filename,
            text_length=len(extracted_text),
            text_preview=extracted_text[:500],
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("upload_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )


@router.post("/upload/text", response_model=UploadResponse)
async def upload_text(request: TextUploadRequest):
    """
    Alternative endpoint for pasting text directly (JSON body).
    """
    text = request.text.strip()

    if not text or len(text) < 50:
        raise HTTPException(
            status_code=400,
            detail="Text is too short. Please provide at least 50 characters."
        )

    # Create session
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'text': text,
        'filename': request.title,
        'created_at': datetime.now(),
        'text_length': len(text)
    }

    logger.info(
        "text_uploaded",
        session_id=session_id,
        title=request.title,
        text_length=len(text)
    )

    return UploadResponse(
        session_id=session_id,
        filename=request.title,
        text_length=len(text),
        text_preview=text[:500],
        created_at=datetime.now().isoformat()
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Retrieve session data by session_id.
    """
    if session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired"
        )

    session = sessions[session_id]

    return {
        "session_id": session_id,
        "filename": session['filename'],
        "text_length": session['text_length'],
        "text_preview": session['text'][:500],
        "created_at": session['created_at'].isoformat()
    }


def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from PDF using pdfplumber (primary) with PyPDF2 fallback.

    Args:
        file_content: PDF file bytes

    Returns:
        Extracted text as string
    """
    try:
        # Try pdfplumber first (better for complex PDFs)
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            full_text = "\n\n".join(text_parts)

            if full_text.strip():
                logger.info("pdf_extracted_with_pdfplumber", pages=len(pdf.pages))
                return full_text

    except Exception as e:
        logger.warning("pdfplumber_failed", error=str(e))

    # Fallback to PyPDF2
    try:
        pdf_reader = PdfReader(BytesIO(file_content))
        text_parts = []

        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n\n".join(text_parts)

        if full_text.strip():
            logger.info("pdf_extracted_with_pypdf2", pages=len(pdf_reader.pages))
            return full_text
        else:
            raise ValueError("No text could be extracted from PDF")

    except Exception as e:
        logger.error("pdf_extraction_failed", error=str(e))
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


# Session cleanup (optional - runs on startup)
def cleanup_old_sessions(max_age_hours: int = 24):
    """
    Remove sessions older than max_age_hours.
    In production, use a background task scheduler.
    """
    now = datetime.now()
    expired_sessions = []

    for session_id, session_data in sessions.items():
        age = (now - session_data['created_at']).total_seconds() / 3600
        if age > max_age_hours:
            expired_sessions.append(session_id)

    for session_id in expired_sessions:
        del sessions[session_id]
        logger.info("session_expired", session_id=session_id)

    return len(expired_sessions)

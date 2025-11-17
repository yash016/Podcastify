"""
Outline generation endpoints.
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import OutlineRequest, OutlineResponse
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/outline", response_model=OutlineResponse)
async def generate_outline(request: OutlineRequest):
    """
    Generate 2-3 outline options for the requested topic.

    This endpoint uses the LLM to create scaffolded, Socratic outlines
    based on the topic, level, and duration specified.
    """
    logger.info(
        "outline_generation_requested",
        topic=request.topic,
        level=request.level,
        duration=request.duration,
    )

    # TODO: Implement outline generation logic
    # 1. Call LLM service with outline generation prompt
    # 2. Generate 2-3 different outline options
    # 3. Store in database with outline_id
    # 4. Return options

    raise HTTPException(
        status_code=501,
        detail="Outline generation not yet implemented",
    )

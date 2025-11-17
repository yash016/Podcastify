"""
Episode generation and retrieval endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import (
    EpisodeRequest,
    EpisodeStatusResponse,
    TranscriptResponse,
    DeepDiveRequest,
    DeepDiveResponse,
)
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/episode")
async def create_episode(request: EpisodeRequest, background_tasks: BackgroundTasks):
    """
    Create a new episode based on the selected outline.

    This queues a background job that:
    1. Researches the topic
    2. Generates dialogue
    3. Creates audio with TTS
    4. Returns a job_id for status polling
    """
    logger.info(
        "episode_creation_requested",
        outline_id=request.outline_id,
        outline_title=request.selected_outline.title,
    )

    # TODO: Implement episode creation
    # 1. Queue job in Redis/RQ
    # 2. Return job_id

    raise HTTPException(
        status_code=501,
        detail="Episode creation not yet implemented",
    )


@router.get("/episode/{job_id}/status", response_model=EpisodeStatusResponse)
async def get_episode_status(job_id: str):
    """
    Get the current status of an episode generation job.
    """
    logger.info("status_check", job_id=job_id)

    # TODO: Implement status check
    # 1. Query job status from Redis/RQ
    # 2. Return current progress

    raise HTTPException(
        status_code=501,
        detail="Status check not yet implemented",
    )


@router.get("/episode/{job_id}/audio")
async def get_episode_audio(job_id: str):
    """
    Stream the generated audio file.
    """
    logger.info("audio_download", job_id=job_id)

    # TODO: Implement audio retrieval
    # 1. Check if episode is completed
    # 2. Stream audio file

    raise HTTPException(
        status_code=501,
        detail="Audio retrieval not yet implemented",
    )


@router.get("/episode/{job_id}/transcript", response_model=TranscriptResponse)
async def get_episode_transcript(job_id: str):
    """
    Get the structured transcript with timing information.
    """
    logger.info("transcript_request", job_id=job_id)

    # TODO: Implement transcript retrieval
    # 1. Fetch from database
    # 2. Return structured segments

    raise HTTPException(
        status_code=501,
        detail="Transcript retrieval not yet implemented",
    )


@router.post("/episode/{episode_id}/deep-dive", response_model=DeepDiveResponse)
async def create_deep_dive(episode_id: str, request: DeepDiveRequest):
    """
    Generate a deep-dive answer for a specific section.

    This is the killer feature that NotebookLM doesn't have!
    """
    logger.info(
        "deep_dive_requested",
        episode_id=episode_id,
        section_id=request.section_id,
        question=request.user_question,
    )

    # TODO: Implement deep-dive generation
    # 1. Retrieve section context
    # 2. Retrieve RAG chunks for that section
    # 3. Optional: New web search
    # 4. Generate Socratic answer
    # 5. Optional: TTS for audio format

    raise HTTPException(
        status_code=501,
        detail="Deep-dive not yet implemented",
    )

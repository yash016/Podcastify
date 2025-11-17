"""
Pydantic schemas for request/response models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class LevelEnum(str, Enum):
    """Learning level options."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class OutlineSection(BaseModel):
    """A section within an episode outline."""
    title: str
    description: str
    learning_outcomes: List[str] = []


class Outline(BaseModel):
    """Episode outline structure."""
    title: str
    description: str
    sections: List[OutlineSection]
    estimated_duration_min: int


class OutlineRequest(BaseModel):
    """Request to generate episode outlines."""
    topic: str = Field(..., min_length=3, max_length=500)
    level: LevelEnum
    duration: int = Field(..., ge=5, le=20)
    custom_outline: Optional[str] = None


class OutlineResponse(BaseModel):
    """Response with multiple outline options."""
    outline_id: str
    options: List[Outline]


class EpisodeRequest(BaseModel):
    """Request to generate an episode."""
    outline_id: str
    selected_outline: Outline


class JobStatus(str, Enum):
    """Job processing status."""
    QUEUED = "queued"
    RESEARCHING = "researching"
    WRITING = "writing"
    GENERATING_AUDIO = "generating_audio"
    COMPLETED = "completed"
    FAILED = "failed"


class EpisodeStatusResponse(BaseModel):
    """Episode generation status."""
    job_id: str
    status: JobStatus
    progress: float = Field(..., ge=0, le=100)
    current_step: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None


class Speaker(str, Enum):
    """Podcast speaker."""
    BRAINY = "Brainy"
    SNARKY = "Snarky"


class TranscriptSegment(BaseModel):
    """A single dialogue segment."""
    speaker: Speaker
    text: str
    start_time: float  # seconds
    end_time: float  # seconds
    section_id: Optional[str] = None


class TranscriptResponse(BaseModel):
    """Full episode transcript."""
    episode_id: str
    segments: List[TranscriptSegment]
    total_duration: float


class DeepDiveRequest(BaseModel):
    """Request for deep-dive explanation."""
    section_id: str
    user_question: str = Field(..., min_length=3, max_length=500)
    format: str = "text"  # "text" | "audio" | "mini-episode"


class DeepDiveResponse(BaseModel):
    """Deep-dive answer response."""
    answer_text: str
    answer_audio_url: Optional[str] = None
    related_sections: List[str] = []


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    environment: str

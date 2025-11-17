"""
Quiz Session Model - Tracks quiz state, attempts, and Interactive Learning Mode progress.

State Machine:
NOT_STARTED → IN_PROGRESS → (LEARNING_MODE) → COMPLETED
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel


class QuizStatus(str, Enum):
    """Overall quiz session status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    LEARNING_MODE = "learning_mode"  # Interactive Learning Mode active
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class QuestionStatus(str, Enum):
    """Individual question status."""
    NOT_ATTEMPTED = "not_attempted"
    IN_PROGRESS = "in_progress"
    CORRECT = "correct"
    LEARNING_MODE = "learning_mode"
    SKIPPED = "skipped"


class QuestionAttempt(BaseModel):
    """A single attempt at answering a question."""
    selected_option: str  # Option ID (a, b, c, d)
    is_correct: bool
    timestamp: datetime
    time_spent_seconds: Optional[float] = None


class CheckpointProgress(BaseModel):
    """Progress through a learning checkpoint."""
    checkpoint_id: str
    status: str  # "not_started", "in_progress", "completed"
    conversation_history: List[Dict[str, str]] = []  # [{"question": "...", "answer": "..."}]
    current_hint_level: int = 0
    attempts: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class QuestionProgress(BaseModel):
    """Progress on a single question."""
    question_id: str
    status: QuestionStatus = QuestionStatus.NOT_ATTEMPTED
    attempts: List[QuestionAttempt] = []
    hints_used: List[int] = []  # [1, 2] means Level 1 and Level 2 hints used
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Learning Mode tracking
    in_learning_mode: bool = False
    learning_mode_checkpoints: List[CheckpointProgress] = []
    current_checkpoint_index: int = 0


class QuizSession(BaseModel):
    """Complete quiz session state."""
    session_id: str
    episode_id: str  # Link back to podcast episode
    user_id: Optional[str] = None  # For future user tracking

    # Quiz content
    questions: List[Dict[str, Any]] = []  # Full question objects
    concepts: List[Dict[str, Any]] = []  # Concepts from document
    document_text: str = ""  # For context in learning mode

    # Progress tracking
    status: QuizStatus = QuizStatus.NOT_STARTED
    current_question_index: int = 0
    question_progress: List[QuestionProgress] = []

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Stats
    score: int = 0  # Correct answers
    total_questions: int = 0
    hints_used_total: int = 0
    learning_mode_triggered_count: int = 0

    # Metadata
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


# In-memory storage for quiz sessions (replace with DB in production)
quiz_sessions: Dict[str, QuizSession] = {}


def create_quiz_session(
    session_id: str,
    episode_id: str,
    questions: List[Dict[str, Any]],
    concepts: List[Dict[str, Any]],
    document_text: str
) -> QuizSession:
    """
    Create a new quiz session.

    Args:
        session_id: Unique session ID
        episode_id: Associated podcast episode ID
        questions: List of quiz questions
        concepts: List of concepts from document
        document_text: Full document text

    Returns:
        QuizSession instance
    """
    quiz_session = QuizSession(
        session_id=session_id,
        episode_id=episode_id,
        questions=questions,
        concepts=concepts,
        document_text=document_text,
        total_questions=len(questions),
        question_progress=[
            QuestionProgress(question_id=q['question_id'])
            for q in questions
        ]
    )

    quiz_sessions[session_id] = quiz_session
    return quiz_session


def get_quiz_session(session_id: str) -> Optional[QuizSession]:
    """Get quiz session by ID."""
    return quiz_sessions.get(session_id)


def update_quiz_session(session_id: str, quiz_session: QuizSession):
    """Update quiz session."""
    quiz_session.updated_at = datetime.now()
    quiz_sessions[session_id] = quiz_session


def start_quiz(session_id: str) -> QuizSession:
    """Mark quiz as started."""
    quiz_session = quiz_sessions[session_id]
    quiz_session.status = QuizStatus.IN_PROGRESS
    quiz_session.started_at = datetime.now()
    quiz_session.updated_at = datetime.now()

    # Mark first question as in progress
    if quiz_session.question_progress:
        quiz_session.question_progress[0].status = QuestionStatus.IN_PROGRESS
        quiz_session.question_progress[0].started_at = datetime.now()

    quiz_sessions[session_id] = quiz_session
    return quiz_session


def record_attempt(
    session_id: str,
    question_id: str,
    selected_option: str,
    is_correct: bool,
    time_spent_seconds: Optional[float] = None
) -> QuizSession:
    """Record a question attempt."""
    quiz_session = quiz_sessions[session_id]

    # Find question progress
    q_progress = next(
        (qp for qp in quiz_session.question_progress if qp.question_id == question_id),
        None
    )

    if q_progress:
        # Add attempt
        attempt = QuestionAttempt(
            selected_option=selected_option,
            is_correct=is_correct,
            timestamp=datetime.now(),
            time_spent_seconds=time_spent_seconds
        )
        q_progress.attempts.append(attempt)

        # Update status
        if is_correct:
            q_progress.status = QuestionStatus.CORRECT
            q_progress.completed_at = datetime.now()
            quiz_session.score += 1

    quiz_session.updated_at = datetime.now()
    quiz_sessions[session_id] = quiz_session
    return quiz_session


def enter_learning_mode(
    session_id: str,
    question_id: str,
    checkpoints: List[Dict[str, Any]]
) -> QuizSession:
    """Enter Interactive Learning Mode for a question."""
    quiz_session = quiz_sessions[session_id]
    quiz_session.status = QuizStatus.LEARNING_MODE
    quiz_session.learning_mode_triggered_count += 1

    # Find question progress
    q_progress = next(
        (qp for qp in quiz_session.question_progress if qp.question_id == question_id),
        None
    )

    if q_progress:
        q_progress.status = QuestionStatus.LEARNING_MODE
        q_progress.in_learning_mode = True
        q_progress.learning_mode_checkpoints = [
            CheckpointProgress(
                checkpoint_id=cp['checkpoint_id'],
                status="not_started"
            )
            for cp in checkpoints
        ]
        q_progress.current_checkpoint_index = 0

        # Mark first checkpoint as in progress
        if q_progress.learning_mode_checkpoints:
            q_progress.learning_mode_checkpoints[0].status = "in_progress"
            q_progress.learning_mode_checkpoints[0].started_at = datetime.now()

    quiz_session.updated_at = datetime.now()
    quiz_sessions[session_id] = quiz_session
    return quiz_session


def exit_learning_mode(session_id: str, question_id: str) -> QuizSession:
    """Exit Learning Mode and return to normal quiz."""
    quiz_session = quiz_sessions[session_id]
    quiz_session.status = QuizStatus.IN_PROGRESS

    # Find question progress
    q_progress = next(
        (qp for qp in quiz_session.question_progress if qp.question_id == question_id),
        None
    )

    if q_progress:
        q_progress.in_learning_mode = False
        # Keep question in progress so user can try again
        q_progress.status = QuestionStatus.IN_PROGRESS

    quiz_session.updated_at = datetime.now()
    quiz_sessions[session_id] = quiz_session
    return quiz_session


def complete_quiz(session_id: str) -> QuizSession:
    """Mark quiz as completed."""
    quiz_session = quiz_sessions[session_id]
    quiz_session.status = QuizStatus.COMPLETED
    quiz_session.completed_at = datetime.now()
    quiz_session.updated_at = datetime.now()

    quiz_sessions[session_id] = quiz_session
    return quiz_session

"""
Quiz API endpoints for interactive learning with Progressive Socratic Questioning.

Endpoints:
- POST /quiz/generate - Generate quiz from uploaded document
- POST /quiz/submit-answer - Submit answer and get feedback/hints
- POST /quiz/enter-learning-mode - Enter Interactive Learning Mode after 3 wrong attempts
- POST /quiz/checkpoint-response - Respond to Socratic checkpoint question
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm import llm_service
from app.services.quiz_generator import init_quiz_generator
from app.services.learning_coach import init_learning_coach
from app.services.struggle_detector import struggle_detector
from app.services.socratic_hint_generator import init_socratic_hint_generator
from app.core.logging_config import get_logger

# Import sessions from upload endpoint to get document text
from app.api.endpoints.upload import sessions

# Import quiz session functions
from app.models.quiz_session import (
    create_quiz_session,
    get_quiz_session,
    start_quiz,
    record_attempt,
    enter_learning_mode,
    exit_learning_mode,
    complete_quiz,
    QuizStatus,
    QuestionStatus
)

router = APIRouter()
logger = get_logger(__name__)

# Initialize services
quiz_generator = init_quiz_generator(llm_service)
learning_coach = init_learning_coach(llm_service)
socratic_hint_gen = init_socratic_hint_generator(llm_service)


# Request/Response Models

class GenerateQuizRequest(BaseModel):
    session_id: str  # Upload session ID to get document
    question_count: int = 5  # Default 5 questions


class GenerateQuizResponse(BaseModel):
    quiz_session_id: str
    questions: List[Dict[str, Any]]
    total_questions: int
    message: str


class SubmitAnswerRequest(BaseModel):
    quiz_session_id: str
    question_id: str
    selected_option: str  # a, b, c, d
    time_spent_seconds: Optional[float] = None


class SubmitAnswerResponse(BaseModel):
    is_correct: bool
    feedback: str
    hint: Optional[Dict[str, Any]] = None  # If wrong: {level, text} - legacy format
    should_trigger_learning_mode: bool
    struggle_analysis: Optional[Dict[str, Any]] = None
    correct_answer: Optional[str] = None  # Only if 3+ wrong attempts
    explanation: Optional[str] = None  # Only if 3+ wrong attempts
    next_question_id: Optional[str] = None  # If correct, show next question

    # NEW: Enhanced Socratic hint fields
    current_hint_level: Optional[int] = None  # 1, 2, or 3
    socratic_hint: Optional[Dict[str, Any]] = None  # Current Socratic hint data
    all_hints_available: Optional[List[int]] = None  # [1, 2, 3] - available hint levels

    # NEW: Question navigation
    current_question_index: Optional[int] = None
    total_questions: Optional[int] = None
    has_previous_question: bool = False
    has_next_question: bool = False


class GetHintRequest(BaseModel):
    quiz_session_id: str
    question_id: str
    hint_level: int  # 1, 2, or 3
    selected_option: str  # User's current wrong answer


class GetHintResponse(BaseModel):
    hint_level: int
    socratic_hint: Dict[str, Any]
    message: str


class NavigateQuestionRequest(BaseModel):
    quiz_session_id: str
    direction: str  # "previous" or "next" or "jump"
    target_question_index: Optional[int] = None  # For "jump" direction


class NavigateQuestionResponse(BaseModel):
    question: Dict[str, Any]
    question_index: int  # 1-indexed
    total_questions: int
    has_previous: bool
    has_next: bool
    message: str


class EnterLearningModeRequest(BaseModel):
    quiz_session_id: str
    question_id: str


class EnterLearningModeResponse(BaseModel):
    message: str
    checkpoints: List[Dict[str, Any]]
    current_checkpoint: Dict[str, Any]
    total_checkpoints: int


class CheckpointResponseRequest(BaseModel):
    quiz_session_id: str
    question_id: str
    checkpoint_id: str
    user_response: str


class CheckpointResponseResponse(BaseModel):
    feedback: str
    hint: Optional[Dict[str, Any]] = None
    should_advance: bool
    next_checkpoint: Optional[Dict[str, Any]] = None
    learning_complete: bool  # True if all checkpoints done


# Endpoints

@router.post("/quiz/generate", response_model=GenerateQuizResponse)
async def generate_quiz(request: GenerateQuizRequest):
    """
    Generate a quiz from uploaded document concepts.

    Flow:
    1. Get document from upload session
    2. Extract concepts (should already exist from generate endpoint)
    3. Generate quiz questions from concepts
    4. Create quiz session
    """
    logger.info("quiz_generate_request", session_id=request.session_id)

    # Get upload session
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session_data = sessions[request.session_id]
    document_text = session_data['text']
    filename = session_data['filename']

    # Get concepts (if they exist from a previous generate call)
    # For MVP, we'll extract concepts fresh here
    from app.services.concept_extractor import init_concept_extractor

    try:
        # Extract concepts
        logger.info("extracting_concepts_for_quiz")
        extractor = init_concept_extractor(llm_service)
        concepts = await extractor.extract_concepts_from_document(
            document_text=document_text,
            target_count=10
        )

        # DEBUG: Log concepts type and structure
        logger.info(
            "concepts_extracted_debug",
            concepts_type=type(concepts).__name__,
            concepts_length=len(concepts) if isinstance(concepts, list) else "N/A",
            first_concept_type=type(concepts[0]).__name__ if isinstance(concepts, list) and len(concepts) > 0 else "N/A",
            first_concept_preview=str(concepts[0])[:200] if isinstance(concepts, list) and len(concepts) > 0 else "N/A",
            concepts_preview=str(concepts)[:300]
        )

        # Validate concepts structure before passing to quiz generator
        if not isinstance(concepts, list):
            logger.error(
                "quiz_concepts_not_list",
                type=type(concepts).__name__,
                data=str(concepts)[:300]
            )
            raise ValueError(f"Expected list of concepts but got {type(concepts).__name__}")

        if len(concepts) > 0 and not isinstance(concepts[0], dict):
            logger.error(
                "quiz_concepts_not_dicts",
                first_type=type(concepts[0]).__name__,
                first_item=str(concepts[0])[:200],
                all_types=[type(c).__name__ for c in concepts[:3]]
            )
            raise ValueError(f"Expected list of dicts but got list of {type(concepts[0]).__name__}")

        # Generate quiz questions
        logger.info("generating_quiz_questions", target_count=request.question_count)
        questions = await quiz_generator.generate_quiz(
            concepts=concepts,
            document_text=document_text,
            target_question_count=request.question_count
        )

        # Create quiz session
        quiz_session_id = f"quiz_{uuid.uuid4().hex[:12]}"
        quiz_session = create_quiz_session(
            session_id=quiz_session_id,
            episode_id=request.session_id,  # Link to upload session
            questions=questions,
            concepts=concepts,
            document_text=document_text
        )

        # Start quiz
        start_quiz(quiz_session_id)

        logger.info(
            "quiz_generated_successfully",
            quiz_session_id=quiz_session_id,
            question_count=len(questions),
            concept_count=len(concepts)
        )

        return GenerateQuizResponse(
            quiz_session_id=quiz_session_id,
            questions=questions,
            total_questions=len(questions),
            message=f"Generated {len(questions)} questions from {filename}"
        )

    except Exception as e:
        logger.error("quiz_generation_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quiz: {str(e)}"
        )


@router.post("/quiz/submit-answer", response_model=SubmitAnswerResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """
    Submit an answer to a quiz question.

    Flow:
    1. Record attempt
    2. Check if correct
    3. If wrong:
       a. Analyze struggle level
       b. Provide graduated hint (Level 1, 2, or 3)
       c. If 3+ wrong attempts, suggest Interactive Learning Mode
    4. If correct, move to next question
    """
    logger.info(
        "answer_submission",
        quiz_session_id=request.quiz_session_id,
        question_id=request.question_id,
        selected_option=request.selected_option
    )

    # Get quiz session
    quiz_session = get_quiz_session(request.quiz_session_id)
    if not quiz_session:
        raise HTTPException(status_code=404, detail="Quiz session not found")

    # Get question
    question = next(
        (q for q in quiz_session.questions if q['question_id'] == request.question_id),
        None
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check if correct
    correct_answer = question['correct_answer']
    is_correct = request.selected_option == correct_answer

    # Record attempt
    record_attempt(
        session_id=request.quiz_session_id,
        question_id=request.question_id,
        selected_option=request.selected_option,
        is_correct=is_correct,
        time_spent_seconds=request.time_spent_seconds
    )

    # Refresh quiz session after recording
    quiz_session = get_quiz_session(request.quiz_session_id)

    # Get question progress
    q_progress = next(
        (qp for qp in quiz_session.question_progress if qp.question_id == request.question_id),
        None
    )

    if is_correct:
        # Correct answer - move to next question
        logger.info("answer_correct", question_id=request.question_id)

        # Find next question
        next_q_id = None
        if quiz_session.current_question_index < len(quiz_session.questions) - 1:
            quiz_session.current_question_index += 1
            next_q = quiz_session.questions[quiz_session.current_question_index]
            next_q_id = next_q['question_id']

            # Mark next question as in progress
            next_q_progress = quiz_session.question_progress[quiz_session.current_question_index]
            next_q_progress.status = QuestionStatus.IN_PROGRESS
            next_q_progress.started_at = datetime.now()
        else:
            # Quiz completed
            complete_quiz(request.quiz_session_id)

        return SubmitAnswerResponse(
            is_correct=True,
            feedback="Correct! Well done.",
            next_question_id=next_q_id,
            should_trigger_learning_mode=False
        )

    else:
        # Wrong answer - analyze struggle and provide Socratic hint
        logger.info("answer_incorrect", question_id=request.question_id)

        # Convert attempts to format expected by struggle detector
        attempts_data = [
            {
                "selected_option": a.selected_option,
                "is_correct": a.is_correct,
                "timestamp": a.timestamp
            }
            for a in q_progress.attempts
        ]

        # Analyze struggle
        struggle_analysis = struggle_detector.analyze_attempts(
            attempts=attempts_data,
            question=question,
            time_spent_seconds=request.time_spent_seconds
        )

        should_trigger_learning = struggle_analysis['should_trigger_learning_mode']
        wrong_count = struggle_analysis['wrong_attempt_count']

        # Determine hint level
        if wrong_count == 1:
            hint_level = 1
        elif wrong_count == 2:
            hint_level = 2
        else:
            hint_level = 3

        # Get legacy hint (fallback)
        hints = question.get('hints', [])
        hint_obj = next(
            (h for h in hints if h['level'] == hint_level),
            hints[-1] if hints else {"level": 3, "type": "explicit", "text": "Try again!"}
        )

        # NEW: Generate dynamic Socratic hint analyzing their specific wrong answer
        socratic_hint = None
        try:
            socratic_hint = await socratic_hint_gen.generate_socratic_hint(
                question=question,
                selected_option=request.selected_option,
                hint_level=hint_level,
                document_context=quiz_session.document_text,
                use_web_search=True
            )
            logger.info("socratic_hint_generated_for_submission", hint_level=hint_level)
        except Exception as e:
            logger.error("socratic_hint_generation_failed_in_submit", error=str(e))
            # Fall back to legacy hint if Socratic generation fails

        # Track hint usage
        if hint_level not in q_progress.hints_used:
            q_progress.hints_used.append(hint_level)
            quiz_session.hints_used_total += 1

        # NEW: Calculate navigation metadata
        current_idx = quiz_session.current_question_index
        total_q = len(quiz_session.questions)
        has_prev = current_idx > 0
        has_next = current_idx < total_q - 1

        response = SubmitAnswerResponse(
            is_correct=False,
            feedback=f"Not quite. Let's explore why.",
            hint=hint_obj,  # Legacy hint
            should_trigger_learning_mode=should_trigger_learning,
            struggle_analysis=struggle_analysis,
            # NEW: Socratic hint data
            current_hint_level=hint_level,
            socratic_hint=socratic_hint,
            all_hints_available=[1, 2, 3],
            # NEW: Navigation data
            current_question_index=current_idx + 1,  # 1-indexed for display
            total_questions=total_q,
            has_previous_question=has_prev,
            has_next_question=has_next
        )

        # If 3+ wrong attempts, reveal answer and explanation
        if wrong_count >= 3:
            response.correct_answer = correct_answer
            response.explanation = question.get('explanation', '')
            response.feedback = "After 3 attempts, let's review the correct answer. Consider entering Interactive Learning Mode to build deeper understanding."

        logger.info(
            "hint_provided_with_socratic",
            question_id=request.question_id,
            hint_level=hint_level,
            should_trigger_learning=should_trigger_learning,
            socratic_generated=socratic_hint is not None
        )

        return response


@router.post("/quiz/get-hint", response_model=GetHintResponse)
async def get_hint(request: GetHintRequest):
    """
    Get a specific hint level on demand.

    Allows users to navigate between hint levels (1, 2, 3) to get different
    degrees of help with their Socratic questions.
    """
    logger.info(
        "get_hint_request",
        quiz_session_id=request.quiz_session_id,
        question_id=request.question_id,
        hint_level=request.hint_level
    )

    # Get quiz session
    quiz_session = get_quiz_session(request.quiz_session_id)
    if not quiz_session:
        raise HTTPException(status_code=404, detail="Quiz session not found")

    # Get question
    question = next(
        (q for q in quiz_session.questions if q['question_id'] == request.question_id),
        None
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Validate hint level
    if request.hint_level not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Hint level must be 1, 2, or 3")

    try:
        # Generate Socratic hint for requested level
        socratic_hint = await socratic_hint_gen.generate_socratic_hint(
            question=question,
            selected_option=request.selected_option,
            hint_level=request.hint_level,
            document_context=quiz_session.document_text,
            use_web_search=True
        )

        logger.info(
            "hint_generated_on_demand",
            question_id=request.question_id,
            hint_level=request.hint_level
        )

        return GetHintResponse(
            hint_level=request.hint_level,
            socratic_hint=socratic_hint,
            message=f"Level {request.hint_level} hint generated"
        )

    except Exception as e:
        logger.error("get_hint_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate hint: {str(e)}"
        )


@router.post("/quiz/navigate-question", response_model=NavigateQuestionResponse)
async def navigate_question(request: NavigateQuestionRequest):
    """
    Navigate between quiz questions (previous/next/jump).

    Allows users to review previous questions or skip to specific questions.
    """
    logger.info(
        "navigate_question_request",
        quiz_session_id=request.quiz_session_id,
        direction=request.direction
    )

    # Get quiz session
    quiz_session = get_quiz_session(request.quiz_session_id)
    if not quiz_session:
        raise HTTPException(status_code=404, detail="Quiz session not found")

    current_idx = quiz_session.current_question_index
    total_q = len(quiz_session.questions)

    # Calculate new index based on direction
    new_idx = current_idx
    if request.direction == "next":
        if current_idx < total_q - 1:
            new_idx = current_idx + 1
        else:
            raise HTTPException(status_code=400, detail="Already at last question")
    elif request.direction == "previous":
        if current_idx > 0:
            new_idx = current_idx - 1
        else:
            raise HTTPException(status_code=400, detail="Already at first question")
    elif request.direction == "jump":
        if request.target_question_index is None:
            raise HTTPException(status_code=400, detail="target_question_index required for jump")
        # Convert from 1-indexed to 0-indexed
        new_idx = request.target_question_index - 1
        if new_idx < 0 or new_idx >= total_q:
            raise HTTPException(status_code=400, detail=f"Invalid question index: must be 1-{total_q}")
    else:
        raise HTTPException(status_code=400, detail="direction must be 'next', 'previous', or 'jump'")

    # Update current question index
    quiz_session.current_question_index = new_idx
    question = quiz_session.questions[new_idx]

    # Update question progress if not already started
    q_progress = quiz_session.question_progress[new_idx]
    if q_progress.status.value == "not_started":
        from app.models.quiz_session import QuestionStatus
        q_progress.status = QuestionStatus.IN_PROGRESS
        q_progress.started_at = datetime.now()

    logger.info(
        "question_navigated",
        new_index=new_idx,
        direction=request.direction
    )

    return NavigateQuestionResponse(
        question=question,
        question_index=new_idx + 1,  # 1-indexed for display
        total_questions=total_q,
        has_previous=new_idx > 0,
        has_next=new_idx < total_q - 1,
        message=f"Navigated to question {new_idx + 1} of {total_q}"
    )


@router.post("/quiz/enter-learning-mode", response_model=EnterLearningModeResponse)
async def enter_learning_mode_endpoint(request: EnterLearningModeRequest):
    """
    Enter Interactive Learning Mode for a question.

    Flow:
    1. Get concept for this question
    2. Generate 3-5 Socratic checkpoints
    3. Update quiz session state
    4. Return first checkpoint question
    """
    logger.info(
        "entering_learning_mode",
        quiz_session_id=request.quiz_session_id,
        question_id=request.question_id
    )

    # Get quiz session
    quiz_session = get_quiz_session(request.quiz_session_id)
    if not quiz_session:
        raise HTTPException(status_code=404, detail="Quiz session not found")

    # Get question
    question = next(
        (q for q in quiz_session.questions if q['question_id'] == request.question_id),
        None
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Get associated concept
    concept_id = question.get('concept_id')
    concept = next(
        (c for c in quiz_session.concepts if c.get('id') == concept_id),
        None
    )

    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found for this question")

    try:
        # Generate learning checkpoints
        logger.info("generating_learning_checkpoints", concept=concept['name'])
        checkpoints = await learning_coach.generate_checkpoints(
            concept=concept,
            document_text=quiz_session.document_text,
            target_checkpoint_count=3
        )

        # Update quiz session
        enter_learning_mode(
            session_id=request.quiz_session_id,
            question_id=request.question_id,
            checkpoints=checkpoints
        )

        logger.info(
            "learning_mode_started",
            question_id=request.question_id,
            checkpoint_count=len(checkpoints)
        )

        return EnterLearningModeResponse(
            message=f"Let's build understanding of '{concept['name']}' through guided exploration.",
            checkpoints=checkpoints,
            current_checkpoint=checkpoints[0],
            total_checkpoints=len(checkpoints)
        )

    except Exception as e:
        logger.error("learning_mode_entry_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enter learning mode: {str(e)}"
        )


@router.post("/quiz/checkpoint-response", response_model=CheckpointResponseResponse)
async def checkpoint_response_endpoint(request: CheckpointResponseRequest):
    """
    Handle user response to a Socratic checkpoint question.

    Flow:
    1. Get checkpoint
    2. Analyze user response
    3. Provide adaptive hint if needed
    4. Advance to next checkpoint if ready
    5. Exit learning mode when all checkpoints complete
    """
    logger.info(
        "checkpoint_response",
        quiz_session_id=request.quiz_session_id,
        checkpoint_id=request.checkpoint_id
    )

    # Get quiz session
    quiz_session = get_quiz_session(request.quiz_session_id)
    if not quiz_session:
        raise HTTPException(status_code=404, detail="Quiz session not found")

    # Get question progress
    q_progress = next(
        (qp for qp in quiz_session.question_progress if qp.question_id == request.question_id),
        None
    )

    if not q_progress or not q_progress.in_learning_mode:
        raise HTTPException(status_code=400, detail="Not in learning mode for this question")

    # Get current checkpoint progress
    cp_index = q_progress.current_checkpoint_index
    if cp_index >= len(q_progress.learning_mode_checkpoints):
        raise HTTPException(status_code=400, detail="All checkpoints completed")

    cp_progress = q_progress.learning_mode_checkpoints[cp_index]

    # Get checkpoint definition from first question
    question = next(q for q in quiz_session.questions if q['question_id'] == request.question_id)
    # We need to retrieve checkpoints - they're not stored in session currently
    # For MVP, we'll fetch from concept again

    concept_id = question.get('concept_id')
    concept = next(c for c in quiz_session.concepts if c.get('id') == concept_id)

    # Generate checkpoints again (in production, we'd cache these)
    checkpoints = await learning_coach.generate_checkpoints(
        concept=concept,
        document_text=quiz_session.document_text,
        target_checkpoint_count=len(q_progress.learning_mode_checkpoints)
    )

    checkpoint = checkpoints[cp_index]

    try:
        # Record conversation
        cp_progress.conversation_history.append({
            "question": checkpoint['socratic_question'],
            "answer": request.user_response
        })
        cp_progress.attempts += 1

        # Get adaptive hint
        hint_result = await learning_coach.provide_adaptive_hint(
            checkpoint=checkpoint,
            user_response=request.user_response,
            attempt_count=cp_progress.attempts,
            conversation_history=cp_progress.conversation_history
        )

        should_advance = hint_result['should_advance']

        response = CheckpointResponseResponse(
            feedback=await learning_coach.generate_encouragement(
                checkpoint_completed=should_advance,
                understanding_level=hint_result['understanding_level']
            ),
            hint=hint_result if not should_advance else None,
            should_advance=should_advance,
            learning_complete=False
        )

        if should_advance:
            # Mark current checkpoint complete
            cp_progress.status = "completed"
            cp_progress.completed_at = datetime.now()

            # Move to next checkpoint
            q_progress.current_checkpoint_index += 1

            if q_progress.current_checkpoint_index < len(checkpoints):
                # Start next checkpoint
                next_cp_progress = q_progress.learning_mode_checkpoints[q_progress.current_checkpoint_index]
                next_cp_progress.status = "in_progress"
                next_cp_progress.started_at = datetime.now()

                response.next_checkpoint = checkpoints[q_progress.current_checkpoint_index]
                logger.info("checkpoint_advanced", new_checkpoint_index=q_progress.current_checkpoint_index)
            else:
                # All checkpoints complete - exit learning mode
                exit_learning_mode(request.quiz_session_id, request.question_id)
                response.learning_complete = True
                response.feedback = "Great work! You've built solid understanding. Let's return to the quiz."
                logger.info("learning_mode_completed", question_id=request.question_id)

        return response

    except Exception as e:
        logger.error("checkpoint_response_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process checkpoint response: {str(e)}"
        )

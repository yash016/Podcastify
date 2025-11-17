"""
Quiz Generator Service - Generate multiple-choice questions from document concepts.

Uses LLM to create engaging questions with:
- 4 multiple choice options (1 correct, 3 plausible distractors)
- 3-level graduated hint system
- Concept-based question generation
"""

import json
from typing import List, Dict, Any, Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class QuizGenerator:
    """
    Generates quiz questions from extracted document concepts.
    """

    def __init__(self, llm_service):
        self.llm_service = llm_service
        logger.info("quiz_generator_initialized")

    async def generate_quiz(
        self,
        concepts: List[Dict[str, Any]],
        document_text: str,
        target_question_count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate quiz questions from document concepts.

        Args:
            concepts: List of concepts extracted from document
            document_text: Full document text for context
            target_question_count: Number of questions to generate (default: 5)

        Returns:
            List of question dictionaries with answers, hints, and metadata
        """
        # Validate input - fail fast if concepts is not a list
        if not isinstance(concepts, list):
            logger.error("invalid_concepts_type",
                       type=type(concepts).__name__,
                       data_preview=str(concepts)[:200])
            raise ValueError(f"Expected list of concepts but got {type(concepts).__name__}")

        # Validate that concepts list contains dictionaries, not strings
        if len(concepts) > 0 and not isinstance(concepts[0], dict):
            logger.error("invalid_concept_item_type",
                       type=type(concepts[0]).__name__,
                       first_item=str(concepts[0])[:100],
                       concepts_preview=str(concepts)[:200])
            raise ValueError(f"Expected list of concept dicts but got list of {type(concepts[0]).__name__}")

        logger.info(
            "generating_quiz",
            concept_count=len(concepts),
            target_questions=target_question_count
        )

        # Select top concepts by importance
        selected_concepts = self._select_top_concepts(concepts, target_question_count)

        # Generate questions for selected concepts
        questions = await self._generate_questions(
            selected_concepts,
            document_text,
            target_question_count
        )

        logger.info(
            "quiz_generation_complete",
            questions_generated=len(questions)
        )

        return questions

    def _select_top_concepts(
        self,
        concepts: List[Dict[str, Any]],
        count: int
    ) -> List[Dict[str, Any]]:
        """
        Select top N concepts by importance score.

        Args:
            concepts: List of all concepts
            count: Number of concepts to select

        Returns:
            Top N concepts sorted by importance
        """
        # Sort by importance (descending)
        sorted_concepts = sorted(
            concepts,
            key=lambda c: c.get('importance', 0),
            reverse=True
        )

        # Take top N
        selected = sorted_concepts[:count]

        logger.debug(
            "concepts_selected_for_quiz",
            total_concepts=len(concepts),
            selected_count=len(selected),
            selected_names=[c['name'] for c in selected]
        )

        return selected

    async def _generate_questions(
        self,
        concepts: List[Dict[str, Any]],
        document_text: str,
        target_count: int
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple-choice questions using LLM.

        Args:
            concepts: Selected concepts to generate questions for
            document_text: Full document text
            target_count: Target number of questions

        Returns:
            List of question dictionaries
        """
        # Build concept context for LLM
        concept_context = "\n".join([
            f"- {c['name']}: {c.get('definition', '')}"
            for c in concepts
        ])

        system_instruction = """You are an expert educational assessment designer who creates quiz questions in valid JSON format.
CRITICAL: You MUST return ONLY valid JSON. Each question in the array must be a complete JSON object.
Do NOT use shorthand syntax. Do NOT use comma-separated key-value pairs.
Every question must follow standard JSON object format with proper structure."""

        prompt = f"""Generate EXACTLY {target_count} multiple-choice quiz questions from the document concepts below.

**Document Excerpt**:
{document_text[:1500]}...

**Key Concepts**:
{concept_context}

Return a valid JSON array. Each question must be a complete object in the array.

Example of correct format:
[
  {{
    "question_id": "q1",
    "concept_id": "c1",
    "concept_name": "Example Concept",
    "question": "What is the main idea?",
    "options": [
      {{"id": "a", "text": "Correct answer"}},
      {{"id": "b", "text": "Wrong answer 1"}},
      {{"id": "c", "text": "Wrong answer 2"}},
      {{"id": "d", "text": "Wrong answer 3"}}
    ],
    "correct_answer": "a",
    "explanation": "Explanation text",
    "hints": [
      {{"level": 1, "type": "nudge", "text": "Hint 1"}},
      {{"level": 2, "type": "partial", "text": "Hint 2"}},
      {{"level": 3, "type": "explicit", "text": "Hint 3"}}
    ],
    "difficulty": "medium",
    "audio_timestamp": null
  }}
]

CRITICAL Requirements:
- Generate EXACTLY {target_count} questions
- Each question tests ONE concept from the list
- Options should be similar length and complexity
- Distractors must be plausible but clearly wrong upon reflection
- Hints must be graduated: Level 1 (subtle) → Level 2 (moderate) → Level 3 (explicit)
- Include audio_timestamp from concept data if available
- Question IDs: q1, q2, q3, etc.
- Option IDs: a, b, c, d (always 4 options)
- Difficulty: easy/medium/hard based on concept complexity
"""

        result = await self.llm_service.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,  # Lower temperature for more reliable JSON
            max_tokens=3072,
            response_format="json"
        )

        # Parse LLM response and handle both array and object formats
        parsed_result = json.loads(result)

        # Handle Gemini wrapping response in object
        if isinstance(parsed_result, dict):
            if 'questions' in parsed_result:
                questions = parsed_result['questions']
            else:
                # Single question object, wrap in array
                questions = [parsed_result]
        else:
            questions = parsed_result

        # Validate it's now a list
        if not isinstance(questions, list):
            logger.error(
                "quiz_questions_invalid_type",
                type=type(questions).__name__,
                data=str(questions)[:300]
            )
            raise ValueError(f"Expected list of questions but got {type(questions).__name__}")

        logger.info(
            "llm_quiz_response_parsed",
            response_type=type(questions).__name__,
            question_count=len(questions),
            first_question_preview=str(questions[0])[:200] if len(questions) > 0 else "empty"
        )

        # Enrich questions with concept metadata
        concept_map = {c['id']: c for c in concepts}
        for q in questions:
            concept = concept_map.get(q['concept_id'])
            if concept:
                # Add timestamp if available
                if 'absolute_timestamp' in concept and concept['absolute_timestamp']:
                    q['audio_timestamp'] = concept['absolute_timestamp']
                else:
                    q['audio_timestamp'] = None

        logger.info(
            "questions_generated_via_llm",
            question_count=len(questions)
        )

        return questions


# Function to create quiz generator instance
def init_quiz_generator(llm_service):
    """Initialize quiz generator with LLM service."""
    return QuizGenerator(llm_service)

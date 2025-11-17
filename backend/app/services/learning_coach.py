"""
Learning Coach Service - Progressive Socratic Questioning for Interactive Learning Mode.

Adapted from worklearn's CoachAgent. Helps learners build understanding through:
- 3-5 progressive checkpoints per concept
- Adaptive Socratic questioning
- Graduated hints based on struggle patterns
"""

import json
from typing import List, Dict, Any, Optional
from enum import Enum

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class CheckpointStatus(str, Enum):
    """Status of a learning checkpoint."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class LearningCoach:
    """
    Guides learners through Progressive Socratic Questioning.
    """

    def __init__(self, llm_service):
        self.llm_service = llm_service
        logger.info("learning_coach_initialized")

    async def generate_checkpoints(
        self,
        concept: Dict[str, Any],
        document_text: str,
        target_checkpoint_count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate progressive Socratic checkpoints for a concept.

        Args:
            concept: Concept to build understanding of
            document_text: Full document text for context
            target_checkpoint_count: Number of checkpoints (default: 3)

        Returns:
            List of checkpoint dictionaries with questions and expected insights
        """
        logger.info(
            "generating_checkpoints",
            concept_name=concept['name'],
            target_count=target_checkpoint_count
        )

        system_instruction = """You are a Socratic teaching expert.
You create progressive learning checkpoints that guide learners to discover understanding themselves.
Each checkpoint builds on the previous one, moving from basic foundations to deeper insights."""

        prompt = f"""Generate {target_checkpoint_count} progressive Socratic checkpoints to help a learner understand this concept.

**Concept**: {concept['name']}
**Definition**: {concept.get('definition', 'See document context')}

**Document Context**:
{document_text[:1500]}...

Return as JSON array:
[
  {{
    "checkpoint_id": "cp1",
    "order": 1,
    "title": "Foundation Understanding",
    "socratic_question": "Let's start simple - in your own words, what do you think [concept] means?",
    "expected_insight": "Learner should grasp basic definition",
    "follow_up_questions": [
      "Can you give an example?",
      "Why might this be important?"
    ],
    "hints": [
      {{
        "level": 1,
        "text": "Think about what the term literally means..."
      }},
      {{
        "level": 2,
        "text": "Consider the context in which this appears in the document..."
      }},
      {{
        "level": 3,
        "text": "The key is understanding that [partial explanation]..."
      }}
    ],
    "mastery_criteria": "Learner can explain basic definition in own words"
  }},
  {{
    "checkpoint_id": "cp2",
    "order": 2,
    "title": "Connecting Ideas",
    "socratic_question": "How does [concept] relate to [related concept or context]?",
    "expected_insight": "Learner should see connections to broader context",
    "follow_up_questions": [
      "What would happen if this wasn't true?",
      "Can you think of a real-world application?"
    ],
    "hints": [
      {{
        "level": 1,
        "text": "Consider what we just discussed about the definition..."
      }},
      {{
        "level": 2,
        "text": "Think about cause and effect..."
      }},
      {{
        "level": 3,
        "text": "The connection is that [partial explanation]..."
      }}
    ],
    "mastery_criteria": "Learner can explain relationships and implications"
  }}
]

CRITICAL Requirements:
- Generate EXACTLY {target_checkpoint_count} checkpoints
- Order: 1 (foundation) → 2 (connections) → 3+ (deeper insights/applications)
- Each checkpoint must BUILD on previous ones progressively
- Questions should be OPEN-ENDED, not yes/no
- Hints should be GRADUATED: subtle nudge → moderate → explicit
- Mastery criteria should be specific and measurable
- Checkpoint IDs: cp1, cp2, cp3, etc.
"""

        result = await self.llm_service.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.7,
            max_tokens=2048,
            response_format="json"
        )

        checkpoints = json.loads(result)

        logger.info(
            "checkpoints_generated",
            concept=concept['name'],
            checkpoint_count=len(checkpoints)
        )

        return checkpoints

    async def provide_adaptive_hint(
        self,
        checkpoint: Dict[str, Any],
        user_response: str,
        attempt_count: int,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Provide adaptive hint based on user's response and struggle level.

        Args:
            checkpoint: Current checkpoint
            user_response: User's latest response
            attempt_count: Number of attempts at this checkpoint
            conversation_history: Previous Q&A in this checkpoint

        Returns:
            Dict with hint_level, hint_text, and should_advance flag
        """
        if conversation_history is None:
            conversation_history = []

        logger.info(
            "providing_adaptive_hint",
            checkpoint_id=checkpoint['checkpoint_id'],
            attempt_count=attempt_count
        )

        # Determine hint level based on attempts
        if attempt_count == 1:
            hint_level = 1
        elif attempt_count == 2:
            hint_level = 2
        else:
            hint_level = 3

        # Get pre-generated hint
        hints = checkpoint.get('hints', [])
        hint_obj = next(
            (h for h in hints if h['level'] == hint_level),
            hints[-1] if hints else {"level": 3, "text": "Let me explain..."}
        )

        # Analyze response quality using LLM
        system_instruction = """You are analyzing a learner's response to a Socratic question.
Determine if they've grasped the key insight, are partially there, or are still struggling."""

        conversation_context = "\n".join([
            f"Q: {msg['question']}\nA: {msg['answer']}"
            for msg in conversation_history
        ])

        prompt = f"""Analyze this learner's response to determine understanding level.

**Checkpoint**: {checkpoint['title']}
**Socratic Question**: {checkpoint['socratic_question']}
**Expected Insight**: {checkpoint['expected_insight']}

**Conversation So Far**:
{conversation_context}

**Latest Response**: {user_response}

Return as JSON:
{{
  "understanding_level": "none|partial|good|mastery",
  "reasoning": "Brief explanation of assessment",
  "should_advance": true/false,
  "suggested_follow_up": "Next question to ask, or null if should advance"
}}

Criteria:
- "none": Completely off-track or confused
- "partial": Shows some understanding but missing key elements
- "good": Demonstrates core understanding, minor gaps
- "mastery": Clearly articulates expected insight
- should_advance: true only if understanding_level is "good" or "mastery"
"""

        analysis_result = await self.llm_service.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,  # Lower temp for consistent evaluation
            max_tokens=512,
            response_format="json"
        )

        analysis = json.loads(analysis_result)

        logger.info(
            "response_analyzed",
            checkpoint_id=checkpoint['checkpoint_id'],
            understanding_level=analysis['understanding_level'],
            should_advance=analysis['should_advance']
        )

        return {
            "hint_level": hint_level,
            "hint_text": hint_obj['text'],
            "understanding_level": analysis['understanding_level'],
            "should_advance": analysis['should_advance'],
            "follow_up_question": analysis.get('suggested_follow_up'),
            "reasoning": analysis.get('reasoning', '')
        }

    async def generate_encouragement(
        self,
        checkpoint_completed: bool,
        understanding_level: str
    ) -> str:
        """
        Generate encouraging feedback based on progress.

        Args:
            checkpoint_completed: Whether checkpoint was completed
            understanding_level: Level of understanding demonstrated

        Returns:
            Encouraging message
        """
        if checkpoint_completed and understanding_level == "mastery":
            messages = [
                "Excellent! You've really grasped this concept.",
                "Great work! That's exactly the insight we're looking for.",
                "Perfect! You're building strong understanding."
            ]
        elif checkpoint_completed:
            messages = [
                "Good progress! You're on the right track.",
                "Nice! You're developing solid understanding.",
                "Well done! Let's keep building on this."
            ]
        else:
            messages = [
                "Keep thinking through this - you're getting closer!",
                "Don't worry, this is a challenging concept. Let's break it down.",
                "Good effort! Let me give you another hint to guide your thinking."
            ]

        # Simple rotation (could be randomized)
        return messages[0]


# Function to create learning coach instance
def init_learning_coach(llm_service):
    """Initialize learning coach with LLM service."""
    return LearningCoach(llm_service)

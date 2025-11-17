"""
Struggle Detector Service - Monitors user attempts to determine when to trigger Interactive Learning Mode.

Detects struggle based on:
- Number of wrong attempts (primary trigger: 3 attempts)
- Time spent on question (secondary indicator)
- Pattern of answers (random guessing vs. consistent misconception)
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class StruggleLevel(str):
    """Levels of detected struggle."""
    NONE = "none"              # 0 wrong attempts
    MINOR = "minor"            # 1 wrong attempt
    MODERATE = "moderate"      # 2 wrong attempts
    SIGNIFICANT = "significant"  # 3+ wrong attempts (trigger Interactive Learning)


class StruggleDetector:
    """
    Detects when learners are struggling and need Interactive Learning Mode.
    """

    def __init__(self):
        logger.info("struggle_detector_initialized")

    def analyze_attempts(
        self,
        attempts: List[Dict[str, Any]],
        question: Dict[str, Any],
        time_spent_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze user attempts to determine struggle level.

        Args:
            attempts: List of attempt dictionaries with selected_option, is_correct, timestamp
            question: The question being attempted
            time_spent_seconds: Total time spent on this question

        Returns:
            Dict with struggle_level, should_trigger_learning_mode, and analysis
        """
        wrong_attempts = [a for a in attempts if not a.get('is_correct', False)]
        wrong_count = len(wrong_attempts)

        # Determine struggle level
        if wrong_count == 0:
            struggle_level = StruggleLevel.NONE
        elif wrong_count == 1:
            struggle_level = StruggleLevel.MINOR
        elif wrong_count == 2:
            struggle_level = StruggleLevel.MODERATE
        else:
            struggle_level = StruggleLevel.SIGNIFICANT

        # Should trigger Interactive Learning Mode?
        should_trigger = wrong_count >= 3

        # Analyze pattern
        pattern_analysis = self._analyze_answer_pattern(
            attempts,
            question.get('options', [])
        )

        # Time-based analysis (if available)
        time_analysis = None
        if time_spent_seconds:
            time_analysis = self._analyze_time_spent(
                time_spent_seconds,
                wrong_count
            )

        logger.info(
            "struggle_analysis_complete",
            question_id=question.get('question_id'),
            wrong_count=wrong_count,
            struggle_level=struggle_level,
            should_trigger_learning=should_trigger,
            pattern=pattern_analysis['pattern_type']
        )

        return {
            "struggle_level": struggle_level,
            "should_trigger_learning_mode": should_trigger,
            "wrong_attempt_count": wrong_count,
            "total_attempt_count": len(attempts),
            "pattern_analysis": pattern_analysis,
            "time_analysis": time_analysis,
            "recommendation": self._get_recommendation(
                struggle_level,
                pattern_analysis,
                should_trigger
            )
        }

    def _analyze_answer_pattern(
        self,
        attempts: List[Dict[str, Any]],
        options: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze pattern of selected answers to understand misconception.

        Args:
            attempts: List of attempts
            options: Available answer options

        Returns:
            Dict with pattern_type and insights
        """
        if len(attempts) < 2:
            return {
                "pattern_type": "insufficient_data",
                "insight": "Not enough attempts to detect pattern"
            }

        selected_options = [a.get('selected_option') for a in attempts]

        # Check if repeating same wrong answer (consistent misconception)
        if len(set(selected_options)) == 1:
            return {
                "pattern_type": "consistent_misconception",
                "insight": "User consistently selects same answer - likely has specific misconception",
                "repeated_option": selected_options[0]
            }

        # Check if trying different options each time (random guessing)
        if len(set(selected_options)) == len(selected_options):
            return {
                "pattern_type": "random_guessing",
                "insight": "User tries different option each time - may not understand concept"
            }

        # Mixed pattern
        return {
            "pattern_type": "mixed",
            "insight": "User has tried multiple different answers",
            "option_frequencies": {opt: selected_options.count(opt) for opt in set(selected_options)}
        }

    def _analyze_time_spent(
        self,
        time_spent_seconds: float,
        wrong_count: int
    ) -> Dict[str, Any]:
        """
        Analyze time spent on question.

        Args:
            time_spent_seconds: Total time on question
            wrong_count: Number of wrong attempts

        Returns:
            Dict with time analysis
        """
        # Rough heuristics for time assessment
        avg_time_per_attempt = time_spent_seconds / max(1, wrong_count + 1)

        if avg_time_per_attempt < 10:
            assessment = "rushed"
            insight = "Quick attempts - user may be guessing without careful thought"
        elif avg_time_per_attempt < 30:
            assessment = "normal"
            insight = "Reasonable time per attempt"
        else:
            assessment = "deliberate"
            insight = "Significant time per attempt - user is thinking carefully but may be confused"

        return {
            "total_time_seconds": time_spent_seconds,
            "avg_time_per_attempt": avg_time_per_attempt,
            "assessment": assessment,
            "insight": insight
        }

    def _get_recommendation(
        self,
        struggle_level: str,
        pattern_analysis: Dict[str, Any],
        should_trigger: bool
    ) -> str:
        """
        Get recommendation for next action.

        Args:
            struggle_level: Current struggle level
            pattern_analysis: Pattern analysis results
            should_trigger: Whether to trigger learning mode

        Returns:
            Recommendation string
        """
        if should_trigger:
            return "Trigger Interactive Learning Mode to build understanding through Socratic questioning"

        if struggle_level == StruggleLevel.NONE:
            return "No intervention needed - user is progressing well"

        if struggle_level == StruggleLevel.MINOR:
            return "Provide Level 1 hint (gentle nudge)"

        if struggle_level == StruggleLevel.MODERATE:
            if pattern_analysis['pattern_type'] == 'consistent_misconception':
                return "Provide Level 2 hint addressing specific misconception"
            else:
                return "Provide Level 2 hint to guide thinking"

        return "Continue monitoring"


# Global instance
struggle_detector = StruggleDetector()

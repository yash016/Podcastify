"""
Socratic Hint Generator - Dynamic hint generation that analyzes wrong answers.

Generates targeted Socratic questions that:
- Explain WHY the user's answer is wrong
- Question their assumptions
- Guide them toward correct thinking through discovery
- Integrate WebSearch for enriched context
"""

import json
from typing import Dict, List, Any, Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SocraticHintGenerator:
    """
    Generates dynamic Socratic hints that analyze specific wrong answers.
    """

    def __init__(self, llm_service):
        """
        Args:
            llm_service: LLMService instance for hint generation
        """
        self.llm = llm_service
        logger.info("socratic_hint_generator_initialized")

    async def generate_socratic_hint(
        self,
        question: Dict[str, Any],
        selected_option: str,
        hint_level: int,
        document_context: str,
        use_web_search: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a Socratic hint analyzing the user's wrong answer.

        Args:
            question: The quiz question dict with options, correct_answer, etc.
            selected_option: The user's selected option ID (a, b, c, d)
            hint_level: 1 (subtle), 2 (moderate), or 3 (explicit)
            document_context: Original document text for context
            use_web_search: Whether to enrich with WebSearch

        Returns:
            Dict with socratic_questions, wrong_answer_reasoning, guiding_questions, etc.
        """
        logger.info(
            "generating_socratic_hint",
            question_id=question.get('question_id'),
            selected_option=selected_option,
            hint_level=hint_level
        )

        # Get option texts
        selected_option_obj = next(
            (o for o in question['options'] if o['id'] == selected_option),
            None
        )
        correct_option_obj = next(
            (o for o in question['options'] if o['id'] == question['correct_answer']),
            None
        )

        if not selected_option_obj or not correct_option_obj:
            logger.error("option_not_found", selected=selected_option, correct=question['correct_answer'])
            return self._create_fallback_hint(question, hint_level)

        # WebSearch for concept context (if enabled)
        search_context = ""
        search_url = None
        if use_web_search:
            try:
                concept_name = question.get('concept_name', '')
                search_result = await self._search_web_for_concept(concept_name)
                search_context = search_result.get('summary', '')
                search_url = search_result.get('url')
            except Exception as e:
                logger.warning("websearch_failed", error=str(e))
                search_context = ""

        # Generate Socratic hint using LLM
        hint_data = await self._generate_hint_with_llm(
            question=question,
            selected_option_obj=selected_option_obj,
            correct_option_obj=correct_option_obj,
            hint_level=hint_level,
            document_context=document_context,
            search_context=search_context
        )

        # Add search URL if available
        if search_url:
            hint_data['search_url'] = search_url

        logger.info(
            "socratic_hint_generated",
            question_id=question.get('question_id'),
            hint_level=hint_level,
            socratic_questions_count=len(hint_data.get('socratic_questions', []))
        )

        return hint_data

    async def _generate_hint_with_llm(
        self,
        question: Dict,
        selected_option_obj: Dict,
        correct_option_obj: Dict,
        hint_level: int,
        document_context: str,
        search_context: str
    ) -> Dict[str, Any]:
        """
        Use LLM to generate Socratic hint analyzing the wrong answer.
        """
        # Define hint level characteristics
        level_instructions = {
            1: """Level 1 (Subtle): Question their assumptions gently. Don't reveal the answer.
            - Ask why they might have thought this
            - Point out contradictions in their logic
            - Hint at what they should consider""",
            2: """Level 2 (Moderate): Be more direct but still Socratic.
            - Explain why their answer is incorrect
            - Eliminate 1-2 obviously wrong options
            - Guide them toward key concepts they missed""",
            3: """Level 3 (Explicit): Almost reveal the answer through guidance.
            - Clearly explain why their answer fails
            - Point directly to the correct reasoning
            - Leave only minimal discovery work for them"""
        }

        system_instruction = """You are a Socratic teaching expert who helps learners
discover understanding through thoughtful questioning, not direct answers. Your goal is to
help students realize why their answer is wrong and guide them to the correct answer through
their own reasoning."""

        prompt = f"""A student answered a quiz question incorrectly. Generate a Socratic dialogue
to help them discover why their answer is wrong and guide them to the right answer.

**Question**: {question['question']}

**Options**:
{self._format_options(question['options'])}

**Student's Answer**: {selected_option_obj['id'].upper()}. {selected_option_obj['text']}
**Correct Answer**: {correct_option_obj['text']} (don't reveal this directly unless Level 3)

**Hint Level**: {hint_level}
{level_instructions[hint_level]}

**Document Context** (use to ground explanations):
{document_context[:500]}...

**Additional Context** (from web search):
{search_context if search_context else "None available"}

Generate a JSON response with:
{{
  "wrong_answer_reasoning": "Explain in 2-3 sentences why their selected answer is incorrect. Be clear and specific about what makes it wrong.",
  "socratic_questions": [
    "You selected '{selected_option_obj['text']}' - [Question that reveals assumption or contradiction]",
    "[Question that hints at what they should consider]",
    "[Question that guides toward correct reasoning]"
  ],
  "guiding_questions": [
    "[What key concept or fact should they recall?]",
    "[What relationship or connection are they missing?]"
  ],
  "search_context_summary": "Brief 1-2 sentence summary of web search findings (if available, otherwise empty string)"
}}

IMPORTANT:
- Make socratic_questions specific to their wrong answer
- Reference their selected option in at least the first question
- For Level 1: Be subtle, question assumptions
- For Level 2: Be clearer, narrow down options
- For Level 3: Be explicit, almost point to answer
- Keep all text concise and focused
"""

        try:
            result = await self.llm.generate(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.5,  # Moderate creativity
                max_tokens=1024,
                response_format="json"
            )

            hint_data = json.loads(result)

            # Validate structure
            if not isinstance(hint_data, dict):
                logger.error("hint_generation_invalid_format", type=type(hint_data).__name__)
                return self._create_fallback_hint(question, hint_level)

            return hint_data

        except Exception as e:
            logger.error("hint_generation_failed", error=str(e))
            return self._create_fallback_hint(question, hint_level)

    async def _search_web_for_concept(self, concept_name: str) -> Dict[str, str]:
        """
        Search the web for concept explanation to enrich hints.

        Args:
            concept_name: Name of the concept to search for

        Returns:
            Dict with 'summary' and 'url' keys
        """
        from app.services.llm import llm_service

        # Note: WebSearch tool is available via the agent/tool system
        # For MVP, we'll use a simple prompt to the LLM to simulate search context
        # In production, integrate actual WebSearch tool

        try:
            # Simplified web search simulation using LLM knowledge
            prompt = f"""Provide a brief 2-3 sentence explanation of '{concept_name}' suitable for a student learning about this topic. Focus on the core idea and its significance."""

            result = await self.llm.generate(
                prompt=prompt,
                system_instruction="You are a concise educational resource that explains concepts clearly.",
                temperature=0.3,
                max_tokens=200
            )

            return {
                "summary": result.strip(),
                "url": f"https://www.google.com/search?q={concept_name.replace(' ', '+')}"
            }
        except Exception as e:
            logger.warning("web_search_simulation_failed", error=str(e))
            return {"summary": "", "url": None}

    def _format_options(self, options: List[Dict]) -> str:
        """Format options for display in prompt."""
        return "\n".join([
            f"{opt['id'].upper()}. {opt['text']}"
            for opt in options
        ])

    def _create_fallback_hint(self, question: Dict, hint_level: int) -> Dict[str, Any]:
        """
        Create a basic fallback hint if LLM generation fails.
        """
        logger.warning("using_fallback_socratic_hint", question_id=question.get('question_id'))

        return {
            "wrong_answer_reasoning": "This answer doesn't align with the core concept being tested.",
            "socratic_questions": [
                "What does this concept fundamentally mean?",
                "How does it relate to the other key ideas we've discussed?",
                "What would you expect to see if this were the correct answer?"
            ],
            "guiding_questions": [
                "Review the definition of the concept",
                "Consider the relationships between key ideas"
            ],
            "search_context_summary": ""
        }


# Global instance
socratic_hint_generator: Optional[SocraticHintGenerator] = None


def init_socratic_hint_generator(llm_service):
    """Initialize the global Socratic hint generator with LLM service."""
    global socratic_hint_generator
    socratic_hint_generator = SocraticHintGenerator(llm_service)
    logger.info("socratic_hint_generator_service_initialized")
    return socratic_hint_generator

"""
LLM service with support for Gemini and Groq (fallback).
Handles outline generation, dialogue scripting, and compression.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
import google.generativeai as genai
from groq import Groq

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Get project root (Podcastify directory)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    GROQ = "groq"


class LLMService:
    """
    Unified LLM service supporting multiple providers.
    Primary: Gemini 2.5 Flash (cheap, fast)
    Fallback: Groq Llama 3.1 8B (cheapest alternative)
    """

    def __init__(self):
        self.provider = LLMProvider(settings.llm_provider)
        self._setup_clients()

    def _setup_clients(self):
        """Initialize API clients."""
        # Gemini setup
        genai.configure(api_key=settings.gemini_api_key)
        self.gemini_model = genai.GenerativeModel(settings.gemini_model)

        # Groq setup
        self.groq_client = Groq(api_key=settings.groq_api_key)

        logger.info(
            "llm_service_initialized",
            provider=self.provider,
            gemini_model=settings.gemini_model,
            groq_model=settings.groq_model,
        )

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,  # "json" or None
    ) -> str:
        """
        Generate text using the configured LLM provider.

        Args:
            prompt: The user prompt
            system_instruction: System/role instruction
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            response_format: "json" to request JSON output

        Returns:
            Generated text
        """
        logger.info(
            "llm_generate_start",
            provider=self.provider,
            prompt_length=len(prompt),
            temperature=temperature,
        )

        try:
            if self.provider == LLMProvider.GEMINI:
                return await self._generate_gemini(
                    prompt, system_instruction, temperature, max_tokens, response_format
                )
            else:
                return await self._generate_groq(
                    prompt, system_instruction, temperature, max_tokens, response_format
                )
        except Exception as e:
            logger.error(
                "llm_generate_failed",
                provider=self.provider,
                error=str(e),
            )
            # Try fallback if primary fails
            if self.provider == LLMProvider.GEMINI:
                logger.info("attempting_groq_fallback")
                return await self._generate_groq(
                    prompt, system_instruction, temperature, max_tokens, response_format
                )
            raise

    async def _generate_gemini(
        self,
        prompt: str,
        system_instruction: Optional[str],
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> str:
        """Generate using Gemini API."""
        from google.generativeai.types import HarmCategory, HarmBlockThreshold

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if response_format == "json":
            generation_config["response_mime_type"] = "application/json"

        # Disable safety filters to prevent blocks on educational content
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        # Combine system instruction with prompt
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"

        response = self.gemini_model.generate_content(
            full_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

        result = response.text

        # Validate JSON if expected
        if response_format == "json":
            try:
                json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(
                    "gemini_invalid_json",
                    error=str(e),
                    response_preview=result[:500]
                )
                raise Exception(f"Gemini returned invalid JSON: {str(e)}")

        logger.info(
            "gemini_generate_success",
            input_tokens=response.usage_metadata.prompt_token_count,
            output_tokens=response.usage_metadata.candidates_token_count,
            total_tokens=response.usage_metadata.total_token_count,
        )

        return result

    async def _generate_groq(
        self,
        prompt: str,
        system_instruction: Optional[str],
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> str:
        """Generate using Groq API."""
        messages = []

        if system_instruction:
            messages.append({
                "role": "system",
                "content": system_instruction,
            })

        messages.append({
            "role": "user",
            "content": prompt,
        })

        completion_kwargs = {
            "model": settings.groq_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            completion_kwargs["response_format"] = {"type": "json_object"}

        response = self.groq_client.chat.completions.create(**completion_kwargs)

        result = response.choices[0].message.content
        logger.info(
            "groq_generate_success",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        return result

    async def generate_outline(
        self,
        topic: str,
        level: str = "adaptive",
        duration: float = 5.0,
        custom_outline: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate podcast outline using the outline generation prompt template.

        Returns:
            Dict with outline (now returns 1 outline instead of 3 for V1 MVP)
        """
        # Load prompt template
        prompt_path = PROMPTS_DIR / "outline_generation.md"
        with open(prompt_path, "r") as f:
            prompt_template = f.read()

        # Extract system role from template (first section after ## System Role)
        system_instruction = """You are an expert educational content designer specializing in micro-learning and Socratic coaching. Your goal is to create engaging, transformative 5 minute podcast outlines that shift thinking through powerful questions and deep insights."""

        prompt = f"""Generate ONE optimized outline for a micro-coaching episode.

**Topic**: {topic}
**Level**: {level}
**Duration**: {duration} minutes
**Custom Outline**: {custom_outline if custom_outline else "None"}

Return your response as valid JSON matching this structure:
{{
  "title": "Engaging title for the micro-episode",
  "socratic_question": "The ONE transformative question that hooks the listener",
  "key_insight": "The ONE core insight that shifts thinking",
  "description": "1 sentence overview",
  "sections": [
    {{
      "id": "section_1",
      "title": "Section name",
      "description": "What this covers",
      "learning_outcomes": ["Specific thing learner will understand"],
      "is_socratic_checkpoint": false,
      "estimated_duration_sec": 45
    }}
  ],
  "estimated_duration_min": {duration},
  "estimated_word_count": 900
}}

IMPORTANT: Number sections sequentially starting from "section_1", "section_2", etc.

CRITICAL Guidelines for 5 minute format:
- Lead with a transformative Socratic question that creates curiosity
- Focus on ONE key insight with supporting concepts
- Use 4-5 sections (Socratic Hook → Core Concept → Deep Dive → Key Insight → Takeaway)
- Keep it engaging: ~900 words total, 25-30 dialogue turns
- End with a clear key insight that shifts thinking

See the full prompt template at: {prompt_path}
"""

        result = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.8,
            max_tokens=2048,
            response_format="json",
        )

        return json.loads(result)

    async def generate_dialogue(
        self,
        outline: Dict[str, Any],
        teaching_materials: List[Dict[str, Any]] = None,
        topic: str = "",
        level: str = "adaptive",
        duration: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Generate Brainy & Snarky dialogue script for 5 minute micro-coaching.

        Returns:
            Dict with script array and metadata
        """
        if teaching_materials is None:
            teaching_materials = []

        system_instruction = """You are writing a dyadic podcast script between:
- Brainy: Patient, structured teacher who guides understanding through scaffolding. Responds warmly to Snarky's humor while staying focused on teaching.
- Snarky: Witty, skeptical learner who uses sarcasm and humor to question ideas. Playfully challenges concepts while genuinely curious to understand.

Create engaging, transformative Socratic dialogue with humor and personality. Snarky's sarcasm keeps things fun without being mean."""

        # Extract Socratic question and key insight from outline if available
        socratic_question = outline.get("socratic_question", "")
        key_insight = outline.get("key_insight", "")

        # Calculate target turns based on duration (12 turns per minute for 3-min episodes)
        target_turns = int(duration * 12)  # 3 min = ~36 turns

        prompt = f"""Generate a complete {duration}-minute micro-coaching podcast script.

**Topic**: {topic}
**Duration**: {duration} minutes (~{int(duration * 180)} words)

**Outline**: {json.dumps(outline, indent=2)}

**Teaching Materials**: {json.dumps(teaching_materials, indent=2) if teaching_materials else "None"}

Return as JSON:
{{
  "script": [
    {{
      "speaker": "Brainy" or "Snarky",
      "text": "What they say...",
      "section_id": "section_1",
      "notes": "Brief context"
    }}
  ],
  "metadata": {{
    "estimated_word_count": {int(duration * 180)},
    "estimated_duration_min": {duration},
    "brainy_percentage": 60,
    "snarky_percentage": 40
  }}
}}

CRITICAL Requirements - APPROXIMATELY {target_turns} TURNS:

Socratic dialogue structure:
1. Brainy: Transformative opening question (hook) - "{socratic_question}" (30-40 words)
2. Snarky: Confusion/initial reaction (20-30 words)
3-{target_turns-2}: Alternate between Brainy and Snarky for:
   - Scaffolding questions that guide understanding
   - Partial realizations and "aha!" moments
   - Concrete analogies and examples
   - Applications to new contexts
   - Progressive deepening of insight
{target_turns-1}. Brainy: Key insight summary - "{key_insight}" (35-45 words)
{target_turns}. Snarky: Closing reflection/takeaway (20-30 words)

Rules:
- Target {target_turns} turns total (alternating Brainy/Snarky, starting with Brainy)
- Each turn: 25-45 words (longer turns for 3-minute format)
- Total: ~{int(duration * 180)} words ({duration} min audio)
- Include 2-3 concrete analogies throughout
- Build progressively toward key insight
- Natural pacing with moments of excitement and reflection
- IMPORTANT: Assign each turn to the corresponding section_id from the outline (e.g., "section_1", "section_2", etc.)

Concept Markers (IMPORTANT for interactive features):
- When introducing key concepts, mark them with [CONCEPT: name]
- If Teaching Materials are provided, prioritize marking those concepts
- If no Teaching Materials, mark the most important concepts you discuss
- Example: "Well, [CONCEPT: Simulation Hypothesis] suggests we might be living in a computer simulation."
- Only mark concepts on FIRST mention (not every time)
- Mark 5-8 key concepts throughout the dialogue
- Keep the concept name concise (2-4 words max)
- Markers enable interactive graph clicks to jump to timestamps

Character Guidelines:
- Brainy: ~60% dialogue, calm, patient, guides Snarky through reasoning. Responds to Snarky's humor with good-natured explanations.
- Snarky: ~40% dialogue, witty and questioning. Uses sarcasm/humor selectively (not every turn!) to:
  * Challenge unclear explanations ("Oh sure, because THAT makes total sense...")
  * Point out absurd implications ("Wait, you're telling me that...?")
  * Express skepticism playfully ("Let me guess... it's complicated?")
  * React with deadpan humor when concepts click ("Wow. Mind = blown.")
- Natural interruptions, reactions, and conversational flow with personality
"""

        result = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.9,
            max_tokens=3072,
            response_format="json",
        )

        return json.loads(result)


# Global service instance
llm_service = LLMService()

"""
Voice profiles for Brainy & Snarky using Maya1's natural language descriptions.
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class VoiceProfile:
    """Voice profile with description and emotion preferences."""
    name: str
    description: str
    default_emotions: Dict[str, float]  # Emotion → probability
    personality_traits: List[str]


# Brainy - The Structured Sage
BRAINY_PROFILE = VoiceProfile(
    name="Brainy",
    description=(
        "45-year-old British male with a warm baritone voice. "
        "Speaks with measured pace and patient, thoughtful delivery. "
        "Professional yet approachable tone, like a friendly university professor. "
        "Slightly formal but not stuffy. Clear articulation with subtle warmth."
    ),
    default_emotions={
        "neutral": 0.7,
        "thoughtful": 0.15,
        "encouraging": 0.10,
        "chuckle": 0.05,
    },
    personality_traits=[
        "patient",
        "structured",
        "warm",
        "measured pace",
        "clear articulation",
        "professorial"
    ]
)

# Snarky - The Curious Skeptic
SNARKY_PROFILE = VoiceProfile(
    name="Snarky",
    description=(
        "28-year-old American female with a bright, energetic voice. "
        "Fast-paced, playful delivery with natural curiosity and enthusiasm. "
        "Casual, conversational tone like talking to a smart friend. "
        "Expressive with dynamic pitch variations. Youthful energy without being childish."
    ),
    default_emotions={
        "curious": 0.4,
        "excited": 0.25,
        "playful": 0.20,
        "confused": 0.10,
        "laugh": 0.05,
    },
    personality_traits=[
        "energetic",
        "playful",
        "curious",
        "fast-paced",
        "expressive",
        "conversational"
    ]
)


# Emotion tag mappings for different contexts
EMOTION_TAGS = {
    # Brainy emotions
    "brainy_explains": "<thoughtful>",
    "brainy_confirms": "<encouraging>",
    "brainy_amused": "<chuckle>",
    "brainy_contemplates": "<sigh>",

    # Snarky emotions
    "snarky_realizes": "<gasp>",
    "snarky_excited": "<laugh>",
    "snarky_confused": "<confused>",
    "snarky_whispers": "<whisper>",
    "snarky_surprised": "<surprised>",
}


def get_voice_profile(speaker: str) -> VoiceProfile:
    """Get voice profile for a speaker."""
    profiles = {
        "Brainy": BRAINY_PROFILE,
        "Snarky": SNARKY_PROFILE,
    }
    return profiles.get(speaker, BRAINY_PROFILE)


def add_emotion_tags(text: str, speaker: str, context: str = None) -> str:
    """
    Add appropriate emotion tags to text based on context.

    Args:
        text: The dialogue text
        speaker: "Brainy" or "Snarky"
        context: Optional context hint for emotion selection

    Returns:
        Text with inline emotion tags
    """
    # Simple rule-based emotion insertion
    # In production, this could be ML-driven or LLM-enhanced

    if speaker == "Brainy":
        # Brainy is thoughtful and measured
        if "exactly" in text.lower() or "that's right" in text.lower():
            return f"<encouraging> {text}"
        elif "hmm" in text.lower() or "interesting" in text.lower():
            return f"<thoughtful> {text}"
        elif "!" in text and len(text.split()) < 10:  # Short exclamation
            return f"<chuckle> {text}"

    else:  # Snarky
        # Snarky is energetic and expressive
        if "wait" in text.lower() or "hold" in text.lower():
            return f"<confused> {text}"
        elif "oh!" in text.lower() or "aha!" in text.lower():
            return f"<gasp> {text}"
        elif "haha" in text.lower() or text.count("!") > 1:
            return f"<laugh> {text}"
        elif "..." in text:
            return f"<whisper> {text}"

    return text

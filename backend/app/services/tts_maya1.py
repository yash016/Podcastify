"""
Enhanced TTS service using Maya1 for high-quality voices.
Includes fallback to gTTS if Maya1 unavailable.
"""

import os
from typing import List, Dict, Optional
from pathlib import Path

from pydub import AudioSegment

from app.core.logging_config import get_logger
from app.models.voice_profiles import (
    get_voice_profile,
    add_emotion_tags,
    BRAINY_PROFILE,
    SNARKY_PROFILE
)
from app.services.maya1_client_v2 import maya1_client_v2 as maya1_client

# Fallback to gTTS
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

logger = get_logger(__name__)


class Maya1TTSService:
    """
    TTS service using Maya1 for Brainy & Snarky voices.
    Falls back to gTTS if Maya1 unavailable.
    """

    def __init__(self, use_maya1: bool = True):
        self.use_maya1 = use_maya1 and self._test_maya1_availability()
        self.maya1_available = self.use_maya1

        if self.use_maya1:
            logger.info("tts_service_initialized", provider="Maya1")
        else:
            logger.info("tts_service_initialized", provider="gTTS_fallback")

        # gTTS fallback settings
        self.gtts_brainy_lang = 'en-uk'
        self.gtts_snarky_lang = 'en-us'

    def _test_maya1_availability(self) -> bool:
        """Test if Maya1 is available."""
        try:
            return maya1_client.test_connection()
        except Exception as e:
            logger.warning("maya1_unavailable", error=str(e))
            return False

    def generate_audio_segment(
        self,
        text: str,
        speaker: str,
        add_emotions: bool = True,
    ) -> AudioSegment:
        """
        Generate audio for a single dialogue turn.

        Args:
            text: What to say
            speaker: "Brainy" or "Snarky"
            add_emotions: Whether to add automatic emotion tags

        Returns:
            AudioSegment object
        """
        logger.info(
            "generating_audio_segment",
            speaker=speaker,
            text_length=len(text),
            provider="Maya1" if self.use_maya1 else "gTTS"
        )

        if self.use_maya1:
            return self._generate_maya1(text, speaker, add_emotions)
        else:
            return self._generate_gtts_fallback(text, speaker)

    def _generate_maya1(
        self,
        text: str,
        speaker: str,
        add_emotions: bool
    ) -> AudioSegment:
        """Generate audio using Maya1."""
        try:
            # Get voice profile
            profile = get_voice_profile(speaker)

            # Add emotion tags if enabled
            enhanced_text = text
            if add_emotions:
                enhanced_text = add_emotion_tags(text, speaker)

            # Generate with Maya1
            audio = maya1_client.generate_audio(
                text=enhanced_text,
                voice_description=profile.description
            )

            logger.info(
                "maya1_audio_generated",
                speaker=speaker,
                duration_ms=len(audio)
            )

            return audio

        except Exception as e:
            logger.error(
                "maya1_generation_failed",
                speaker=speaker,
                error=str(e)
            )

            # Fall back to gTTS
            logger.info("falling_back_to_gtts")
            return self._generate_gtts_fallback(text, speaker)

    def _generate_gtts_fallback(
        self,
        text: str,
        speaker: str
    ) -> AudioSegment:
        """Generate audio using gTTS fallback."""
        if not GTTS_AVAILABLE:
            raise ImportError("gTTS not available and Maya1 failed")

        # Choose voice parameters
        lang = self.gtts_brainy_lang if speaker == "Brainy" else self.gtts_snarky_lang
        slow = (speaker == "Brainy")

        # Generate TTS
        tts = gTTS(text=text, lang=lang, slow=slow)

        # Save to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            temp_path = tmp_file.name
            tts.save(temp_path)

        # Load as AudioSegment
        audio = AudioSegment.from_mp3(temp_path)

        # Clean up
        os.unlink(temp_path)

        return audio

    def generate_episode_audio(
        self,
        script: List[Dict],
        output_path: str,
        silence_between_turns: int = 500,
        use_emotions: bool = True,
    ) -> Dict:
        """
        Generate full episode audio from script.

        Args:
            script: List of dialogue turns
            output_path: Where to save final audio
            silence_between_turns: Pause between speakers (ms)
            use_emotions: Enable automatic emotion tags (Maya1 only)

        Returns:
            Dict with metadata
        """
        logger.info(
            "generating_episode_audio",
            total_turns=len(script),
            output_path=output_path,
            provider="Maya1" if self.use_maya1 else "gTTS"
        )

        # Combine all audio segments
        full_audio = AudioSegment.empty()
        silence = AudioSegment.silent(duration=silence_between_turns)

        for i, turn in enumerate(script, 1):
            speaker = turn['speaker']
            text = turn['text']

            logger.info(
                "processing_turn",
                turn_number=i,
                speaker=speaker,
            )

            # Generate audio for this turn
            audio_segment = self.generate_audio_segment(
                text=text,
                speaker=speaker,
                add_emotions=use_emotions
            )

            # Add to full audio
            full_audio += audio_segment

            # Add silence between turns (except after last turn)
            if i < len(script):
                full_audio += silence

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        # Export final audio
        full_audio.export(output_path, format='mp3')

        # Calculate metadata
        duration_seconds = len(full_audio) / 1000.0
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        metadata = {
            'duration_seconds': duration_seconds,
            'duration_minutes': duration_seconds / 60,
            'file_size_mb': round(file_size_mb, 2),
            'total_turns': len(script),
            'output_path': output_path,
            'tts_provider': "Maya1" if self.use_maya1 else "gTTS",
            'emotions_enabled': use_emotions and self.use_maya1,
        }

        logger.info(
            "episode_audio_generated",
            **metadata
        )

        return metadata


# Global service instance
maya1_tts_service = Maya1TTSService(use_maya1=True)

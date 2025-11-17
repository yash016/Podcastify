"""
Text-to-Speech service using gTTS for Phase 0.
Will upgrade to Chatterbox in Phase 1.
"""

import os
import tempfile
from typing import List, Dict
from pathlib import Path

from gtts import gTTS
from pydub import AudioSegment
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class TTSService:
    """
    TTS service for generating Brainy & Snarky voices.
    Phase 0: Using gTTS (Google Text-to-Speech)
    Phase 1: Will upgrade to Chatterbox
    """

    def __init__(self):
        self.brainy_lang = 'en-uk'  # British English (formal)
        self.snarky_lang = 'en-us'  # American English (casual)
        self.brainy_slow = True      # Slower, more measured
        self.snarky_slow = False     # Faster, more energetic

        logger.info("tts_service_initialized", provider="gTTS")

    def generate_audio_segment(
        self,
        text: str,
        speaker: str,
    ) -> AudioSegment:
        """
        Generate audio for a single dialogue turn.

        Args:
            text: What to say
            speaker: "Brainy" or "Snarky"

        Returns:
            AudioSegment object
        """
        # Choose voice parameters
        if speaker == "Brainy":
            lang = self.brainy_lang
            slow = self.brainy_slow
        else:  # Snarky
            lang = self.snarky_lang
            slow = self.snarky_slow

        logger.info(
            "generating_audio_segment",
            speaker=speaker,
            text_length=len(text),
            lang=lang,
        )

        # Generate TTS
        tts = gTTS(text=text, lang=lang, slow=slow)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            temp_path = tmp_file.name
            tts.save(temp_path)

        # Load as AudioSegment
        audio = AudioSegment.from_mp3(temp_path)

        # Clean up temp file
        os.unlink(temp_path)

        return audio

    def generate_episode_audio(
        self,
        script: List[Dict],
        output_path: str,
        silence_between_turns: int = 500,  # milliseconds
    ) -> Dict:
        """
        Generate full episode audio from script.

        Args:
            script: List of dialogue turns
            output_path: Where to save final audio
            silence_between_turns: Pause between speakers (ms)

        Returns:
            Dict with metadata (duration, file size, etc.)
        """
        logger.info(
            "generating_episode_audio",
            total_turns=len(script),
            output_path=output_path,
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
            audio_segment = self.generate_audio_segment(text, speaker)

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
        }

        logger.info(
            "episode_audio_generated",
            **metadata
        )

        return metadata


# Global service instance
tts_service = TTSService()

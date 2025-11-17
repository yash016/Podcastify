"""
Kokoro TTS client using Gradio Client.
Connects to hexgrad/Kokoro-TTS Space on HuggingFace.

Kokoro-82M is a lightweight, high-quality TTS with:
- FREE unlimited quota (no rate limits)
- 82M parameters (efficient, fast)
- High quality voice synthesis
- Apache license (open source)
"""

import os
import tempfile
from typing import Optional
from pathlib import Path

from gradio_client import Client
from pydub import AudioSegment

from app.core.logging_config import get_logger
from app.models.voice_profiles import VoiceProfile

logger = get_logger(__name__)


class KokoroClient:
    """
    Client for Kokoro-82M TTS using Gradio Client.
    Connects to the Kokoro TTS HuggingFace Space.
    FREE and UNLIMITED fallback provider.
    """

    def __init__(self, hf_token: Optional[str] = None):
        self.space_name = "hexgrad/Kokoro-TTS"  # Official Kokoro TTS Space
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_API_KEY", None)
        self.client = None

        self._initialize_client()

    def _initialize_client(self):
        """Initialize Gradio client connection."""
        try:
            logger.info("initializing_kokoro_client", space=self.space_name)

            # Connect to Kokoro TTS Space (FREE, no token required but we provide it anyway)
            if self.hf_token:
                self.client = Client(self.space_name, hf_token=self.hf_token)
            else:
                self.client = Client(self.space_name)

            logger.info("kokoro_client_ready", space=self.space_name)

        except Exception as e:
            logger.error("kokoro_client_init_failed", error=str(e))
            self.client = None

    def generate_audio(
        self,
        text: str,
        voice_description: str,
        voice_preset: str = "af_heart",
        speed: float = 1.0,
    ) -> AudioSegment:
        """
        Generate audio using Kokoro-82M TTS.

        Args:
            text: Text to synthesize
            voice_description: Natural language voice description (used to select preset)
            voice_preset: Voice preset (default: "af_heart" - female voice)
                Options: af_heart, af_bella, af_sarah, am_adam, am_michael, bf_emma, bf_isabella, bm_george, bm_lewis
            speed: Speech speed (0.5-2.0), default 1.0

        Returns:
            AudioSegment with generated audio
        """
        if not self.client:
            raise Exception("Kokoro client not initialized")

        # Map voice descriptions to Kokoro presets
        preset = voice_preset
        desc_lower = voice_description.lower()

        # Select voice based on description
        if "female" in desc_lower or "woman" in desc_lower:
            if "british" in desc_lower:
                preset = "bf_emma"  # British female
            elif "warm" in desc_lower or "friendly" in desc_lower:
                preset = "af_heart"  # American female (warm)
            else:
                preset = "af_sarah"  # American female (neutral)
        elif "male" in desc_lower or "man" in desc_lower:
            if "british" in desc_lower:
                preset = "bm_george"  # British male
            elif "warm" in desc_lower or "friendly" in desc_lower:
                preset = "am_adam"  # American male (warm)
            else:
                preset = "am_michael"  # American male (neutral)

        logger.info(
            "kokoro_generate_request",
            text_length=len(text),
            voice_preset=preset,
            speed=speed
        )

        try:
            # Call Kokoro TTS Space
            result = self.client.predict(
                text=text,
                voice=preset,
                speed=speed,
                api_name="/generate_speech"
            )

            # Result can be a path string or tuple
            if isinstance(result, tuple):
                audio_path = result[0]
            else:
                audio_path = result

            logger.info("kokoro_audio_path_received", path=str(audio_path)[:100])

            # Load audio file
            if isinstance(audio_path, str):
                if audio_path.endswith('.wav'):
                    audio = AudioSegment.from_wav(audio_path)
                elif audio_path.endswith('.mp3'):
                    audio = AudioSegment.from_mp3(audio_path)
                else:
                    # Try as WAV by default
                    audio = AudioSegment.from_file(audio_path)
            else:
                # If it's a file handle, convert to path
                audio = AudioSegment.from_file(audio_path)

            logger.info(
                "kokoro_generate_success",
                audio_duration_ms=len(audio),
                provider="kokoro_82m",
                quota="UNLIMITED"
            )

            return audio

        except Exception as e:
            logger.error(
                "kokoro_generate_failed",
                error=str(e),
                provider="kokoro_82m"
            )
            raise

    def test_connection(self) -> bool:
        """Test if Kokoro TTS Space is accessible."""
        try:
            if self.client is None:
                self._initialize_client()

            if self.client:
                # Simple connection test - just verify the client is ready
                logger.info("kokoro_connection_test_passed", quota="UNLIMITED")
                return True

            return False

        except Exception as e:
            logger.warning("kokoro_connection_test_failed", error=str(e))
            return False


# Global client instance
kokoro_client = KokoroClient()

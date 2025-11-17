"""
Maya1 TTS client using Gradio Client.
Connects to maya-research/maya1 Space on HuggingFace.
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


class Maya1ClientV2:
    """
    Client for Maya1 TTS using Gradio Client.
    Connects to the Maya1 HuggingFace Space.
    """

    def __init__(self):
        self.space_name = "maya-research/maya1"
        self.hf_token = os.getenv("HUGGINGFACE_API_KEY", None)
        self.client = None

        self._initialize_client()

    def _initialize_client(self):
        """Initialize Gradio client connection."""
        try:
            logger.info("initializing_maya1_client", space=self.space_name)

            # Connect to Maya1 Space
            if self.hf_token:
                self.client = Client(self.space_name, hf_token=self.hf_token)
            else:
                self.client = Client(self.space_name)

            logger.info("maya1_client_ready", space=self.space_name)

        except Exception as e:
            logger.error("maya1_client_init_failed", error=str(e))
            self.client = None

    def generate_audio(
        self,
        text: str,
        voice_description: str,
        emotion_tag: Optional[str] = None,
    ) -> AudioSegment:
        """
        Generate audio using Maya1.

        Args:
            text: Text to synthesize
            voice_description: Natural language voice description
            emotion_tag: Optional emotion tag (e.g., "laugh", "sigh")

        Returns:
            AudioSegment with generated audio
        """
        if not self.client:
            raise Exception("Maya1 client not initialized")

        # Prepend emotion tag if provided
        if emotion_tag:
            text = f"<{emotion_tag}> {text}"

        logger.info(
            "maya1_generate_request",
            text_length=len(text),
            has_emotion=bool(emotion_tag),
            voice_desc_length=len(voice_description)
        )

        try:
            # Call Maya1 Space with correct parameters
            result = self.client.predict(
                preset_name="Male American",  # Can be customized
                description=voice_description,
                text=text,
                temperature=0.4,  # Default, can be tuned
                max_tokens=1500,  # Default
                api_name="/generate_speech"
            )

            # result is a tuple: (audio_filepath, status_message)
            audio_path = result[0]
            status = result[1]

            logger.info("maya1_generation_status", status=status)

            logger.info("maya1_audio_path_received", path=audio_path)

            # Load audio file
            if audio_path.endswith('.wav'):
                audio = AudioSegment.from_wav(audio_path)
            elif audio_path.endswith('.mp3'):
                audio = AudioSegment.from_mp3(audio_path)
            else:
                # Try as WAV by default
                audio = AudioSegment.from_file(audio_path)

            logger.info(
                "maya1_generate_success",
                audio_duration_ms=len(audio),
                provider="gradio_space"
            )

            return audio

        except Exception as e:
            logger.error(
                "maya1_generate_failed",
                error=str(e),
                provider="gradio_space"
            )
            raise

    def test_connection(self) -> bool:
        """Test if Maya1 Space is accessible."""
        try:
            if self.client is None:
                self._initialize_client()

            if self.client:
                # Test with a simple request
                result = self.client.predict(
                    preset_name="Male American",
                    description="neutral voice",
                    text="test",
                    temperature=0.4,
                    max_tokens=1500,
                    api_name="/generate_speech"
                )
                logger.info("maya1_connection_test_passed")
                return True

            return False

        except Exception as e:
            logger.warning("maya1_connection_test_failed", error=str(e))
            return False


# Global client instance
maya1_client_v2 = Maya1ClientV2()

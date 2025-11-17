"""
Parler TTS client for connecting to Colab-hosted Parler TTS server.

This client connects to a Parler TTS server running on Google Colab
and uses natural language voice descriptions for Brainy and Snarky.
"""

import os
import requests
import tempfile
from typing import Optional
from pathlib import Path

from pydub import AudioSegment
from dotenv import load_dotenv

# Load .env file to get PARLER_URL
load_dotenv()

from app.core.logging_config import get_logger
from app.models.voice_profiles import VoiceProfile

logger = get_logger(__name__)


class ParlerClient:
    """
    Client for Parler TTS server running on Google Colab.

    Parler TTS uses natural language descriptions to control voice characteristics.
    Supports 34 pre-trained speaker voices with customizable attributes.
    """

    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or os.getenv("PARLER_URL", "http://localhost:8000")
        self.server_url = self.server_url.rstrip("/")  # Remove trailing slash

        logger.info("parler_client_initialized", server_url=self.server_url)

    def test_connection(self) -> bool:
        """Test if Parler TTS server is accessible."""
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5,
                headers={"ngrok-skip-browser-warning": "true"}
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(
                    "parler_connection_test_passed",
                    status=data.get("status"),
                    model_loaded=data.get("model_loaded"),
                    gpu_available=data.get("gpu_available")
                )
                return True
            else:
                logger.warning(
                    "parler_connection_test_failed_status",
                    status_code=response.status_code
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.warning("parler_connection_test_failed", error=str(e))
            return False

    def generate_audio(
        self,
        text: str,
        speaker: str,  # "Brainy" or "Snarky"
        timeout: int = 120,  # Increased for parallel processing
    ) -> AudioSegment:
        """
        Generate audio using Parler TTS server.

        Args:
            text: Text to synthesize
            speaker: Speaker name ("Brainy" or "Snarky")
            timeout: Request timeout in seconds

        Returns:
            AudioSegment with generated audio

        Raises:
            Exception if generation fails
        """
        logger.info(
            "parler_generate_request",
            text_length=len(text),
            speaker=speaker,
            server=self.server_url
        )

        try:
            # Call Parler TTS server
            response = requests.post(
                f"{self.server_url}/generate",
                json={
                    "text": text,
                    "speaker": speaker
                },
                timeout=timeout,
                headers={"ngrok-skip-browser-warning": "true"}
            )

            response.raise_for_status()

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name

            # Load as AudioSegment
            audio = AudioSegment.from_wav(tmp_path)

            # Cleanup
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning("failed_to_cleanup_temp_file", path=tmp_path, error=str(e))

            logger.info(
                "parler_generate_success",
                audio_duration_ms=len(audio),
                speaker=speaker,
                response_size=len(response.content)
            )

            return audio

        except requests.exceptions.Timeout:
            error_msg = f"Parler TTS request timed out after {timeout}s"
            logger.error("parler_timeout", error=error_msg, speaker=speaker)
            raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Parler TTS request failed: {str(e)}"
            logger.error("parler_request_failed", error=error_msg, speaker=speaker)
            raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Parler TTS generation failed: {str(e)}"
            logger.error("parler_generation_failed", error=error_msg, speaker=speaker)
            raise Exception(error_msg)


# Global client instance
parler_client = ParlerClient()

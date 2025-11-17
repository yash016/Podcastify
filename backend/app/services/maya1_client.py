"""
Maya1 TTS client for generating high-quality voices.
Supports both HuggingFace API and local deployment.
"""

import os
import requests
import tempfile
from typing import Optional
from pathlib import Path

import soundfile as sf
from pydub import AudioSegment

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.voice_profiles import VoiceProfile

logger = get_logger(__name__)


class Maya1Client:
    """
    Client for Maya1 TTS model.
    Phase 0: Uses HuggingFace Inference API
    Phase 1: Will support local deployment
    """

    def __init__(self):
        self.provider = os.getenv("MAYA1_PROVIDER", "huggingface_api")
        self.model_id = os.getenv("MAYA1_MODEL", "maya-research/maya1")
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY", "")

        if self.provider == "huggingface_api":
            self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
            logger.info(
                "maya1_client_initialized",
                provider="huggingface_api",
                model=self.model_id
            )
        else:
            # Local deployment (Phase 1)
            self.api_url = "http://localhost:8002/generate"
            logger.info(
                "maya1_client_initialized",
                provider="local",
                endpoint=self.api_url
            )

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
        # Prepend emotion tag if provided
        if emotion_tag:
            text = f"<{emotion_tag}> {text}"

        logger.info(
            "maya1_generate_request",
            text_length=len(text),
            has_emotion=bool(emotion_tag),
            voice_desc_length=len(voice_description)
        )

        if self.provider == "huggingface_api":
            return self._generate_hf_api(text, voice_description)
        else:
            return self._generate_local(text, voice_description)

    def _generate_hf_api(self, text: str, voice_description: str) -> AudioSegment:
        """Generate audio via HuggingFace Inference API."""
        headers = {}
        if self.hf_api_key:
            headers["Authorization"] = f"Bearer {self.hf_api_key}"

        # Maya1 API format (based on HF Spaces)
        payload = {
            "inputs": {
                "text": text,
                "description": voice_description
            },
            "parameters": {
                "max_new_tokens": 2048,
                "temperature": 0.8,
            }
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 503:
                # Model is loading
                logger.warning("maya1_model_loading", retry_after=20)
                raise Exception("Maya1 model is loading, please retry in 20 seconds")

            response.raise_for_status()

            # Save response audio to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                tmp_file.write(response.content)
                temp_path = tmp_file.name

            # Load as AudioSegment
            audio = AudioSegment.from_wav(temp_path)

            # Clean up
            os.unlink(temp_path)

            logger.info(
                "maya1_generate_success",
                audio_duration_ms=len(audio),
                provider="hf_api"
            )

            return audio

        except Exception as e:
            logger.error(
                "maya1_generate_failed",
                error=str(e),
                provider="hf_api"
            )
            raise

    def _generate_local(self, text: str, voice_description: str) -> AudioSegment:
        """Generate audio via local Maya1 deployment (Phase 1)."""
        # This will be implemented in Phase 1
        raise NotImplementedError("Local Maya1 deployment not yet implemented")

    def test_connection(self) -> bool:
        """Test if Maya1 service is accessible."""
        try:
            if self.provider == "huggingface_api":
                # Test with simple request
                headers = {}
                if self.hf_api_key:
                    headers["Authorization"] = f"Bearer {self.hf_api_key}"

                response = requests.get(
                    self.api_url,
                    headers=headers,
                    timeout=5
                )

                # 503 means model is loading (still accessible)
                # 200 means ready
                if response.status_code in [200, 503]:
                    logger.info("maya1_connection_test_passed")
                    return True

            return False

        except Exception as e:
            logger.error("maya1_connection_test_failed", error=str(e))
            return False


# Global client instance
maya1_client = Maya1Client()

"""
Chatterbox TTS client - supports both local HTTP API and HuggingFace Space.

Chatterbox features:
- First open-source TTS with emotion exaggeration control
- Parameter-based emotion intensity (0.0 to 1.0)
- Benchmarked favorably vs ElevenLabs
- Multilingual (30+ languages)
- Fast generation speed
- UNLIMITED generation when running locally
"""

import os
import tempfile
import requests
from typing import Optional
from pathlib import Path

from gradio_client import Client
from pydub import AudioSegment

from app.core.logging_config import get_logger
from app.models.voice_profiles import VoiceProfile

logger = get_logger(__name__)


class ChatterboxClient:
    """
    Client for Chatterbox TTS - supports both local API and HuggingFace Space.

    Modes:
    - Local: Uses HTTP API (unlimited, free, fast)
    - Remote: Uses Gradio client to HuggingFace Space (quota limited)
    """

    def __init__(self, hf_token: Optional[str] = None):
        # Check if we should use local Chatterbox
        self.use_local = os.getenv("USE_LOCAL_CHATTERBOX", "false").lower() == "true"
        self.local_url = os.getenv("CHATTERBOX_URL", "http://localhost:4123")

        # Remote HuggingFace Space configuration
        self.space_name = "ResembleAI/Chatterbox"
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_API_KEY", None)
        self.client = None

        if self.use_local:
            logger.info("chatterbox_mode", mode="local", url=self.local_url)
        else:
            logger.info("chatterbox_mode", mode="remote", space=self.space_name)
            self._initialize_client()

    def _initialize_client(self):
        """Initialize Gradio client connection."""
        try:
            logger.info("initializing_chatterbox_client", space=self.space_name)

            # Connect to Chatterbox Space
            if self.hf_token:
                self.client = Client(self.space_name, hf_token=self.hf_token)
            else:
                self.client = Client(self.space_name)

            logger.info("chatterbox_client_ready", space=self.space_name)

        except Exception as e:
            logger.error("chatterbox_client_init_failed", error=str(e))
            self.client = None

    def generate_audio(
        self,
        text: str,
        voice_description: str,
        exaggeration: float = 0.5,
        cfg: float = 0.5,
    ) -> AudioSegment:
        """
        Generate audio using Chatterbox (local or remote).

        Args:
            text: Text to synthesize
            voice_description: Text-based voice description
                Example: "A British male speaker with formal, measured tone"
            exaggeration: Emotion exaggeration intensity (0.0-1.0)
                - 0.0: Monotone, flat
                - 0.3: Subtle emotion (good for Brainy)
                - 0.7: Dramatic emotion (good for Snarky)
                - 1.0: Maximum expressiveness
            cfg: Classifier-free guidance scale (0.0-1.0), default 0.5

        Returns:
            AudioSegment with generated audio
        """
        logger.info(
            "chatterbox_generate_request",
            text_length=len(text),
            exaggeration=exaggeration,
            cfg=cfg,
            voice_desc_length=len(voice_description),
            mode="local" if self.use_local else "remote"
        )

        try:
            if self.use_local:
                return self._generate_audio_local(text, voice_description, exaggeration, cfg)
            else:
                return self._generate_audio_remote(text, voice_description, exaggeration, cfg)

        except Exception as e:
            logger.error(
                "chatterbox_generate_failed",
                error=str(e),
                mode="local" if self.use_local else "remote"
            )
            raise

    def _generate_audio_local(
        self,
        text: str,
        voice_description: str,
        exaggeration: float,
        cfg: float,
    ) -> AudioSegment:
        """
        Generate audio using local Chatterbox HTTP API (OpenAI-compatible format).

        Note: Local Chatterbox uses OpenAI-compatible API which doesn't support
        voice_description, exaggeration, or cfg parameters. It uses the voice
        sample configured in the Docker container's .env file.
        """
        try:
            # Call local Chatterbox API (OpenAI-compatible format)
            url = f"{self.local_url}/audio/speech"

            # OpenAI-compatible payload - only 'input' field required
            payload = {
                "input": text,  # OpenAI uses 'input' instead of 'text'
            }

            logger.info(
                "calling_local_chatterbox",
                url=url,
                text_length=len(text),
                note="Voice parameters ignored (uses configured voice sample)"
            )

            # Longer timeout for CPU inference (can take 2-3 min per request)
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()

            # Save response to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name

            # Load audio file
            audio = AudioSegment.from_wav(tmp_path)

            # Clean up temp file
            os.unlink(tmp_path)

            logger.info(
                "chatterbox_generate_success",
                audio_duration_ms=len(audio),
                provider="local_http_api_unlimited"
            )

            return audio

        except Exception as e:
            logger.error("local_chatterbox_failed", error=str(e))
            raise

    def _generate_audio_remote(
        self,
        text: str,
        voice_description: str,
        exaggeration: float,
        cfg: float,
    ) -> AudioSegment:
        """Generate audio using remote HuggingFace Space via Gradio client."""
        if not self.client:
            raise Exception("Chatterbox client not initialized")

        try:
            # Call Chatterbox Space
            # Try without api_name first (auto-detect), then fallback to common names
            try:
                result = self.client.predict(
                    text,
                    voice_description,
                    exaggeration,
                    cfg
                )
            except Exception as e1:
                logger.warning("chatterbox_auto_detect_failed", error=str(e1))
                # Try common API endpoint names
                for api_name in ["/generate", "/synthesize", "/tts", "/predict"]:
                    try:
                        logger.info("trying_api_endpoint", endpoint=api_name)
                        result = self.client.predict(
                            text,
                            voice_description,
                            exaggeration,
                            cfg,
                            api_name=api_name
                        )
                        logger.info("chatterbox_endpoint_found", endpoint=api_name)
                        break
                    except:
                        continue
                else:
                    raise e1

            # Result format varies by Space implementation
            if isinstance(result, tuple):
                audio_path = result[0]
                logger.info("chatterbox_generation_metadata", metadata=result[1] if len(result) > 1 else "none")
            else:
                audio_path = result

            logger.info("chatterbox_audio_path_received", path=audio_path)

            # Load audio file
            if audio_path.endswith('.wav'):
                audio = AudioSegment.from_wav(audio_path)
            elif audio_path.endswith('.mp3'):
                audio = AudioSegment.from_mp3(audio_path)
            else:
                # Try as WAV by default
                audio = AudioSegment.from_file(audio_path)

            logger.info(
                "chatterbox_generate_success",
                audio_duration_ms=len(audio),
                provider="gradio_space"
            )

            return audio

        except Exception as e:
            logger.error("remote_chatterbox_failed", error=str(e))
            raise

    def test_connection(self) -> bool:
        """Test if Chatterbox (local or remote) is accessible."""
        try:
            if self.use_local:
                # Test local Chatterbox health endpoint
                health_url = f"{self.local_url}/health"
                response = requests.get(health_url, timeout=5)
                response.raise_for_status()
                health_data = response.json()
                logger.info("local_chatterbox_health_check", status=health_data.get("status"))
                return health_data.get("status") == "healthy"
            else:
                # Test remote Gradio Space
                if self.client is None:
                    self._initialize_client()

                if self.client:
                    # Test with a simple request (auto-detect endpoint)
                    result = self.client.predict(
                        "test",
                        "neutral voice",
                        0.5,
                        0.5
                    )
                    logger.info("chatterbox_connection_test_passed")
                    return True

                return False

        except Exception as e:
            logger.warning("chatterbox_connection_test_failed", error=str(e), mode="local" if self.use_local else "remote")
            return False


# Global client instance
chatterbox_client = ChatterboxClient()

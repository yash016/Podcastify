"""
Higgs Audio V2 TTS client using Gradio Client.
Connects to bosonai/higgs-audio-v2 Space on HuggingFace.

Higgs Audio V2 is SOTA TTS with:
- 20+ emotion support
- Auto-prosody adaptation
- Multi-speaker dialogue generation
- Beats GPT-4o-mini on emotion tasks
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


class HiggsAudioClient:
    """
    Client for Higgs Audio V2 TTS using Gradio Client.
    Connects to the Higgs Audio V2 HuggingFace Space.
    """

    def __init__(self, hf_token: Optional[str] = None):
        self.space_name = "smola/higgs_audio_v2"  # Community Gradio Space for Higgs Audio V2
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_API_KEY", None)
        self.client = None

        self._initialize_client()

    def _initialize_client(self):
        """Initialize Gradio client connection."""
        try:
            logger.info("initializing_higgs_client", space=self.space_name)

            # Connect to Higgs Audio V2 Space
            if self.hf_token:
                self.client = Client(self.space_name, hf_token=self.hf_token)
            else:
                self.client = Client(self.space_name)

            logger.info("higgs_client_ready", space=self.space_name)

        except Exception as e:
            logger.error("higgs_client_init_failed", error=str(e))
            self.client = None

    def generate_audio(
        self,
        text: str,
        voice_description: str,
        emotion: Optional[str] = None,
        temperature: float = 0.7,
        reference_audio_path: Optional[str] = None,
        reference_text: Optional[str] = None,
    ) -> AudioSegment:
        """
        Generate audio using Higgs Audio V2 with optional voice cloning.

        Args:
            text: Text to synthesize
            voice_description: Natural language voice description
                Example: "A warm, friendly British male voice with measured pacing"
            emotion: Optional emotion hint (Higgs has auto-prosody, so this is optional)
            temperature: Sampling temperature (0.0-1.5), default 0.7
            reference_audio_path: Path to reference audio for voice cloning (3-10 sec)
            reference_text: Transcript of reference audio (for better voice cloning)

        Returns:
            AudioSegment with generated audio
        """
        if not self.client:
            raise Exception("Higgs client not initialized")

        # Build system prompt with voice description and emotion
        system_prompt = f"Generate audio following instruction.\n\n<|scene_desc_start|>\n{voice_description}"
        if emotion:
            system_prompt += f" {emotion} emotion."
        system_prompt += "\n<|scene_desc_end|>"

        # Map voice descriptions to presets if possible
        voice_preset = "EMPTY"  # Let model use description
        if "british" in voice_description.lower() or "warm" in voice_description.lower():
            voice_preset = "chadwick"  # British male
        elif "female" in voice_description.lower() or "woman" in voice_description.lower():
            voice_preset = "mabel"  # Female
        elif "male" in voice_description.lower() or "man" in voice_description.lower():
            voice_preset = "en_man"  # Male

        logger.info(
            "higgs_generate_request",
            text_length=len(text),
            voice_preset=voice_preset,
            has_emotion=bool(emotion)
        )

        try:
            # Use reference audio if provided (for voice cloning consistency)
            ref_audio_file = None
            ref_text_content = reference_text

            if reference_audio_path:
                # Higgs expects file handle, not path
                ref_audio_file = reference_audio_path
                logger.info("using_reference_audio", path=reference_audio_path[:50])

            # Call Higgs Audio V2 Space with correct endpoint
            result = self.client.predict(
                text=text,
                voice_preset=voice_preset,
                reference_audio=ref_audio_file,
                reference_text=ref_text_content,
                max_completion_tokens=1024,
                temperature=temperature,
                top_p=0.95,
                top_k=50,
                system_prompt=system_prompt,
                stop_strings={'headers': ['stops'], 'data': [['<|end_of_text|>'], ['<|eot_id|>']], 'metadata': None},
                ras_win_len=7,
                ras_win_max_num_repeat=2,
                api_name="/generate_speech"
            )

            # Result is (model_response, generated_audio)
            if isinstance(result, tuple):
                model_response, audio_path = result
                logger.info("higgs_model_response", response=model_response[:100] if model_response else "none")
            else:
                audio_path = result

            logger.info("higgs_audio_path_received", path=audio_path)

            # Load audio file
            if audio_path.endswith('.wav'):
                audio = AudioSegment.from_wav(audio_path)
            elif audio_path.endswith('.mp3'):
                audio = AudioSegment.from_mp3(audio_path)
            else:
                # Try as WAV by default
                audio = AudioSegment.from_file(audio_path)

            logger.info(
                "higgs_generate_success",
                audio_duration_ms=len(audio),
                provider="higgs_audio_v2"
            )

            return audio

        except Exception as e:
            logger.error(
                "higgs_generate_failed",
                error=str(e),
                provider="higgs_audio_v2"
            )
            raise

    def test_connection(self) -> bool:
        """Test if Higgs Audio V2 Space is accessible."""
        try:
            if self.client is None:
                self._initialize_client()

            if self.client:
                # Simple connection test - just verify the client is ready
                # Don't actually generate audio to save quota
                logger.info("higgs_connection_test_passed")
                return True

            return False

        except Exception as e:
            logger.warning("higgs_connection_test_failed", error=str(e))
            return False


# Global client instance
higgs_client = HiggsAudioClient()

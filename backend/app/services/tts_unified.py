"""
Parler TTS service - simplified, Colab-hosted only.

Uses Parler TTS running on Google Colab via ngrok tunnel.
No fallbacks, no quota limits, no token rotation.

Features:
- High-quality voice synthesis with natural prosody
- Per-speaker voice profiles (Brainy & Snarky)
- Precise turn timing metadata for synchronization
- Parallel generation for 3x faster audio creation
- Simple, fast, reliable
"""

import os
import asyncio
from typing import List, Dict
from pathlib import Path

from pydub import AudioSegment

from app.core.logging_config import get_logger
from app.models.voice_profiles import get_voice_profile
from app.services.parler_client import ParlerClient

logger = get_logger(__name__)


class UnifiedTTSService:
    """
    Parler TTS service - Colab-hosted, no fallbacks.
    """

    def __init__(self):
        # Initialize only Parler client
        self.parler_client = ParlerClient()
        self.parler_available = self.parler_client.test_connection()

        logger.info(
            "tts_service_initialized",
            parler_available=self.parler_available,
            provider="parler_only"
        )

    async def generate_episode_audio(
        self,
        script: List[Dict],
        output_path: str,
        silence_between_turns: int = 400,
        use_emotions: bool = True,
    ) -> Dict:
        """
        Generate full episode audio using Parler TTS.

        Args:
            script: List of dialogue turns
            output_path: Where to save final audio
            silence_between_turns: Pause between speakers (ms)
            use_emotions: Enable automatic emotion tags (unused for Parler)

        Returns:
            Dict with metadata including turn_timings for synchronization

        Raises:
            Exception: If Parler TTS is unavailable or generation fails
        """
        logger.info(
            "generating_episode_audio_parler",
            total_turns=len(script),
            output_path=output_path
        )

        # Check Parler availability
        if not self.parler_available:
            raise Exception(
                "Parler TTS is not available. "
                "Please check that your Colab notebook is running and "
                f"the ngrok URL is correct in .env: PARLER_URL"
            )

        try:
            # Generate audio with Parler (parallel processing for 3x speedup)
            full_audio, turn_timings = await self._generate_with_parler_parallel(
                script=script,
                silence_between_turns=silence_between_turns
            )

            # Save audio
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
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
                'tts_provider_used': 'parler',
                'tts_providers_available': {
                    'parler': self.parler_available,
                },
                'emotions_enabled': use_emotions,
                'voice_consistency': 'guaranteed',
                'turn_timings': turn_timings,
            }

            logger.info(
                "episode_audio_generated_successfully",
                provider="parler",
                duration_seconds=duration_seconds,
                turn_count=len(script),
                file_size_mb=metadata['file_size_mb']
            )

            return metadata

        except Exception as e:
            logger.error(
                "parler_generation_failed",
                error=str(e),
                turns_attempted=len(script)
            )
            raise Exception(f"Parler TTS generation failed: {str(e)}")

    async def _generate_with_parler_parallel(
        self,
        script: List[Dict],
        silence_between_turns: int,
        max_concurrent: int = 2  # Reduced from 4 to avoid overloading Parler server
    ) -> tuple[AudioSegment, List[Dict]]:
        """
        Generate audio for all turns using Parler TTS with parallel processing.

        Args:
            script: List of dialogue turns
            silence_between_turns: Pause duration (ms)
            max_concurrent: Maximum concurrent TTS requests (default: 4)

        Returns:
            Tuple of (full_audio, turn_timings)
        """
        silence = AudioSegment.silent(duration=silence_between_turns)

        logger.info(
            "starting_parler_generation_parallel",
            turn_count=len(script),
            silence_ms=silence_between_turns,
            max_concurrent=max_concurrent
        )

        # Generate all turns in parallel with async wrapper
        async def generate_turn(i: int, turn: Dict):
            """Generate a single turn asynchronously."""
            speaker = turn.get("speaker", "Brainy")
            text = turn.get("text", "")

            logger.debug(
                "generating_turn_parallel",
                turn_index=i,
                speaker=speaker,
                text_length=len(text)
            )

            # Run synchronous generate_audio in thread pool
            audio_segment = await asyncio.to_thread(
                self.parler_client.generate_audio,
                text=text,
                speaker=speaker
            )

            logger.debug(
                "turn_generated_parallel",
                turn_index=i,
                duration_ms=len(audio_segment)
            )

            return i, audio_segment, turn

        # Process all turns with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_limit(i, turn):
            async with semaphore:
                return await generate_turn(i, turn)

        # Generate all turns concurrently
        tasks = [generate_with_limit(i, turn) for i, turn in enumerate(script)]
        results = await asyncio.gather(*tasks)

        # Sort by turn index to ensure correct order
        results.sort(key=lambda x: x[0])

        # Stitch audio in order and calculate timings
        full_audio = AudioSegment.empty()
        turn_timings = []
        cumulative_ms = 0

        for i, audio_segment, turn in results:
            speaker = turn.get("speaker", "Brainy")
            turn_duration_ms = len(audio_segment)

            turn_timings.append({
                "turn_index": i,
                "start_ms": cumulative_ms,
                "end_ms": cumulative_ms + turn_duration_ms,
                "duration_ms": turn_duration_ms,
                "speaker": speaker,
                "section_id": turn.get('section_id', '')
            })

            # Add to full audio
            full_audio += audio_segment
            cumulative_ms += turn_duration_ms

            # Add silence between turns (except after last turn)
            if i < len(script) - 1:
                full_audio += silence
                cumulative_ms += silence_between_turns

        logger.info(
            "parler_generation_complete_parallel",
            total_duration_ms=cumulative_ms,
            total_turns=len(script)
        )

        return full_audio, turn_timings


# Global service instance
unified_tts_service = UnifiedTTSService()

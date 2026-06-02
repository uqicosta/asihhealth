"""
AsihHealth - Text-to-Speech Module
Primary: edge-tts (Microsoft Edge voices) - Best free Indonesian quality in 2026
Alternative: Piper TTS (for fully offline)
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, List
from config.settings import TTS_VOICE, OUTPUT_AUDIO
from core.voice_cloning import generate_cloned_voiceover

logger = logging.getLogger(__name__)


class EdgeTTS:
    """Wrapper around edge-tts for high-quality Indonesian voiceover."""

    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or TTS_VOICE
        self._validate_edge_tts()

    def _validate_edge_tts(self):
        try:
            import edge_tts
        except ImportError:
            raise ImportError(
                "edge-tts is required. Install with: pip install edge-tts"
            )

    async def _synthesize_async(self, text: str, output_path: Path) -> Path:
        """Internal async synthesis."""
        import edge_tts

        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(str(output_path))
        return output_path

    def synthesize(
        self,
        text: str,
        output_filename: Optional[str] = None,
        rate: str = "+0%",
        volume: str = "+0%"
    ) -> Path:
        """
        Convert text to natural Indonesian speech.

        Args:
            text: Full script text
            output_filename: Custom filename (default: auto-generated)
            rate: Speed adjustment (e.g. "+15%", "-10%")
            volume: Volume adjustment

        Returns:
            Path to generated .wav or .mp3 file
        """
        if not output_filename:
            # Simple hash for filename
            import hashlib
            text_hash = hashlib.md5(text[:100].encode()).hexdigest()[:8]
            output_filename = f"voice_{text_hash}.mp3"

        output_path = OUTPUT_AUDIO / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating voiceover with voice: {self.voice}")
        logger.info(f"Text length: {len(text)} characters")

        # edge-tts supports rate and volume via Communicate
        import edge_tts

        async def _run():
            communicate = edge_tts.Communicate(
                text,
                self.voice,
                rate=rate,
                volume=volume
            )
            await communicate.save(str(output_path))

        asyncio.run(_run())

        logger.info(f"Voiceover saved: {output_path}")
        return output_path

    @staticmethod
    def list_indonesian_voices() -> List[str]:
        """List all available Indonesian voices."""
        try:
            result = subprocess.run(
                ["edge-tts", "--list-voices"],
                capture_output=True,
                text=True,
                check=True
            )
            lines = result.stdout.splitlines()
            id_voices = [line.strip() for line in lines if "id-ID" in line]
            return id_voices
        except Exception as e:
            logger.warning(f"Could not list voices via CLI: {e}")
            # Fallback known good voices
            return [
                "id-ID-AndikaNeural",
                "id-ID-GadisNeural",
                "id-ID-ArdiNeural",
            ]


def generate_voiceover(
    script_text: str,
    voice: Optional[str] = None,
    output_name: Optional[str] = None,
    clone_reference: Optional[Path] = None
) -> Path:
    """
    High-level convenience function.
    - Jika clone_reference diberikan dan valid → pakai voice cloning (XTTS)
    - Else → pakai edge-tts (gratis, bagus untuk ID)
    """
    if clone_reference and clone_reference.exists():
        cloned = generate_cloned_voiceover(script_text, clone_reference, output_name)
        if cloned:
            return cloned
        logger.warning("Cloning gagal, fallback ke edge-tts...")

    tts = EdgeTTS(voice=voice)
    return tts.synthesize(script_text, output_filename=output_name)


def estimate_duration(text: str, wpm: int = 145) -> float:
    """
    Estimate audio duration in minutes.
    Indonesian speech rate is roughly 140-155 words per minute.
    """
    words = len(text.split())
    minutes = words / wpm
    return round(minutes, 1)

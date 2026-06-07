"""
Edge-TTS provider (Microsoft Azure voices via edge-tts).
"""

import asyncio
import hashlib
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

from config.settings import TTS_VOICE, OUTPUT_AUDIO

from .base import TTSProvider
from .utils import clean_text_for_tts

logger = logging.getLogger(__name__)

# Fallback voices
FALLBACK_VOICE = "id-ID-AndikaNeural"


class EdgeTTSProvider(TTSProvider):
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

    def generate(self, script_text: str, output_name: Optional[str] = None) -> Path:
        cleaned_text = clean_text_for_tts(script_text)

        if not output_name:
            text_hash = hashlib.md5(script_text[:100].encode()).hexdigest()[:8]
            output_name = f"voice_{text_hash}.mp3"

        output_path = OUTPUT_AUDIO / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating voiceover with voice: {self.voice}")
        logger.info(f"Text length: {len(cleaned_text)} characters")

        import edge_tts
        from edge_tts.exceptions import NoAudioReceived

        async def _run(voice_to_use: str, use_rate_volume: bool = True, rate: str = "+0%", volume: str = "+0%"):
            communicate = edge_tts.Communicate(
                cleaned_text,
                voice_to_use,
                rate=rate if use_rate_volume else "+0%",
                volume=volume if use_rate_volume else "+0%"
            )
            await communicate.save(str(output_path))

        attempts = [
            (self.voice, True),
            (self.voice, False),
            (FALLBACK_VOICE, True),
        ]

        last_exception = None
        for i, (voice_to_try, use_rv) in enumerate(attempts):
            try:
                logger.info(f"Attempt {i+1}: voice={voice_to_try}, rate/volume={use_rv}")
                asyncio.run(_run(voice_to_try, use_rv))
                if output_path.exists() and output_path.stat().st_size > 0:
                    self.voice = voice_to_try
                    logger.info(f"Voiceover berhasil dibuat dengan voice: {voice_to_try}")
                    logger.info(f"Voiceover saved: {output_path}")
                    return output_path
            except NoAudioReceived as e:
                last_exception = e
                logger.warning(f"NoAudioReceived pada attempt {i+1} dengan voice {voice_to_try}")
            except Exception as e:
                last_exception = e
                logger.warning(f"Error pada attempt {i+1}: {e}")

        error_msg = (
            f"Tidak bisa menghasilkan audio dengan voice '{self.voice}'.\n"
            f"Error: {last_exception}\n\n"
            "Solusi:\n"
            "1. Pastikan voice valid. Jalankan: python scripts/list_voices.py\n"
            "2. Coba voice lain, misalnya id-ID-GadisNeural\n"
            "3. Periksa koneksi internet (edge-tts butuh online)\n"
            "4. Kurangi panjang script atau coba lagi nanti\n"
            f"5. Voice yang dicoba: {self.voice}"
        )
        logger.error(error_msg)
        raise NoAudioReceived(error_msg)

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
            return [
                "id-ID-AndikaNeural",
                "id-ID-GadisNeural",
                "id-ID-ArdiNeural",
            ]

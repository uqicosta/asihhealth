"""
XTTS / Voice Cloning provider (local Coqui XTTS).
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from config.settings import TTS_REFERENCE_AUDIO, OUTPUT_AUDIO

from .base import TTSProvider

logger = logging.getLogger(__name__)


class XTTSTTSProvider(TTSProvider):
    """Local XTTS provider (delegates to voice_cloning module)."""

    def generate(self, script_text: str, output_name: Optional[str] = None, reference_audio: Optional[Path] = None) -> Path:
        from core.voice_cloning import generate_cloned_voiceover

        ref = reference_audio or (Path(TTS_REFERENCE_AUDIO) if TTS_REFERENCE_AUDIO else None)

        if not ref or not ref.exists():
            raise FileNotFoundError(
                "Untuk TTS_PROVIDER=xtts, Anda perlu menyediakan TTS_REFERENCE_AUDIO "
                "(file audio 10-30 detik) di .env"
            )

        if not output_name:
            h = hashlib.md5(script_text[:100].encode()).hexdigest()[:8]
            output_name = f"voice_{h}.wav"

        return generate_cloned_voiceover(script_text, ref, output_name)

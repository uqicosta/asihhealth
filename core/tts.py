"""
AsihHealth - Text-to-Speech Module (thin public interface)

The implementation has been split for maintainability:

core/tts/
    __init__.py
    utils.py          # shared helpers (clean_text, split, concat)
    base.py           # TTSProvider + BaseChunkedTTSProvider
    edge.py
    piper.py
    openai.py
    elevenlabs.py
    xtts.py

Public API (backward compatible):
    - generate_voiceover(script_text, voice=None, output_name=None, clone_reference=None)
    - estimate_duration(text, wpm=145)
"""

import logging
from pathlib import Path
from typing import Optional

from config.settings import TTS_PROVIDER, TTS_VOICE, TTS_REFERENCE_AUDIO

from .tts.edge import EdgeTTSProvider
from .tts.piper import PiperTTSProvider
from .tts.openai import OpenAIProvider
from .tts.elevenlabs import ElevenLabsProvider
from .tts.xtts import XTTSTTSProvider

logger = logging.getLogger(__name__)


def generate_voiceover(
    script_text: str,
    voice: Optional[str] = None,
    output_name: Optional[str] = None,
    clone_reference: Optional[Path] = None,
) -> Path:
    """
    High-level dispatcher based on TTS_PROVIDER in .env.

    Supported providers:
      - edge-tts (default)
      - piper
      - xtts / voice-clone
      - openai
      - elevenlabs
    """
    provider = TTS_PROVIDER.lower().strip()

    # Explicit clone_reference always prefers XTTS
    if clone_reference and clone_reference.exists():
        logger.info("Using XTTS because reference audio was provided")
        try:
            return XTTSTTSProvider().generate(script_text, output_name, clone_reference)
        except Exception as e:
            logger.warning(f"XTTS failed: {e}. Falling back to configured provider...")

    if provider == "piper":
        return PiperTTSProvider().generate(script_text, output_name)

    elif provider in ("xtts", "voice-clone", "xtts-v2"):
        ref = clone_reference or (Path(TTS_REFERENCE_AUDIO) if TTS_REFERENCE_AUDIO else None)
        return XTTSTTSProvider().generate(script_text, output_name, ref)

    elif provider == "openai":
        return OpenAIProvider().generate(script_text, output_name)

    elif provider in ("elevenlabs", "eleven", "11labs", "eleven-labs", "elevenlabs-tts"):
        return ElevenLabsProvider().generate(script_text, output_name)

    else:
        # Default: edge-tts
        if clone_reference and clone_reference.exists():
            from core.voice_cloning import generate_cloned_voiceover
            cloned = generate_cloned_voiceover(script_text, clone_reference, output_name)
            if cloned:
                return cloned
            logger.warning("Voice cloning failed, falling back to edge-tts...")

        tts = EdgeTTSProvider(voice=voice)
        return tts.generate(script_text, output_name)


def estimate_duration(text: str, wpm: int = 145) -> float:
    """
    Estimate audio duration in minutes.
    Indonesian speech rate ≈ 140-155 words per minute.
    """
    words = len(text.split())
    minutes = words / wpm
    return round(minutes, 1)

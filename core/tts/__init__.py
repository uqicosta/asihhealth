"""
core.tts package

Split implementation of TTS providers for better maintainability.
"""

from .utils import clean_text_for_tts
from .edge import EdgeTTSProvider
from .piper import PiperTTSProvider
from .openai import OpenAIProvider
from .elevenlabs import ElevenLabsProvider
from .xtts import XTTSTTSProvider

__all__ = [
    "clean_text_for_tts",
    "EdgeTTSProvider",
    "PiperTTSProvider",
    "OpenAIProvider",
    "ElevenLabsProvider",
    "XTTSTTSProvider",
]

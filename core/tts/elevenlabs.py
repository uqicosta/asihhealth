"""
ElevenLabs TTS provider.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from config.settings import (
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL,
    ELEVENLABS_STABILITY, ELEVENLABS_SIMILARITY, OUTPUT_AUDIO
)

from .base import BaseChunkedTTSProvider
from .utils import clean_text_for_tts

logger = logging.getLogger(__name__)


class ElevenLabsProvider(BaseChunkedTTSProvider):
    """ElevenLabs TTS provider with chunking support."""

    def _get_chunk_max_chars(self) -> int:
        return 4500

    def _generate_single_chunk(self, text: str, **kwargs) -> bytes:
        import requests

        if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
            raise ValueError("ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID are required.")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY,
        }
        voice_settings = {
            "stability": max(0.0, min(1.0, ELEVENLABS_STABILITY)),
            "similarity_boost": max(0.0, min(1.0, ELEVENLABS_SIMILARITY)),
        }
        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": voice_settings,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        return resp.content

    def generate(self, script_text: str, output_name: Optional[str] = None) -> Path:
        if not ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY belum diset di .env.")
        if not ELEVENLABS_VOICE_ID:
            raise ValueError("ELEVENLABS_VOICE_ID belum diset di .env.")

        if not output_name:
            h = hashlib.md5(script_text[:100].encode()).hexdigest()[:8]
            output_name = f"voice_{h}.mp3"

        output_path = OUTPUT_AUDIO / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cleaned_text = clean_text_for_tts(script_text)

        logger.info(
            f"Generating ElevenLabs TTS voiceover (model={ELEVENLABS_MODEL}, voice_id={ELEVENLABS_VOICE_ID[:8]}...)"
        )

        try:
            return self.generate_chunked(
                cleaned_text,
                output_path,
                provider_name="ElevenLabs TTS",
            )
        except Exception as e:
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass

            if "HTTPError" in str(type(e)) or hasattr(e, "response"):
                resp = getattr(e, "response", None)
                status = getattr(resp, "status_code", "?") if resp else "?"
                err_detail = ""
                try:
                    if resp is not None:
                        err_detail = resp.json().get("detail", {}).get("message", str(e))
                except Exception:
                    err_detail = str(e)

                logger.error(f"ElevenLabs TTS HTTP error ({status}): {err_detail}")
                raise RuntimeError(f"ElevenLabs TTS gagal (HTTP {status}): {err_detail}") from e

            logger.error(f"ElevenLabs TTS gagal: {e}")
            raise RuntimeError(f"ElevenLabs TTS synthesis gagal: {e}") from e

"""
OpenAI TTS provider.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from config.settings import OPENAI_API_KEY, OPENAI_TTS_MODEL, OPENAI_TTS_VOICE, OUTPUT_AUDIO

from .base import BaseChunkedTTSProvider
from .utils import clean_text_for_tts

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseChunkedTTSProvider):
    """OpenAI TTS provider with automatic chunking for long scripts."""

    def _get_chunk_max_chars(self) -> int:
        return 4000

    def _generate_single_chunk(self, text: str, **kwargs) -> bytes:
        import requests

        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI TTS.")

        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENAI_TTS_MODEL,
            "input": text,
            "voice": OPENAI_TTS_VOICE,
            "response_format": "mp3",
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        return resp.content

    def generate(self, script_text: str, output_name: Optional[str] = None) -> Path:
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY belum diset di .env.\n\n"
                "Cara setup OpenAI TTS:\n"
                "1. Buka https://platform.openai.com/api-keys\n"
                "2. Buat API key\n"
                "3. Tambahkan OPENAI_API_KEY + TTS_PROVIDER=openai di .env"
            )

        if not output_name:
            h = hashlib.md5(script_text[:100].encode()).hexdigest()[:8]
            output_name = f"voice_{h}.mp3"

        output_path = OUTPUT_AUDIO / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cleaned_text = clean_text_for_tts(script_text)

        logger.info(
            f"Generating OpenAI TTS voiceover (model={OPENAI_TTS_MODEL}, voice={OPENAI_TTS_VOICE})"
        )

        try:
            return self.generate_chunked(
                cleaned_text,
                output_path,
                provider_name="OpenAI TTS",
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
                        err_detail = resp.json().get("error", {}).get("message", str(e))
                except Exception:
                    err_detail = str(e)
                logger.error(f"OpenAI TTS HTTP error: {err_detail}")
                raise RuntimeError(
                    f"OpenAI TTS gagal (HTTP {status}):\n{err_detail}\n\n"
                    "Pastikan OPENAI_API_KEY, model dan voice benar."
                ) from e

            logger.error(f"OpenAI TTS gagal: {e}")
            raise RuntimeError(
                f"OpenAI TTS synthesis gagal: {e}\n\n"
                "Cek koneksi internet, API key, dan quota."
            ) from e

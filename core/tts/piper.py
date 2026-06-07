"""
Piper TTS provider (local, fast, offline).
"""

import hashlib
import logging
import wave
from pathlib import Path
from typing import Optional

from config.settings import PIPER_MODEL, PIPER_CONFIG, OUTPUT_AUDIO

from .base import TTSProvider
from .utils import clean_text_for_tts

logger = logging.getLogger(__name__)


class PiperTTSProvider(TTSProvider):
    """Local Piper TTS (very reliable, offline, fast)."""

    def generate(self, script_text: str, output_name: Optional[str] = None) -> Path:
        if not PIPER_MODEL or not Path(PIPER_MODEL).exists():
            raise FileNotFoundError(
                f"Piper model tidak ditemukan. Set PIPER_MODEL di .env ke file .onnx yang valid.\n"
                f"Contoh Indonesian voice: id_ID-fahmi-medium.onnx (download dari HuggingFace piper-voices)"
            )

        if not output_name:
            h = hashlib.md5(script_text[:100].encode()).hexdigest()[:8]
            output_name = f"voice_{h}.wav"

        output_path = OUTPUT_AUDIO / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from piper import PiperVoice

            config_path = PIPER_CONFIG or (str(PIPER_MODEL) + ".json")
            if not Path(config_path).exists():
                config_path = str(PIPER_MODEL).replace(".onnx", ".json")
                if not Path(config_path).exists():
                    raise FileNotFoundError(f"Piper config tidak ditemukan di {config_path}.")

            voice = PiperVoice.load(PIPER_MODEL, config_path=config_path)

            # Normalize text
            cleaned_text = " ".join(script_text.split())

            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(voice.config.sample_rate)
                voice.synthesize(cleaned_text, wav_file)

            file_size = output_path.stat().st_size
            if file_size < 128:
                output_path.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Piper menghasilkan file audio kosong (0 KB).\n"
                    f"File size: {file_size} bytes\n\n"
                    "Penyebab umum:\n"
                    "• espeak-ng belum terinstall\n"
                    "• Model voice tidak kompatibel\n\n"
                    "Solusi:\n"
                    "1. Install espeak-ng.\n"
                    "2. Jalankan ulang: python scripts/download_piper_voice.py\n"
                    "3. Ganti ke TTS_PROVIDER=xtts atau openai."
                )

            logger.info(f"Piper voiceover saved: {output_path} ({file_size} bytes)")
            return output_path

        except Exception as e:
            if output_path.exists():
                try:
                    output_path.unlink()
                except:
                    pass
            logger.error(f"Piper TTS gagal: {e}")
            if isinstance(e, RuntimeError) and "Piper menghasilkan" in str(e):
                raise
            raise RuntimeError(
                f"Piper synthesis gagal: {e}\n"
                "Pastikan PIPER_MODEL dan PIPER_CONFIG di .env benar.\n"
                "Jalankan: python scripts/download_piper_voice.py"
            ) from e

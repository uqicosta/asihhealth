"""
AsihHealth - Voice Cloning (Cost Efficient & Offline)

Menggunakan Coqui XTTS-v2 (open source) untuk voice cloning.
- Butuh reference audio pendek (5-30 detik) suara yang jelas dalam Bahasa Indonesia.
- Kualitas cloning cukup baik untuk narasi kesehatan.
- Fully local setelah model di-download pertama kali.

Installation (opsional, cukup berat):
    # WAJIB: Python 3.9 atau 3.10 (TTS package TIDAK support Python 3.11+)
    py -3.10 -m pip install TTS
    # Windows CPU fix:
    py -3.10 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

Model XTTS (~2GB) akan di-download otomatis pertama kali.

Jika tidak terinstall atau Python salah, sistem akan error dengan pesan instalasi yang jelas + saran downgrade Python.

Cara pakai di pipeline:
    python pipeline/run.py --topic "..." --voice-clone assets/voices/reference/narator_saya.wav
    # atau set di .env:
    # TTS_PROVIDER=xtts
    # TTS_REFERENCE_AUDIO=assets/voices/reference/narator_saya.wav
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from config.settings import OUTPUT_AUDIO

logger = logging.getLogger(__name__)

# XTTS (TTS package) is not compatible with Python 3.11+
# Many versions on PyPI have "Requires-Python >=3.7.0,<3.11"
MIN_PYTHON = (3, 7)
MAX_PYTHON = (3, 10)  # inclusive

def _check_python_version():
    version = sys.version_info[:2]
    if not (MIN_PYTHON <= version <= MAX_PYTHON):
        msg = (
            f"❌ XTTS / TTS package requires Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} and < {MAX_PYTHON[0]+1}.0\n"
            f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n\n"
            "Recommended: Use Python 3.9 or 3.10 for XTTS (banyak user berhasil dengan 3.10).\n\n"
            "On Windows (recommended):\n"
            "  1. Download & install Python 3.10: https://www.python.org/downloads/release/python-31013/\n"
            "  2. Use the py launcher (sudah include di installer):\n"
            "     py -3.10 -m venv .venv\n"
            "     .venv\\Scripts\\Activate.ps1\n"
            "     py -3.10 -m pip install -r requirements.txt\n"
            "     py -3.10 pipeline/run.py --topic \"...\"\n\n"
            "Alternative pakai Conda (paling gampang):\n"
            "  conda create -n asih python=3.10 -y\n"
            "  conda activate asih\n"
            "  pip install -r requirements.txt\n\n"
            "Lalu set di .env:\n"
            "  TTS_PROVIDER=xtts\n"
            "  TTS_REFERENCE_AUDIO=assets/voices/reference/narator.wav\n\n"
            "Alternative kalau males ganti Python:\n"
            "  - TTS_PROVIDER=piper (butuh espeak-ng di Windows)\n"
            "  - atau TTS_PROVIDER=edge-tts (online, kadang unreliable)"
        )
        logger.error(msg)
        raise RuntimeError(msg)


class VoiceCloner:
    def __init__(self, reference_audio: Optional[Path] = None, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.reference_audio = reference_audio
        self.model_name = model_name
        self.tts = None
        self.available = False
        self.last_error = None
        self._try_load_model()

    def _try_load_model(self):
        """Coba load XTTS. Kalau gagal (tidak terinstall), available = False."""
        _check_python_version()

        if not self.reference_audio or not self.reference_audio.exists():
            self.last_error = "No reference audio provided for voice cloning."
            logger.info(self.last_error)
            return

        try:
            from TTS.api import TTS
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading XTTS voice cloning model on {device}... (first time will download ~2GB)")

            self.tts = TTS(self.model_name).to(device)
            self.available = True
            logger.info("Voice cloning ready (XTTS-v2).")
        except ImportError as e:
            self.last_error = "TTS (Coqui) or torch not installed. Install with: pip install TTS"
            logger.warning(self.last_error)
            self.available = False
        except Exception as e:
            self.last_error = f"Failed to initialize voice cloner: {e}"
            logger.warning(self.last_error)
            self.available = False

    def synthesize(self, text: str, output_filename: Optional[str] = None) -> Optional[Path]:
        """
        Generate cloned voice audio.
        Returns path to audio file, or None if cloning not available.
        """
        if not self.available or not self.tts or not self.reference_audio:
            return None

        if not output_filename:
            import hashlib
            h = hashlib.md5(text[:80].encode()).hexdigest()[:8]
            output_filename = f"cloned_voice_{h}.wav"

        output_path = OUTPUT_AUDIO / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            logger.info("Generating voice with cloned speaker (XTTS)...")
            self.tts.tts_to_file(
                text=text,
                speaker_wav=str(self.reference_audio),
                language="id",   # Indonesian
                file_path=str(output_path)
            )
            logger.info(f"Cloned voice saved: {output_path}")
            return output_path
        except Exception as e:
            self.last_error = f"XTTS synthesis failed during tts_to_file: {e}"
            logger.error(self.last_error)
            return None


def generate_cloned_voiceover(
    script_text: str,
    reference_audio: Path,
    output_name: Optional[str] = None
) -> Optional[Path]:
    """High level helper. Raises RuntimeError with details on failure."""
    cloner = VoiceCloner(reference_audio=reference_audio)
    if not cloner.available:
        error_msg = cloner.last_error or "Voice cloning not available. Please install TTS / torch."
        logger.error(error_msg)
        raise RuntimeError(
            f"XTTS gagal diinisialisasi: {error_msg}\n\n"
            "Lihat pesan error versi Python di atas. "
            "Kamu harus pakai Python 3.9 atau 3.10."
        )
    result = cloner.synthesize(script_text, output_name)
    if not result and cloner.last_error:
        raise RuntimeError(
            f"XTTS synthesis gagal: {cloner.last_error}\n\n"
            "Pastikan Anda menggunakan Python 3.9 atau 3.10 (lihat pesan versi Python di atas).\n"
            "Model ~2GB akan di-download otomatis pertama kali saat load."
        )
    return result

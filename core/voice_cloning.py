"""
AsihHealth - Voice Cloning (Cost Efficient & Offline)

Menggunakan Coqui XTTS-v2 (open source) untuk voice cloning.
- Butuh reference audio pendek (5-30 detik) suara yang jelas dalam Bahasa Indonesia.
- Kualitas cloning cukup baik untuk narasi kesehatan.
- Fully local setelah model di-download pertama kali.

Installation (opsional, cukup berat):
    pip install TTS torch torchaudio

Jika tidak terinstall, sistem akan fallback ke edge-tts biasa.

Cara pakai di pipeline:
    python pipeline/run.py --topic "..." --voice-clone assets/voices/reference/narator_saya.wav
"""

import logging
from pathlib import Path
from typing import Optional
from config.settings import OUTPUT_AUDIO

logger = logging.getLogger(__name__)


class VoiceCloner:
    def __init__(self, reference_audio: Optional[Path] = None, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.reference_audio = reference_audio
        self.model_name = model_name
        self.tts = None
        self.available = False
        self._try_load_model()

    def _try_load_model(self):
        """Coba load XTTS. Kalau gagal (tidak terinstall), available = False."""
        if not self.reference_audio or not self.reference_audio.exists():
            logger.info("No reference audio provided for voice cloning.")
            return

        try:
            from TTS.api import TTS
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading XTTS voice cloning model on {device}... (first time will download ~2GB)")

            self.tts = TTS(self.model_name).to(device)
            self.available = True
            logger.info("Voice cloning ready (XTTS-v2).")
        except ImportError:
            logger.warning("TTS (Coqui) not installed. Voice cloning disabled. Fallback to edge-tts.")
            logger.warning("Install with: pip install TTS")
            self.available = False
        except Exception as e:
            logger.warning(f"Failed to initialize voice cloner: {e}")
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
            logger.error(f"Voice cloning synthesis failed: {e}")
            return None


def generate_cloned_voiceover(
    script_text: str,
    reference_audio: Path,
    output_name: Optional[str] = None
) -> Optional[Path]:
    """High level helper."""
    cloner = VoiceCloner(reference_audio=reference_audio)
    if not cloner.available:
        logger.warning("Voice cloning not available. Please install TTS or provide valid reference.")
        return None
    return cloner.synthesize(script_text, output_name)

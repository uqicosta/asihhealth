"""
AsihHealth - Text-to-Speech Module

Pilihan provider (set di .env TTS_PROVIDER):
- edge-tts : gratis, kualitas bagus untuk ID, tapi kadang unreliable (online) - default
- xtts     : local XTTS (Coqui), lebih reliable, butuh reference audio + pip install TTS (+ torch)
- piper    : local Piper, paling ringan & cepat (offline), butuh espeak-ng di Windows

Untuk daily/scheduler generation, sangat direkomendasikan pakai local (xtts atau piper).
Lihat QUICKSTART.md untuk instalasi detail.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, List

from config.settings import (
    TTS_PROVIDER, TTS_VOICE, TTS_REFERENCE_AUDIO,
    OUTPUT_AUDIO,
    PIPER_MODEL, PIPER_CONFIG
)
from core.voice_cloning import generate_cloned_voiceover

logger = logging.getLogger(__name__)

# Fallback voice yang terbukti bagus untuk Bahasa Indonesia
FALLBACK_VOICE = "id-ID-AndikaNeural"
SAFE_VOICES = ["id-ID-AndikaNeural", "id-ID-GadisNeural"]


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

        # Bersihkan teks dari karakter yang bisa bermasalah untuk TTS
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Teks untuk voiceover kosong.")

        # Ganti karakter aneh yang kadang muncul dari LLM
        cleaned_text = (
            cleaned_text
            .replace("—", "-")
            .replace("–", "-")
            .replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
            .replace("…", "...")
        )

        logger.info(f"Generating voiceover with voice: {self.voice}")
        logger.info(f"Text length: {len(cleaned_text)} characters")

        import edge_tts
        from edge_tts.exceptions import NoAudioReceived

        async def _run(voice_to_use: str, use_rate_volume: bool = True):
            communicate = edge_tts.Communicate(
                cleaned_text,
                voice_to_use,
                rate=rate if use_rate_volume else "+0%",
                volume=volume if use_rate_volume else "+0%"
            )
            await communicate.save(str(output_path))

        # Coba beberapa strategi jika gagal
        attempts = [
            (self.voice, True),                    # Voice pilihan user + rate/volume
            (self.voice, False),                   # Voice pilihan user tanpa rate/volume
            (FALLBACK_VOICE, True),                # Fallback voice
        ]

        last_exception = None
        for i, (voice_to_try, use_rv) in enumerate(attempts):
            try:
                logger.info(f"Attempt {i+1}: voice={voice_to_try}, rate/volume={use_rv}")
                asyncio.run(_run(voice_to_try, use_rv))
                if output_path.exists() and output_path.stat().st_size > 0:
                    self.voice = voice_to_try  # update jika berhasil dengan fallback
                    logger.info(f"Voiceover berhasil dibuat dengan voice: {voice_to_try}")
                    logger.info(f"Voiceover saved: {output_path}")
                    return output_path
            except NoAudioReceived as e:
                last_exception = e
                logger.warning(f"NoAudioReceived pada attempt {i+1} dengan voice {voice_to_try}")
            except Exception as e:
                last_exception = e
                logger.warning(f"Error pada attempt {i+1}: {e}")

        # Jika semua gagal
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
            # Fallback known good voices
            return [
                "id-ID-AndikaNeural",
                "id-ID-GadisNeural",
                "id-ID-ArdiNeural",
            ]


def generate_piper_voiceover(
    script_text: str,
    output_name: Optional[str] = None,
) -> Path:
    """Generate using local Piper TTS (very reliable, offline, fast)."""
    if not PIPER_MODEL or not Path(PIPER_MODEL).exists():
        raise FileNotFoundError(
            f"Piper model tidak ditemukan. Set PIPER_MODEL di .env ke file .onnx yang valid.\n"
            f"Contoh Indonesian voice: id_ID-fahmi-medium.onnx (download dari HuggingFace piper-voices)"
        )

    if not output_name:
        import hashlib
        h = hashlib.md5(script_text[:100].encode()).hexdigest()[:8]
        output_name = f"voice_{h}.wav"

    output_path = OUTPUT_AUDIO / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from piper import PiperVoice
        import wave

        config_path = PIPER_CONFIG or (str(PIPER_MODEL) + ".json")
        if not Path(config_path).exists():
            # Try common naming
            config_path = str(PIPER_MODEL).replace(".onnx", ".json")
            if not Path(config_path).exists():
                raise FileNotFoundError(f"Piper config tidak ditemukan di {config_path}. Pastikan file .json ada di samping .onnx")

        voice = PiperVoice.load(PIPER_MODEL, config_path=config_path)

        # Normalize text for better phonemization (newlines and extra spaces can cause issues)
        cleaned_text = " ".join(script_text.split())

        with wave.open(str(output_path), "wb") as wav_file:
            # Set params explicitly BEFORE synthesize to prevent 
            # "wave.Error: # channels not specified" when the file is closed.
            # This can happen if synthesize fails early or in certain piper versions.
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(voice.config.sample_rate)

            voice.synthesize(cleaned_text, wav_file)

        # Verify we actually got audio data.
        # Piper sometimes "succeeds" but writes no frames (0-byte or tiny header-only file)
        # especially on Windows without espeak-ng, or with incompatible voices/text.
        file_size = output_path.stat().st_size
        if file_size < 128:  # Typical WAV header is ~44 bytes; anything under ~128 is suspicious
            output_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Piper menghasilkan file audio kosong (0 KB).\n"
                f"File size: {file_size} bytes\n\n"
                "Penyebab umum:\n"
                "• espeak-ng belum terinstall (penting di Windows untuk phonemization)\n"
                "  Download: https://github.com/espeak-ng/espeak-ng/releases\n"
                "• Model voice tidak kompatibel atau rusak\n"
                "• Teks mengandung terlalu banyak karakter khusus / terlalu pendek\n\n"
                "Solusi:\n"
                "1. Install espeak-ng, lalu coba lagi.\n"
                "2. Jalankan ulang: python scripts/download_piper_voice.py (coba voice lain)\n"
                "3. Ganti ke TTS_PROVIDER=xtts + TTS_REFERENCE_AUDIO (lebih robust di Windows)\n"
                "4. Pastikan PIPER_MODEL dan config json benar di .env"
            )

        logger.info(f"Piper voiceover saved: {output_path} ({file_size} bytes)")
        return output_path
    except Exception as e:
        # Clean up partial/corrupt file
        if output_path.exists():
            try:
                output_path.unlink()
            except:
                pass
        logger.error(f"Piper TTS gagal: {e}")
        # Re-raise with more context
        if isinstance(e, RuntimeError) and "Piper menghasilkan" in str(e):
            raise  # already good message
        raise RuntimeError(
            f"Piper synthesis gagal: {e}\n"
            "Pastikan:\n"
            "• PIPER_MODEL dan PIPER_CONFIG di .env benar\n"
            "• Model .onnx kompatibel dengan piper-tts package\n"
            "• File config .json ada (biasanya sama nama dengan .onnx + .json)\n\n"
            "Cara termudah: jalankan helper script:\n"
            "  python scripts/download_piper_voice.py\n\n"
            "Atau download manual dari https://huggingface.co/rhasspy/piper-voices/tree/main/id"
        ) from e


def generate_xtts_voiceover(
    script_text: str,
    output_name: Optional[str] = None,
    reference_audio: Optional[Path] = None,
) -> Path:
    """Generate using local XTTS (reliable offline, good multilingual ID support)."""
    ref = reference_audio or (Path(TTS_REFERENCE_AUDIO) if TTS_REFERENCE_AUDIO else None)

    if not ref or not ref.exists():
        raise FileNotFoundError(
            "Untuk TTS_PROVIDER=xtts, Anda perlu menyediakan TTS_REFERENCE_AUDIO "
            "(file audio 10-30 detik suara jelas dalam Bahasa Indonesia) di .env\n\n"
            "Contoh di .env:\nTTS_PROVIDER=xtts\nTTS_REFERENCE_AUDIO=assets/voices/reference/narator.wav\n\n"
            "Lihat QUICKSTART.md untuk langkah instalasi TTS dan XTTS."
        )

    if not output_name:
        import hashlib
        h = hashlib.md5(script_text[:100].encode()).hexdigest()[:8]
        output_name = f"voice_{h}.wav"

    # Reuse the existing cloner (it handles XTTS). It will raise detailed error if fails.
    return generate_cloned_voiceover(script_text, ref, output_name)


def generate_voiceover(
    script_text: str,
    voice: Optional[str] = None,
    output_name: Optional[str] = None,
    clone_reference: Optional[Path] = None,
) -> Path:
    """
    High-level dispatcher berdasarkan TTS_PROVIDER di .env.

    Provider yang didukung:
    - edge-tts (default, online)
    - xtts     (local, lebih reliable)
    - piper    (local, paling cepat & reliable untuk automation)
    """
    provider = TTS_PROVIDER.lower().strip()

    # Jika user kasih explicit clone_reference, prioritaskan XTTS
    if clone_reference and clone_reference.exists():
        logger.info("Menggunakan XTTS karena reference audio disediakan")
        try:
            return generate_xtts_voiceover(script_text, output_name, clone_reference)
        except Exception as e:
            logger.warning(f"XTTS gagal: {e}. Fallback ke provider default...")

    if provider == "piper":
        return generate_piper_voiceover(script_text, output_name)

    elif provider in ("xtts", "voice-clone", "xtts-v2"):
        ref = clone_reference or (Path(TTS_REFERENCE_AUDIO) if TTS_REFERENCE_AUDIO else None)
        return generate_xtts_voiceover(script_text, output_name, ref)

    else:
        # Default / edge-tts
        if clone_reference and clone_reference.exists():
            cloned = generate_cloned_voiceover(script_text, clone_reference, output_name)
            if cloned:
                return cloned
            logger.warning("Cloning gagal, fallback ke edge-tts...")

        try:
            tts = EdgeTTS(voice=voice)
            return tts.synthesize(script_text, output_filename=output_name)
        except Exception as e:
            if "NoAudioReceived" in str(type(e)) or "No audio was received" in str(e):
                helpful_msg = (
                    "\n❌ Gagal generate voiceover dengan edge-tts.\n"
                    f"Voice: {voice or TTS_VOICE}\n\n"
                    "Karena edge-tts kurang reliable (online), pertimbangkan:\n"
                    "• Set TTS_PROVIDER=xtts + TTS_REFERENCE_AUDIO (local, lebih stabil)\n"
                    "• Atau TTS_PROVIDER=piper (paling reliable & offline)\n\n"
                    "Lihat detail di .env.example dan QUICKSTART.md"
                )
                logger.error(helpful_msg)
            raise


def estimate_duration(text: str, wpm: int = 145) -> float:
    """
    Estimate audio duration in minutes.
    Indonesian speech rate is roughly 140-155 words per minute.
    """
    words = len(text.split())
    minutes = words / wpm
    return round(minutes, 1)

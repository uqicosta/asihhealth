"""
AsihHealth - Text-to-Speech Module

Pilihan provider (set di .env TTS_PROVIDER):
- edge-tts   : gratis, kualitas bagus untuk ID, tapi kadang unreliable (online) - default
- xtts       : local XTTS (Coqui), lebih reliable, butuh reference audio + pip install TTS (+ torch)
- piper      : local Piper, paling ringan & cepat (offline), butuh espeak-ng di Windows
- openai     : reliable paid cloud API via OpenAI TTS (mudah setup, kualitas bagus, tanpa install berat). Auto-splits long scripts.
- elevenlabs : premium cloud via ElevenLabs (kualitas sangat natural & emosional, support ID bagus via multilingual_v2).
               Butuh ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID. Auto-splits long scripts + FFmpeg concat.

Untuk daily/scheduler generation, sangat direkomendasikan pakai local (xtts atau piper) atau cloud reliable (openai / elevenlabs).
Lihat QUICKSTART.md untuk instalasi detail.
"""

import asyncio
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List

from config.settings import (
    TTS_PROVIDER, TTS_VOICE, TTS_REFERENCE_AUDIO,
    OUTPUT_AUDIO,
    PIPER_MODEL, PIPER_CONFIG,
    OPENAI_API_KEY, OPENAI_TTS_MODEL, OPENAI_TTS_VOICE,
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL,
    ELEVENLABS_STABILITY, ELEVENLABS_SIMILARITY,
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


def _split_text_into_chunks(text: str, max_chars: int = 4000) -> list[str]:
    """
    Split long narration text into chunks safe for OpenAI TTS (max 4096 chars per request).
    Prefers natural sentence/paragraph boundaries to avoid cutting words mid-sentence.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    # Split while trying to keep sentence punctuation attached
    # Matches common Indonesian/English sentence endings + whitespace or blank lines
    parts = re.split(r'([.!?。！？]\s+|\n\s*\n+)', text)

    sentences: list[str] = []
    i = 0
    while i < len(parts):
        chunk = parts[i]
        if i + 1 < len(parts) and re.match(r'[.!?。！？]\s+|\n\s*\n+', parts[i + 1]):
            chunk += parts[i + 1]
            i += 2
        else:
            i += 1
        s = chunk.strip()
        if s:
            sentences.append(s)

    if not sentences:
        sentences = [text]

    chunks: list[str] = []
    current = ""

    for sent in sentences:
        if len(current) + len(" " + sent) <= max_chars:
            current = (current + " " + sent).strip() if current else sent
        else:
            if current:
                chunks.append(current)
            current = sent

            # Hard split any single sentence/paragraph that is still too long
            while len(current) > max_chars:
                # Prefer breaking at a space near the limit
                break_point = current.rfind(" ", 0, max_chars - 50)
                if break_point < 100:  # avoid creating tiny leading fragments
                    break_point = max_chars
                piece = current[:break_point].strip()
                if piece:
                    chunks.append(piece)
                current = current[break_point:].strip()

    if current:
        chunks.append(current)

    # Ultimate safety: hard chunk anything still over limit
    final_chunks: list[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            final_chunks.append(c)
        else:
            for j in range(0, len(c), max_chars):
                final_chunks.append(c[j : j + max_chars])

    return [c for c in final_chunks if c.strip()]


def _concat_mp3_chunks_ffmpeg(chunk_paths: list[Path], output_path: Path) -> None:
    """
    Concatenate multiple MP3 files into one using FFmpeg's concat demuxer.

    Uses stream copy (-c copy) for speed and zero quality loss.
    Uses only FFmpeg (already required by the project) so it works on Python 3.13+ without audioop/pyaudioop.
    """
    if not chunk_paths:
        raise ValueError("Tidak ada chunk audio untuk digabungkan")

    if len(chunk_paths) == 1:
        # Simple copy for the single-chunk case (shouldn't normally reach here)
        import shutil
        shutil.copy2(chunk_paths[0], output_path)
        return

    # Write concat list file (FFmpeg concat demuxer format)
    concat_list = output_path.with_name(f"{output_path.stem}.concat.txt")
    try:
        with open(concat_list, "w", encoding="utf-8") as f:
            for p in chunk_paths:
                # Use absolute path and properly escape for the concat protocol
                safe_path = str(p.resolve()).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",           # Important: no re-encoding
            str(output_path)
        ]

        logger.info(f"FFmpeg: Menggabungkan {len(chunk_paths)} potongan audio (concat demuxer)...")
        logger.debug(" ".join(cmd))

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            logger.error("FFmpeg concat gagal.")
            if result.stderr:
                logger.error(result.stderr[-2000:])
            raise RuntimeError(
                "Gagal menggabungkan potongan audio dengan FFmpeg.\n"
                "Pastikan FFmpeg terinstall dan ada di PATH."
            )
    finally:
        # Always clean up the temporary list file
        concat_list.unlink(missing_ok=True)


def generate_openai_voiceover(
    script_text: str,
    output_name: Optional[str] = None,
) -> Path:
    """
    Generate voiceover using OpenAI TTS API (reliable, high quality, zero local heavy deps).

    Requires OPENAI_API_KEY in .env.
    Supports Indonesian text natively.
    Uses mp3 output (compatible with rest of pipeline via ffmpeg).

    Long scripts (> ~4000 chars) are automatically split into multiple API calls
    (on sentence boundaries when possible) and the audio chunks are concatenated.
    """
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY belum diset di .env.\n\n"
            "Cara setup OpenAI TTS (reliable API option):\n"
            "1. Buka https://platform.openai.com/api-keys\n"
            "2. Buat API key baru (copy secret)\n"
            "3. Tambahkan di .env:\n"
            "   OPENAI_API_KEY=sk-...\n"
            "   TTS_PROVIDER=openai\n"
            "   # Opsional:\n"
            "   OPENAI_TTS_VOICE=onyx   # onyx | nova | alloy | echo | shimmer | fable\n"
            "   OPENAI_TTS_MODEL=tts-1  # tts-1 (murah) atau tts-1-hd (kualitas lebih tinggi)\n\n"
            "Biaya sangat rendah: ~$0.015 per 1.000 kata (tts-1) / ~$0.030 (tts-1-hd)."
        )

    if not output_name:
        import hashlib
        h = hashlib.md5(script_text[:100].encode()).hexdigest()[:8]
        output_name = f"voice_{h}.mp3"

    output_path = OUTPUT_AUDIO / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Clean text similar to edge-tts
    cleaned_text = (
        script_text.strip()
        .replace("—", "-")
        .replace("–", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("…", "...")
    )
    if not cleaned_text:
        raise ValueError("Teks untuk voiceover kosong.")

    chunks = _split_text_into_chunks(cleaned_text, max_chars=4000)
    logger.info(
        f"Generating OpenAI TTS voiceover (model={OPENAI_TTS_MODEL}, voice={OPENAI_TTS_VOICE}) "
        f"— {len(chunks)} chunk(s), total {len(cleaned_text)} chars"
    )

    try:
        import requests

        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        if len(chunks) == 1:
            # Fast path: single request
            payload = {
                "model": OPENAI_TTS_MODEL,
                "input": chunks[0],
                "voice": OPENAI_TTS_VOICE,
                "response_format": "mp3",
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=180)
            resp.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(resp.content)

        else:
            # Multi-chunk: synthesize to temp files then concat with FFmpeg
            # (avoids audioop/pyaudioop dependency that pydub needs on Python 3.13+)
            chunk_files: list[Path] = []

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                for idx, chunk in enumerate(chunks):
                    payload = {
                        "model": OPENAI_TTS_MODEL,
                        "input": chunk,
                        "voice": OPENAI_TTS_VOICE,
                        "response_format": "mp3",
                    }
                    resp = requests.post(url, headers=headers, json=payload, timeout=180)
                    resp.raise_for_status()

                    chunk_path = tmpdir_path / f"tts_chunk_{idx:03d}.mp3"
                    chunk_path.write_bytes(resp.content)
                    chunk_files.append(chunk_path)
                    logger.info(f"  Chunk {idx+1}/{len(chunks)} synthesized ({len(chunk)} chars)")

                # Concatenate MP3s using FFmpeg concat demuxer (fast, stream copy, no re-encode)
                _concat_mp3_chunks_ffmpeg(chunk_files, output_path)
                logger.info(f"  Concatenated {len(chunks)} chunks with FFmpeg → final audio")

        file_size = output_path.stat().st_size
        if file_size < 100:
            output_path.unlink(missing_ok=True)
            raise RuntimeError("OpenAI TTS mengembalikan audio kosong / terlalu kecil.")

        logger.info(f"OpenAI TTS voiceover saved: {output_path} ({file_size} bytes)")
        return output_path

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", "?")
        err_detail = ""
        try:
            if e.response is not None:
                err_detail = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            err_detail = str(e)
        logger.error(f"OpenAI TTS HTTP error: {err_detail}")
        raise RuntimeError(
            f"OpenAI TTS gagal (HTTP {status}):\n{err_detail}\n\n"
            "Pastikan:\n"
            "• OPENAI_API_KEY valid dan ada kredit\n"
            "• Model valid: tts-1 atau tts-1-hd\n"
            "• Voice valid: onyx, nova, alloy, echo, shimmer, fable\n"
            "• Teks per chunk <= 4096 karakter (kami sudah auto-split berdasarkan kalimat)\n"
            "Lihat https://platform.openai.com/docs/guides/text-to-speech"
        ) from e
    except Exception as e:
        if output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass
        logger.error(f"OpenAI TTS gagal: {e}")
        raise RuntimeError(
            f"OpenAI TTS synthesis gagal: {e}\n\n"
            "Cek koneksi internet, API key, dan quota di https://platform.openai.com/usage"
        ) from e


def generate_elevenlabs_voiceover(
    script_text: str,
    output_name: Optional[str] = None,
) -> Path:
    """
    Generate voiceover using ElevenLabs TTS API (premium natural quality, excellent for Indonesian).

    Requires ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env.
    Uses high-quality multilingual model by default (great Indonesian support).

    Long scripts are automatically split into safe chunks (~4500 chars) on sentence boundaries
    and concatenated with FFmpeg (same reliable logic as OpenAI TTS).

    Voice cloning: Create a custom voice in the ElevenLabs dashboard (Voice Lab) and use its voice_id.
    """
    if not ELEVENLABS_API_KEY:
        raise ValueError(
            "ELEVENLABS_API_KEY belum diset di .env.\n\n"
            "Cara setup ElevenLabs TTS (kualitas premium):\n"
            "1. Daftar di https://elevenlabs.io\n"
            "2. Buka https://elevenlabs.io/app/voice-lab atau tab Voices\n"
            "3. Pilih / clone voice yang bagus (atau pakai salah satu premade yang support multilingual)\n"
            "4. Copy Voice ID (contoh: 21m00Tcm4TlvDq8ikWAM)\n"
            "5. Tambahkan di .env:\n"
            "   ELEVENLABS_API_KEY=sk_...\n"
            "   ELEVENLABS_VOICE_ID=xxxxxxxxxxxxxxxxxxxxxxxx\n"
            "   TTS_PROVIDER=elevenlabs\n"
            "   # Opsional (rekomendasi default sudah bagus):\n"
            "   ELEVENLABS_MODEL=eleven_multilingual_v2   # atau eleven_turbo_v2_5 (lebih cepat)\n"
            "   ELEVENLABS_STABILITY=0.5\n"
            "   ELEVENLABS_SIMILARITY=0.75\n\n"
            "Catatan: Kualitas biasanya lebih natural & emosional daripada OpenAI TTS, tapi lebih mahal per karakter."
        )

    if not ELEVENLABS_VOICE_ID:
        raise ValueError(
            "ELEVENLABS_VOICE_ID belum diset.\n"
            "Buka ElevenLabs dashboard → pilih voice → copy Voice ID → set di .env sebagai ELEVENLABS_VOICE_ID"
        )

    if not output_name:
        import hashlib
        h = hashlib.md5(script_text[:100].encode()).hexdigest()[:8]
        output_name = f"voice_{h}.mp3"

    output_path = OUTPUT_AUDIO / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Clean text (same as other providers)
    cleaned_text = (
        script_text.strip()
        .replace("—", "-")
        .replace("–", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("…", "...")
    )
    if not cleaned_text:
        raise ValueError("Teks untuk voiceover kosong.")

    # ElevenLabs per-request limit is generous (~5k chars), we use 4500 to be safe
    chunks = _split_text_into_chunks(cleaned_text, max_chars=4500)
    logger.info(
        f"Generating ElevenLabs TTS voiceover (model={ELEVENLABS_MODEL}, voice_id={ELEVENLABS_VOICE_ID[:8]}...) "
        f"— {len(chunks)} chunk(s), total {len(cleaned_text)} chars"
    )

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }

    voice_settings = {
        "stability": max(0.0, min(1.0, ELEVENLABS_STABILITY)),
        "similarity_boost": max(0.0, min(1.0, ELEVENLABS_SIMILARITY)),
        # "style": 0.0,                 # uncomment if you want to experiment (newer models)
        # "use_speaker_boost": True,
    }

    try:
        import requests

        if len(chunks) == 1:
            # Fast path
            payload = {
                "text": chunks[0],
                "model_id": ELEVENLABS_MODEL,
                "voice_settings": voice_settings,
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=180)
            resp.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(resp.content)

        else:
            # Multi-chunk path (reuse the excellent FFmpeg concat logic)
            chunk_files: list[Path] = []

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                for idx, chunk in enumerate(chunks):
                    payload = {
                        "text": chunk,
                        "model_id": ELEVENLABS_MODEL,
                        "voice_settings": voice_settings,
                    }
                    resp = requests.post(url, headers=headers, json=payload, timeout=180)
                    resp.raise_for_status()

                    chunk_path = tmpdir_path / f"tts_chunk_{idx:03d}.mp3"
                    chunk_path.write_bytes(resp.content)
                    chunk_files.append(chunk_path)
                    logger.info(f"  Chunk {idx+1}/{len(chunks)} synthesized ({len(chunk)} chars)")

                _concat_mp3_chunks_ffmpeg(chunk_files, output_path)
                logger.info(f"  Concatenated {len(chunks)} chunks with FFmpeg → final audio")

        file_size = output_path.stat().st_size
        if file_size < 100:
            output_path.unlink(missing_ok=True)
            raise RuntimeError("ElevenLabs TTS mengembalikan audio kosong / terlalu kecil.")

        logger.info(f"ElevenLabs TTS voiceover saved: {output_path} ({file_size} bytes)")
        return output_path

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", "?")
        err_detail = ""
        try:
            if e.response is not None:
                err_detail = e.response.json().get("detail", {}).get("message", str(e))
                if not err_detail:
                    err_detail = e.response.text[:500]
        except Exception:
            err_detail = str(e)

        # Common ElevenLabs errors
        if status == 401:
            hint = "API key tidak valid atau expired."
        elif status == 422:
            hint = "Voice ID salah, atau teks mengandung karakter yang bermasalah, atau model tidak support voice tersebut."
        elif status in (429, 402):
            hint = "Quota habis / billing limit. Cek di https://elevenlabs.io/app/subscription"
        else:
            hint = "Periksa Voice ID, model (eleven_multilingual_v2 direkomendasikan), dan koneksi."

        logger.error(f"ElevenLabs TTS HTTP error ({status}): {err_detail}")
        raise RuntimeError(
            f"ElevenLabs TTS gagal (HTTP {status}):\n{err_detail}\n\n"
            f"{hint}\n\n"
            "Pastikan:\n"
            "• ELEVENLABS_API_KEY dan ELEVENLABS_VOICE_ID benar\n"
            "• Model valid: eleven_multilingual_v2 (paling bagus untuk ID) atau eleven_turbo_v2_5\n"
            "• Teks per chunk <= ~4500 karakter (kami sudah auto-split)\n"
            "Lihat https://elevenlabs.io/docs/api-reference/text-to-speech"
        ) from e
    except Exception as e:
        if output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass
        logger.error(f"ElevenLabs TTS gagal: {e}")
        raise RuntimeError(
            f"ElevenLabs TTS synthesis gagal: {e}\n\n"
            "Cek API key, Voice ID, dan quota di https://elevenlabs.io/app"
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
    - edge-tts   (default, online gratis tapi kadang unreliable)
    - xtts       (local, lebih reliable)
    - piper      (local, paling cepat & reliable untuk automation)
    - openai     (cloud API reliable, mudah, biaya kecil; auto-split untuk script panjang)
    - elevenlabs (premium cloud, kualitas sangat natural, auto-split + concat)
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

    elif provider == "openai":
        return generate_openai_voiceover(script_text, output_name)

    elif provider in ("elevenlabs", "eleven", "11labs", "eleven-labs", "elevenlabs-tts"):
        return generate_elevenlabs_voiceover(script_text, output_name)

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
                    "• Set TTS_PROVIDER=openai + OPENAI_API_KEY (reliable cloud API, mudah setup, auto-split script panjang)\n"
                    "• Set TTS_PROVIDER=elevenlabs + ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID (kualitas premium)\n"
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

"""
Shared utilities for TTS providers.
"""

import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def clean_text_for_tts(text: str) -> str:
    """Common text cleaning for most TTS providers."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Teks untuk voiceover kosong.")

    # Ganti karakter aneh yang kadang muncul dari LLM
    return (
        cleaned
        .replace("—", "-")
        .replace("–", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("…", "...")
    )


def _split_text_into_chunks(text: str, max_chars: int = 4000) -> List[str]:
    """
    Split long narration text into chunks safe for cloud TTS.
    Prefers natural sentence/paragraph boundaries.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    # Split while trying to keep sentence punctuation attached
    parts = re.split(r'([.!?。！？]\s+|\n\s*\n+)', text)

    sentences: List[str] = []
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

    chunks: List[str] = []
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
                break_point = current.rfind(" ", 0, max_chars - 50)
                if break_point < 100:
                    break_point = max_chars
                piece = current[:break_point].strip()
                if piece:
                    chunks.append(piece)
                current = current[break_point:].strip()

    if current:
        chunks.append(current)

    # Ultimate safety
    final_chunks: List[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            final_chunks.append(c)
        else:
            for j in range(0, len(c), max_chars):
                final_chunks.append(c[j : j + max_chars])

    return [c for c in final_chunks if c.strip()]


def _concat_mp3_chunks_ffmpeg(chunk_paths: List[Path], output_path: Path) -> None:
    """
    Concatenate multiple MP3 files into one using FFmpeg's concat demuxer.
    Uses stream copy for speed and zero quality loss.
    """
    if not chunk_paths:
        raise ValueError("Tidak ada chunk audio untuk digabungkan")

    if len(chunk_paths) == 1:
        import shutil
        shutil.copy2(chunk_paths[0], output_path)
        return

    concat_list = output_path.with_name(f"{output_path.stem}.concat.txt")
    try:
        with open(concat_list, "w", encoding="utf-8") as f:
            for p in chunk_paths:
                safe_path = str(p.resolve()).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
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
        concat_list.unlink(missing_ok=True)

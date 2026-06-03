"""
AsihHealth - Automatic Subtitle Generation + Burning
Uses faster-whisper (local) for accurate Indonesian transcription + alignment.
If the original LLM-generated script is provided (recommended), it is passed
as `initial_prompt` to Whisper. This produces higher-quality subtitles because
we start from the clean, structured script text instead of relying only on
audio transcription (fewer errors on health terms, better fidelity to the
intended narration).

Subtitles are automatically wrapped to SUBTITLE_MAX_CHARS_PER_LINE (~42 chars)
and max SUBTITLE_MAX_LINES (2) for tidy display that doesn't fill the screen.
See config/settings.py and .env.example for tuning.
Then burns subtitles into video using FFmpeg.
"""

import logging
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple

from config.settings import (
    OUTPUT_SUBTITLES,
    SUBTITLE_MAX_CHARS_PER_LINE,
    SUBTITLE_MAX_LINES,
    WHISPER_DEVICE,
    WHISPER_MODEL,
)

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: Path,
    model_size: str = WHISPER_MODEL,
    device: str = WHISPER_DEVICE,
    language: str = "id",  # Indonesian
    initial_prompt: Optional[str] = None,
) -> List[dict]:
    """
    Transcribe audio using faster-whisper.
    If initial_prompt (the original generated script) is provided, it is passed
    to Whisper to bias the transcription towards the known high-quality text.
    This greatly improves accuracy for health/medical terms compared to blind transcription.
    Returns list of segments with timing.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError("faster-whisper is required. Run: pip install faster-whisper")

    logger.info(f"Loading Whisper model: {model_size} on {device}")
    model = WhisperModel(
        model_size, device=device, compute_type="int8" if device == "cpu" else "float16"
    )

    logger.info(f"Transcribing: {audio_path.name}")
    transcribe_kwargs = dict(
        language=language,
        beam_size=5,
        word_timestamps=False,
        vad_filter=True,
    )
    if initial_prompt:
        # Use the original LLM-generated script as prompt for much better fidelity
        transcribe_kwargs["initial_prompt"] = initial_prompt[
            :2000
        ]  # Whisper prompt limit ~224 tokens, this is safe
        logger.info(
            "Using original script as initial_prompt for Whisper (better accuracy)"
        )

    segments, info = model.transcribe(
        str(audio_path),
        **transcribe_kwargs,
    )

    results = []
    for seg in segments:
        results.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})

    logger.info(f"Transcription done. {len(results)} segments.")
    return results


def _wrap_subtitle_text(text: str, max_chars: int = None, max_lines: int = None) -> str:
    """
    Wrap subtitle text to keep it tidy and readable on screen.
    Forces at most max_lines (default 2) so it never fills the video with many lines.
    Each line aims for ~max_chars (default 42), but for very long spoken segments
    we still show all text using up to 2 (possibly longer) lines.
    """
    if max_chars is None:
        max_chars = SUBTITLE_MAX_CHARS_PER_LINE
    if max_lines is None:
        max_lines = SUBTITLE_MAX_LINES

    text = text.strip()
    if not text:
        return ""

    # Wrap the full text into short lines first (word-aware)
    short_lines = textwrap.wrap(
        text, width=max_chars, break_long_words=False, break_on_hyphens=False
    )

    if len(short_lines) <= max_lines:
        return "\n".join(short_lines)

    # Too many short lines → distribute into exactly max_lines groups.
    # This guarantees we never display more than max_lines at once,
    # while preserving 100% of the text.
    n = len(short_lines)
    # Calculate how many short lines per final line
    group_size = (n + max_lines - 1) // max_lines

    final_lines = []
    for i in range(0, n, group_size):
        group = short_lines[i : i + group_size]
        joined = " ".join(group)
        # The joined may exceed max_chars, but we accept it to fit in max_lines total.
        # (This is common for dense dialogue segments.)
        final_lines.append(joined)

    return "\n".join(final_lines[:max_lines])


def generate_srt(
    segments: List[dict],
    output_path: Path,
    max_chars: int = None,
    max_lines: int = None,
) -> Path:
    """Write standard .srt subtitle file.
    Text is automatically wrapped (see _wrap_subtitle_text) to keep lines short and tidy
    (prevents long subtitles from filling the entire video width).
    """

    def format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{format_time(seg['start'])} --> {format_time(seg['end'])}")
        wrapped = _wrap_subtitle_text(
            seg["text"], max_chars=max_chars, max_lines=max_lines
        )
        lines.append(wrapped)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"SRT saved: {output_path}")
    return output_path


def burn_subtitles_ffmpeg(
    video_path: Path,
    srt_path: Path,
    output_path: Optional[Path] = None,
    font_size: int = 14,
    font_color: str = "white",
    outline_color: str = "black",
) -> Path:
    """
    Burn subtitles into video using FFmpeg drawtext / subtitles filter.
    Best quality: use libass (usually available in modern FFmpeg builds).
    """
    if output_path is None:
        output_path = video_path.parent / f"{video_path.stem}_with_subs.mp4"

    # FFmpeg subtitles filter (requires proper fontconfig + libass)
    # Escape path for filter (Windows backslashes are problematic)
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")

    # High quality subtitle style for Indonesian health videos
    # Using subtitles filter with style override.
    # Added MarginL/MarginR to prevent text from filling edge-to-edge (tidier look).
    # Alignment=2 is bottom-center (good for most videos).
    filter_complex = (
        f"subtitles='{srt_escaped}':force_style='FontSize={font_size},"
        f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,"
        f"BorderStyle=4,Outline=1.5,Shadow=0.8,MarginL=60,MarginR=60,MarginV=40,Alignment=2'"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        filter_complex,
        "-c:a",
        "copy",  # Copy audio without re-encode
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    logger.info("Burning subtitles into video (this may take a while)...")

    import subprocess

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error("FFmpeg subtitle burn failed:")
        logger.error(result.stderr[-1500:])
        # Fallback: just copy the original video if burning fails
        import shutil

        shutil.copy(video_path, output_path)
        logger.warning(
            "Subtitle burning failed. Output video without burned subtitles."
        )
    else:
        logger.info(f"Video with subtitles: {output_path}")

    return output_path


def create_subtitles_and_burn(
    audio_path: Path,
    video_path: Path,
    output_dir: Optional[Path] = None,
    script_text: Optional[str] = None,
    max_chars_per_line: int = None,
    max_lines: int = None,
) -> Tuple[Path, Path]:
    """
    Full pipeline: transcribe audio → generate .srt (with automatic line wrapping
    for tidy display) → burn into video.
    If script_text (from the LLM-generated script) is provided, it is used
    as initial_prompt to Whisper. This makes subtitles much more accurate
    because we use the clean, author-written text instead of blind transcription.

    max_chars_per_line / max_lines: override the settings for this call (useful for testing).

    Returns (srt_path, final_video_path)
    """
    if output_dir is None:
        output_dir = OUTPUT_SUBTITLES

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Transcribe (guided by original script if available)
    segments = transcribe_audio(audio_path, initial_prompt=script_text)

    # 2. Generate SRT (with wrapping for tidy, non-filling subtitles)
    srt_path = output_dir / f"{audio_path.stem}.srt"
    generate_srt(segments, srt_path, max_chars=max_chars_per_line, max_lines=max_lines)

    # 3. Burn
    final_video = burn_subtitles_ffmpeg(video_path, srt_path)

    return srt_path, final_video

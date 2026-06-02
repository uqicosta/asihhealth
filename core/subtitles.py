"""
AsihHealth - Automatic Subtitle Generation + Burning
Uses faster-whisper (local) for accurate Indonesian transcription + alignment.
Then burns subtitles into video using FFmpeg.
"""

import logging
from pathlib import Path
from typing import Optional, List, Tuple
from config.settings import WHISPER_MODEL, WHISPER_DEVICE, OUTPUT_SUBTITLES

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: Path,
    model_size: str = WHISPER_MODEL,
    device: str = WHISPER_DEVICE,
    language: str = "id"  # Indonesian
) -> List[dict]:
    """
    Transcribe audio using faster-whisper.
    Returns list of segments with timing.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper is required. Run: pip install faster-whisper"
        )

    logger.info(f"Loading Whisper model: {model_size} on {device}")
    model = WhisperModel(model_size, device=device, compute_type="int8" if device == "cpu" else "float16")

    logger.info(f"Transcribing: {audio_path.name}")
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        word_timestamps=False,
        vad_filter=True,
    )

    results = []
    for seg in segments:
        results.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip()
        })

    logger.info(f"Transcription done. {len(results)} segments.")
    return results


def generate_srt(segments: List[dict], output_path: Path) -> Path:
    """Write standard .srt subtitle file."""
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
        lines.append(seg["text"])
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"SRT saved: {output_path}")
    return output_path


def burn_subtitles_ffmpeg(
    video_path: Path,
    srt_path: Path,
    output_path: Optional[Path] = None,
    font_size: int = 28,
    font_color: str = "white",
    outline_color: str = "black"
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
    # Using subtitles filter with style override
    filter_complex = (
        f"subtitles='{srt_escaped}':force_style='FontSize={font_size},"
        f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,"
        f"BorderStyle=4,Outline=1.5,Shadow=0.8,MarginV=35,Alignment=2'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", filter_complex,
        "-c:a", "copy",           # Copy audio without re-encode
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-movflags", "+faststart",
        str(output_path)
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
        logger.warning("Subtitle burning failed. Output video without burned subtitles.")
    else:
        logger.info(f"Video with subtitles: {output_path}")

    return output_path


def create_subtitles_and_burn(
    audio_path: Path,
    video_path: Path,
    output_dir: Optional[Path] = None
) -> Tuple[Path, Path]:
    """
    Full pipeline: transcribe audio → generate .srt → burn into video.
    Returns (srt_path, final_video_path)
    """
    if output_dir is None:
        output_dir = OUTPUT_SUBTITLES

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Transcribe
    segments = transcribe_audio(audio_path)

    # 2. Generate SRT
    srt_path = output_dir / f"{audio_path.stem}.srt"
    generate_srt(segments, srt_path)

    # 3. Burn
    final_video = burn_subtitles_ffmpeg(video_path, srt_path)

    return srt_path, final_video

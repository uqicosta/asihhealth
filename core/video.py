"""
AsihHealth - FFmpeg Video Assembly Engine
Cost-efficient video creation using pure FFmpeg.

Supported styles:
- "simple": Solid background + centered text (title + key points)
- "kenburns": Image slideshow with slow zoom/pan effect (requires images)
"""

import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Literal
from config.settings import (
    OUTPUT_VIDEOS, VIDEO_RESOLUTION, VIDEO_FPS, VIDEO_BITRATE
)

logger = logging.getLogger(__name__)

VideoStyle = Literal["simple", "kenburns", "stock"]


def check_ffmpeg() -> bool:
    """Verify FFmpeg is installed and accessible."""
    return shutil.which("ffmpeg") is not None


def _run_ffmpeg(cmd: List[str], description: str = "") -> bool:
    """Execute FFmpeg command with proper logging."""
    if description:
        logger.info(f"FFmpeg: {description}")

    logger.debug(" ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {description}")
        logger.error(e.stderr[-2000:] if e.stderr else str(e))
        return False


def create_simple_video(
    audio_path: Path,
    title: str,
    output_path: Optional[Path] = None,
    background_color: str = "0f172a",  # Dark slate (modern look)
    resolution: str = VIDEO_RESOLUTION,
) -> Path:
    """
    Create a clean, professional faceless video (lowest cost):
    - Dark elegant background
    - Title text overlay
    - Channel branding
    - Narration audio

    This is ideal for health education channels (talking-head alternative).
    """
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg tidak ditemukan di PATH. Install dengan: winget install ffmpeg")

    if output_path is None:
        output_path = OUTPUT_VIDEOS / f"{audio_path.stem}_simple.mp4"

    # Get exact audio duration
    duration_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ]
    result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())

    width, height = (1920, 1080) if resolution == "1080p" else (1280, 720)

    temp_bg = output_path.with_suffix(".bg.mp4")

    # 1. Create clean background video (no audio)
    cmd_bg = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={background_color}:s={width}x{height}:d={duration}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        str(temp_bg)
    ]
    if not _run_ffmpeg(cmd_bg, "Membuat background video"):
        raise RuntimeError("Gagal membuat background video")

    # 2. Safe title text (escape problematic characters for FFmpeg drawtext)
    safe_title = title.replace("'", "’").replace(":", " -").replace("%", " persen")[:65]

    # Filter: title at top + channel name at bottom
    vf = (
        f"drawtext=fontfile=/Windows/Fonts/arial.ttf:fontsize=48:fontcolor=white:"
        f"text='{safe_title}':x=(w-text_w)/2:y=160,"
        f"drawtext=fontfile=/Windows/Fonts/arial.ttf:fontsize=24:fontcolor=94a3b8:"
        f"text='AsihHealth - Edukasi Kesehatan':x=(w-text_w)/2:y=h-90"
    )

    # 3. Mux background + audio + text
    cmd_final = [
        "ffmpeg", "-y",
        "-i", str(temp_bg),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path)
    ]

    success = _run_ffmpeg(cmd_final, "Menggabungkan audio + teks overlay")
    temp_bg.unlink(missing_ok=True)

    if not success:
        raise RuntimeError("Gagal membuat video sederhana")

    logger.info(f"Video sederhana berhasil dibuat: {output_path}")
    return output_path


def create_video_with_images(
    audio_path: Path,
    images: List[Path],
    output_path: Optional[Path] = None,
    resolution: str = VIDEO_RESOLUTION,
    image_duration: float = 6.5,   # seconds per image before transition
    transition_duration: float = 0.9,
) -> Path:
    """
    Create professional-looking video using Ken Burns effect (slow zoom/pan) on stock images.

    This produces much better results than plain background for faceless health channels.
    Uses pure FFmpeg (zoompan + xfade).
    """
    if not images:
        raise ValueError("At least one image is required")

    if output_path is None:
        output_path = OUTPUT_VIDEOS / f"{audio_path.stem}_kenburns.mp4"

    if not check_ffmpeg():
        raise RuntimeError("FFmpeg tidak ditemukan. Install: winget install ffmpeg")

    width, height = (1920, 1080) if resolution == "1080p" else (1280, 720)
    images = [img for img in images if img.exists()][:12]  # safety cap

    if len(images) < 2:
        # Fallback to simple if not enough images
        logger.warning("Less than 2 images found. Falling back to simple video.")
        return create_simple_video(audio_path, "AsihHealth", output_path)

    logger.info(f"Creating Ken Burns video with {len(images)} images...")

    # Get audio duration
    audio_dur = get_audio_duration(audio_path)
    total_image_time = len(images) * image_duration

    # If images don't cover the full audio, we will loop the sequence or extend last image
    # For simplicity, we scale image_duration so total visual time >= audio
    if total_image_time < audio_dur:
        image_duration = (audio_dur + 3) / len(images)   # add a bit of padding
        logger.info(f"Adjusted image duration to {image_duration:.1f}s to cover audio")

    # Step 1: Create individual Ken Burns clips for each image
    clips: List[Path] = []
    temp_dir = output_path.parent / ".tmp_kenburns"
    temp_dir.mkdir(exist_ok=True)

    zoom_directions = [
        "zoompan=z='min(zoom+0.0015,1.25)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "zoompan=z='min(zoom+0.0012,1.18)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "zoompan=z='min(zoom+0.0018,1.30)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    ]

    for idx, img in enumerate(images):
        clip_path = temp_dir / f"clip_{idx:02d}.mp4"

        # Different subtle motion per image
        zf = zoom_directions[idx % len(zoom_directions)]

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,{zf}:s={width}x{height}:fps={VIDEO_FPS}",
            "-t", str(image_duration),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(clip_path)
        ]

        if _run_ffmpeg(cmd, f"Ken Burns clip {idx+1}/{len(images)}"):
            clips.append(clip_path)

    if not clips:
        raise RuntimeError("Failed to create any image clips")

    # Step 2: Build xfade filter chain for smooth transitions
    # This is the complex but beautiful part
    filter_parts = []
    concat_inputs = ""

    for i in range(len(clips)):
        concat_inputs += f"[{i}:v]"

    # Create xfade chain
    xfade_expr = ""
    current_label = "v0"

    for i in range(1, len(clips)):
        offset = (image_duration - transition_duration) * i
        next_label = f"v{i}"
        xfade_expr += (
            f"[{current_label}][{i}:v]"
            f"xfade=transition=fade:duration={transition_duration}:offset={offset:.3f}[{next_label}];"
        )
        current_label = next_label

    # Final filter
    filter_complex = xfade_expr + f"[{current_label}]format=yuv420p[video]"

    # Build the full command
    cmd_inputs = []
    for c in clips:
        cmd_inputs.extend(["-i", str(c)])

    cmd_xfade = [
        "ffmpeg", "-y",
        *cmd_inputs,
        "-filter_complex", filter_complex,
        "-map", "[video]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", str(VIDEO_FPS),
        str(output_path.with_suffix(".visual.mp4"))
    ]

    visual_only = output_path.with_suffix(".visual.mp4")
    if not _run_ffmpeg(cmd_xfade, "Merging clips with xfade transitions"):
        # Cleanup and fallback
        for c in clips:
            c.unlink(missing_ok=True)
        temp_dir.rmdir()
        raise RuntimeError("Ken Burns xfade failed")

    # Step 3: Mux the beautiful visual with audio narration
    cmd_mux = [
        "ffmpeg", "-y",
        "-i", str(visual_only),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path)
    ]

    success = _run_ffmpeg(cmd_mux, "Muxing Ken Burns video + audio")

    # Cleanup temp files
    visual_only.unlink(missing_ok=True)
    for c in clips:
        c.unlink(missing_ok=True)
    try:
        temp_dir.rmdir()
    except:
        pass

    if not success:
        raise RuntimeError("Failed to mux final video")

    logger.info(f"✅ Ken Burns video created successfully: {output_path}")
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

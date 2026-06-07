"""
AsihHealth - Output Discovery Helpers

Utilities to find previously generated artifacts (scripts, audio, videos)
by filesystem modification time. Used for convenient "latest" resume modes
(--latest, --refresh-images, --refresh-subtitles).

These are intentionally simple and filesystem-based so they work without
any database or extra metadata.
"""

from pathlib import Path
from typing import Optional

from config.settings import OUTPUT_SCRIPTS, OUTPUT_AUDIO, OUTPUT_VIDEOS


def find_latest_script() -> Optional[Path]:
    """Return the most recently modified script JSON (by filesystem mtime)."""
    scripts = list(OUTPUT_SCRIPTS.glob("*.json"))
    if not scripts:
        return None
    return max(scripts, key=lambda p: p.stat().st_mtime)


def find_latest_audio() -> Optional[Path]:
    """Return the most recently modified voiceover audio (by filesystem mtime)."""
    audios = list(OUTPUT_AUDIO.glob("voice_*.mp3"))
    if not audios:
        return None
    return max(audios, key=lambda p: p.stat().st_mtime)


def find_latest_base_video() -> Optional[Path]:
    """Return the most recently modified *base* video (before subtitles/logo were burned).

    Prefers files that do not contain 'with_subs' or 'with_logo' in the name
    (i.e. the direct output of create_video_with_images / create_simple_video).
    Falls back to the overall newest .mp4 if no clean base is found.

    This is useful when you want to re-generate subtitles or thumbnails
    against the clean visual track.
    """
    videos = list(OUTPUT_VIDEOS.glob("*.mp4"))
    if not videos:
        return None

    # Prefer clean base videos (kenburns.mp4 or simple.mp4, not the final ones)
    base_candidates = [
        v for v in videos
        if "with_subs" not in v.name.lower() and "with_logo" not in v.name.lower()
    ]
    if base_candidates:
        return max(base_candidates, key=lambda p: p.stat().st_mtime)

    # Fallback: just the newest video file
    return max(videos, key=lambda p: p.stat().st_mtime)

"""
AsihHealth - Automatic Thumbnail Generator (thin facade)

The implementation has been split for maintainability into:
  core/thumbnail/
    - utils.py          (font loading, title shortening, DALL·E prompt building)
    - pillow.py         (Pillow composition for local thumbnails)
    - openai.py         (DALL·E background generation when THUMBNAIL_PROVIDER=openai)
    - __init__.py

This file now serves as a thin re-export layer so that existing imports continue to work:
    from core.thumbnail import generate_thumbnails_for_script, create_thumbnail
"""

from core.thumbnail.utils import (
    THUMB_WIDTH,
    THUMB_HEIGHT,
    get_font as _get_font,
    shorten_title as _shorten_title,
    build_dalle_prompt as _build_dalle_prompt,
)
from core.thumbnail.pillow import create_thumbnail
from core.thumbnail.openai import generate_openai_thumbnail_image

# For convenience, also expose the generator used internally
__all__ = [
    "create_thumbnail",
    "generate_openai_thumbnail_image",
    "generate_thumbnails_for_script",
]

# Import the main orchestrator function (defined below for the high-level logic that was in the old file)
import logging
from pathlib import Path
from typing import List, Optional

from config.settings import THUMBNAIL_PROVIDER

logger = logging.getLogger(__name__)


def generate_thumbnails_for_script(
    script_data: dict, stock_images: Optional[List[Path]] = None, count: int = 1
) -> List[Path]:
    """
    Generate thumbnail(s) from a script JSON + optional stock images.
    If THUMBNAIL_PROVIDER=openai, it will generate custom AI images via DALL·E
    (and still overlay professional text on top using Pillow).
    """
    title = script_data.get("title", "Video Kesehatan")
    thumbnails = []

    # Determine background
    bg = None
    dalle_bgs = []
    if stock_images:
        bg = stock_images[0]
    elif THUMBNAIL_PROVIDER == "openai":
        # Generate one or more custom AI backgrounds
        for _ in range(count):
            dalle_bg = generate_openai_thumbnail_image(title, script_data=script_data)
            if dalle_bg:
                dalle_bgs.append(dalle_bg)

    for i in range(count):
        name = None
        if count > 1:
            import hashlib
            h = hashlib.md5(title.encode()).hexdigest()[:6]
            name = f"thumb_{h}_{i + 1}.png"

        this_bg = bg
        if dalle_bgs:
            this_bg = dalle_bgs[i] if i < len(dalle_bgs) else dalle_bgs[0]

        thumb = create_thumbnail(
            title=title,
            output_name=name,
            background_image=this_bg,
            script_data=script_data,
        )
        thumbnails.append(thumb)

    return thumbnails

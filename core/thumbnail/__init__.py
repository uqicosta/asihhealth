"""
core.thumbnail package

Split implementation for thumbnail generation:
- utils.py: helpers (fonts, title shortening, DALL·E prompt building)
- pillow.py: Pillow-based composition (local)
- openai.py: DALL·E background generation

Main public functions are re-exported from the thin core/thumbnail.py facade.
"""

from .utils import (
    THUMB_WIDTH,
    THUMB_HEIGHT,
    get_font,
    shorten_title,
    build_dalle_prompt,
)
from .pillow import create_thumbnail
from .openai import generate_openai_thumbnail_image

__all__ = [
    "THUMB_WIDTH",
    "THUMB_HEIGHT",
    "get_font",
    "shorten_title",
    "build_dalle_prompt",
    "create_thumbnail",
    "generate_openai_thumbnail_image",
]

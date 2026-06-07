"""
Thumbnail utilities: fonts, text shortening, prompt building.
"""

import logging
import textwrap
from pathlib import Path
from typing import Optional

from PIL import ImageFont

logger = logging.getLogger(__name__)

THUMB_WIDTH = 1280
THUMB_HEIGHT = 720


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try to load a good system font for Indonesian text."""
    font_paths = [
        r"C:\Windows\Fonts\arialbd.ttf",  # Arial Bold
        r"C:\Windows\Fonts\Arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",  # Segoe UI Bold
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            continue
    return ImageFont.load_default()


def shorten_title(title: str, max_chars: int = 55) -> str:
    """Make title thumbnail-friendly (shorter, punchier)."""
    if len(title) <= max_chars:
        return title
    words = title.split()
    result = ""
    for w in words:
        if len(result) + len(w) + 1 > max_chars:
            break
        result += (" " if result else "") + w
    return result.strip() + "..." if len(result) < len(title) else result


def build_dalle_prompt(title: str, script_data: Optional[dict] = None) -> str:
    """Create a strong English prompt for DALL·E YouTube thumbnail generation."""
    style_block = ""
    try:
        style_path = (
            Path(__file__).parent.parent.parent
            / "templates"
            / "prompts"
            / "image_style_block_thumbnail.txt"
        )
        if style_path.exists():
            style_block = style_path.read_text(encoding="utf-8").strip()
        else:
            style_path = (
                Path(__file__).parent.parent.parent
                / "templates"
                / "prompts"
                / "image_style_block.txt"
            )
            if style_path.exists():
                style_block = style_path.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    if not style_block:
        style_block = (
            "cinematic high-contrast YouTube thumbnail background for Indonesian health education video, "
            "dramatic lighting, professional photography style, emotional and attention-grabbing, "
            "dark moody background with bright clean highlights, rich colors with subtle red health accents, "
            "highly detailed, sharp focus, 16:9 composition, clean negative space on the right side suitable for bold text overlay, "
            "no text, no logos, no watermarks in the image itself, photorealistic or cinematic illustration"
        )

    base = (
        f"Cinematic, high-contrast YouTube thumbnail background for an Indonesian health education video about: {title}. "
        f"{style_block}. "
        "Include subtle medical or health imagery (doctor, patient, heart, brain, food, warning symbols), "
        "rich colors with strong red accents for urgency, dark moody background with bright highlights, "
        "highly detailed, 16:9 composition suitable for YouTube thumbnail"
    )

    if script_data:
        key_points = script_data.get("key_points", [])
        if key_points:
            points_str = "; ".join(key_points[:3])
            base += f". Key themes: {points_str}"

    base += (
        ". Bold composition with clear negative space on the right side suitable for bold text overlay, "
        "high resolution, sharp focus, viral YouTube thumbnail aesthetic, "
        "no text, no logos, no watermarks in the image itself"
    )
    return base

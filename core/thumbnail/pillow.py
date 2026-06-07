"""
Pillow-based thumbnail composition (local, free).
"""

import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from config.settings import OUTPUT_THUMBNAILS, THUMBNAIL_ACCENT_COLOR

from .utils import (
    THUMB_WIDTH,
    THUMB_HEIGHT,
    get_font,
    shorten_title,
)

logger = logging.getLogger(__name__)


def create_thumbnail(
    title: str,
    output_name: Optional[str] = None,
    background_image: Optional[Path] = None,
    accent_color: tuple = None,
    channel_name: str = "ASIHHEALTH",
    script_data: Optional[dict] = None,
) -> Path:
    """
    Generate a professional YouTube thumbnail using Pillow.

    Args:
        title: Full video title (will be shortened)
        output_name: Custom filename
        background_image: Path to a stock image or AI image to use as base
        accent_color: RGB tuple for accent elements
        script_data: Full script dict (passed through for potential future use)

    Returns:
        Path to generated thumbnail (PNG)
    """
    if output_name is None:
        import hashlib
        h = hashlib.md5(title.encode()).hexdigest()[:8]
        output_name = f"thumb_{h}.png"

    output_path = OUTPUT_THUMBNAILS / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if accent_color is None:
        accent_color = THUMBNAIL_ACCENT_COLOR

    # Create base canvas
    used_bg = background_image

    if used_bg and used_bg.exists():
        try:
            base = Image.open(used_bg).convert("RGBA")
            base = base.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
            # Darken for text readability
            enhancer = ImageEnhance.Brightness(base)
            base = enhancer.enhance(0.55)
            # Slight blur for cleaner text
            base = base.filter(ImageFilter.GaussianBlur(radius=1.5))
        except Exception as e:
            logger.warning(f"Failed to use background image: {e}")
            base = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (15, 23, 42, 255))
    else:
        # Fallback dark background
        base = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (15, 23, 42, 255))

    draw = ImageDraw.Draw(base)

    # Accent bar at top
    draw.rectangle([0, 0, THUMB_WIDTH, 18], fill=accent_color)

    # Title text (big and bold)
    display_title = shorten_title(title)
    title_font = get_font(78, bold=True)
    subtitle_font = get_font(42, bold=False)
    brand_font = get_font(32, bold=True)

    # Wrap title into 2-3 lines
    max_width = THUMB_WIDTH - 120
    lines = []
    for line in __import__("textwrap").wrap(display_title, width=22):
        lines.append(line)
        if len(lines) >= 3:
            break

    # Draw title with strong outline (shadow + stroke)
    y_start = 160
    line_height = 92

    for i, line in enumerate(lines):
        y = y_start + i * line_height
        x = 60

        # Black outline for readability
        for ox, oy in [
            (-3, -3),
            (-3, 3),
            (3, -3),
            (3, 3),
            (-2, 0),
            (2, 0),
            (0, -2),
            (0, 2),
        ]:
            draw.text((x + ox, y + oy), line, font=title_font, fill=(0, 0, 0, 220))

        # Main white text
        draw.text((x, y), line, font=title_font, fill=(255, 255, 255, 255))

    # Accent underline under title
    last_y = y_start + (len(lines) - 1) * line_height + 85
    draw.rectangle([60, last_y, 60 + 180, last_y + 8], fill=accent_color)

    # Channel branding at bottom
    brand_text = f"▶ {channel_name}"
    draw.text(
        (60, THUMB_HEIGHT - 85), brand_text, font=brand_font, fill=(148, 163, 184)
    )

    # Small health badge
    badge = "EDUKASI KESEHATAN"
    draw.text(
        (THUMB_WIDTH - 340, THUMB_HEIGHT - 85),
        badge,
        font=subtitle_font,
        fill=(251, 191, 36),
    )

    # Convert and save
    final = base.convert("RGB")
    final.save(output_path, "PNG", quality=95)
    logger.info(f"Thumbnail created: {output_path}")
    return output_path

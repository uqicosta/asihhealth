"""
AsihHealth - Automatic Thumbnail Generator
Creates click-worthy YouTube thumbnails for Indonesian health content.

Style:
- 1280x720 (YouTube standard)
- Uses stock image as base when available (Ken Burns style)
- Bold title overlay with strong contrast
- Health channel branding
- Cost: 100% free with Pillow
"""

import logging
from pathlib import Path
from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import textwrap
from config.settings import OUTPUT_THUMBNAILS, ASSETS_DIR, THUMBNAIL_ACCENT_COLOR

logger = logging.getLogger(__name__)

THUMB_WIDTH = 1280
THUMB_HEIGHT = 720


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try to load a good system font for Indonesian text."""
    font_paths = [
        r"C:\Windows\Fonts\arialbd.ttf",      # Arial Bold
        r"C:\Windows\Fonts\Arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",     # Segoe UI Bold
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except:
            continue
    return ImageFont.load_default()


def _shorten_title(title: str, max_chars: int = 55) -> str:
    """Make title thumbnail-friendly (shorter, punchier)."""
    if len(title) <= max_chars:
        return title
    # Try to cut at good point
    words = title.split()
    result = ""
    for w in words:
        if len(result) + len(w) + 1 > max_chars:
            break
        result += (" " if result else "") + w
    return result.strip() + "..." if len(result) < len(title) else result


def create_thumbnail(
    title: str,
    output_name: Optional[str] = None,
    background_image: Optional[Path] = None,
    accent_color: tuple = None,
    channel_name: str = "ASIHHEALTH",
) -> Path:
    """
    Generate a professional YouTube thumbnail.

    Args:
        title: Full video title (will be shortened)
        output_name: Custom filename
        background_image: Path to a stock image to use as base
        accent_color: RGB tuple for accent elements

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
    if background_image and background_image.exists():
        try:
            base = Image.open(background_image).convert("RGBA")
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
        # Fallback dark gradient-like background
        base = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (15, 23, 42, 255))

    draw = ImageDraw.Draw(base)

    # Accent bar at top
    draw.rectangle([0, 0, THUMB_WIDTH, 18], fill=accent_color)

    # Title text (big and bold)
    display_title = _shorten_title(title)
    title_font = _get_font(78, bold=True)
    subtitle_font = _get_font(42, bold=False)
    brand_font = _get_font(32, bold=True)

    # Wrap title into 2-3 lines
    max_width = THUMB_WIDTH - 120
    lines = []
    for line in textwrap.wrap(display_title, width=22):
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
        for ox, oy in [(-3,-3), (-3,3), (3,-3), (3,3), (-2,0), (2,0), (0,-2), (0,2)]:
            draw.text((x + ox, y + oy), line, font=title_font, fill=(0, 0, 0, 220))

        # Main white text
        draw.text((x, y), line, font=title_font, fill=(255, 255, 255, 255))

    # Accent underline under title
    last_y = y_start + (len(lines) - 1) * line_height + 85
    draw.rectangle([60, last_y, 60 + 180, last_y + 8], fill=accent_color)

    # Channel branding at bottom
    brand_text = f"▶ {channel_name}"
    draw.text((60, THUMB_HEIGHT - 85), brand_text, font=brand_font, fill=(148, 163, 184))

    # Small health badge
    badge = "EDUKASI KESEHATAN"
    draw.text((THUMB_WIDTH - 340, THUMB_HEIGHT - 85), badge, font=subtitle_font, fill=(251, 191, 36))

    # Convert and save
    final = base.convert("RGB")
    final.save(output_path, "PNG", quality=95)
    logger.info(f"Thumbnail created: {output_path}")
    return output_path


def generate_thumbnails_for_script(
    script_data: dict,
    stock_images: Optional[List[Path]] = None,
    count: int = 1
) -> List[Path]:
    """
    Generate thumbnail(s) from a script JSON + optional stock images.
    Returns list of thumbnail paths.
    """
    title = script_data.get("title", "Video Kesehatan")
    thumbnails = []

    # Use first available stock image as background if possible
    bg = None
    if stock_images:
        bg = stock_images[0]

    for i in range(count):
        name = None
        if count > 1:
            import hashlib
            h = hashlib.md5(title.encode()).hexdigest()[:6]
            name = f"thumb_{h}_{i+1}.png"

        thumb = create_thumbnail(
            title=title,
            output_name=name,
            background_image=bg,
        )
        thumbnails.append(thumb)

    return thumbnails

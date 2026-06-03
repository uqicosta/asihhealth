"""
AsihHealth - Automatic Thumbnail Generator
Creates click-worthy YouTube thumbnails for Indonesian health content.

Providers (controlled by THUMBNAIL_PROVIDER in .env):
- "pillow" (default): Free local generation using Pillow + optional stock image background
- "openai": Uses DALL·E (via OPENAI_API_KEY) to generate a custom AI background image,
           then composites the bold title + branding on top with Pillow for professional results.

Style:
- 1280x720 (YouTube standard)
- Bold title overlay with strong contrast
- Health channel branding (red accent)
"""

import logging
from pathlib import Path
from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import textwrap
from config.settings import (
    OUTPUT_THUMBNAILS, ASSETS_DIR, THUMBNAIL_ACCENT_COLOR,
    THUMBNAIL_PROVIDER, OPENAI_API_KEY, OPENAI_THUMBNAIL_MODEL, OPENAI_THUMBNAIL_SIZE
)

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


def _build_dalle_prompt(title: str, script_data: Optional[dict] = None) -> str:
    """Create a strong English prompt for DALL·E YouTube thumbnail generation.
    Uses the central style reference in templates/prompts/image_style_block.txt
    to keep visual consistency across all generated images.
    """
    # Load the canonical AsihHealth image style reference
    # Prefer thumbnail-specific block, fall back to general block
    style_block = ""
    try:
        style_path = Path(__file__).parent.parent / "templates" / "prompts" / "image_style_block_thumbnail.txt"
        if style_path.exists():
            style_block = style_path.read_text(encoding="utf-8").strip()
        else:
            # fallback to general style
            style_path = Path(__file__).parent.parent / "templates" / "prompts" / "image_style_block.txt"
            if style_path.exists():
                style_block = style_path.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    if not style_block:
        # Fallback style if files are missing
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

    # Thumbnail-specific instructions for text overlay compatibility
    base += (
        ". Bold composition with clear negative space on the right side suitable for bold text overlay, "
        "high resolution, sharp focus, viral YouTube thumbnail aesthetic, "
        "no text, no logos, no watermarks in the image itself"
    )
    return base


def generate_openai_thumbnail_image(
    title: str,
    script_data: Optional[dict] = None,
    output_name: Optional[str] = None,
) -> Optional[Path]:
    """
    Generate a custom background image for the thumbnail using OpenAI DALL·E.
    Returns path to the generated image (or None on failure).
    The caller (create_thumbnail) will still overlay the bold text on top.
    """
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set. Cannot generate OpenAI thumbnail. Falling back.")
        return None

    if output_name is None:
        import hashlib
        h = hashlib.md5(title.encode()).hexdigest()[:8]
        output_name = f"dalle_thumb_bg_{h}.png"

    output_path = OUTPUT_THUMBNAILS / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = _build_dalle_prompt(title, script_data)

    logger.info(f"Generating DALL·E thumbnail background for: {title[:60]}...")
    logger.debug(f"DALL·E prompt: {prompt[:200]}...")

    try:
        import requests

        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        model = OPENAI_THUMBNAIL_MODEL
        size = OPENAI_THUMBNAIL_SIZE
        # dall-e-2 only supports square sizes
        if model and "dall-e-2" in model.lower():
            size = "1024x1024"

        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        # "quality" and "response_format" are only for dall-e-3 / dall-e-2 respectively.
        # dall-e-2 does not support "quality". dall-e-3 does not need/accept "response_format" in some cases.
        # Omitting unknown params prevents "Unknown parameter" 400 errors.
        if "dall-e-3" in model.lower() or not model or "dall-e" not in model.lower():
            payload["quality"] = "standard"  # or "hd"
        if "dall-e-2" in model.lower():
            payload["response_format"] = "url"

        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        image_url = data["data"][0]["url"]

        # Download the image immediately (URLs expire after ~1 hour)
        img_resp = requests.get(image_url, timeout=60)
        img_resp.raise_for_status()

        # Save as PNG
        with open(output_path, "wb") as f:
            f.write(img_resp.content)

        logger.info(f"OpenAI thumbnail background saved: {output_path}")
        return output_path

    except requests.exceptions.HTTPError as e:
        error_detail = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                err_json = e.response.json()
                error_detail = err_json.get("error", {}).get("message", str(err_json))
            except Exception:
                error_detail = e.response.text[:600]
        logger.error(f"Failed to generate OpenAI thumbnail image: {error_detail}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate OpenAI thumbnail image: {e}")
        return None


def create_thumbnail(
    title: str,
    output_name: Optional[str] = None,
    background_image: Optional[Path] = None,
    accent_color: tuple = None,
    channel_name: str = "ASIHHEALTH",
    script_data: Optional[dict] = None,
) -> Path:
    """
    Generate a professional YouTube thumbnail.

    Args:
        title: Full video title (will be shortened)
        output_name: Custom filename
        background_image: Path to a stock image to use as base
        accent_color: RGB tuple for accent elements
        script_data: Full script dict (used to enrich DALL·E prompt when THUMBNAIL_PROVIDER=openai)

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

    # If no background provided and OpenAI is configured, generate one with DALL·E
    if (not used_bg or not used_bg.exists()) and THUMBNAIL_PROVIDER == "openai":
        dalle_bg = generate_openai_thumbnail_image(title, script_data=script_data)
        if dalle_bg and dalle_bg.exists():
            used_bg = dalle_bg
            logger.info("Using AI-generated DALL·E image as thumbnail background")

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
            name = f"thumb_{h}_{i+1}.png"

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

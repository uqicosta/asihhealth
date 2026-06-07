"""
OpenAI DALL·E thumbnail background generator.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from config.settings import (
    OPENAI_API_KEY,
    OPENAI_IMAGE_QUALITY,
    OPENAI_IMAGE_RESPONSE_FORMAT,
    OPENAI_THUMBNAIL_MODEL,
    OPENAI_THUMBNAIL_SIZE,
    OUTPUT_THUMBNAILS,
)

from .utils import build_dalle_prompt

logger = logging.getLogger(__name__)


def generate_openai_thumbnail_image(
    title: str,
    script_data: Optional[dict] = None,
    output_name: Optional[str] = None,
) -> Optional[Path]:
    """
    Generate a custom background image for the thumbnail using OpenAI DALL·E.
    Returns path to the generated image (or None on failure).
    The caller will still overlay the bold text on top.
    """
    if not OPENAI_API_KEY:
        logger.warning(
            "OPENAI_API_KEY not set. Cannot generate OpenAI thumbnail. Falling back."
        )
        return None

    if output_name is None:
        h = hashlib.md5(title.encode()).hexdigest()[:8]
        output_name = f"dalle_thumb_bg_{h}.png"

    output_path = OUTPUT_THUMBNAILS / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = build_dalle_prompt(title, script_data)

    logger.info(
        f"Generating {OPENAI_THUMBNAIL_MODEL} thumbnail background for: {title[:60]}..."
    )
    logger.debug(f"{OPENAI_THUMBNAIL_MODEL} prompt: {prompt[:200]}...")

    try:
        import requests

        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        model = OPENAI_THUMBNAIL_MODEL
        model_lower = model.lower()
        size = OPENAI_THUMBNAIL_SIZE
        if "dall-e-2" in model_lower:
            size = "1024x1024"
        elif "gpt-image-1" in model_lower:
            size = "1024x1024" if "1024" in size else "1536x1024"

        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        if OPENAI_IMAGE_QUALITY:
            payload["quality"] = OPENAI_IMAGE_QUALITY
        elif "dall-e-2" in model_lower:
            pass
        elif "dall-e-3" in model_lower:
            payload["quality"] = "standard"
        elif "gpt-image-1" in model_lower:
            payload["quality"] = "medium"
        else:
            payload["quality"] = "medium"

        response_format = OPENAI_IMAGE_RESPONSE_FORMAT
        if response_format and ("dall-e-2" in model_lower or "dall-e-3" in model_lower):
            payload["response_format"] = response_format

        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        image_item = data["data"][0]

        if "b64_json" in image_item and image_item["b64_json"]:
            import base64
            image_bytes = base64.b64decode(image_item["b64_json"])
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"OpenAI thumbnail background saved (b64_json): {output_path}")
        else:
            image_url = image_item.get("url")
            if not image_url:
                raise RuntimeError("No image data returned from OpenAI")
            img_resp = requests.get(image_url, timeout=60)
            img_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(img_resp.content)
            logger.info(f"OpenAI thumbnail background saved (from url): {output_path}")

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

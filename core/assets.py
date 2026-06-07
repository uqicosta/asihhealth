"""
AsihHealth - Stock Footage / Image Downloader
Cost-efficient visuals using free stock APIs or AI generation.

Providers (ASSET_IMAGE_PROVIDER in .env):
- "pexels" (default): Download from Pexels (free with API key)
- "openai": Generate custom images with DALL·E (paid). When script_data is provided,
  we inject the full title + key_points + a representative script excerpt into the prompt
  so generated visuals are tightly matched to the actual narration content.

Images are saved to assets/stock/ and used for Ken Burns video effect.
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

from config.settings import (
    ASSET_IMAGE_PROVIDER,
    ASSETS_DIR,
    OPENAI_API_KEY,
    OPENAI_IMAGE_QUALITY,
    OPENAI_IMAGE_RESPONSE_FORMAT,
    OPENAI_THUMBNAIL_MODEL,
    OPENAI_THUMBNAIL_SIZE,
)

logger = logging.getLogger(__name__)

PEXELS_API_URL = "https://api.pexels.com/v1"
PEXELS_VIDEO_URL = "https://api.pexels.com/videos"


class PexelsClient:
    """Client for Pexels free stock API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY", "")
        if not self.api_key:
            logger.warning("PEXELS_API_KEY not set. Stock download will be disabled.")
        self.headers = {"Authorization": self.api_key} if self.api_key else {}
        self.session = requests.Session()

    def search_images(
        self,
        query: str,
        per_page: int = 10,
        orientation: str = "landscape",
        size: str = "large",
    ) -> List[Dict]:
        """
        Search Pexels images.
        Returns list of photo objects with 'src' dict containing different sizes.
        """
        if not self.api_key:
            return []

        params = {
            "query": query,
            "per_page": min(per_page, 80),
            "orientation": orientation,
            "size": size,
        }

        try:
            resp = self.session.get(
                f"{PEXELS_API_URL}/search",
                headers=self.headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("photos", [])
        except Exception as e:
            logger.error(f"Pexels image search failed for '{query}': {e}")
            return []

    def search_videos(
        self,
        query: str,
        per_page: int = 5,
        min_duration: int = 5,
        max_duration: int = 60,
    ) -> List[Dict]:
        """Search Pexels videos (more premium look but heavier)."""
        if not self.api_key:
            return []

        params = {
            "query": query,
            "per_page": min(per_page, 80),
            "min_duration": min_duration,
            "max_duration": max_duration,
        }

        try:
            resp = self.session.get(
                f"{PEXELS_VIDEO_URL}/search",
                headers=self.headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("videos", [])
        except Exception as e:
            logger.error(f"Pexels video search failed: {e}")
            return []

    def download_image(
        self, photo: Dict, dest_dir: Path, filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download the best available image version."""
        if not photo or "src" not in photo:
            return None

        # Prefer 'large' or 'original' for good quality without huge files
        src = photo["src"]
        url = src.get("large") or src.get("original") or src.get("medium")

        if not url:
            return None

        if not filename:
            ext = url.split("?")[0].split(".")[-1]
            filename = f"pexels_{photo.get('id', int(time.time()))}.{ext}"

        dest_path = dest_dir / filename
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            r = self.session.get(url, timeout=30, stream=True)
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            logger.info(f"Downloaded image: {filename}")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None

    def download_best_video_file(self, video: Dict, dest_dir: Path) -> Optional[Path]:
        """Download the highest quality video file available (usually HD)."""
        if not video or "video_files" not in video:
            return None

        # Prefer HD or high quality
        files = sorted(
            video["video_files"],
            key=lambda x: (x.get("height", 0) or 0, x.get("width", 0) or 0),
            reverse=True,
        )

        for vf in files:
            if vf.get("file_type") == "video/mp4":
                url = vf["link"]
                filename = f"pexels_vid_{video.get('id', int(time.time()))}.mp4"
                dest_path = dest_dir / filename
                dest_dir.mkdir(parents=True, exist_ok=True)

                try:
                    r = self.session.get(url, timeout=60, stream=True)
                    r.raise_for_status()
                    with open(dest_path, "wb") as f:
                        for chunk in r.iter_content(32768):
                            f.write(chunk)
                    logger.info(f"Downloaded video clip: {filename}")
                    return dest_path
                except Exception as e:
                    logger.error(f"Failed to download video: {e}")
                    continue
        return None


def get_relevant_queries_from_script(
    script_text: str, max_queries: int = 8, script_data: Optional[dict] = None
) -> List[str]:
    """
    Extract relevant visual search / prompt seeds from script or topic.
    Prefers structured data (key_points + title) when available for much richer context.
    Falls back to lightweight keyword matching on raw script text.
    """
    queries: List[str] = []

    # 1) Best source: structured key_points and title from the generated script (distilled context)
    if script_data:
        title = script_data.get("title") or ""
        if title and len(title) > 8:
            queries.append(title)

        for kp in script_data.get("key_points", []) or []:
            if kp and kp not in queries:
                # Use the key point as-is (it's already a concise, script-derived visual theme)
                queries.append(kp)
                if len(queries) >= max_queries:
                    break

    # 2) Lightweight keyword extraction from raw script (Indonesian health terms)
    if len(queries) < max_queries and script_text:
        health_keywords = [
            "kopi", "kopi hitam", "kesehatan hati", "jantung", "tidur", "stres",
            "makanan sehat", "olahraga", "vitamin", "air putih", "puasa",
            "gula darah", "kolesterol", "tekanan darah", "dokter", "rumah sakit",
            "sayur", "buah", "protein", "senam", "meditasi", "kanker", "diabetes",
            "insomnia", "kecemasan", "pencernaan", "asam lambung", "hipertensi",
        ]
        text_lower = script_text.lower()
        for kw in health_keywords:
            if kw in text_lower and kw not in queries:
                queries.append(kw)
                if len(queries) >= max_queries:
                    break

    # 3) Generic high-quality health visuals as final fallback
    if len(queries) < max_queries:
        generics = [
            "healthy lifestyle",
            "doctor patient consultation",
            "fresh vegetables and fruits",
            "peaceful nature walk",
            "medical research lab",
            "Indonesian family healthy living",
        ]
        for g in generics:
            if g not in queries:
                queries.append(g)
                if len(queries) >= max_queries:
                    break

    return queries[:max_queries]


def _extract_representative_excerpt(script_text: str, max_words: int = 140) -> str:
    """
    Extract a useful, non-raw prefix from the full narration script for image prompts.
    Prefers the hook + first main explanation over just cutting at N words.
    This gives DALL·E much better semantic context from the actual script.
    """
    if not script_text:
        return ""

    text = script_text.strip()

    # Try to cut at a natural section break first (the script uses "---" separators)
    for sep in ["\n---\n", "---", "\n\nPoin ", "\n\nHai, ", "\n\n"]:
        if sep in text:
            head = text.split(sep)[0].strip()
            if 40 < len(head) < 900:  # reasonable length before we fall back
                text = head
                break

    # Word-based cap (more meaningful than raw char or first-N)
    words = text.split()
    if len(words) > max_words:
        excerpt = " ".join(words[:max_words])
        # Try not to cut mid-sentence
        for ender in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
            if ender in excerpt:
                # keep up to last good sentence end
                last = excerpt.rfind(ender)
                if last > max_words * 0.6:
                    excerpt = excerpt[: last + 1]
                    break
        return excerpt.strip() + "..."
    return text.strip()


def _generate_openai_stock_for_topic(
    topic: str,
    script_text: str = "",
    num_images: int = 8,
    script_data: Optional[dict] = None,
) -> List[Path]:
    """
    Generate custom stock images using OpenAI DALL·E instead of downloading from Pexels.
    Injects rich context from the script (title + all key_points + representative excerpt)
    into every image prompt so the generated visuals are tightly aligned with the actual narration.
    """
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured. Cannot generate OpenAI assets.")
        return []

    stock_dir = ASSETS_DIR / "stock"
    stock_dir.mkdir(parents=True, exist_ok=True)

    queries = get_relevant_queries_from_script(
        script_text or topic, script_data=script_data
    )
    logger.info(
        f"Generating OpenAI {OPENAI_THUMBNAIL_MODEL} stock images for: {queries[:3]}..."
    )

    downloaded: List[Path] = []
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    for query in queries:
        if len(downloaded) >= num_images:
            break

        # Build a prompt optimized for video backgrounds (Ken Burns zoom/pan friendly).
        # Use the central style reference file for visual consistency.
        style_block = ""
        try:
            style_path = (
                Path(__file__).parent.parent
                / "templates"
                / "prompts"
                / "image_style_block_assets.txt"
            )
            if style_path.exists():
                style_block = style_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

        if not style_block:
            style_block = (
                "high-quality detailed cinematic still for Indonesian health education video, "
                "photorealistic or clean artistic illustration, natural lighting, rich but clean composition, "
                "suitable for slow Ken Burns zoom and pan effect, subtle medical and wellness elements, "
                "Indonesian cultural context, professional stock photo aesthetic, high resolution, "
                "16:9 landscape, no text, no watermarks, no logos"
            )

        # === Rich script context injection (user request: more context from the script) ===
        # We now feed title + key_points + a meaningful excerpt instead of only 50 raw words.
        context_parts: List[str] = []
        title = (script_data or {}).get("title") or topic or ""
        if title:
            context_parts.append(f"Video title: {title}")

        key_points = (script_data or {}).get("key_points") or []
        if key_points:
            # Use ALL key points for global context (they are the distilled essence of the script)
            context_parts.append("Key points in this video: " + " | ".join(key_points))

        # Meaningful excerpt (far more useful than first 50 words)
        if script_text:
            excerpt = _extract_representative_excerpt(script_text, max_words=140)
            if excerpt:
                context_parts.append(f"Script context: {excerpt}")

        rich_context = ". ".join(context_parts) if context_parts else ""

        # The 'query' here is now often a key_point or title-derived phrase (much better than old keyword list)
        prompt = (
            f"High-quality, detailed cinematic still for an Indonesian health education video. "
            f"Visual theme: {query}. "
            f"{style_block}. "
        )
        if rich_context:
            prompt += f"Broader video context: {rich_context}."

        model = OPENAI_THUMBNAIL_MODEL or "dall-e-3"
        model_lower = model.lower()

        # Choose a supported size for the model
        size = OPENAI_THUMBNAIL_SIZE or "1792x1024"
        if "dall-e-2" in model_lower:
            size = "1024x1024"
        elif "gpt-image-1" in model_lower:
            # gpt-image-1 supports 1024x1024, 1536x1024, 1024x1536
            size = "1024x1024" if "1024" in size else "1536x1024"

        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }

        # Set quality based on model (or use OPENAI_IMAGE_QUALITY override if set).
        # gpt-image-1 supports: low, medium, high, auto
        # dall-e-3 supports: standard, hd
        if OPENAI_IMAGE_QUALITY:
            payload["quality"] = OPENAI_IMAGE_QUALITY
        elif "dall-e-2" in model_lower:
            pass  # no quality
        elif "dall-e-3" in model_lower:
            payload["quality"] = "standard"
        elif "gpt-image-1" in model_lower:
            payload["quality"] = "medium"
        else:
            payload["quality"] = "medium"

        # response_format: only include for models that support it (dall-e-2 and dall-e-3).
        # For gpt-image-1 and similar, it is not accepted (causes "unknown parameter").
        # We default to b64_json for reliability (no URL expiration).
        response_format = OPENAI_IMAGE_RESPONSE_FORMAT
        if response_format and ("dall-e-2" in model_lower or "dall-e-3" in model_lower):
            payload["response_format"] = response_format

        try:
            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=payload,
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            image_item = data["data"][0]

            safe_query = (
                "".join(c if c.isalnum() or c in " _-" else "" for c in query)[:60]
                .strip()
                .replace(" ", "_")
            )
            filename = f"openai_{safe_query}_{int(time.time())}.png"
            dest_path = stock_dir / filename

            # Handle both b64_json (preferred) and url
            if "b64_json" in image_item and image_item["b64_json"]:
                import base64
                image_bytes = base64.b64decode(image_item["b64_json"])
                with open(dest_path, "wb") as f:
                    f.write(image_bytes)
                logger.info(f"Generated OpenAI asset image (b64_json): {filename}")
            else:
                # Fallback to URL download
                image_url = image_item.get("url")
                if not image_url:
                    raise RuntimeError("No image data returned from OpenAI")
                # Download immediately (DALL-E URLs expire quickly)
                img_resp = requests.get(image_url, timeout=60)
                img_resp.raise_for_status()
                with open(dest_path, "wb") as f:
                    f.write(img_resp.content)
                logger.info(f"Generated OpenAI asset image (from url): {filename}")

            downloaded.append(dest_path)
            time.sleep(0.8)  # Rate limit courtesy

        except requests.exceptions.HTTPError as e:
            # Capture the actual OpenAI error message (critical for debugging 400s)
            error_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    err_json = e.response.json()
                    error_detail = err_json.get("error", {}).get(
                        "message", str(err_json)
                    )
                except Exception:
                    error_detail = e.response.text[:600]
            logger.error(
                f"OpenAI image generation failed for query '{query}': {error_detail}"
            )
            continue
        except Exception as e:
            logger.error(f"OpenAI image generation failed for query '{query}': {e}")
            continue

    logger.info(f"Generated {len(downloaded)} OpenAI stock assets to {stock_dir}")
    return downloaded


def download_stock_for_topic(
    topic: str,
    script_text: str = "",
    num_images: int = 8,
    use_videos: bool = False,
    api_key: Optional[str] = None,
    script_data: Optional[dict] = None,
) -> List[Path]:
    """
    High-level function: Given a topic + script, get relevant stock visuals.
    Provider is controlled by ASSET_IMAGE_PROVIDER env var:
      - "pexels" (default): download from Pexels
      - "openai": generate with DALL·E using rich context from the script
        (title + key_points + narration excerpt) for highly relevant, script-aligned images.
    Returns list of local file paths ready to be used in video assembly (Ken Burns).

    script_data: full script JSON dict from the LLM step. Strongly recommended for OpenAI provider
                 so we can pull the actual key_points and script content instead of weak keyword matching.
    """
    stock_dir = ASSETS_DIR / "stock"
    stock_dir.mkdir(parents=True, exist_ok=True)

    queries = get_relevant_queries_from_script(
        script_text or topic, script_data=script_data
    )

    if ASSET_IMAGE_PROVIDER == "openai":
        return _generate_openai_stock_for_topic(
            topic, script_text, num_images, script_data=script_data
        )

    # === Pexels path (original) ===
    client = PexelsClient(api_key=api_key)

    logger.info(f"Searching stock visuals for: {queries[:3]}...")

    downloaded: List[Path] = []

    for query in queries:
        if len(downloaded) >= num_images:
            break

        photos = client.search_images(query, per_page=3)
        for photo in photos:
            if len(downloaded) >= num_images:
                break
            path = client.download_image(photo, stock_dir)
            if path and path not in downloaded:
                downloaded.append(path)
                time.sleep(0.4)  # Be nice to the API

        if use_videos and len(downloaded) < num_images:
            videos = client.search_videos(query, per_page=2)
            for vid in videos:
                if len(downloaded) >= num_images:
                    break
                path = client.download_best_video_file(vid, stock_dir)
                if path:
                    downloaded.append(path)
                    time.sleep(0.6)

    logger.info(f"Downloaded {len(downloaded)} stock assets to {stock_dir}")
    return downloaded

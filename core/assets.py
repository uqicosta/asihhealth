"""
AsihHealth - Stock Footage / Image Downloader
Cost-efficient visuals using free stock APIs or AI generation.

Providers (ASSET_IMAGE_PROVIDER in .env):
- "pexels" (default): Download from Pexels (free with API key)
- "openai": Generate custom images with DALL·E (paid, but highly relevant to your script)

Images are saved to assets/stock/ and used for Ken Burns video effect.
"""

import logging
import os
import time
from pathlib import Path
from typing import List, Optional, Dict
import requests
from config.settings import ASSETS_DIR, ASSET_IMAGE_PROVIDER, OPENAI_API_KEY, OPENAI_THUMBNAIL_MODEL, OPENAI_THUMBNAIL_SIZE

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
        size: str = "large"
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
                timeout=15
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
        max_duration: int = 60
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
                timeout=15
            )
            resp.raise_for_status()
            return resp.json().get("videos", [])
        except Exception as e:
            logger.error(f"Pexels video search failed: {e}")
            return []

    def download_image(self, photo: Dict, dest_dir: Path, filename: Optional[str] = None) -> Optional[Path]:
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
            reverse=True
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


def get_relevant_queries_from_script(script_text: str, max_queries: int = 8) -> List[str]:
    """
    Very simple keyword extraction for health topics.
    In a real system we could use LLM for this, but for cost efficiency we do lightweight.
    """
    # Common health-related themes
    health_keywords = [
        "kopi", "kopi hitam", "kesehatan hati", "jantung", "tidur", "stres",
        "makanan sehat", "olahraga", "vitamin", "air putih", "puasa",
        "gula darah", "kolesterol", "tekanan darah", "dokter", "rumah sakit",
        "sayur", "buah", "protein", "senam", "meditasi", "kanker", "diabetes"
    ]

    text_lower = script_text.lower()
    found = []

    for kw in health_keywords:
        if kw in text_lower and kw not in found:
            found.append(kw)

    # Fallback generic good visuals for health videos
    generics = ["healthy lifestyle", "doctor patient", "fresh vegetables", "nature walk", "medical research"]

    # Combine found + some generics
    queries = found[:max_queries]
    while len(queries) < 5:
        for g in generics:
            if g not in queries:
                queries.append(g)
                if len(queries) >= max_queries:
                    break

    return queries[:max_queries]


def _generate_openai_stock_for_topic(
    topic: str,
    script_text: str = "",
    num_images: int = 8,
    script_data: Optional[dict] = None,
) -> List[Path]:
    """
    Generate custom stock images using OpenAI DALL·E instead of downloading from Pexels.
    Uses the script/topic/key_points to create highly relevant visual prompts.
    """
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured. Cannot generate OpenAI assets.")
        return []

    stock_dir = ASSETS_DIR / "stock"
    stock_dir.mkdir(parents=True, exist_ok=True)

    queries = get_relevant_queries_from_script(script_text or topic)
    logger.info(f"Generating OpenAI DALL·E stock images for: {queries[:3]}...")

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
            style_path = Path(__file__).parent.parent / "templates" / "prompts" / "image_style_block_assets.txt"
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

        prompt = (
            f"High-quality, detailed cinematic still for an Indonesian health education video about '{query}'. "
            f"{style_block}."
        )

        if script_data and script_data.get("key_points"):
            points = "; ".join(script_data["key_points"][:3])
            prompt += f" Key visual themes: {points}."
        elif script_text:
            # Fallback short context
            context = " ".join(script_text.split()[:50])
            prompt += f" Visual context: {context}"

        model = OPENAI_THUMBNAIL_MODEL or "dall-e-3"
        # Choose a supported size for the model (dall-e-2 only supports square sizes up to 1024)
        size = OPENAI_THUMBNAIL_SIZE or "1792x1024"
        if "dall-e-2" in model.lower():
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

        try:
            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=payload,
                timeout=90
            )
            resp.raise_for_status()
            data = resp.json()
            image_url = data["data"][0]["url"]

            # Download immediately (DALL-E URLs expire quickly)
            img_resp = requests.get(image_url, timeout=60)
            img_resp.raise_for_status()

            safe_query = "".join(c if c.isalnum() or c in " _-" else "" for c in query)[:40].strip().replace(" ", "_")
            filename = f"openai_{safe_query}_{int(time.time())}.png"
            dest_path = stock_dir / filename

            with open(dest_path, "wb") as f:
                f.write(img_resp.content)

            logger.info(f"Generated OpenAI asset image: {filename}")
            downloaded.append(dest_path)
            time.sleep(0.8)  # Rate limit courtesy

        except requests.exceptions.HTTPError as e:
            # Capture the actual OpenAI error message (critical for debugging 400s)
            error_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    err_json = e.response.json()
                    error_detail = err_json.get("error", {}).get("message", str(err_json))
                except Exception:
                    error_detail = e.response.text[:600]
            logger.error(f"OpenAI image generation failed for query '{query}': {error_detail}")
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
      - "openai": generate with DALL·E using the script for highly relevant images
    Returns list of local file paths ready to be used in video assembly (Ken Burns).

    script_data: optional full script dict (used to extract key_points for better OpenAI prompts)
    """
    stock_dir = ASSETS_DIR / "stock"
    stock_dir.mkdir(parents=True, exist_ok=True)

    queries = get_relevant_queries_from_script(script_text or topic)

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

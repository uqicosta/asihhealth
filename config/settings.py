"""
AsihHealth - Configuration Management
Cost-efficient YouTube automation for Indonesian content
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Literal

# Load .env file
load_dotenv()

# === Project Paths ===
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
ASSETS_DIR = Path(os.getenv("ASSETS_DIR", "assets"))

# Create directories
for d in [OUTPUT_DIR, ASSETS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Subdirectories
OUTPUT_SCRIPTS = OUTPUT_DIR / "scripts"
OUTPUT_AUDIO = OUTPUT_DIR / "audio"
OUTPUT_VIDEOS = OUTPUT_DIR / "videos"
OUTPUT_SUBTITLES = OUTPUT_DIR / "subtitles"
OUTPUT_THUMBNAILS = OUTPUT_DIR / "thumbnails"

for d in [OUTPUT_SCRIPTS, OUTPUT_AUDIO, OUTPUT_VIDEOS, OUTPUT_SUBTITLES, OUTPUT_THUMBNAILS]:
    d.mkdir(parents=True, exist_ok=True)

# === LLM Settings ===
LLM_PROVIDER: Literal["ollama", "groq", "gemini", "openrouter"] = os.getenv("LLM_PROVIDER", "ollama")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# Groq models (very fast & cheap). Good options:
# - "llama-3.3-70b-versatile"   (best quality)
# - "llama-3.1-8b-instant"      (very fast & cheap)
# - "gemma2-9b-it"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# === TTS Settings ===
# Providers:
# - "edge-tts"   : free online, good quality ID voices, but can be unreliable (network/service)
# - "xtts"       : local (Coqui XTTS), more reliable for automation, needs reference audio for best results
# - "piper"      : fast local offline (Piper), very reliable, needs voice model download
# - "openai"     : reliable cloud API (OpenAI TTS), easy setup, small cost, no local models/espeak needed. Good fallback.
# - "elevenlabs" : premium cloud (ElevenLabs), highest natural/emotional quality, great Indonesian support via multilingual_v2.
#                  Requires ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID. More expensive than OpenAI but often sounds best.
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge-tts")

# For edge-tts
TTS_VOICE = os.getenv("TTS_VOICE", "id-ID-AndikaNeural")  # Excellent Indonesian male voice

# For xtts / piper local (recommended for reliability in scheduler/daily use)
# Provide a short clear Indonesian audio sample (10-30s) for cloning or reference.
# Not needed for openai or edge-tts.
TTS_REFERENCE_AUDIO = os.getenv("TTS_REFERENCE_AUDIO", "")  # e.g. assets/voices/reference/narator.wav

# Piper model path (if using TTS_PROVIDER=piper)
PIPER_MODEL = os.getenv("PIPER_MODEL", "")  # e.g. assets/voices/piper/id_ID-fahmi-medium.onnx
PIPER_CONFIG = os.getenv("PIPER_CONFIG", "")  # usually model.json next to onnx

# === OpenAI TTS (reliable cloud API option, costs small $ but no local install hassle) ===
# Get key: https://platform.openai.com/api-keys
# Good for when local TTS install is problematic (Python version, espeak-ng, heavy models)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1")  # tts-1 (cheaper) or tts-1-hd (better quality)
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "onyx")  # onyx (deep male, great for narration), nova (female), alloy, echo, shimmer, fable

# === ElevenLabs TTS (premium quality, very natural & emotional voices, excellent multilingual incl. Indonesian) ===
# Get key + voice ID: https://elevenlabs.io (sign up, go to Voice Lab or Voices tab)
# Higher quality than OpenAI TTS for many users, but more expensive per character.
# Supports voice cloning (create custom voice in dashboard → use its voice_id here).
# Long scripts are auto-split (reuse the same chunking + FFmpeg concat logic as OpenAI).
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")  # REQUIRED for this provider. Example: "21m00Tcm4TlvDq8ikWAM" (Rachel) or your cloned ID
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")  # Recommended: eleven_multilingual_v2 (best quality, supports ID) or eleven_turbo_v2_5 (faster & cheaper)
ELEVENLABS_STABILITY = float(os.getenv("ELEVENLABS_STABILITY", "0.5"))  # 0.0-1.0 (lower = more expressive/variation, 0.5 is good default)
ELEVENLABS_SIMILARITY = float(os.getenv("ELEVENLABS_SIMILARITY", "0.75"))  # 0.0-1.0 (how closely to match the target voice)

# === Whisper Settings ===
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

# Subtitle formatting for tidier display (prevents long lines filling the screen)
SUBTITLE_MAX_CHARS_PER_LINE = int(os.getenv("SUBTITLE_MAX_CHARS_PER_LINE", "42"))
SUBTITLE_MAX_LINES = int(os.getenv("SUBTITLE_MAX_LINES", "2"))

# === Video Settings ===
VIDEO_RESOLUTION = os.getenv("VIDEO_RESOLUTION", "1080p")
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))
VIDEO_BITRATE = os.getenv("VIDEO_BITRATE", "6000k")

# === YouTube ===
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
YOUTUBE_CREDENTIALS = os.getenv("YOUTUBE_CREDENTIALS", "token.json")

# === Cost Control ===
MAX_SCRIPT_WORDS = int(os.getenv("MAX_SCRIPT_WORDS", "1200"))

# === Stock Visuals ===
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
USE_STOCK_VISUALS = os.getenv("USE_STOCK_VISUALS", "true").lower() == "true"
NUM_STOCK_IMAGES = int(os.getenv("NUM_STOCK_IMAGES", "7"))
USE_PEXELS_VIDEOS = os.getenv("USE_PEXELS_VIDEOS", "false").lower() == "true"

# Provider for asset images / video visuals (used in Ken Burns effect)
# "pexels": download free stock photos/videos from Pexels (default, requires PEXELS_API_KEY)
# "openai": generate custom images using DALL·E (requires OPENAI_API_KEY, paid)
ASSET_IMAGE_PROVIDER = os.getenv("ASSET_IMAGE_PROVIDER", "pexels")  # pexels | openai

# === Thumbnail ===
THUMBNAIL_ACCENT_COLOR = tuple(map(int, os.getenv("THUMBNAIL_ACCENT_COLOR", "220,38,38").split(",")))

# === Logo / Watermark Overlay ===
# Path to your logo image (PNG with transparency recommended)
LOGO_PATH = os.getenv("LOGO_PATH", "")  # e.g. assets/logo.png
# Position: bottom_right, bottom_left, top_right, top_left, or custom like "W-w-20:H-h-20"
LOGO_POSITION = os.getenv("LOGO_POSITION", "bottom_right")
# Size as fraction of video width (e.g. 0.08 = 8%)
LOGO_SIZE = float(os.getenv("LOGO_SIZE", "0.08"))
# Opacity 0.0 (invisible) to 1.0 (solid)
LOGO_OPACITY = float(os.getenv("LOGO_OPACITY", "0.75"))

# Thumbnail image generation provider
# "pillow": free local Pillow + stock image or solid bg (default, always works)
# "openai": use DALL·E via OpenAI to generate a custom AI thumbnail background image
THUMBNAIL_PROVIDER = os.getenv("THUMBNAIL_PROVIDER", "pillow")  # pillow | openai

# OpenAI model for thumbnail (and asset images) generation (if THUMBNAIL_PROVIDER=openai or ASSET_IMAGE_PROVIDER=openai)
OPENAI_THUMBNAIL_MODEL = os.getenv("OPENAI_THUMBNAIL_MODEL", "dall-e-3")  # dall-e-3, dall-e-2, or gpt-image-1
OPENAI_THUMBNAIL_SIZE = os.getenv("OPENAI_THUMBNAIL_SIZE", "1792x1024")  # auto-adjusted per model
# Optional override for quality (if set, used for all models that support it).
# gpt-image-1 supports: low, medium, high, auto
# dall-e-3 supports: standard, hd
OPENAI_IMAGE_QUALITY = os.getenv("OPENAI_IMAGE_QUALITY", "")
# Note: if OPENAI_IMAGE_QUALITY is empty, code auto-selects based on model.

# Response format for OpenAI image generation.
# "b64_json" (recommended - gets image data directly, no URL expiration issues)
# "url" (returns a temporary URL that expires after ~60 minutes)
OPENAI_IMAGE_RESPONSE_FORMAT = os.getenv("OPENAI_IMAGE_RESPONSE_FORMAT", "b64_json")

# === Health Content Specific Prompts ===
HEALTH_DISCLAIMER = """
PENTING: Video ini hanya untuk tujuan edukasi dan informasi umum. 
Bukan pengganti nasihat medis profesional. 
Konsultasikan dengan dokter atau tenaga kesehatan untuk kondisi kesehatan pribadi Anda.
"""

# Recommended Indonesian voices for health content
RECOMMENDED_VOICES = {
    "male_narration": "id-ID-AndikaNeural",      # Paling direkomendasikan
    "female_narration": "id-ID-GadisNeural",
    "male_formal": "id-ID-ArdiNeural",
}

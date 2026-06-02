#!/usr/bin/env python3
"""
Download a Piper TTS voice model for AsihHealth.

This helps get reliable offline Indonesian (or other) voices
since edge-tts can be unreliable for automation.

Usage examples:
    python scripts/download_piper_voice.py
    python scripts/download_piper_voice.py --voice id_ID-news_tts-medium
    python scripts/download_piper_voice.py --voice id_ID-fahmi-medium --quality medium

The script will download the .onnx and .onnx.json files into
assets/voices/piper/

After download, update your .env:
    TTS_PROVIDER=piper
    PIPER_MODEL=assets/voices/piper/id_ID-news_tts-medium.onnx

Good Indonesian voices (from rhasspy/piper-voices):
- id_ID-news_tts-medium   (recommended, news-style)
- Others may be available under id/ on HuggingFace

See: https://huggingface.co/rhasspy/piper-voices/tree/main/id
"""

import argparse
import os
from pathlib import Path
import sys

try:
    import requests
except ImportError:
    print("This script requires 'requests'. Install with:")
    print("pip install requests")
    sys.exit(1)


DEFAULT_TARGET_DIR = Path("assets/voices/piper")

# Known good Indonesian voices and their HF subpaths
KNOWN_VOICES = {
    "id_ID-news_tts-medium": "id/id_ID/news_tts/medium/id_ID-news_tts-medium",
    "id_ID-fahmi-medium": "id/id_ID/fahmi/medium/id_ID-fahmi-medium",  # if exists
}

def get_voice_path(voice: str) -> str:
    if voice in KNOWN_VOICES:
        return KNOWN_VOICES[voice]
    # Fallback: try common pattern
    # Assume user passes full like "id/id_ID/xxx/medium/voice"
    if "/" in voice:
        return voice
    # Last resort guess
    return f"id/id_ID/{voice.split('-')[0] if '-' in voice else 'news_tts'}/medium/{voice}"


def download_file(url: str, dest: Path, chunk_size: int = 8192):
    """Download a file with simple progress."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"  {dest.name} already exists, skipping download.")
        return

    print(f"Downloading {url} ...")
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()

    total_size = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = downloaded * 100 / total_size
                    print(f"\r  Progress: {percent:.1f}% ({downloaded // 1024} KB)", end="", flush=True)
    print()  # newline


def main():
    parser = argparse.ArgumentParser(description="Download Piper voice for AsihHealth (reliable local TTS)")
    parser.add_argument(
        "--voice",
        default="id_ID-news_tts-medium",
        help="Voice name, e.g. id_ID-news_tts-medium or id_ID-fahmi-medium"
    )
    parser.add_argument(
        "--quality",
        default="medium",
        choices=["low", "medium", "high"],
        help="Quality level (usually 'medium' is fine)"
    )
    parser.add_argument(
        "--lang",
        default="id_ID",
        help="Language code folder (default id_ID for Indonesian)"
    )
    parser.add_argument(
        "--target-dir",
        default=str(DEFAULT_TARGET_DIR),
        help="Where to save the voice files (default: assets/voices/piper)"
    )
    parser.add_argument(
        "--hf-repo",
        default="rhasspy/piper-voices",
        help="HuggingFace repo (default rhasspy/piper-voices)"
    )
    parser.add_argument(
        "--revision",
        default="main",
        help="Git revision/branch (default main)"
    )

    args = parser.parse_args()

    target_dir = Path(args.target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    voice_name = args.voice
    voice_path = get_voice_path(voice_name)

    onnx_filename = f"{voice_name}.onnx"
    json_filename = f"{voice_name}.onnx.json"

    # voice_path like "id/id_ID/news_tts/medium/id_ID-news_tts-medium"
    # base dir is everything except last segment
    dir_part = "/".join(voice_path.split("/")[:-1])
    base_url = f"https://huggingface.co/{args.hf_repo}/resolve/{args.revision}/{dir_part}"

    onnx_url = f"{base_url}/{onnx_filename}"
    json_url = f"{base_url}/{json_filename}"

    print(f"Target voice: {voice_name}")
    print(f"Downloading to: {target_dir}")
    print(f"ONNX URL: {onnx_url}")
    print(f"JSON URL: {json_url}")
    print()

    try:
        download_file(onnx_url, target_dir / onnx_filename)
        download_file(json_url, target_dir / json_filename)
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print("\n[ERROR] 404 Not Found. The voice layout might be different.")
            print("Please check available Indonesian voices at:")
            print("https://huggingface.co/rhasspy/piper-voices/tree/main/id")
            print("\nYou can specify exact subpath with manual download or update the script.")
            sys.exit(1)
        raise

    onnx_path = target_dir / onnx_filename
    json_path = target_dir / json_filename

    print("\n✅ Download complete!")
    print(f"ONNX : {onnx_path}")
    print(f"JSON : {json_path}")

    print("\nNow add to your .env file:")
    print(f"TTS_PROVIDER=piper")
    print(f"PIPER_MODEL={onnx_path.as_posix()}")
    print(f"# PIPER_CONFIG={json_path.as_posix()}   (usually auto-detected)")

    print("\nThen run the pipeline:")
    print("python pipeline/run.py --topic \"...\" --use-stock")


if __name__ == "__main__":
    main()
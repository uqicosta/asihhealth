"""
AsihHealth - Main Pipeline Orchestrator
One-command YouTube content automation (Bahasa Indonesia)

Usage examples:
    python pipeline/run.py --topic "Bahaya terlalu banyak minum kopi"
    python pipeline/run.py --topic "..." --model llama-3.3-70b-versatile --voice id-ID-GadisNeural
    python pipeline/run.py --topic "..." --only-script-voice
"""

# --- Path fix for direct script execution ---
# Allows running `python pipeline/run.py` from project root
# so that "from config..." and "from core..." resolve correctly.
import sys
from pathlib import Path as _PathForSetup

_project_root = _PathForSetup(__file__).parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
# --- end path fix ---

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config.settings import (
    OUTPUT_SCRIPTS, OUTPUT_AUDIO, OUTPUT_VIDEOS,
    TTS_VOICE, TTS_PROVIDER, TTS_REFERENCE_AUDIO,
    USE_STOCK_VISUALS, NUM_STOCK_IMAGES, PEXELS_API_KEY
)
from core.llm import LLMClient, generate_health_script
from core.tts import generate_voiceover, estimate_duration
from core.video import create_simple_video, create_video_with_images, check_ffmpeg
from core.subtitles import create_subtitles_and_burn
from core.assets import download_stock_for_topic
from core.thumbnail import generate_thumbnails_for_script
from core.youtube import upload_complete_from_pipeline

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("asihhealth")


def save_script_json(script_data: dict, topic: str) -> Path:
    """Save generated script data to JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(c for c in topic[:40] if c.isalnum() or c in " -_").strip().replace(" ", "_")
    filename = f"{timestamp}_{safe_topic}.json"
    path = OUTPUT_SCRIPTS / filename
    path.write_text(json.dumps(script_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_full_pipeline(
    topic: str,
    model: str = "qwen2.5:7b",
    voice: str = TTS_VOICE,
    generate_video: bool = True,
    burn_subtitles: bool = True,
    only_script_voice: bool = False,
    use_stock: Optional[bool] = None,
    generate_thumbnail: bool = True,
    auto_upload: bool = False,
    youtube_privacy: str = "private",
    voice_clone_reference: Optional[Path] = None,
):
    """
    Full automation pipeline for Indonesian health YouTube content.
    """
    console.print(Panel.fit(
        f"[bold cyan]AsihHealth YouTube Automation[/bold cyan]\n"
        f"Topic: [yellow]{topic}[/yellow]",
        border_style="blue"
    ))

    # === STEP 1: Generate Script ===
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Generating script with LLM...", total=None)
        client = LLMClient(model=model)
        console.print(f"[dim]LLM Provider: {client.provider} | Model: {client.model}[/dim]")
        script_data = generate_health_script(topic, client=client)
        script_path = save_script_json(script_data, topic)
        progress.update(task, description="Script generated ✓")

    console.print(f"\n[green]✓[/green] Script saved: [link={script_path}]{script_path.name}[/link]")
    console.print(f"   Title: [bold]{script_data['title']}[/bold]")
    console.print(f"   Est. duration: ~{script_data.get('estimated_duration_minutes', '?')} menit")

    if only_script_voice:
        # Stop here
        console.print("\n[yellow]--only-script-voice mode: stopping after script + voice generation.[/yellow]")
        _generate_voice_only(script_data, voice)
        return

    # === STEP 2: Generate Voiceover ===
    script_text = script_data["script"]
    clone_ref = voice_clone_reference

    # Auto use reference from env if using local TTS provider and no CLI override
    if not clone_ref and TTS_PROVIDER.lower() in ("xtts", "piper") and TTS_REFERENCE_AUDIO:
        clone_ref = Path(TTS_REFERENCE_AUDIO)

    task_desc = f"Generating voiceover ({TTS_PROVIDER})..."
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task(task_desc, total=None)
        try:
            audio_path = generate_voiceover(script_text, voice=voice, clone_reference=clone_ref)
        except Exception as tts_err:
            progress.update(task, description="Voiceover gagal ✗")
            console.print(f"\n[bold red]Error saat generate voiceover:[/bold red]")
            console.print(str(tts_err))
            console.print("\n[yellow]Tips: Untuk reliability lebih baik, set TTS_PROVIDER=xtts atau piper + reference audio di .env.[/yellow]")
            console.print("[yellow]PENTING: TTS/XTTS butuh Python 3.9 atau 3.10. Kamu pakai 3.14 → lihat QUICKSTART.md 'Python Version'.[/yellow]")
            raise
        progress.update(task, description="Voiceover generated ✓")

    console.print(f"[green]✓[/green] Audio: {audio_path.name}  |  Est. duration: {estimate_duration(script_text)} menit")

    if not generate_video:
        console.print("\n[cyan]Video generation skipped (--no-video).[/cyan]")
        return

    # === STEP 3: Create Video ===
    if not check_ffmpeg():
        console.print("[red]FFmpeg not found. Skipping video creation.[/red]")
        return

    # Decide video style: stock Ken Burns (recommended) vs simple background
    effective_use_stock = USE_STOCK_VISUALS if use_stock is None else use_stock

    stock_images: List[Path] = []

    if effective_use_stock:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Downloading free stock images from Pexels...", total=None)
            stock_images = download_stock_for_topic(
                topic=topic,
                script_text=script_text,
                num_images=NUM_STOCK_IMAGES,
                api_key=PEXELS_API_KEY or None
            )
            progress.update(task, description="Stock images downloaded ✓")

        console.print(f"[green]✓[/green] {len(stock_images)} stock images ready for visuals")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        if stock_images:
            task = progress.add_task("Creating Ken Burns video (stock images + smooth transitions)...", total=None)
            video_path = create_video_with_images(
                audio_path=audio_path,
                images=stock_images
            )
            progress.update(task, description="Ken Burns video created ✓")
            console.print(f"[green]✓[/green] Video (with stock): {video_path.name}")
        else:
            task = progress.add_task("Assembling simple background video...", total=None)
            video_path = create_simple_video(
                audio_path=audio_path,
                title=script_data["title"]
            )
            progress.update(task, description="Simple video assembled ✓")
            console.print(f"[green]✓[/green] Video (simple): {video_path.name}")

    # === STEP 4: Generate Thumbnail ===
    thumbnail_path: Optional[Path] = None
    if generate_thumbnail and 'video_path' in locals():
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Membuat thumbnail otomatis...", total=None)
            thumbs = generate_thumbnails_for_script(
                script_data=script_data,
                stock_images=stock_images if 'stock_images' in locals() else None,
                count=1
            )
            if thumbs:
                thumbnail_path = thumbs[0]
            progress.update(task, description="Thumbnail dibuat ✓")

        if thumbnail_path:
            console.print(f"[green]✓[/green] Thumbnail: {thumbnail_path.name}")

    # === STEP 5: Auto Upload to YouTube (optional) ===
    if auto_upload and 'video_path' in locals():
        console.print("\n[bold yellow]Memulai upload ke YouTube...[/bold yellow]")
        try:
            video_id = upload_complete_from_pipeline(
                video_path=video_path,
                script_json_path=script_path,
                thumbnail_path=thumbnail_path,
                privacy=youtube_privacy,
            )
            if video_id:
                console.print(f"[green]✓ Upload berhasil![/green] https://youtu.be/{video_id}")
            else:
                console.print("[red]Upload gagal. Cek log.[/red]")
        except Exception as e:
            console.print(f"[red]Error upload: {e}[/red]")

    # === Auto Subtitles + Burn (after video) ===
    if burn_subtitles and 'video_path' in locals():
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Generating subtitles with Whisper + burning...", total=None)
            srt_path, final_video = create_subtitles_and_burn(audio_path, video_path)
            progress.update(task, description="Subtitles burned ✓")

        console.print(f"[green]✓[/green] Final video with subtitles: [bold]{final_video.name}[/bold]")
        console.print(f"   SRT: {srt_path.name}")

    # Final summary
    video_display = "N/A"
    if 'final_video' in locals():
        video_display = final_video
    elif 'video_path' in locals():
        video_display = video_path

    console.print(Panel.fit(
        f"[bold green]SELESAI![/bold green]\n\n"
        f"Video siap: [cyan]{video_display}[/cyan]\n"
        f"Thumbnail: [cyan]{thumbnail_path.name if thumbnail_path else 'Tidak dibuat'}[/cyan]\n\n"
        f"[dim]Langkah selanjutnya:\n"
        f"• Review script di {script_path}\n"
        f"• Upload manual atau pakai --upload",
        border_style="green",
        title="Pipeline Complete"
    ))


def _generate_voice_only(script_data: dict, voice: str):
    """Helper for --only-script-voice mode."""
    script_text = script_data["script"]

    # auto ref for local providers
    clone_ref = None
    if TTS_PROVIDER.lower() in ("xtts", "piper") and TTS_REFERENCE_AUDIO:
        clone_ref = Path(TTS_REFERENCE_AUDIO)

    try:
        audio_path = generate_voiceover(script_text, voice=voice, clone_reference=clone_ref)
        console.print(f"\n[green]✓ Voiceover created:[/green] {audio_path}")
        console.print(f"  Duration estimate: {estimate_duration(script_text)} minutes")
    except Exception as tts_err:
        console.print(f"\n[bold red]Error saat generate voiceover (only-script-voice mode):[/bold red]")
        console.print(str(tts_err))
        console.print("\n[yellow]Tips: Untuk lebih reliable gunakan local TTS (xtts/piper) via .env.[/yellow]")
        console.print("[yellow]PENTING: TTS/XTTS butuh Python 3.9 atau 3.10. Kamu pakai 3.14 → lihat QUICKSTART.md 'Python Version'.[/yellow]")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="AsihHealth - Otomasi Konten YouTube Berbahasa Indonesia (Cost Efficient)"
    )
    parser.add_argument("--topic", "-t", required=True, help="Topik video kesehatan (dalam bahasa Indonesia)")
    parser.add_argument("--model", "-m", default=None, 
                        help="LLM model name. Default depends on LLM_PROVIDER in .env "
                             "(qwen2.5:7b for Ollama, llama-3.3-70b-versatile for Groq, etc.)")
    parser.add_argument("--voice", "-v", default=TTS_VOICE, 
                        help="Voice (untuk edge-tts). Untuk provider lokal, gunakan TTS_REFERENCE_AUDIO di .env")
    parser.add_argument("--no-video", action="store_true", help="Hanya generate script + voiceover")
    parser.add_argument("--no-subtitles", action="store_true", help="Skip auto subtitle generation")
    parser.add_argument("--only-script-voice", action="store_true", help="Stop setelah script + voice (untuk editing manual)")
    parser.add_argument("--use-stock", action="store_true", help="Force download & use Pexels stock images (Ken Burns style)")
    parser.add_argument("--no-stock", action="store_true", help="Force simple background video (no stock download)")
    parser.add_argument("--no-thumbnail", action="store_true", help="Skip automatic thumbnail generation")
    parser.add_argument("--upload", action="store_true", help="Upload otomatis ke YouTube setelah selesai (private by default)")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"], help="Privacy status untuk upload")
    parser.add_argument("--voice-clone", type=str, default=None, help="Path ke reference audio untuk voice cloning (XTTS). Contoh: assets/voices/reference/narator.wav")

    args = parser.parse_args()

    # Resolve stock preference from CLI + config
    use_stock_final = USE_STOCK_VISUALS
    if args.use_stock:
        use_stock_final = True
    if args.no_stock:
        use_stock_final = False

    clone_ref = Path(args.voice_clone) if args.voice_clone else None

    run_full_pipeline(
        topic=args.topic,
        model=args.model,
        voice=args.voice,
        generate_video=not args.no_video,
        burn_subtitles=not args.no_subtitles,
        only_script_voice=args.only_script_voice,
        use_stock=use_stock_final,
        generate_thumbnail=not args.no_thumbnail,
        auto_upload=args.upload,
        youtube_privacy=args.privacy,
        voice_clone_reference=clone_ref,
    )


if __name__ == "__main__":
    main()

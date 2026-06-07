"""
AsihHealth - Main Pipeline Orchestrator
One-command YouTube content automation (Bahasa Indonesia)

The public entry point is `run_full_pipeline(...)` (flat parameters for easy CLI use)
and `main()` for the argparse CLI.

Internal structure (after refactor):
- `pipeline/discovery.py`   : find_latest_* helpers for resume modes
- `RunInputs` dataclass     : clean container for resolved CLI + auto-discovery state
- `run_full_pipeline`       : thin orchestrator that delegates to private helpers:
    _load_or_generate_script
    _get_or_generate_audio
    _get_or_create_video
    _handle_thumbnail_and_subtitles
    _apply_logo_and_upload
    _print_final_summary

Usage examples:
    python pipeline/run.py --topic "Bahaya terlalu banyak minum kopi"
    python pipeline/run.py --topic "..." --model llama-3.3-70b-versatile --voice id-ID-GadisNeural
    python pipeline/run.py --topic "..." --only-script-voice

    # Resume with explicit paths (skip LLM + TTS):
    python pipeline/run.py --script output/scripts/....json --audio output/audio/voice_xxx.mp3 --use-stock

    # Easiest for re-generating images only (uses latest good script + audio):
    python pipeline/run.py --latest --use-stock
    python pipeline/run.py --refresh-images

    # Regenerate only subtitles (re-run Whisper guided by script + re-burn):
    python pipeline/run.py --script ... --audio ... --video output/videos/xxx_kenburns.mp4
    python pipeline/run.py --refresh-subtitles
    # Or use an already edited .srt and just re-burn it:
    python pipeline/run.py --video output/videos/xxx_kenburns.mp4 --srt output/subtitles/xxx.srt
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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

@dataclass
class RunInputs:
    """Resolved configuration for a pipeline run (from CLI args + auto-discovery).

    This makes the many resume modes (latest, refresh-*, explicit paths) easier
    to pass around and reason about.
    """
    topic: str
    model: Optional[str]
    voice: str
    generate_video: bool
    burn_subtitles: bool
    only_script_voice: bool
    use_stock: bool
    generate_thumbnail: bool
    auto_upload: bool
    youtube_privacy: str
    voice_clone_reference: Optional[Path]
    script_json: Optional[str]
    existing_audio: Optional[str]
    existing_video: Optional[str]
    existing_srt: Optional[str]

from config.settings import (
    OUTPUT_SCRIPTS, OUTPUT_AUDIO, OUTPUT_VIDEOS,
    TTS_VOICE, TTS_PROVIDER, TTS_REFERENCE_AUDIO,
    USE_STOCK_VISUALS, NUM_STOCK_IMAGES, PEXELS_API_KEY,
    ASSET_IMAGE_PROVIDER,
    SUBTITLE_MAX_CHARS_PER_LINE, SUBTITLE_MAX_LINES,
    LOGO_PATH, LOGO_POSITION, LOGO_SIZE, LOGO_OPACITY
)
from core.llm import LLMClient, generate_health_script
from core.tts import generate_voiceover, estimate_duration
from core.video import create_simple_video, create_video_with_images, check_ffmpeg, add_logo_overlay
from core.subtitles import create_subtitles_and_burn, burn_subtitles_ffmpeg
from pipeline.discovery import (
    find_latest_script,
    find_latest_audio,
    find_latest_base_video,
)
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


def _load_or_generate_script(
    script_json: Optional[str],
    topic: str,
    model: str,
) -> tuple[Path, dict]:
    """Load an existing script JSON or generate a new one via LLM.

    Returns (script_path, script_data).
    """
    if script_json:
        script_path = Path(script_json)
        if not script_path.exists():
            raise FileNotFoundError(f"Script JSON not found: {script_path}")
        script_data = json.loads(script_path.read_text(encoding="utf-8"))
        console.print(f"\n[green]✓[/green] Loaded existing script: [link={script_path}]{script_path.name}[/link]")
        console.print(f"   Title: [bold]{script_data.get('title', '?')}[/bold]")
        console.print(f"   Est. duration: ~{script_data.get('estimated_duration_minutes', '?')} menit")
        return script_path, script_data

    # Generate new script
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
    return script_path, script_data


def _get_or_generate_audio(
    existing_audio: Optional[str],
    script_data: Optional[dict],
    voice: str,
    voice_clone_reference: Optional[Path],
    burn_subtitles: bool,
    existing_srt: Optional[str],
) -> Optional[Path]:
    """Return an audio Path (existing or newly generated), or None if not needed.

    Audio is only required when we need to run Whisper for subtitles and
    no pre-existing SRT is provided.
    """
    script_text = (script_data or {}).get("script", "") if script_data else ""
    clone_ref = voice_clone_reference

    if not clone_ref and TTS_PROVIDER.lower() in ("xtts", "piper") and TTS_REFERENCE_AUDIO:
        clone_ref = Path(TTS_REFERENCE_AUDIO)

    needs_audio_for_transcription = burn_subtitles and not existing_srt

    audio_path: Optional[Path] = None
    if existing_audio:
        audio_path = Path(existing_audio)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        console.print(f"[green]✓[/green] Using existing voiceover: {audio_path.name}")
    elif needs_audio_for_transcription:
        if not script_text and script_data:
            script_text = script_data.get("script", "")
        task_desc = f"Generating voiceover ({TTS_PROVIDER})..."
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task(task_desc, total=None)
            try:
                audio_path = generate_voiceover(script_text or " ", voice=voice, clone_reference=clone_ref)
            except Exception as tts_err:
                progress.update(task, description="Voiceover gagal ✗")
                console.print(f"\n[bold red]Error saat generate voiceover:[/bold red]")
                console.print(str(tts_err))
                console.print("\n[yellow]Tips: Untuk reliability lebih baik, set TTS_PROVIDER=openai atau elevenlabs (cloud API, auto-split script panjang) atau xtts/piper + reference audio di .env.[/yellow]")
                console.print("[yellow]PENTING: TTS/XTTS butuh Python 3.9 atau 3.10. Kamu pakai 3.14 → lihat QUICKSTART.md 'Python Version'.[/yellow]")
                raise
            progress.update(task, description="Voiceover generated ✓")
    else:
        # Pure --video + --srt burn case: no audio/transcription needed
        console.print("[dim]No audio needed (re-burning existing subtitles)[/dim]")

    if audio_path:
        console.print(f"[green]✓[/green] Audio: {audio_path.name}  |  Est. duration: {estimate_duration(script_text or '')} menit")

    return audio_path


def _get_or_create_video(
    existing_video: Optional[str],
    audio_path: Optional[Path],
    script_data: Optional[dict],
    script_text: str,
    topic: str,
    use_stock: Optional[bool],
    stock_images_out: List[Path],  # mutated: populated when we generate images
) -> Path:
    """Return a video Path.

    If `existing_video` is provided, use it (for subtitle-only resume).
    Otherwise generate a new one (Ken Burns with stock or simple background).
    """
    if existing_video:
        video_path = Path(existing_video)
        if not video_path.exists():
            raise FileNotFoundError(f"Base video not found: {video_path}")
        console.print(f"[green]✓[/green] Using existing base video: {video_path.name} (subtitle regeneration mode)")
        return video_path

    if not check_ffmpeg():
        console.print("[red]FFmpeg not found. Skipping video creation.[/red]")
        # We still need to raise or handle; the caller already checked once, but keep consistent
        raise RuntimeError("FFmpeg not found")

    stock_images: List[Path] = []
    effective_use_stock = USE_STOCK_VISUALS if use_stock is None else use_stock

    if effective_use_stock:
        provider = ASSET_IMAGE_PROVIDER
        action = "Generating AI images with OpenAI" if provider == "openai" else "Downloading free stock images from Pexels"
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task(f"{action}...", total=None)
            stock_images = download_stock_for_topic(
                topic=topic,
                script_text=script_text,
                num_images=NUM_STOCK_IMAGES,
                api_key=PEXELS_API_KEY or None,
                script_data=script_data,
            )
            progress.update(task, description="Stock images ready ✓")

        console.print(f"[green]✓[/green] {len(stock_images)} stock images ready for visuals (provider: {ASSET_IMAGE_PROVIDER})")

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
            title = (script_data or {}).get("title", "AsihHealth") if script_data else "AsihHealth"
            video_path = create_simple_video(
                audio_path=audio_path,
                title=title
            )
            progress.update(task, description="Simple video assembled ✓")
            console.print(f"[green]✓[/green] Video (simple): {video_path.name}")

    # Pass the generated images back to the caller (for thumbnail step)
    stock_images_out.clear()
    stock_images_out.extend(stock_images)
    return video_path


def _handle_thumbnail_and_subtitles(
    video_path: Path,
    audio_path: Optional[Path],
    script_data: Optional[dict],
    generate_thumbnail: bool,
    stock_images: List[Path],
    burn_subtitles: bool,
    existing_srt: Optional[str],
) -> tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """Handle optional thumbnail generation + subtitles (or re-burn existing SRT).

    Returns (thumbnail_path, srt_path, final_video_path).
    """
    # Thumbnail
    thumbnail_path: Optional[Path] = None
    if generate_thumbnail and video_path:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Membuat thumbnail otomatis...", total=None)
            thumbs = generate_thumbnails_for_script(
                script_data=script_data,
                stock_images=stock_images,
                count=1
            )
            if thumbs:
                thumbnail_path = thumbs[0]
            progress.update(task, description="Thumbnail dibuat ✓")

        if thumbnail_path:
            console.print(f"[green]✓[/green] Thumbnail: {thumbnail_path.name}")

    # Subtitles
    srt_path: Optional[Path] = None
    final_video: Optional[Path] = None

    if burn_subtitles and video_path:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            if existing_srt:
                srt_path = Path(existing_srt)
                if not srt_path.exists():
                    raise FileNotFoundError(f"SRT file not found: {srt_path}")
                console.print(f"[green]✓[/green] Using existing SRT: {srt_path.name} (skipping transcription)")
                task = progress.add_task("Burning provided subtitles...", total=None)
                final_video = burn_subtitles_ffmpeg(video_path, srt_path)
                progress.update(task, description="Subtitles burned from existing SRT ✓")
            else:
                task = progress.add_task("Generating subtitles with Whisper + burning...", total=None)
                script_for_subs = None
                if script_data:
                    script_for_subs = script_data.get("script")
                if not audio_path:
                    raise RuntimeError("Cannot generate subtitles: audio file is required for Whisper transcription. Provide --audio or use --srt to burn an existing subtitle file.")
                srt_path, final_video = create_subtitles_and_burn(
                    audio_path, video_path,
                    script_text=script_for_subs,
                    max_chars_per_line=SUBTITLE_MAX_CHARS_PER_LINE,
                    max_lines=SUBTITLE_MAX_LINES,
                )
                progress.update(task, description="Subtitles burned ✓")

        if srt_path and final_video:
            console.print(f"[green]✓[/green] Final video with subtitles: [bold]{final_video.name}[/bold]")
            console.print(f"   SRT: {srt_path.name}")

    return thumbnail_path, srt_path, final_video


def _apply_logo_and_upload(
    video_path: Path,
    final_video: Optional[Path],
    script_path: Optional[Path],
    thumbnail_path: Optional[Path],
    auto_upload: bool,
    youtube_privacy: str,
) -> Optional[Path]:
    """Apply logo (if configured) and optionally upload. Returns the final video path."""
    current_final = final_video or video_path

    if LOGO_PATH:
        logo_p = Path(LOGO_PATH)
        if logo_p.exists():
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task = progress.add_task("Menambahkan logo/watermark...", total=None)
                current_final = add_logo_overlay(
                    current_final,
                    logo_p,
                    position=LOGO_POSITION,
                    size=LOGO_SIZE,
                    opacity=LOGO_OPACITY,
                )
                progress.update(task, description="Logo ditambahkan ✓")

            console.print(f"[green]✓[/green] Logo overlay added")

    if auto_upload and current_final:
        console.print("\n[bold yellow]Memulai upload ke YouTube...[/bold yellow]")
        try:
            video_id = upload_complete_from_pipeline(
                video_path=current_final,
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

    return current_final


def _print_final_summary(
    final_video: Optional[Path],
    video_path: Path,
    thumbnail_path: Optional[Path],
    script_path: Optional[Path],
):
    """Print the final completion panel."""
    video_display = final_video or video_path or "N/A"

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
    script_json: Optional[str] = None,
    existing_audio: Optional[str] = None,
    existing_video: Optional[str] = None,
    existing_srt: Optional[str] = None,
):
    """
    Full automation pipeline for Indonesian health YouTube content.

    Resume options for incremental work:
      --script + --audio + --video     → skip to subtitles (re-generate subs only)
      --video + --srt                  → just re-burn an (edited) .srt, skip Whisper
      --refresh-images                 → latest script+audio + new stock visuals
      --refresh-subtitles              → latest base video + re-do subtitles
    """
    console.print(Panel.fit(
        f"[bold cyan]AsihHealth YouTube Automation[/bold cyan]\n"
        f"Topic: [yellow]{topic}[/yellow]",
        border_style="blue"
    ))

    # === STEP 1: Script (generate or load existing) ===
    script_path, script_data = _load_or_generate_script(script_json, topic, model)

    if only_script_voice:
        # Stop here
        if existing_audio:
            console.print(f"\n[yellow]--only-script-voice + existing audio provided: nothing more to generate.[/yellow]")
            console.print(f"[green]✓[/green] Using audio: {existing_audio}")
            return
        console.print("\n[yellow]--only-script-voice mode: stopping after script + voice generation.[/yellow]")
        _generate_voice_only(script_data, voice)
        return

    # === STEP 2: Voiceover (generate or use existing) ===
    audio_path = _get_or_generate_audio(
        existing_audio=existing_audio,
        script_data=script_data,
        voice=voice,
        voice_clone_reference=voice_clone_reference,
        burn_subtitles=burn_subtitles,
        existing_srt=existing_srt,
    )
    script_text = (script_data or {}).get("script", "") if script_data else ""

    if not generate_video:
        console.print("\n[cyan]Video generation skipped (--no-video).[/cyan]")
        return

    # === STEP 3: Video (create new, or use existing base video for subtitle-only work) ===
    stock_images: List[Path] = []
    video_path = _get_or_create_video(
        existing_video=existing_video,
        audio_path=audio_path,
        script_data=script_data,
        script_text=script_text,
        topic=topic,
        use_stock=use_stock,
        stock_images_out=stock_images,
    )

    # === STEP 4: Thumbnail + Subtitles ===
    thumbnail_path, srt_path, final_video = _handle_thumbnail_and_subtitles(
        video_path=video_path,
        audio_path=audio_path,
        script_data=script_data,
        generate_thumbnail=generate_thumbnail,
        stock_images=stock_images,
        burn_subtitles=burn_subtitles,
        existing_srt=existing_srt,
    )

    # === STEP 5: Logo + Upload + Summary ===
    final_video = _apply_logo_and_upload(
        video_path=video_path,
        final_video=final_video,
        script_path=script_path,
        thumbnail_path=thumbnail_path,
        auto_upload=auto_upload,
        youtube_privacy=youtube_privacy,
    )

    _print_final_summary(
        final_video=final_video,
        video_path=video_path,
        thumbnail_path=thumbnail_path,
        script_path=script_path,
    )


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
        console.print("\n[yellow]Tips: Untuk lebih reliable gunakan TTS_PROVIDER=openai atau elevenlabs (API, auto-split untuk script panjang) atau local TTS (xtts/piper) via .env.[/yellow]")
        console.print("[yellow]PENTING: TTS/XTTS butuh Python 3.9 atau 3.10. Kamu pakai 3.14 → lihat QUICKSTART.md 'Python Version'.[/yellow]")
        raise




def main():
    parser = argparse.ArgumentParser(
        description="AsihHealth - Otomasi Konten YouTube Berbahasa Indonesia (Cost Efficient)"
    )
    parser.add_argument("--topic", "-t", required=False, help="Topik video kesehatan (dalam bahasa Indonesia). Wajib kecuali --script disediakan.")
    parser.add_argument("--model", "-m", default=None, 
                        help="LLM model name. Default depends on LLM_PROVIDER in .env "
                             "(qwen2.5:7b for Ollama, llama-3.3-70b-versatile for Groq, etc.)")
    parser.add_argument("--voice", "-v", default=TTS_VOICE, 
                        help="Voice (untuk edge-tts). Untuk openai gunakan OPENAI_TTS_VOICE di .env. Untuk provider lokal, gunakan TTS_REFERENCE_AUDIO.")
    parser.add_argument("--no-video", action="store_true", help="Hanya generate script + voiceover (lalu resume nanti pakai --script --audio)")
    parser.add_argument("--no-subtitles", action="store_true", help="Skip auto subtitle generation")
    parser.add_argument("--only-script-voice", action="store_true", help="Stop setelah script + voice (untuk editing manual). Gunakan --script + --audio untuk resume nanti.")
    parser.add_argument("--use-stock", action="store_true", help="Use stock images for video (Pexels or OpenAI DALL·E depending on ASSET_IMAGE_PROVIDER)")
    parser.add_argument("--no-stock", action="store_true", help="Force simple background video (no stock download)")
    parser.add_argument("--no-thumbnail", action="store_true", help="Skip automatic thumbnail generation")
    # Logo/watermark is configured via LOGO_PATH, LOGO_POSITION etc in .env (applied automatically to final video)
    parser.add_argument("--upload", action="store_true", help="Upload otomatis ke YouTube setelah selesai (private by default)")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"], help="Privacy status untuk upload")
    parser.add_argument("--voice-clone", type=str, default=None, help="Path ke reference audio untuk voice cloning (XTTS). Contoh: assets/voices/reference/narator.wav")
    parser.add_argument("--script", type=str, default=None,
                        help="Path ke script JSON existing (output/scripts/....json) untuk skip generate script (LLM)")
    parser.add_argument("--audio", type=str, default=None,
                        help="Path ke file audio/voiceover existing untuk skip TTS generation. Gunakan bersama --script untuk melanjutkan dari video creation.")
    parser.add_argument("--video", type=str, default=None,
                        help="Path ke base video existing (mis. *_kenburns.mp4 atau *_simple.mp4) untuk skip pembuatan visual dan lanjut ke subtitle regeneration.")
    parser.add_argument("--srt", type=str, default=None,
                        help="Path ke file .srt existing. Digunakan bersama --video untuk langsung burn subtitle tanpa Whisper (berguna setelah edit manual .srt).")

    # Convenience for "scripts + audio good, just want fresh images"
    parser.add_argument("--latest", action="store_true",
                        help="Auto-pick the most recent script + audio pair (perfect for re-generating only images)")
    parser.add_argument("--refresh-images", "--regen-images", dest="refresh_images", action="store_true",
                        help="Auto-select latest script+audio + force fresh stock images (new Ken Burns video)")
    parser.add_argument("--refresh-subtitles", "--regen-subs", dest="refresh_subtitles", action="store_true",
                        help="Auto-select latest base video + re-generate subtitles (re-run Whisper guided by script + burn)")

    args = parser.parse_args()

    try:
        inputs = _resolve_inputs(args)
    except SystemExit as e:
        # Allow _resolve_inputs to signal usage errors cleanly
        parser.error(str(e))

    run_full_pipeline(**inputs)


def _resolve_inputs(args) -> RunInputs:
    """Resolve CLI args + 'latest' auto-discovery into a clean RunInputs object.

    This keeps main() small and makes the many resume/latest modes easier
    to follow, test, and extend.
    """
    script_arg = args.script
    audio_arg = args.audio
    video_arg = args.video
    srt_arg = args.srt

    if args.latest or args.refresh_images or args.refresh_subtitles:
        if not script_arg:
            latest_script = find_latest_script()
            if latest_script:
                script_arg = str(latest_script)
                console.print(f"[cyan]→ Using latest script:[/cyan] {latest_script.name}")
            else:
                raise SystemExit("No scripts found in output/scripts/ (cannot use --latest / --refresh-images / --refresh-subtitles)")

        if not audio_arg and not (video_arg and srt_arg):
            latest_audio = find_latest_audio()
            if latest_audio:
                audio_arg = str(latest_audio)
                console.print(f"[cyan]→ Using latest audio:[/cyan] {latest_audio.name}")

    if args.refresh_images:
        console.print("[yellow]→ Refresh images mode: forcing fresh stock visuals (new Ken Burns video)[/yellow]")

    if args.refresh_subtitles:
        if not video_arg:
            latest_video = find_latest_base_video()
            if latest_video:
                video_arg = str(latest_video)
                console.print(f"[cyan]→ Using latest base video:[/cyan] {latest_video.name}")
            else:
                raise SystemExit("No videos found in output/videos/ (cannot use --refresh-subtitles)")
        console.print("[yellow]→ Refresh subtitles mode: will re-generate subtitles (Whisper + burn) on the base video[/yellow]")

    # Topic requirement
    if not args.topic and not script_arg:
        if not (video_arg and srt_arg):
            raise SystemExit("--topic is required (unless you provide --script, --video + --srt, or use --latest / --refresh-*)")

    # Derive effective topic (used for stock image prompts, simple video title, etc.)
    effective_topic = args.topic
    if not effective_topic and script_arg:
        try:
            with open(script_arg, encoding="utf-8") as f:
                tmp = json.load(f)
            effective_topic = tmp.get("title") or Path(script_arg).stem
        except Exception:
            effective_topic = "resumed-video"

    # Stock visuals preference
    use_stock_final = USE_STOCK_VISUALS
    if args.refresh_images:
        use_stock_final = True
    elif args.use_stock:
        use_stock_final = True
    if args.no_stock:
        use_stock_final = False

    if args.refresh_subtitles and not args.refresh_images:
        if not args.use_stock:
            use_stock_final = False

    clone_ref = Path(args.voice_clone) if args.voice_clone else None

    return RunInputs(
        topic=effective_topic,
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
        script_json=script_arg,
        existing_audio=audio_arg,
        existing_video=video_arg,
        existing_srt=srt_arg,
    )


if __name__ == "__main__":
    main()

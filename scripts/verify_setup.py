"""
AsihHealth Setup Verification Script
Checks all critical dependencies before running the pipeline.
"""

import sys
import shutil
from rich.console import Console
from rich.table import Table

console = Console()


def check(name: str, check_fn, fix: str):
    try:
        ok = check_fn()
        status = "[green]OK[/green]" if ok else "[red]MISSING[/red]"
        if not ok:
            console.print(f"  Fix: {fix}", style="dim")
        return ok
    except Exception as e:
        console.print(f"  Error checking {name}: {e}", style="red")
        return False


def main():
    console.print("[bold cyan]AsihHealth - Setup Verification[/bold cyan]\n")

    table = Table(title="Dependency Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Recommendation")

    checks = [
        ("Python 3.11+", lambda: sys.version_info >= (3, 11), "Upgrade Python"),
        ("FFmpeg", lambda: shutil.which("ffmpeg") is not None, "winget install ffmpeg"),
        ("Ollama (optional)", lambda: shutil.which("ollama") is not None, "Download from ollama.com (recommended for 100% free)"),
    ]

    all_ok = True
    for name, fn, fix in checks:
        ok = check(name, fn, fix)
        status = "[green]✓[/green]" if ok else "[yellow]⚠[/yellow]"
        table.add_row(name, status, fix)
        if not ok and "optional" not in name.lower():
            all_ok = False

    console.print(table)

    # Try importing key packages
    console.print("\n[bold]Python packages:[/bold]")
    packages = [
        ("edge-tts", "pip install edge-tts"),
        ("ollama", "pip install ollama"),
        ("faster-whisper", "pip install faster-whisper"),
        ("pydub", "pip install pydub"),
        ("rich", "pip install rich typer"),
    ]

    for pkg, fix in packages:
        try:
            __import__(pkg.replace("-", "_"))
            console.print(f"  [green]✓[/green] {pkg}")
        except ImportError:
            console.print(f"  [red]✗[/red] {pkg}  → {fix}")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. pip install -r requirements.txt")
    console.print("2. (Recommended) ollama pull qwen2.5:7b")
    console.print("3. python pipeline/run.py --topic \"Bahaya minum kopi setiap hari\"")

    if all_ok:
        console.print("\n[bold green]Basic requirements met. Ready to generate content![/bold green]")


if __name__ == "__main__":
    main()

"""
AsihHealth - Daily Scheduler
Otomatis generate 1 video per hari dari antrian topik.

Cara pakai:
1. Isi / edit scheduler/topics.json
2. Jalankan: python scheduler/daily.py

Untuk menjalankan otomatis setiap hari di Windows:
- Gunakan Task Scheduler (lihat instruksi di bawah)
- Atau biarkan script ini running dengan mode --loop

Cost efficient: hanya generate 1 video/hari.
"""

import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from rich.console import Console
from rich.panel import Panel

from config.settings import OUTPUT_DIR
from pipeline.run import run_full_pipeline

console = Console()
logger = logging.getLogger("asihhealth.scheduler")

TOPICS_FILE = Path(__file__).parent / "topics.json"
PROCESSED_FILE = OUTPUT_DIR / "scheduler_processed.json"


def load_topics() -> List[Dict]:
    if not TOPICS_FILE.exists():
        console.print("[red]topics.json tidak ditemukan![/red]")
        return []
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_processed() -> List[str]:
    if not PROCESSED_FILE.exists():
        return []
    try:
        return json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
    except:
        return []


def save_processed(topics: List[str]):
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")


def get_next_topic() -> Optional[Dict]:
    """Ambil topik berikutnya yang belum diproses (berdasarkan priority)."""
    topics = load_topics()
    processed = load_processed()

    available = [t for t in topics if t["topic"] not in processed]
    if not available:
        return None

    # Sort by priority descending
    available.sort(key=lambda x: x.get("priority", 5), reverse=True)
    return available[0]


def mark_as_done(topic: str):
    processed = load_processed()
    if topic not in processed:
        processed.append(topic)
        save_processed(processed)


def run_daily(generate: bool = True, upload: bool = False, use_stock: bool = True):
    """Generate satu video dari topik berikutnya."""
    topic_info = get_next_topic()

    if not topic_info:
        console.print(Panel.fit(
            "[yellow]Semua topik sudah diproses.[/yellow]\n"
            "Tambahkan topik baru di scheduler/topics.json",
            border_style="yellow"
        ))
        return

    topic = topic_info["topic"]
    console.print(Panel.fit(
        f"[bold cyan]ASIHHEALTH DAILY SCHEDULER[/bold cyan]\n\n"
        f"Topik hari ini:\n[bold yellow]{topic}[/bold yellow]",
        border_style="blue"
    ))

    if not generate:
        console.print("[dim]Mode dry-run. Tidak generate video.[/dim]")
        return

    try:
        run_full_pipeline(
            topic=topic,
            use_stock=use_stock,
            # Kamu bisa tambahkan parameter lain di sini
        )
        mark_as_done(topic)
        console.print(f"\n[green]✓[/green] Topik selesai dan ditandai: {topic}")

        # TODO: Tambahkan auto upload jika upload=True
        # (setelah fitur upload matang)

    except Exception as e:
        logger.exception("Gagal generate video harian")
        console.print(f"[red]Error saat generate: {e}[/red]")


def run_loop(interval_hours: int = 24):
    """Jalankan scheduler dalam loop (untuk development / server)."""
    try:
        import schedule
    except ImportError:
        console.print("[red]Library 'schedule' belum terinstall.[/red]")
        console.print("pip install schedule")
        return

    console.print(f"[green]Scheduler berjalan. Akan generate setiap {interval_hours} jam.[/green]")
    console.print("Tekan Ctrl+C untuk berhenti.\n")

    schedule.every(interval_hours).hours.do(lambda: run_daily())

    # Jalankan sekali langsung
    run_daily()

    while True:
        schedule.run_pending()
        import time
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="AsihHealth Daily Content Scheduler")
    parser.add_argument("--dry-run", action="store_true", help="Hanya tampilkan topik berikutnya, jangan generate")
    parser.add_argument("--loop", action="store_true", help="Jalankan dalam mode loop (setiap 24 jam)")
    parser.add_argument("--no-stock", action="store_true", help="Jangan pakai stock image")
    parser.add_argument("--upload", action="store_true", help="Upload otomatis ke YouTube setelah generate (masih eksperimental)")

    args = parser.parse_args()

    if args.loop:
        run_loop()
    else:
        run_daily(
            generate=not args.dry_run,
            upload=args.upload,
            use_stock=not args.no_stock
        )


if __name__ == "__main__":
    main()

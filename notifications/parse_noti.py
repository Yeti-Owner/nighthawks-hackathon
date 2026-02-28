"""
Webcam phone screen → Gemini notification extractor → CSV

- Watches ../logs/captures (sibling to this script's folder)
- PNG files only; filename stem (HH MM SS) used as the timestamp column
- Queue handles multiple files arriving simultaneously
- Retries with exponential backoff on 429 rate limit errors
- Only deletes image on success — keeps it on failure
"""

import os
import csv
import time
import queue
import base64
import json
import logging
import threading
from pathlib import Path

import requests
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

load_dotenv()

SCRIPT_DIR  = Path(__file__).parent.resolve()
WATCH_DIR   = SCRIPT_DIR.parent / "logs" / "captures"
CSV_FILE    = SCRIPT_DIR.parent / "logs" / "notifications.csv"
API_KEY     = os.getenv("GEMINI_API_KEY")
MODEL       = os.getenv("MODEL", "gemini-2.0-flash")
MAX_RETRIES = 6          # attempts before giving up
RETRY_BASE  = 2          # backoff in seconds: 2, 4, 8, 16, 32, 64

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent?key={API_KEY}"
)

PROMPT = """Look at this phone screen image. If there is a visible notification, return ONLY a JSON object with these fields:
- has_notification: true or false
- urgency: "Low", "Medium", or "High" (null if no notification)
- source: app name like "iMessage", "Discord", "Gmail", etc. (null if no notification)
- sender: who sent it, if visible (null if unknown or no notification)
- summary: one short sentence about what it's about (null if no notification)

Return ONLY the raw JSON, no markdown, no explanation."""

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

image_queue: queue.Queue = queue.Queue()


def init_csv():
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp", "filename", "has_notification",
                 "urgency", "source", "sender", "summary", "error"]
            )


def call_gemini(image_path: Path) -> dict:
    """Send image to Gemini with exponential backoff on 429."""
    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    payload = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": "image/png", "data": image_data}}
            ]
        }]
    }

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.post(GEMINI_URL, json=payload, timeout=30)

        if response.status_code == 429:
            wait = RETRY_BASE ** attempt
            log.warning(f"Rate limited — retry {attempt}/{MAX_RETRIES} in {wait}s")
            time.sleep(wait)
            continue

        response.raise_for_status()
        raw = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)

    raise RuntimeError(f"Rate limit persisted after {MAX_RETRIES} retries")


def write_csv(image_path: Path, result: dict, error: str = ""):
    with open(CSV_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            image_path.stem,        # timestamp from filename e.g. "14 32 07"
            image_path.name,
            result.get("has_notification", ""),
            result.get("urgency", ""),
            result.get("source", ""),
            result.get("sender", ""),
            result.get("summary", ""),
            error
        ])


def process_image(image_path: Path):
    log.info(f"Processing: {image_path.name}")

    try:
        result = call_gemini(image_path)
    except Exception as e:
        log.error(f"Failed: {image_path.name} — {e}  (image kept, error logged)")
        write_csv(image_path, {}, error=str(e))
        return  # do NOT delete — image stays for manual retry

    write_csv(image_path, result)
    image_path.unlink()
    log.info(
        f"Done & deleted: {image_path.name} | "
        f"notification={result.get('has_notification')} "
        f"urgency={result.get('urgency')} source={result.get('source')}"
    )


def worker():
    """Background thread: drain the queue one image at a time."""
    while True:
        image_path = image_queue.get()
        if image_path is None:   # poison pill → exit
            break
        process_image(image_path)
        image_queue.task_done()


class PngHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() == ".png":
            time.sleep(0.3)      # let the file finish writing
            image_queue.put(path)
            log.info(f"Queued: {path.name}  (queue depth: {image_queue.qsize()})")


def enqueue_existing():
    existing = sorted(WATCH_DIR.glob("*.png"))
    if existing:
        log.info(f"Queueing {len(existing)} existing PNG(s)...")
        for p in existing:
            image_queue.put(p)


def batch_mode():
    """Process all existing PNGs in WATCH_DIR then exit."""
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env")

    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    init_csv()

    existing = sorted(WATCH_DIR.glob("*.png"))
    if not existing:
        log.info("Batch mode: no PNG files to process.")
        return

    log.info(f"Batch mode: processing {len(existing)} PNG(s)...")
    for p in existing:
        process_image(p)
    log.info("Batch mode: done.")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", action="store_true",
                        help="Process existing PNGs and exit (no file watching)")
    args = parser.parse_args()

    if args.batch:
        batch_mode()
        return

    if not API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env")

    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    init_csv()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    enqueue_existing()

    observer = Observer()
    observer.schedule(PngHandler(), str(WATCH_DIR), recursive=False)
    observer.start()
    log.info(f"Watching  {WATCH_DIR}")
    log.info(f"CSV output → {CSV_FILE}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down…")
        observer.stop()
        image_queue.put(None)
    observer.join()
    t.join()


if __name__ == "__main__":
    main()
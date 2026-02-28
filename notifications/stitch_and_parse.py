"""
stitch_and_parse.py
-------------------
Stitches all optimized PNG captures into a single grid image,
sends ONE call to Gemini, and writes all notification rows to CSV.

Usage:
    python stitch_and_parse.py          # process logs/captures/*.png
    python stitch_and_parse.py --dry    # just stitch, don't call Gemini

Expects GEMINI_API_KEY in ../.env
"""

import os
import sys
import csv
import json
import math
import base64
from pathlib import Path

import requests
from PIL import Image
from dotenv import load_dotenv

# ── Paths ──
SCRIPT_DIR = Path(__file__).parent.resolve()
CAPTURES_DIR = SCRIPT_DIR.parent / "logs" / "captures"
CSV_FILE = SCRIPT_DIR.parent / "logs" / "notifications.csv"
GRID_FILE = SCRIPT_DIR.parent / "logs" / "captures" / "_grid.png"

# ── Gemini ──
load_dotenv(SCRIPT_DIR.parent / ".env")
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("MODEL", "gemini-2.0-flash")
MAX_RETRIES = 4
RETRY_BASE = 3  # seconds

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent?key={API_KEY}"
)

PROMPT = """This image is a grid of phone screen captures taken during a study session.
Each cell is labeled with a number (1, 2, 3...) in the top-left corner.

For EACH cell, determine if there is a visible notification on the phone screen.
Return a JSON array where each element has:
- cell: the cell number (integer)
- has_notification: true or false
- urgency: "Low", "Medium", or "High" (null if no notification)
- source: app name like "iMessage", "Discord", "Gmail" (null if no notification)
- sender: who sent it if visible (null if unknown)
- summary: one short sentence about what it's about (null if no notification)

Return ONLY the raw JSON array, no markdown, no explanation.
If NO cells have notifications, return an empty array: []"""


# ── Helpers ──

def get_images():
    """Get all PNG files in captures dir (skip the grid file itself)."""
    if not CAPTURES_DIR.is_dir():
        return []
    imgs = sorted([
        f for f in CAPTURES_DIR.iterdir()
        if f.suffix.lower() == ".png" and f.name != "_grid.png"
    ])
    return imgs


def stitch_grid(image_paths, max_cols=3, cell_size=640):
    """
    Stitch images into a grid with numbered labels.
    Returns the grid PIL Image and the mapping of cell# → filename.
    """
    n = len(image_paths)
    cols = min(n, max_cols)
    rows = math.ceil(n / cols)

    grid_w = cols * cell_size
    grid_h = rows * cell_size
    grid = Image.new("RGB", (grid_w, grid_h), (30, 30, 30))

    cell_map = {}  # cell_number → image_path

    for idx, img_path in enumerate(image_paths):
        cell_num = idx + 1
        cell_map[cell_num] = img_path

        row = idx // cols
        col = idx % cols
        x = col * cell_size
        y = row * cell_size

        try:
            img = Image.open(img_path).convert("RGB")
            img.thumbnail((cell_size - 4, cell_size - 4), Image.LANCZOS)

            # Center in cell
            px = x + (cell_size - img.width) // 2
            py = y + (cell_size - img.height) // 2
            grid.paste(img, (px, py))

            # Draw cell number label (simple: white rectangle + number)
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(grid)
            label = str(cell_num)
            # Background box
            draw.rectangle([x + 2, y + 2, x + 36, y + 28], fill=(0, 0, 0))
            draw.text((x + 8, y + 4), label, fill=(255, 255, 255))
        except Exception as e:
            print(f"  [stitch] Failed to load {img_path.name}: {e}")

    return grid, cell_map


def call_gemini(grid_image_path):
    """Send the grid image to Gemini. Returns parsed JSON array."""
    image_data = base64.b64encode(grid_image_path.read_bytes()).decode("utf-8")
    payload = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": "image/png", "data": image_data}}
            ]
        }]
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(GEMINI_URL, json=payload, timeout=60)

            if response.status_code == 429:
                wait = RETRY_BASE ** attempt
                print(f"  [gemini] Rate limited — retry {attempt}/{MAX_RETRIES} in {wait}s")
                import time
                time.sleep(wait)
                continue

            response.raise_for_status()
            raw = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(raw)
        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
            print(f"  [gemini] Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                import time
                time.sleep(RETRY_BASE)
                continue
            raise

    raise RuntimeError(f"Gemini failed after {MAX_RETRIES} retries")


def init_csv():
    """Ensure CSV file exists with header."""
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp", "filename", "has_notification",
                 "urgency", "source", "sender", "summary", "error"]
            )


def write_results(results, cell_map):
    """Write Gemini results to CSV and delete processed images."""
    init_csv()

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        for entry in results:
            cell = entry.get("cell", 0)
            img_path = cell_map.get(cell)
            filename = img_path.name if img_path else f"cell_{cell}"
            # Extract timestamp from filename (capture_HH_MM_SS.png → HH_MM_SS)
            timestamp = filename.replace("capture_", "").replace(".png", "")

            writer.writerow([
                timestamp,
                filename,
                entry.get("has_notification", False),
                entry.get("urgency"),
                entry.get("source"),
                entry.get("sender"),
                entry.get("summary"),
                ""  # no error
            ])

    # Clean up processed images
    for img_path in cell_map.values():
        try:
            img_path.unlink()
        except Exception:
            pass

    # Remove grid file
    if GRID_FILE.exists():
        try:
            GRID_FILE.unlink()
        except Exception:
            pass


# ── Main ──

def main():
    images = get_images()

    if not images:
        print("[stitch] No PNG captures to process.")
        return

    print(f"[stitch] Found {len(images)} image(s) to process.")

    # 1. Stitch into grid
    grid, cell_map = stitch_grid(images)
    GRID_FILE.parent.mkdir(parents=True, exist_ok=True)
    grid.save(str(GRID_FILE), format="PNG", optimize=True)
    size_kb = GRID_FILE.stat().st_size / 1024
    print(f"[stitch] Grid saved: {GRID_FILE} ({size_kb:.0f} KB, {len(images)} cells)")

    # 2. Check for dry run
    if "--dry" in sys.argv:
        print("[stitch] Dry run — skipping Gemini call.")
        return

    # 3. Call Gemini
    if not API_KEY:
        print("[stitch] ERROR: GEMINI_API_KEY not set. Skipping parse.")
        return

    print("[stitch] Calling Gemini...")
    try:
        results = call_gemini(GRID_FILE)
        print(f"[stitch] Gemini returned {len(results)} result(s).")
    except Exception as e:
        print(f"[stitch] Gemini failed: {e}")
        # Write error rows so we know which images were attempted
        init_csv()
        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            for cell_num, img_path in cell_map.items():
                ts = img_path.name.replace("capture_", "").replace(".png", "")
                writer.writerow([ts, img_path.name, "", "", "", "", "", str(e)])
        return

    # 4. Write to CSV and clean up
    write_results(results, cell_map)
    print(f"[stitch] Done. Wrote {len(results)} row(s) to {CSV_FILE}")


if __name__ == "__main__":
    main()

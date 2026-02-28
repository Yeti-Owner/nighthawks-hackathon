"""
phone_watcher.py
----------------
Watches a webcam and saves a photo only when a SIGNIFICANT change is detected.
Designed to capture a phone screen lighting up from a notification/text.

HOW IT WORKS
------------
- Fills a rolling buffer of the last BUFFER_SIZE greyscale frames (every frame, not just saved ones)
- Waits until the buffer is full before saving anything (warm-up phase)
- Computes a running AVERAGE of the buffer as the "baseline"
- A frame triggers a save if EITHER:
    (a) Enough pixels differ from the baseline by more than PIXEL_DIFF_THRESHOLD
    (b) The mean brightness jumps by more than BRIGHTNESS_JUMP_THRESHOLD
        (this catches the phone screen lighting up even in a stable scene)
- Prints live debug stats so you can tune thresholds without guessing
- Dark frames (phone screen off) can be auto-deleted

Press ENTER in the console to stop.

Install: pip install opencv-python numpy
"""

import cv2
import numpy as np
import os
import sys
import time
import signal
import threading
import subprocess
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

# ─────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────────────────────────

CAPTURE_INTERVAL       = 0.5    # seconds between frame reads
OUTPUT_FOLDER          = os.path.join(os.path.dirname(__file__), "captures")
CAMERA_INDEX           = 0

try:
    import json
    with open(os.path.join(os.path.dirname(__file__), "..", "cam_select", "cameras.txt"), "r") as f:
        _cameras = json.load(f)
        CAMERA_INDEX = _cameras.get("secondary", {}).get("id", CAMERA_INDEX)
except Exception:
    pass

# --- Rolling baseline ---
BUFFER_SIZE            = 10     # frames in rolling average

# --- Trigger: brightness INCREASE only (screen lighting up) ---
BRIGHTNESS_JUMP        = 25     # mean brightness must jump UP by this much
MIN_BRIGHTNESS         = 80     # frame must be at least this bright to save (0-255)

# --- Cooldown ---
SAVE_COOLDOWN          = 5      # seconds between saves (prevents spam)

# --- Debug ---
PRINT_EVERY_N_FRAMES   = 10

# ─────────────────────────────────────────────────────────────────

stop_flag = threading.Event()

def _handle_signal(signum, frame):
    stop_flag.set()

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def ensure_output_folder():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def to_grey(frame):
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)


def compute_baseline(buffer):
    return np.mean(np.stack(buffer, axis=0), axis=0)


def save_frame(frame):
    ts = datetime.now(ZoneInfo("America/New_York")).strftime("%H_%M_%S")
    filename = f"capture_{ts}.jpg"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    cv2.imwrite(filepath, frame)
    return filepath


def console_listener():
    input("\n  Press ENTER at any time to stop.\n\n")
    stop_flag.set()


def run():
    ensure_output_folder()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera index {CAMERA_INDEX}.")
        return

    print("=" * 60)
    print(f"  noti_watcher  -  saving to: {os.path.abspath(OUTPUT_FOLDER)}")
    print("=" * 60)
    print(f"  Brightness jump   : +{BRIGHTNESS_JUMP} levels (increase only)")
    print(f"  Min brightness    : {MIN_BRIGHTNESS}")
    print(f"  Cooldown          : {SAVE_COOLDOWN}s between saves")
    print("=" * 60)

    buffer      = deque(maxlen=BUFFER_SIZE)
    saved_count = 0
    frame_count = 0
    last_save   = 0.0  # timestamp of last save

    if sys.stdin and sys.stdin.isatty():
        listener = threading.Thread(target=console_listener, daemon=True)
        listener.start()

    try:
        while not stop_flag.is_set():
            t0 = time.time()

            ret, frame = cap.read()
            if not ret:
                time.sleep(CAPTURE_INTERVAL)
                continue

            frame_count += 1
            grey = to_grey(frame)
            buffer.append(grey)

            # Warm-up
            if len(buffer) < BUFFER_SIZE:
                remaining = BUFFER_SIZE - len(buffer)
                print(f"  [WARM-UP] {remaining} frames left   ", end="\r")
                elapsed = time.time() - t0
                time.sleep(max(0, CAPTURE_INTERVAL - elapsed))
                continue

            baseline = compute_baseline(buffer)
            frame_mean = float(np.mean(grey))
            base_mean  = float(np.mean(baseline))
            brightness_delta = frame_mean - base_mean

            # Debug
            if frame_count % PRINT_EVERY_N_FRAMES == 0:
                print(
                    f"  [LIVE] frame={frame_count:5d} | "
                    f"base={base_mean:5.1f} | now={frame_mean:5.1f} | "
                    f"delta={brightness_delta:+6.1f}   "
                )

            # Trigger: brightness INCREASED + frame is bright + cooldown elapsed
            now = time.time()
            if (brightness_delta >= BRIGHTNESS_JUMP
                    and frame_mean >= MIN_BRIGHTNESS
                    and (now - last_save) >= SAVE_COOLDOWN):
                filepath = save_frame(frame)
                saved_count += 1
                last_save = now
                print(
                    f"\n  [SAVED] {os.path.basename(filepath)}  "
                    f"delta={brightness_delta:+.1f}  mean={frame_mean:.0f}  "
                    f"| total={saved_count}"
                )

            elapsed = time.time() - t0
            time.sleep(max(0, CAPTURE_INTERVAL - elapsed))

    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt received.")
    finally:
        cap.release()
        print(f"\n[DONE] frames={frame_count}  saved={saved_count}")


if __name__ == "__main__":
    run()
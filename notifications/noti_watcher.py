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
import time
import threading
import subprocess
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

# ─────────────────────────────────────────────────────────────────
#  CONFIGURATION  ← tweak these
# ─────────────────────────────────────────────────────────────────

CAPTURE_INTERVAL       = 0.5    # seconds between captures (0.5 = twice/sec)
OUTPUT_FOLDER          = os.path.join(os.path.dirname(__file__), "captures")
CAMERA_INDEX           = 0      # 0 = default webcam

try:
    import json
    with open(os.path.join(os.path.dirname(__file__), "..", "cam_select", "cameras.txt"), "r") as f:
        _cameras = json.load(f)
        CAMERA_INDEX = _cameras.get("secondary", {}).get("id", CAMERA_INDEX)
except Exception:
    pass

# --- Rolling baseline buffer ---
BUFFER_SIZE            = 10     # frames kept in rolling average (also the warm-up period)

# --- Pixel-level diff trigger ---
# A pixel "counts" as changed if it differs from the baseline average by this many levels (0-255)
PIXEL_DIFF_THRESHOLD   = 20     # lower = more sensitive to small changes
# Percentage of total pixels that must be "changed" to trigger a save
CHANGED_PIXEL_PCT      = 20.0    # lower = more sensitive; raise if saving too often

# --- Brightness-jump trigger (phone lighting up) ---
# If the mean brightness of the frame jumps by this many levels vs the baseline mean, always save.
# A phone going from off->on typically causes a +30-80 level jump depending on room lighting.
BRIGHTNESS_JUMP        = 20     # lower = more sensitive to brightness changes

# --- Dark frame removal ---
# Frames whose mean greyscale is below this are considered "phone off / dark"
DARK_BRIGHTNESS        = 50     # 0-255; raise if dark frames are being kept
DELETE_DARK_FRAMES     = True   # delete dark frames automatically

# --- Debug ---
PRINT_EVERY_N_FRAMES   = 5      # print live stats every N frames (1 = every frame, verbose)

# ─────────────────────────────────────────────────────────────────

stop_flag = threading.Event()


def ensure_output_folder():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def to_grey(frame):
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)


def compute_baseline(buffer):
    """Mean image across all frames in the buffer."""
    return np.mean(np.stack(buffer, axis=0), axis=0)


def analyse_frame(grey_f32, baseline):
    """
    Returns (pixel_pct_changed, brightness_delta, base_mean, frame_mean).
    grey_f32 and baseline are both float32 greyscale arrays.
    """
    diff = np.abs(grey_f32 - baseline)
    changed_pixels = np.sum(diff > PIXEL_DIFF_THRESHOLD)
    pixel_pct = (changed_pixels / grey_f32.size) * 100.0
    frame_mean = float(np.mean(grey_f32))
    base_mean  = float(np.mean(baseline))
    brightness_delta = frame_mean - base_mean
    return pixel_pct, brightness_delta, base_mean, frame_mean


def is_significant(pixel_pct, brightness_delta):
    pixel_trigger      = pixel_pct >= CHANGED_PIXEL_PCT
    brightness_trigger = abs(brightness_delta) >= BRIGHTNESS_JUMP
    return pixel_trigger or brightness_trigger, pixel_trigger, brightness_trigger


def save_frame(frame, frame_mean):
    ts = datetime.now(ZoneInfo("America/New_York")).strftime("%H_%M_%S")
    state = "OFF" if frame_mean < DARK_BRIGHTNESS else "ON"
    filename = f"capture_{ts}_{state}.jpg"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    cv2.imwrite(filepath, frame)
    return filepath, state


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
    print(f"  phone_watcher.py  -  saving to: {os.path.abspath(OUTPUT_FOLDER)}")
    print("=" * 60)
    print(f"  Interval          : {CAPTURE_INTERVAL}s")
    print(f"  Buffer size       : {BUFFER_SIZE} frames (warm-up)")
    print(f"  Pixel diff thresh : >{PIXEL_DIFF_THRESHOLD} levels  &  >{CHANGED_PIXEL_PCT:.1f}% pixels")
    print(f"  Brightness jump   : >{BRIGHTNESS_JUMP} levels")
    print(f"  Dark threshold    : <{DARK_BRIGHTNESS}  delete={DELETE_DARK_FRAMES}")
    print("=" * 60)

    # Always-rolling buffer — filled with EVERY captured frame, not just saved ones.
    # This means the baseline adapts to slow/gradual changes (lighting shift, etc.)
    # but still catches sudden jumps like a phone screen turning on.
    buffer   = deque(maxlen=BUFFER_SIZE)
    baseline = None

    saved_count   = 0
    deleted_count = 0
    frame_count   = 0

    listener = threading.Thread(target=console_listener, daemon=True)
    listener.start()

    try:
        while not stop_flag.is_set():
            t0 = time.time()

            ret, frame = cap.read()
            if not ret:
                print("[WARN] Failed to read frame, retrying...")
                time.sleep(CAPTURE_INTERVAL)
                continue

            frame_count += 1
            grey = to_grey(frame)

            # Always push into the rolling buffer
            buffer.append(grey)

            # Warm-up: don't save until buffer is full so baseline is meaningful
            if len(buffer) < BUFFER_SIZE:
                remaining = BUFFER_SIZE - len(buffer)
                print(f"  [WARM-UP] Filling buffer... {remaining} frames left   ", end="\r")
                elapsed = time.time() - t0
                time.sleep(max(0, CAPTURE_INTERVAL - elapsed))
                continue

            # Recompute baseline each frame from the rolling buffer
            baseline = compute_baseline(buffer)

            # Analyse current frame vs baseline
            pixel_pct, brightness_delta, base_mean, frame_mean = analyse_frame(grey, baseline)
            triggered, by_pixel, by_brightness = is_significant(pixel_pct, brightness_delta)

            # Live debug output
            if frame_count % PRINT_EVERY_N_FRAMES == 0:
                print(
                    f"  [LIVE] frame={frame_count:5d} | "
                    f"base={base_mean:5.1f} | "
                    f"now={frame_mean:5.1f} | "
                    f"delta={brightness_delta:+6.1f} | "
                    f"changed_px={pixel_pct:5.2f}%   "
                )

            # Save if triggered
            if triggered:
                filepath, state = save_frame(frame, frame_mean)
                saved_count += 1
                reason = []
                if by_pixel:      reason.append(f"pixel_pct={pixel_pct:.1f}%")
                if by_brightness: reason.append(f"brightness_delta={brightness_delta:+.1f}")

                if DELETE_DARK_FRAMES and state == "OFF":
                    os.remove(filepath)
                    deleted_count += 1
                    print(f"\n  [DARK ] Deleted dark frame. {', '.join(reason)}  "
                          f"| saved={saved_count} deleted={deleted_count}")
                else:
                    print(f"\n  [SAVED] {os.path.basename(filepath)}  {', '.join(reason)}  "
                          f"| saved={saved_count} deleted={deleted_count}")

            elapsed = time.time() - t0
            time.sleep(max(0, CAPTURE_INTERVAL - elapsed))

    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt received.")
    finally:
        cap.release()
        kept = saved_count - deleted_count
        print(f"\n[DONE] frames captured={frame_count}  saved={saved_count}  "
              f"deleted(dark)={deleted_count}  kept={kept}")
        fix_pic = os.path.join(os.path.dirname(__file__), "fix_pic.py")
        subprocess.call(["python", fix_pic, os.path.abspath(OUTPUT_FOLDER)])


if __name__ == "__main__":
    run()
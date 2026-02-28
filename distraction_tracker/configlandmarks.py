"""
Calibration Script — Configure Gaze Detection Landmarks
=========================================================
Guides the user through looking at each edge/corner of the screen,
captures head pose angles (pitch, yaw, roll) at each position via
hotkey, and outputs personalized thresholds to calibration_config.txt.

Usage:
    python configlandmarks.py

Controls:
    Space  — Capture the current head pose for the active calibration step
    Q      — Quit early (no output will be saved)
"""

# Suppress TensorFlow / MediaPipe warnings before any imports
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"

import contextlib
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import numpy as np
import mediapipe as mp


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
MODEL_PATH = str(SCRIPT_DIR / "face_landmarker.task")
OUTPUT_PATH = str(SCRIPT_DIR / "calibration_config.txt")
TZ = ZoneInfo("America/New_York")

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
FRAME_DELAY_MS = 33

# Margin (degrees) added beyond the max observed angle at each edge
# to prevent false positives during normal screen-looking
THRESHOLD_MARGIN = 5

# ──────────────────────────────────────────────────────────────────────────────
# 3D REFERENCE MODEL (same as study_tracker.py)
# ──────────────────────────────────────────────────────────────────────────────
_MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),          # Nose tip
    (0.0, -330.0, -65.0),     # Chin
    (-225.0, 170.0, -135.0),  # Left eye outer corner
    (225.0, 170.0, -135.0),   # Right eye outer corner
    (-150.0, -150.0, -125.0), # Left mouth corner
    (150.0, -150.0, -125.0),  # Right mouth corner
], dtype=np.float64)

_LANDMARK_IDS = [1, 152, 33, 263, 61, 291]


# ──────────────────────────────────────────────────────────────────────────────
# CALIBRATION STEPS
# Each step: (name, instruction text line 1, instruction text line 2)
# ──────────────────────────────────────────────────────────────────────────────
CALIBRATION_STEPS = [
    (
        "center",
        "Look at the CENTER of the screen.",
        "This is your baseline. Press SPACE when ready.",
    ),
    (
        "left",
        "Look at the LEFT EDGE of the screen.",
        "Turn your head to the left edge. Press SPACE when ready.",
    ),
    (
        "right",
        "Look at the RIGHT EDGE of the screen.",
        "Turn your head to the right edge. Press SPACE when ready.",
    ),
    (
        "top",
        "Look at the TOP EDGE of the screen.",
        "Tilt your head up to the top edge. Press SPACE when ready.",
    ),
    (
        "bottom",
        "Look at the BOTTOM EDGE of the screen.",
        "Tilt your head down to the bottom edge. Press SPACE when ready.",
    ),
    (
        "tilt_left",
        "TILT your head LEFT while looking at the screen.",
        "Tilt sideways (ear toward shoulder). Press SPACE when ready.",
    ),
    (
        "tilt_right",
        "TILT your head RIGHT while looking at the screen.",
        "Tilt sideways (ear toward shoulder). Press SPACE when ready.",
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

@contextlib.contextmanager
def suppress_cpp_output():
    """Suppress C++ stdout/stderr by temporarily redirecting file descriptors."""
    try:
        fd_out = sys.stdout.fileno()
        fd_err = sys.stderr.fileno()
    except Exception:
        yield
        return

    with open(os.devnull, 'w') as devnull:
        old_stdout = os.dup(fd_out)
        old_stderr = os.dup(fd_err)
        os.dup2(devnull.fileno(), fd_out)
        os.dup2(devnull.fileno(), fd_err)
        try:
            yield
        finally:
            os.dup2(old_stdout, fd_out)
            os.dup2(old_stderr, fd_err)
            os.close(old_stdout)
            os.close(old_stderr)


def estimate_head_pose(landmarks, w, h):
    """
    Compute yaw, pitch, roll (degrees) from face landmarks using solvePnP.
    Same algorithm as study_tracker.py.
    """
    image_points = np.array(
        [(landmarks[i].x * w, landmarks[i].y * h) for i in _LANDMARK_IDS],
        dtype=np.float64,
    )

    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array(
        [[focal_length, 0, center[0]],
         [0, focal_length, center[1]],
         [0, 0, 1]],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((4, 1))

    _, rotation_vec, _ = cv2.solvePnP(
        _MODEL_POINTS, image_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )

    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    pose_mat = np.hstack((rotation_mat, np.zeros((3, 1))))
    _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(pose_mat)

    pitch, yaw, roll = euler[0, 0], euler[1, 0], euler[2, 0]

    # Normalize pitch (same as study_tracker.py)
    if pitch > 90:
        pitch -= 180
    elif pitch < -90:
        pitch += 180

    return yaw, pitch, roll


def draw_instructions(frame, step_index, total_steps, step_name, line1, line2):
    """Draw the calibration instruction overlay on the frame."""
    h, w = frame.shape[:2]

    # Semi-transparent dark banner at the top
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 120), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Step counter
    step_text = f"Step {step_index + 1} / {total_steps}  —  {step_name.upper()}"
    cv2.putText(frame, step_text, (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 255), 2)

    # Instructions
    cv2.putText(frame, line1, (15, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(frame, line2, (15, 95),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)


def draw_angles(frame, yaw, pitch, roll):
    """Draw the current head pose angles on the frame."""
    h, w = frame.shape[:2]
    angle_text = f"Yaw: {yaw:+.1f}   Pitch: {pitch:+.1f}   Roll: {roll:+.1f}"
    cv2.putText(frame, angle_text, (15, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 1)


def draw_no_face(frame):
    """Draw a warning when no face is detected."""
    h, w = frame.shape[:2]
    cv2.putText(frame, "NO FACE DETECTED — adjust your position", (15, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)


def draw_captured(frame):
    """Flash a brief green 'CAPTURED!' indicator."""
    h, w = frame.shape[:2]
    cv2.putText(frame, "CAPTURED!", (w // 2 - 80, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)


def compute_thresholds(captures):
    """
    Given the captured angles at each calibration position, compute
    recommended thresholds that would encompass all screen-looking positions
    plus a safety margin.
    """
    center = captures["center"]
    c_yaw, c_pitch, c_roll = center

    # Collect all yaw values from left/right looking
    yaw_values = [
        abs(captures["left"][0] - c_yaw),
        abs(captures["right"][0] - c_yaw),
    ]

    # Collect pitch values from top/bottom
    # Top = more negative pitch, bottom = more positive pitch
    pitch_up_values = [abs(captures["top"][1] - c_pitch)]
    pitch_down_values = [abs(captures["bottom"][1] - c_pitch)]

    # Collect roll values from tilt
    roll_values = [
        abs(captures["tilt_left"][2] - c_roll),
        abs(captures["tilt_right"][2] - c_roll),
    ]

    yaw_threshold = max(yaw_values) + THRESHOLD_MARGIN
    pitch_up_threshold = max(pitch_up_values) + THRESHOLD_MARGIN
    pitch_down_threshold = max(pitch_down_values) + THRESHOLD_MARGIN
    roll_threshold = max(roll_values) + THRESHOLD_MARGIN

    return {
        "YAW_THRESHOLD": round(yaw_threshold, 1),
        "PITCH_UP_THRESHOLD": round(pitch_up_threshold, 1),
        "PITCH_DOWN_THRESHOLD": round(pitch_down_threshold, 1),
        "ROLL_THRESHOLD": round(roll_threshold, 1),
    }


def write_output(captures, thresholds):
    """Write calibration results to the output text file."""
    import json
    with open(OUTPUT_PATH, "w") as f:
        json.dump(thresholds, f, indent=4)

    return OUTPUT_PATH


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Landmark Calibration Tool")
    print("  Press SPACE to capture | Q to quit")
    print("=" * 60)

    # ── Initialize MediaPipe ──────────────────────────────────────────────
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] Cannot open camera", file=sys.stderr)
        return

    with suppress_cpp_output():
        landmarker = FaceLandmarker.create_from_options(options)

    frame_ts = 0
    captures = {}  # step_name -> (yaw, pitch, roll)
    current_step = 0
    capture_flash_until = 0.0  # timestamp to show "CAPTURED!" flash

    try:
        while current_step < len(CALIBRATION_STEPS):
            ret, frame = cap.read()
            if not ret:
                continue

            frame_ts += FRAME_DELAY_MS
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            detection = landmarker.detect_for_video(mp_image, frame_ts)

            h, w = frame.shape[:2]
            step_name, line1, line2 = CALIBRATION_STEPS[current_step]

            face_detected = bool(detection.face_landmarks)
            cur_yaw = cur_pitch = cur_roll = 0.0

            if face_detected:
                lm = detection.face_landmarks[0]
                cur_yaw, cur_pitch, cur_roll = estimate_head_pose(lm, w, h)

            # Draw UI
            draw_instructions(frame, current_step, len(CALIBRATION_STEPS),
                              step_name, line1, line2)

            if face_detected:
                draw_angles(frame, cur_yaw, cur_pitch, cur_roll)
            else:
                draw_no_face(frame)

            # Show "CAPTURED!" flash
            if time.monotonic() < capture_flash_until:
                draw_captured(frame)

            cv2.imshow("Landmark Calibration", frame)
            key = cv2.waitKey(FRAME_DELAY_MS) & 0xFF

            if key == ord('q'):
                print("\n  Calibration cancelled by user.")
                return

            if key == ord(' ') and face_detected:
                captures[step_name] = (cur_yaw, cur_pitch, cur_roll)
                print(f"  [{current_step + 1}/{len(CALIBRATION_STEPS)}] "
                      f"{step_name}: Yaw={cur_yaw:+.1f} Pitch={cur_pitch:+.1f} "
                      f"Roll={cur_roll:+.1f}")
                capture_flash_until = time.monotonic() + 0.5
                current_step += 1

                # Brief pause so the user sees the flash
                time.sleep(0.4)

    except KeyboardInterrupt:
        print("\n  Calibration interrupted.")
        return
    finally:
        cap.release()
        cv2.destroyAllWindows()
        landmarker.close()

    # ── All steps captured — compute and write results ────────────────────
    print("\n" + "=" * 60)
    print("  All positions captured! Computing thresholds...")

    thresholds = compute_thresholds(captures)
    output_file = write_output(captures, thresholds)

    print(f"\n  Results written to: {output_file}")
    print()
    print("  Recommended thresholds:")
    for name, value in thresholds.items():
        print(f"    {name:24s} = {value}")
    print()
    print("  study_tracker.py will use these values automatically.")
    print("=" * 60)


if __name__ == "__main__":
    main()

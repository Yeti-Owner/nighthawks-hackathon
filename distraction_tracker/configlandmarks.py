"""
AURELIUS — Gaze Calibration
============================
Fullscreen calibration UI that guides the user through looking at each
edge/corner of the screen, captures head pose angles at each position,
and outputs personalized thresholds to calibration_config.txt.

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

WINDOW_NAME = "AURELIUS  —  Gaze Calibration"

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

try:
    import json
    with open(Path(__file__).parent.resolve().parent / "cam_select" / "cameras.txt", "r") as f:
        _cameras = json.load(f)
        CAMERA_INDEX = _cameras.get("primary", {}).get("id", CAMERA_INDEX)
except Exception:
    pass

FRAME_DELAY_MS = 33
THRESHOLD_MARGIN = 5

# ──────────────────────────────────────────────────────────────────────────────
# AURELIUS COLOR PALETTE (BGR for OpenCV)
# ──────────────────────────────────────────────────────────────────────────────
CLR_CANVAS      = (245, 248, 249)    # #F9F8F5 — warm pearl
CLR_CHARCOAL    = (26, 26, 26)       # #1A1A1A — primary text / dark bg
CLR_ROSE_GOLD   = (179, 195, 215)    # #D7C3B3 — accent / target marker
CLR_PLATINUM    = (173, 169, 168)    # #A8A9AD — secondary text
CLR_MIDNIGHT    = (80, 62, 44)       # #2C3E50 — primary accent
CLR_GREEN       = (50, 125, 46)      # #2E7D32 — positive / captured
CLR_RED         = (40, 40, 198)      # #C62828 — negative / no face
CLR_SURFACE     = (250, 252, 253)    # Card surface tint
CLR_BORDER      = (225, 230, 232)    # Subtle border


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
# Each step: (name, instruction, subtitle, target_position)
#   target_position: (rel_x, rel_y) — relative position on screen
#                    None means use camera feed (center / tilt steps)
# ──────────────────────────────────────────────────────────────────────────────
CALIBRATION_STEPS = [
    (
        "center",
        "Look at the center of the screen",
        "This is your baseline. Press SPACE when ready.",
        (0.5, 0.5),
    ),
    (
        "left",
        "Look at the left edge",
        "Turn your gaze to the highlighted target. Press SPACE when ready.",
        (0.04, 0.5),
    ),
    (
        "right",
        "Look at the right edge",
        "Turn your gaze to the highlighted target. Press SPACE when ready.",
        (0.96, 0.5),
    ),
    (
        "top",
        "Look at the top edge",
        "Move your gaze up to the highlighted target. Press SPACE when ready.",
        (0.5, 0.06),
    ),
    (
        "bottom",
        "Look at the bottom edge",
        "Move your gaze down to the highlighted target. Press SPACE when ready.",
        (0.5, 0.94),
    ),
    (
        "tilt_left",
        "Tilt your head left",
        "Tilt sideways (ear toward left shoulder). Press SPACE when ready.",
        None,
    ),
    (
        "tilt_right",
        "Tilt your head right",
        "Tilt sideways (ear toward right shoulder). Press SPACE when ready.",
        None,
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

    if pitch > 90:
        pitch -= 180
    elif pitch < -90:
        pitch += 180

    return yaw, pitch, roll


# ──────────────────────────────────────────────────────────────────────────────
# FULLSCREEN DRAWING — Aurelius-styled calibration UI
# ──────────────────────────────────────────────────────────────────────────────

def build_frame(screen_w, screen_h, cam_frame, step_index, total_steps,
                step_name, instruction, subtitle, target_pos,
                face_detected, show_captured):
    """
    Build a fullscreen-sized frame with:
      - Warm Pearl background
      - Centered camera preview card with subtle border
      - Step counter + instructions at top
      - Gaze target indicator on screen edges
      - Status bar
    """
    # Create full canvas in Warm Pearl
    canvas = np.full((screen_h, screen_w, 3), CLR_CANVAS, dtype=np.uint8)

    # ── Draw gaze target indicator ────────────────────────────────────────
    if target_pos is not None:
        tx = int(target_pos[0] * screen_w)
        ty = int(target_pos[1] * screen_h)
        _draw_target_marker(canvas, tx, ty)

    # ── Camera preview card (centered, with border) ───────────────────────
    cam_h, cam_w = cam_frame.shape[:2]
    # Scale camera to a nice size relative to screen
    preview_scale = min(screen_w * 0.35 / cam_w, screen_h * 0.45 / cam_h)
    preview_w = int(cam_w * preview_scale)
    preview_h = int(cam_h * preview_scale)
    resized_cam = cv2.resize(cam_frame, (preview_w, preview_h))

    # Card dimensions with padding
    card_pad = 8
    card_w = preview_w + card_pad * 2
    card_h = preview_h + card_pad * 2

    card_x = (screen_w - card_w) // 2
    card_y = (screen_h - card_h) // 2 + 24  # slight offset down for top content

    # Card background + border
    cv2.rectangle(canvas,
                  (card_x - 1, card_y - 1),
                  (card_x + card_w + 1, card_y + card_h + 1),
                  CLR_BORDER, 1, cv2.LINE_AA)
    cv2.rectangle(canvas,
                  (card_x, card_y),
                  (card_x + card_w, card_y + card_h),
                  (255, 255, 255), -1)

    # Place camera feed inside card
    canvas[card_y + card_pad : card_y + card_pad + preview_h,
           card_x + card_pad : card_x + card_pad + preview_w] = resized_cam

    # ── Top bar: branded header + step counter ────────────────────────────
    # Brand micro-label
    cv2.putText(canvas, "AURELIUS", (40, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_ROSE_GOLD, 1, cv2.LINE_AA)

    # Step counter on the right
    step_text = f"STEP {step_index + 1} OF {total_steps}"
    step_size = cv2.getTextSize(step_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    cv2.putText(canvas, step_text, (screen_w - step_size[0] - 40, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_PLATINUM, 1, cv2.LINE_AA)

    # ── Instruction text (centered, above the card) ───────────────────────
    instr_y = card_y - 56

    # Main instruction
    instr_size = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)[0]
    instr_x = (screen_w - instr_size[0]) // 2
    cv2.putText(canvas, instruction, (instr_x, instr_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, CLR_CHARCOAL, 2, cv2.LINE_AA)

    # Subtitle
    sub_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    sub_x = (screen_w - sub_size[0]) // 2
    cv2.putText(canvas, subtitle, (sub_x, instr_y + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_PLATINUM, 1, cv2.LINE_AA)

    # ── Status bar (below the card) ───────────────────────────────────────
    status_y = card_y + card_h + 40

    if show_captured:
        # "Captured" confirmation
        cap_text = "Position captured"
        cap_size = cv2.getTextSize(cap_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        cap_x = (screen_w - cap_size[0]) // 2
        cv2.putText(canvas, cap_text, (cap_x, status_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, CLR_GREEN, 2, cv2.LINE_AA)
    elif face_detected:
        det_text = "Face detected  —  press SPACE to capture"
        det_size = cv2.getTextSize(det_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        det_x = (screen_w - det_size[0]) // 2
        cv2.putText(canvas, det_text, (det_x, status_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_MIDNIGHT, 1, cv2.LINE_AA)
    else:
        warn_text = "No face detected  —  adjust your position"
        warn_size = cv2.getTextSize(warn_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        warn_x = (screen_w - warn_size[0]) // 2
        cv2.putText(canvas, warn_text, (warn_x, status_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_RED, 1, cv2.LINE_AA)

    # ── Bottom hint ───────────────────────────────────────────────────────
    hint = "Q to quit"
    hint_size = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
    cv2.putText(canvas, hint, (screen_w - hint_size[0] - 40, screen_h - 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, CLR_PLATINUM, 1, cv2.LINE_AA)

    return canvas


def _draw_target_marker(canvas, x, y):
    """
    Draw a visual gaze target — concentric rings in Rose Gold with a
    pulsing appearance (static, but layered for depth).
    """
    # Outer ring — faint
    cv2.circle(canvas, (x, y), 32, CLR_ROSE_GOLD, 1, cv2.LINE_AA)
    # Middle ring — medium
    cv2.circle(canvas, (x, y), 18, CLR_ROSE_GOLD, 2, cv2.LINE_AA)
    # Inner dot — solid Midnight Blue
    cv2.circle(canvas, (x, y), 6, CLR_MIDNIGHT, -1, cv2.LINE_AA)

    # Crosshair lines (short, subtle)
    line_len = 10
    thin_color = CLR_PLATINUM
    cv2.line(canvas, (x - 42, y), (x - 42 + line_len, y), thin_color, 1, cv2.LINE_AA)
    cv2.line(canvas, (x + 42 - line_len, y), (x + 42, y), thin_color, 1, cv2.LINE_AA)
    cv2.line(canvas, (x, y - 42), (x, y - 42 + line_len), thin_color, 1, cv2.LINE_AA)
    cv2.line(canvas, (x, y + 42 - line_len), (x, y + 42), thin_color, 1, cv2.LINE_AA)


def build_complete_frame(screen_w, screen_h):
    """Build the 'calibration complete' confirmation screen."""
    canvas = np.full((screen_h, screen_w, 3), CLR_CANVAS, dtype=np.uint8)

    # Brand
    cv2.putText(canvas, "AURELIUS", (40, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_ROSE_GOLD, 1, cv2.LINE_AA)

    # Central message
    msg = "Calibration complete"
    msg_size = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
    msg_x = (screen_w - msg_size[0]) // 2
    msg_y = screen_h // 2 - 20
    cv2.putText(canvas, msg, (msg_x, msg_y),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, CLR_CHARCOAL, 2, cv2.LINE_AA)

    sub = "Configuration saved. This window will close automatically."
    sub_size = cv2.getTextSize(sub, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    sub_x = (screen_w - sub_size[0]) // 2
    cv2.putText(canvas, sub, (sub_x, msg_y + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_PLATINUM, 1, cv2.LINE_AA)

    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# THRESHOLD COMPUTATION & OUTPUT
# ──────────────────────────────────────────────────────────────────────────────

def compute_thresholds(captures):
    center = captures["center"]
    c_yaw, c_pitch, c_roll = center

    yaw_values = [
        abs(captures["left"][0] - c_yaw),
        abs(captures["right"][0] - c_yaw),
    ]
    pitch_up_values = [abs(captures["top"][1] - c_pitch)]
    pitch_down_values = [abs(captures["bottom"][1] - c_pitch)]
    roll_values = [
        abs(captures["tilt_left"][2] - c_roll),
        abs(captures["tilt_right"][2] - c_roll),
    ]

    return {
        "YAW_THRESHOLD": round(max(yaw_values) + THRESHOLD_MARGIN, 1),
        "PITCH_UP_THRESHOLD": round(max(pitch_up_values) + THRESHOLD_MARGIN, 1),
        "PITCH_DOWN_THRESHOLD": round(max(pitch_down_values) + THRESHOLD_MARGIN, 1),
        "ROLL_THRESHOLD": round(max(roll_values) + THRESHOLD_MARGIN, 1),
    }


def write_output(captures, thresholds):
    import json
    with open(OUTPUT_PATH, "w") as f:
        json.dump(thresholds, f, indent=4)
    return OUTPUT_PATH


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print()
    print("  AURELIUS — Gaze Calibration")
    print("  Press SPACE to capture  |  Q to quit")
    print()

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
        print("  Cannot open camera.", file=sys.stderr)
        return

    with suppress_cpp_output():
        landmarker = FaceLandmarker.create_from_options(options)

    # ── Create fullscreen window ──────────────────────────────────────────
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN)

    # Detect screen size from the window
    # We set a reasonable default and let OpenCV handle it
    screen_w = 1920
    screen_h = 1080
    try:
        # Try to get actual screen dimensions
        import ctypes
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
    except Exception:
        pass

    frame_ts = 0
    captures = {}
    current_step = 0
    capture_flash_until = 0.0

    try:
        while current_step < len(CALIBRATION_STEPS):
            ret, cam_frame = cap.read()
            if not ret:
                continue

            frame_ts += FRAME_DELAY_MS
            rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            detection = landmarker.detect_for_video(mp_image, frame_ts)

            h, w = cam_frame.shape[:2]
            step_name, instruction, subtitle, target_pos = \
                CALIBRATION_STEPS[current_step]

            face_detected = bool(detection.face_landmarks)
            cur_yaw = cur_pitch = cur_roll = 0.0

            if face_detected:
                lm = detection.face_landmarks[0]
                cur_yaw, cur_pitch, cur_roll = estimate_head_pose(lm, w, h)

            show_captured = time.monotonic() < capture_flash_until

            # Build the fullscreen frame
            display = build_frame(
                screen_w, screen_h, cam_frame,
                current_step, len(CALIBRATION_STEPS),
                step_name, instruction, subtitle, target_pos,
                face_detected, show_captured,
            )

            cv2.imshow(WINDOW_NAME, display)
            key = cv2.waitKey(FRAME_DELAY_MS) & 0xFF

            if key == ord('q') or key == 27:  # Q or Escape
                print("  Calibration cancelled.")
                return

            if key == ord(' ') and face_detected:
                captures[step_name] = (cur_yaw, cur_pitch, cur_roll)
                capture_flash_until = time.monotonic() + 0.5
                current_step += 1
                time.sleep(0.4)

    except KeyboardInterrupt:
        print("  Calibration interrupted.")
        return
    finally:
        cap.release()
        cv2.destroyAllWindows()
        landmarker.close()

    # ── All steps captured — compute and write results ────────────────────
    thresholds = compute_thresholds(captures)
    output_file = write_output(captures, thresholds)

    # Show completion screen briefly
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN)
    complete = build_complete_frame(screen_w, screen_h)
    cv2.imshow(WINDOW_NAME, complete)
    cv2.waitKey(2000)
    cv2.destroyAllWindows()

    print()
    print("  Calibration complete.")
    print(f"  Configuration saved to: {output_file}")
    print()


if __name__ == "__main__":
    main()

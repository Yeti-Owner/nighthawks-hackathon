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

import sys
import time
import threading
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

THRESHOLD_MARGIN = 5

# ──────────────────────────────────────────────────────────────────────────────
# AURELIUS COLOR PALETTE (BGR for OpenCV)
# ──────────────────────────────────────────────────────────────────────────────
CLR_CANVAS      = (245, 248, 249)
CLR_CHARCOAL    = (26, 26, 26)
CLR_ROSE_GOLD   = (179, 195, 215)
CLR_PLATINUM    = (173, 169, 168)
CLR_MIDNIGHT    = (80, 62, 44)
CLR_GREEN       = (50, 125, 46)
CLR_RED         = (40, 40, 198)
CLR_SURFACE     = (250, 252, 253)
CLR_BORDER      = (225, 230, 232)


# ──────────────────────────────────────────────────────────────────────────────
# 3D REFERENCE MODEL
# ──────────────────────────────────────────────────────────────────────────────
_MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -330.0, -65.0),
    (-225.0, 170.0, -135.0),
    (225.0, 170.0, -135.0),
    (-150.0, -150.0, -125.0),
    (150.0, -150.0, -125.0),
], dtype=np.float64)

_LANDMARK_IDS = [1, 152, 33, 263, 61, 291]
_DIST_COEFFS  = np.zeros((4, 1))

# ──────────────────────────────────────────────────────────────────────────────
# Camera matrix cache — rebuilt only when resolution changes
# ──────────────────────────────────────────────────────────────────────────────
_cam_matrix_cache: dict = {}

def _get_camera_matrix(w: int, h: int) -> np.ndarray:
    key = (w, h)
    if key not in _cam_matrix_cache:
        _cam_matrix_cache[key] = np.array(
            [[w, 0, w / 2],
             [0, w, h / 2],
             [0, 0, 1]],
            dtype=np.float64,
        )
    return _cam_matrix_cache[key]


# ──────────────────────────────────────────────────────────────────────────────
# CALIBRATION STEPS
# ──────────────────────────────────────────────────────────────────────────────
CALIBRATION_STEPS = [
    ("center",     "Look at the center of the screen",  "This is your baseline. Press SPACE when ready.",                          (0.5,  0.5)),
    ("left",       "Look at the left edge",              "Turn your gaze to the highlighted target. Press SPACE when ready.",       (0.04, 0.5)),
    ("right",      "Look at the right edge",             "Turn your gaze to the highlighted target. Press SPACE when ready.",       (0.96, 0.5)),
    ("top",        "Look at the top edge",               "Move your gaze up to the highlighted target. Press SPACE when ready.",    (0.5,  0.06)),
    ("bottom",     "Look at the bottom edge",            "Move your gaze down to the highlighted target. Press SPACE when ready.",  (0.5,  0.94)),
    ("tilt_left",  "Tilt your head left",                "Tilt sideways (ear toward left shoulder). Press SPACE when ready.",       None),
    ("tilt_right", "Tilt your head right",               "Tilt sideways (ear toward right shoulder). Press SPACE when ready.",      None),
]


# ──────────────────────────────────────────────────────────────────────────────
# HEAD POSE — optimized: camera matrix cached, no redundant allocations
# ──────────────────────────────────────────────────────────────────────────────
_img_pts_buf = np.empty((6, 2), dtype=np.float64)  # reusable buffer

def estimate_head_pose(landmarks, w: int, h: int):
    """Compute yaw, pitch, roll (degrees) from face landmarks using solvePnP."""
    for idx, lm_id in enumerate(_LANDMARK_IDS):
        lm = landmarks[lm_id]
        _img_pts_buf[idx, 0] = lm.x * w
        _img_pts_buf[idx, 1] = lm.y * h

    camera_matrix = _get_camera_matrix(w, h)

    _, rotation_vec, _ = cv2.solvePnP(
        _MODEL_POINTS, _img_pts_buf, camera_matrix, _DIST_COEFFS,
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
# CANVAS LAYER CACHE
# We pre-render the static background once per step and just composite
# the camera feed + dynamic status text on top each frame.
# ──────────────────────────────────────────────────────────────────────────────
_bg_cache: dict = {}  # key → (step_index, face_status_key) → canvas copy

def _build_static_bg(screen_w, screen_h, step_index, total_steps,
                     step_name, instruction, subtitle, target_pos) -> np.ndarray:
    """Build the static background layer (no camera, no status text)."""
    canvas = np.full((screen_h, screen_w, 3), CLR_CANVAS, dtype=np.uint8)

    if target_pos is not None:
        tx = int(target_pos[0] * screen_w)
        ty = int(target_pos[1] * screen_h)
        _draw_target_marker(canvas, tx, ty)

    # Brand
    cv2.putText(canvas, "AURELIUS", (40, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_ROSE_GOLD, 1, cv2.LINE_AA)

    # Step counter
    step_text = f"STEP {step_index + 1} OF {total_steps}"
    step_size = cv2.getTextSize(step_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    cv2.putText(canvas, step_text, (screen_w - step_size[0] - 40, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_PLATINUM, 1, cv2.LINE_AA)

    # Instruction (we don't know card_y yet without camera dims — place at fixed Y)
    instr_y = int(screen_h * 0.28)
    instr_size = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)[0]
    instr_x = (screen_w - instr_size[0]) // 2
    cv2.putText(canvas, instruction, (instr_x, instr_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, CLR_CHARCOAL, 2, cv2.LINE_AA)

    sub_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    sub_x = (screen_w - sub_size[0]) // 2
    cv2.putText(canvas, subtitle, (sub_x, instr_y + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_PLATINUM, 1, cv2.LINE_AA)

    # Bottom hint
    hint = "Q to quit"
    hint_size = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
    cv2.putText(canvas, hint, (screen_w - hint_size[0] - 40, screen_h - 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, CLR_PLATINUM, 1, cv2.LINE_AA)

    return canvas


def build_frame(screen_w, screen_h, cam_frame, step_index, total_steps,
                step_name, instruction, subtitle, target_pos,
                face_detected, show_captured,
                _bg_store={}):  # mutable default as simple step-keyed cache
    """
    Build a fullscreen frame efficiently by reusing a cached static background
    and only compositing the camera preview + dynamic status text each frame.
    """
    bg_key = (step_index, screen_w, screen_h)
    if bg_key not in _bg_store:
        _bg_store.clear()  # keep memory bounded to one entry
        _bg_store[bg_key] = _build_static_bg(
            screen_w, screen_h, step_index, total_steps,
            step_name, instruction, subtitle, target_pos
        )

    # Copy the cached background (fast — avoids np.full each frame)
    canvas = _bg_store[bg_key].copy()

    # ── Camera preview card ───────────────────────────────────────────────
    cam_h, cam_w = cam_frame.shape[:2]
    preview_scale = min(screen_w * 0.35 / cam_w, screen_h * 0.45 / cam_h)
    preview_w = int(cam_w * preview_scale)
    preview_h = int(cam_h * preview_scale)
    resized_cam = cv2.resize(cam_frame, (preview_w, preview_h),
                             interpolation=cv2.INTER_LINEAR)

    card_pad = 8
    card_w = preview_w + card_pad * 2
    card_h = preview_h + card_pad * 2
    card_x = (screen_w - card_w) // 2
    card_y = (screen_h - card_h) // 2 + 24

    cv2.rectangle(canvas,
                  (card_x - 1, card_y - 1),
                  (card_x + card_w + 1, card_y + card_h + 1),
                  CLR_BORDER, 1, cv2.LINE_AA)
    cv2.rectangle(canvas,
                  (card_x, card_y),
                  (card_x + card_w, card_y + card_h),
                  (255, 255, 255), -1)

    canvas[card_y + card_pad : card_y + card_pad + preview_h,
           card_x + card_pad : card_x + card_pad + preview_w] = resized_cam

    # ── Dynamic status text ───────────────────────────────────────────────
    status_y = card_y + card_h + 40

    if show_captured:
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

    return canvas


def _draw_target_marker(canvas, x, y):
    cv2.circle(canvas, (x, y), 32, CLR_ROSE_GOLD, 1, cv2.LINE_AA)
    cv2.circle(canvas, (x, y), 18, CLR_ROSE_GOLD, 2, cv2.LINE_AA)
    cv2.circle(canvas, (x, y),  6, CLR_MIDNIGHT, -1, cv2.LINE_AA)
    line_len = 10
    cv2.line(canvas, (x - 42, y),             (x - 42 + line_len, y),    CLR_PLATINUM, 1, cv2.LINE_AA)
    cv2.line(canvas, (x + 42 - line_len, y),  (x + 42, y),               CLR_PLATINUM, 1, cv2.LINE_AA)
    cv2.line(canvas, (x, y - 42),             (x, y - 42 + line_len),    CLR_PLATINUM, 1, cv2.LINE_AA)
    cv2.line(canvas, (x, y + 42 - line_len),  (x, y + 42),               CLR_PLATINUM, 1, cv2.LINE_AA)


def build_complete_frame(screen_w, screen_h):
    canvas = np.full((screen_h, screen_w, 3), CLR_CANVAS, dtype=np.uint8)
    cv2.putText(canvas, "AURELIUS", (40, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_ROSE_GOLD, 1, cv2.LINE_AA)
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
    return {
        "YAW_THRESHOLD":        round(max(abs(captures["left"][0]  - c_yaw),
                                          abs(captures["right"][0] - c_yaw))  + THRESHOLD_MARGIN, 1),
        "PITCH_UP_THRESHOLD":   round(abs(captures["top"][1]    - c_pitch)    + THRESHOLD_MARGIN, 1),
        "PITCH_DOWN_THRESHOLD": round(abs(captures["bottom"][1] - c_pitch)    + THRESHOLD_MARGIN, 1),
        "ROLL_THRESHOLD":       round(max(abs(captures["tilt_left"][2]  - c_roll),
                                          abs(captures["tilt_right"][2] - c_roll)) + THRESHOLD_MARGIN, 1),
    }


def write_output(captures, thresholds):
    import json
    with open(OUTPUT_PATH, "w") as f:
        json.dump(thresholds, f, indent=4)
    return OUTPUT_PATH


# ──────────────────────────────────────────────────────────────────────────────
# LOADING SCREEN
# ──────────────────────────────────────────────────────────────────────────────

def _build_loading_frame(screen_w, screen_h, status="Loading face model..."):
    canvas = np.full((screen_h, screen_w, 3), CLR_CANVAS, dtype=np.uint8)
    cv2.putText(canvas, "AURELIUS", (40, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_ROSE_GOLD, 1, cv2.LINE_AA)
    msg_size = cv2.getTextSize(status, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
    msg_x = (screen_w - msg_size[0]) // 2
    msg_y = screen_h // 2
    cv2.putText(canvas, status, (msg_x, msg_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, CLR_CHARCOAL, 2, cv2.LINE_AA)
    sub = "This may take a moment."
    sub_size = cv2.getTextSize(sub, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    sub_x = (screen_w - sub_size[0]) // 2
    cv2.putText(canvas, sub, (sub_x, msg_y + 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, CLR_PLATINUM, 1, cv2.LINE_AA)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print()
    print("  AURELIUS — Gaze Calibration")
    print("  Press SPACE to capture  |  Q to quit")
    print()

    # ── Detect screen size ────────────────────────────────────────────────
    screen_w, screen_h = 1920, 1080
    try:
        import ctypes
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
    except Exception:
        pass

    # ── Show window IMMEDIATELY with a loading screen ─────────────────────
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow(WINDOW_NAME, _build_loading_frame(screen_w, screen_h))
    cv2.waitKey(1)

    # ── Open camera + load MediaPipe in parallel (biggest startup win) ────
    # Results are stored in these mutable containers so threads can write them.
    _init = {"cap": None, "landmarker": None, "error": None}

    def _open_camera():
        cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        # Ask for MJPEG for faster USB transfer on supported cameras
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
        # Reduce internal buffer so we always get the freshest frame
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        _init["cap"] = cap

    def _load_mediapipe():
        BaseOptions         = mp.tasks.BaseOptions
        FaceLandmarker      = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        VisionRunningMode   = mp.tasks.vision.RunningMode
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
        _init["landmarker"] = FaceLandmarker.create_from_options(options)

    t_cam = threading.Thread(target=_open_camera,    daemon=True)
    t_mp  = threading.Thread(target=_load_mediapipe, daemon=True)
    t_cam.start()
    t_mp.start()

    # While threads are working, animate the loading screen so the user
    # sees something lively rather than a frozen window.
    dots = 0
    while t_cam.is_alive() or t_mp.is_alive():
        dots = (dots + 1) % 4
        status = "Loading" + "." * dots
        cv2.imshow(WINDOW_NAME, _build_loading_frame(screen_w, screen_h, status))
        cv2.waitKey(250)

    t_cam.join()
    t_mp.join()

    cap        = _init["cap"]
    landmarker = _init["landmarker"]

    if cap is None or not cap.isOpened():
        print("  Cannot open camera.", file=sys.stderr)
        cv2.destroyAllWindows()
        return

    captures           = {}
    current_step       = 0
    capture_flash_until = 0.0

    # Real-time timestamp for MediaPipe VIDEO mode
    _start_ns = time.perf_counter_ns()

    try:
        while current_step < len(CALIBRATION_STEPS):
            ret, cam_frame = cap.read()
            if not ret:
                cv2.waitKey(1)
                continue

            # Real elapsed milliseconds — keeps MediaPipe timing accurate
            frame_ts_ms = (time.perf_counter_ns() - _start_ns) // 1_000_000

            rgb      = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            detection = landmarker.detect_for_video(mp_image, int(frame_ts_ms))

            h, w = cam_frame.shape[:2]
            step_name, instruction, subtitle, target_pos = CALIBRATION_STEPS[current_step]

            face_detected = bool(detection.face_landmarks)
            cur_yaw = cur_pitch = cur_roll = 0.0

            if face_detected:
                lm = detection.face_landmarks[0]
                cur_yaw, cur_pitch, cur_roll = estimate_head_pose(lm, w, h)

            show_captured = time.monotonic() < capture_flash_until

            display = build_frame(
                screen_w, screen_h, cam_frame,
                current_step, len(CALIBRATION_STEPS),
                step_name, instruction, subtitle, target_pos,
                face_detected, show_captured,
            )

            cv2.imshow(WINDOW_NAME, display)
            # Use a short waitKey — actual frame pacing is governed by cap.read()
            key = cv2.waitKey(1) & 0xFF

            if key in (ord('q'), 27):
                print("  Calibration cancelled.")
                sys.exit(1)

            if key == ord(' ') and face_detected:
                captures[step_name] = (cur_yaw, cur_pitch, cur_roll)
                capture_flash_until = time.monotonic() + 0.5
                current_step += 1
                # Brief pause so the user sees the "captured" flash without
                # blocking the event loop (keeps window responsive)
                pause_until = time.monotonic() + 0.4
                while time.monotonic() < pause_until:
                    cv2.waitKey(16)

    except KeyboardInterrupt:
        print("  Calibration interrupted.")
        sys.exit(1)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        landmarker.close()

    # ── Compute and write results ─────────────────────────────────────────
    thresholds  = compute_thresholds(captures)
    output_file = write_output(captures, thresholds)

    # Completion screen
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow(WINDOW_NAME, build_complete_frame(screen_w, screen_h))
    cv2.waitKey(2000)
    cv2.destroyAllWindows()

    print()
    print("  Calibration complete.")
    print(f"  Configuration saved to: {output_file}")
    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
"""
Study Tracker — Gaze Detection via Google MediaPipe Face Landmarker
===================================================================
Tracks when a student looks away from the screen using the laptop camera.
Writes highly optimized CSV logs with session IDs and EST timestamps.

Usage:
    Standalone:   python study_tracker.py
    With FastAPI:  uvicorn study_tracker:app --host 0.0.0.0 --port 8000

API Endpoints (when run via uvicorn):
    POST /start   — Start a new tracking session
    POST /stop    — Stop the current tracking session
    GET  /status  — Get tracker state (running, session_id, etc.)
"""

# Suppress TensorFlow / MediaPipe warnings before any imports
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"          # Hide TF info/warning logs
os.environ["GLOG_minloglevel"] = "3"               # Hide MediaPipe C++ warnings

import argparse
import contextlib
import csv
import json
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import numpy as np
import mediapipe as mp
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# ──────────────────────────────────────────────────────────────────────────────
# HEAD POSE THRESHOLDS (degrees)
# These control how far the head can turn before triggering a "look away" event.
# Lower values = stricter (triggers sooner). Higher values = more lenient.
# NOTE: Laptop cameras sit BELOW eye level, so pitch naturally reads ~10-20°.
#       Keep PITCH_DOWN generous to avoid false positives.
# ──────────────────────────────────────────────────────────────────────────────
YAW_THRESHOLD = 37.0          # Max degrees head can turn left/right (horizontal)
PITCH_UP_THRESHOLD = 9.0    # Max degrees head can tilt up (looking up = negative pitch)
PITCH_DOWN_THRESHOLD = 7.0  # Max degrees head can tilt down (looking down = positive pitch)
ROLL_THRESHOLD = 33.7         # Max degrees head can tilt sideways

try:
    with open(Path(__file__).parent.resolve() / "calibration_config.txt", "r") as f:
        _config = json.load(f)
    YAW_THRESHOLD = _config.get("YAW_THRESHOLD", YAW_THRESHOLD)
    PITCH_UP_THRESHOLD = _config.get("PITCH_UP_THRESHOLD", PITCH_UP_THRESHOLD)
    PITCH_DOWN_THRESHOLD = _config.get("PITCH_DOWN_THRESHOLD", PITCH_DOWN_THRESHOLD)
    ROLL_THRESHOLD = _config.get("ROLL_THRESHOLD", ROLL_THRESHOLD)
except Exception:
    pass

# ──────────────────────────────────────────────────────────────────────────────
# IRIS GAZE THRESHOLDS (ratio 0.0–1.0)
# Iris position relative to eye corners. 0.5 = centered.
# Values outside this range mean the eyes are looking to the side.
# Narrower range = stricter. Wider range = more lenient.
# Set ENABLE_IRIS_CHECK to False to rely only on head pose (more stable).
# ──────────────────────────────────────────────────────────────────────────────
ENABLE_IRIS_CHECK = False    # Set True to also use iris tracking (can be noisy)
IRIS_LEFT_THRESHOLD = 0.20  # Below this → looking left
IRIS_RIGHT_THRESHOLD = 0.80 # Above this → looking right

# ──────────────────────────────────────────────────────────────────────────────
# TIMING SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
DEBOUNCE_SECONDS = 0.2       # Seconds a state must hold before logging a transition
FRAME_DELAY_MS = 33          # Min ms between frames (~30 fps). Increase to save CPU.

# ──────────────────────────────────────────────────────────────────────────────
# CAMERA SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
CAMERA_INDEX = 0             # 0 = default webcam. Change for external cameras.
CAMERA_WIDTH = 640           # Capture width in pixels
CAMERA_HEIGHT = 480          # Capture height in pixels

try:
    with open(Path(__file__).parent.resolve().parent / "cam_select" / "cameras.txt", "r") as f:
        _cameras = json.load(f)
        CAMERA_INDEX = _cameras.get("primary", {}).get("id", CAMERA_INDEX)
except Exception:
    pass

# ──────────────────────────────────────────────────────────────────────────────
# MEDIAPIPE SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
MIN_FACE_DETECTION_CONFIDENCE = 0.5   # 0.0–1.0, higher = fewer false positives
MIN_FACE_PRESENCE_CONFIDENCE = 0.5    # 0.0–1.0, higher = more certain face present
MIN_TRACKING_CONFIDENCE = 0.5         # 0.0–1.0, higher = more stable tracking

# ──────────────────────────────────────────────────────────────────────────────
# FILE PATHS
# ──────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
MODEL_PATH = str(SCRIPT_DIR / "face_landmarker.task")
LOG_PATH = str(SCRIPT_DIR.parent / "logs" / "session_log.csv")

# ──────────────────────────────────────────────────────────────────────────────
# TIMEZONE
# ──────────────────────────────────────────────────────────────────────────────
TZ = ZoneInfo("America/New_York")

# ──────────────────────────────────────────────────────────────────────────────
# DISPLAY SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
SHOW_PREVIEW = False          # Set False to run headless (no OpenCV window)

# CLI override: --headless sets SHOW_PREVIEW to False
if "--headless" in sys.argv:
    SHOW_PREVIEW = False


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                           LOG FORMAT SPEC                                  ║
# ║                                                                            ║
# ║  File: session_log.csv                                                     ║
# ║  Header (comment lines starting with #):                                   ║
# ║    # Study Tracker Log v1                                                  ║
# ║    # S=session_id, T=time(HH:MM:SS EST), E=event_type                     ║
# ║    # Events: SS=start SE=end FL=face_lost FF=face_found                   ║
# ║    #         LA=look_away LB=look_back                                     ║
# ║    S,T,E                                                                   ║
# ║  Data rows: session_id,HH:MM:SS,EVENT_CODE                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

LOG_HEADER = (
    "# Study Tracker Log v1\n"
    "# S=session_id, T=time(HH:MM:SS EST), E=event_type\n"
    "# Events: SS=start SE=end FL=face_lost FF=face_found LA=look_away LB=look_back\n"
    "S,T,E\n"
)


# =============================================================================
#  HELPERS
# =============================================================================

def _est_now() -> str:
    """Return current time as HH:MM:SS in America/New_York."""
    return datetime.now(TZ).strftime("%H:%M:%S")


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


# ── 3D reference model points for solvePnP (canonical face) ─────────────────
# Order: nose tip, chin, left eye outer, right eye outer, left mouth, right mouth
_MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),          # Nose tip
    (0.0, -330.0, -65.0),     # Chin
    (-225.0, 170.0, -135.0),  # Left eye outer corner
    (225.0, 170.0, -135.0),   # Right eye outer corner
    (-150.0, -150.0, -125.0), # Left mouth corner
    (150.0, -150.0, -125.0),  # Right mouth corner
], dtype=np.float64)

# MediaPipe landmark indices matching the 3D model points above
_LANDMARK_IDS = [1, 152, 33, 263, 61, 291]

# Iris landmarks: left iris center (468), right iris center (473)
# Eye corners: left inner (133), left outer (33), right inner (362), right outer (263)
_LEFT_IRIS = 468
_RIGHT_IRIS = 473
_LEFT_EYE_INNER = 133
_LEFT_EYE_OUTER = 33
_RIGHT_EYE_INNER = 362
_RIGHT_EYE_OUTER = 263


def estimate_head_pose(
    landmarks: list, w: int, h: int
) -> tuple[float, float, float]:
    """
    Compute yaw, pitch, roll (degrees) from face landmarks using solvePnP.

    Args:
        landmarks: MediaPipe NormalizedLandmark list (478 points).
        w: Frame width in pixels.
        h: Frame height in pixels.

    Returns:
        (yaw, pitch, roll) in degrees.
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

    # Normalize pitch: decomposeProjectionMatrix returns values near ±180°
    # for a forward-facing pose. Shift to 0°-centered so straight ahead ≈ 0°,
    # looking down = positive, looking up = negative.
    if pitch > 90:
        pitch -= 180
    elif pitch < -90:
        pitch += 180

    return yaw, pitch, roll


def check_iris_gaze(landmarks: list) -> bool:
    """
    Return True if the iris position indicates looking to the side.

    Uses horizontal ratio of iris center between inner and outer eye corners.
    """
    for iris, inner, outer in [
        (_LEFT_IRIS, _LEFT_EYE_INNER, _LEFT_EYE_OUTER),
        (_RIGHT_IRIS, _RIGHT_EYE_INNER, _RIGHT_EYE_OUTER),
    ]:
        ix = landmarks[iris].x
        inner_x = landmarks[inner].x
        outer_x = landmarks[outer].x

        eye_width = abs(inner_x - outer_x)
        if eye_width < 1e-6:
            continue

        ratio = (ix - min(inner_x, outer_x)) / eye_width

        if ratio < IRIS_LEFT_THRESHOLD or ratio > IRIS_RIGHT_THRESHOLD:
            return True

    return False


def is_looking_away(landmarks: list, w: int, h: int) -> tuple[bool, float, float, float]:
    """
    Combined check: head pose + iris gaze.
    Returns (is_away, yaw, pitch, roll) so the caller can reuse the angles.
    """
    yaw, pitch, roll = estimate_head_pose(landmarks, w, h)

    if abs(yaw) > YAW_THRESHOLD:
        return True, yaw, pitch, roll
    if pitch < -PITCH_UP_THRESHOLD or pitch > PITCH_DOWN_THRESHOLD:
        return True, yaw, pitch, roll
    if abs(roll) > ROLL_THRESHOLD:
        return True, yaw, pitch, roll

    if ENABLE_IRIS_CHECK and check_iris_gaze(landmarks):
        return True, yaw, pitch, roll

    return False, yaw, pitch, roll


# =============================================================================
#  LOG WRITER
# =============================================================================

class LogWriter:
    """Manages the session_log.csv file with append-only writes."""

    def __init__(self, path: str = LOG_PATH):
        self.path = path
        self.session_id = self._read_last_session() + 1
        self._ensure_header()

    def _read_last_session(self) -> int:
        """Scan the log for the highest session ID. Returns 0 if none found."""
        if not os.path.exists(self.path):
            return 0
        try:
            with open(self.path, "r", newline="") as f:
                reader = csv.reader(f)
                max_id = 0
                for row in reader:
                    if not row or row[0].startswith("#") or row[0] == "S":
                        continue
                    try:
                        max_id = max(max_id, int(row[0]))
                    except (ValueError, IndexError):
                        pass
                return max_id
        except Exception:
            return 0

    def _ensure_header(self) -> None:
        """Write the header block if the file doesn't exist yet."""
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", newline="") as f:
                f.write(LOG_HEADER)

    def log(self, event: str) -> None:
        """Append an event row and flush immediately."""
        with open(self.path, "a", newline="") as f:
            f.write(f"{self.session_id},{_est_now()},{event}\n")
            f.flush()


# =============================================================================
#  TRACKER ENGINE
# =============================================================================

class GazeTracker:
    """
    Core tracking engine. Runs in its own thread.
    Call start() / stop() to control it from an API.
    """

    def __init__(self):
        self.running = False
        self.session_id: int = 0
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self.running

    def start(self) -> dict:
        """Start a new tracking session. Returns status dict."""
        if self.running:
            return {"status": "already_running", "session_id": self.session_id}

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return {"status": "started", "session_id": self.session_id}

    def stop(self) -> dict:
        """Stop the current tracking session. Returns status dict."""
        if not self.running:
            return {"status": "not_running"}

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        return {"status": "stopped", "session_id": self.session_id}

    def _run(self) -> None:
        """Main tracking loop — runs on a background thread."""
        self.running = True
        logger = LogWriter()
        self.session_id = logger.session_id
        logger.log("SS")

        # State machine: "looking" | "away" | "no_face"
        state = "looking"
        pending_state: str | None = None
        pending_since: float = 0.0

        BaseOptions = mp.tasks.BaseOptions
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=VisionRunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=MIN_FACE_DETECTION_CONFIDENCE,
            min_face_presence_confidence=MIN_FACE_PRESENCE_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )

        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        if not cap.isOpened():
            print("[ERROR] Cannot open camera", file=sys.stderr)
            logger.log("SE")
            self.running = False
            return

        # Create landmarker ONCE, reuse across all frames
        with suppress_cpp_output():
            landmarker = FaceLandmarker.create_from_options(options)
        frame_ts = 0
        frame_interval = FRAME_DELAY_MS / 1000.0
        last_frame_time = time.monotonic()

        try:
            while not self._stop_event.is_set():
                # ── Frame-rate limiter (non-blocking) ────────────────────
                now_mono = time.monotonic()
                elapsed = now_mono - last_frame_time
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                last_frame_time = time.monotonic()

                ret, frame = cap.read()
                if not ret:
                    continue

                frame_ts += FRAME_DELAY_MS
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                detection = landmarker.detect_for_video(mp_image, frame_ts)

                h, w = frame.shape[:2]
                now = time.monotonic()

                face_detected = bool(detection.face_landmarks)
                cur_yaw = cur_pitch = cur_roll = 0.0

                if face_detected:
                    lm = detection.face_landmarks[0]
                    away, cur_yaw, cur_pitch, cur_roll = is_looking_away(lm, w, h)
                    desired = "away" if away else "looking"
                else:
                    desired = "no_face"

                # ── Debounce logic ───────────────────────────────────────
                if desired != state:
                    if pending_state != desired:
                        pending_state = desired
                        pending_since = now
                    elif now - pending_since >= DEBOUNCE_SECONDS:
                        # Transition confirmed
                        if state == "looking" and desired == "away":
                            logger.log("LA")
                        elif state == "looking" and desired == "no_face":
                            logger.log("FL")
                        elif state == "away" and desired == "looking":
                            logger.log("LB")
                        elif state == "away" and desired == "no_face":
                            logger.log("FL")
                        elif state == "no_face" and desired == "looking":
                            logger.log("FF")
                        elif state == "no_face" and desired == "away":
                            logger.log("FF")
                            logger.log("LA")

                        state = desired
                        pending_state = None
                else:
                    pending_state = None

                # ── Optional preview window ──────────────────────────────
                if SHOW_PREVIEW:
                    status_text = f"State: {state.upper()}"
                    color = (0, 255, 0) if state == "looking" else (0, 0, 255)
                    cv2.putText(
                        frame, status_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2,
                    )

                    if face_detected:
                        # Reuse angles already computed by is_looking_away()
                        pose_text = f"Y:{cur_yaw:.0f} P:{cur_pitch:.0f} R:{cur_roll:.0f}"
                        cv2.putText(
                            frame, pose_text, (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
                        )
                        thresh_text = (
                            f"Thresholds  Y:<{YAW_THRESHOLD}  "
                            f"P:-{PITCH_UP_THRESHOLD}<>{PITCH_DOWN_THRESHOLD}  R:<{ROLL_THRESHOLD}"
                        )
                        cv2.putText(
                            frame, thresh_text, (10, 85),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1,
                        )

                    cv2.imshow("Study Tracker", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

        except KeyboardInterrupt:
            pass
        finally:
            logger.log("SE")
            cap.release()
            if SHOW_PREVIEW:
                cv2.destroyAllWindows()
            landmarker.close()
            self.running = False


# =============================================================================
#  FASTAPI APP
# =============================================================================

app = FastAPI(title="Study Tracker API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

tracker = GazeTracker()


@app.post("/start")
def api_start():
    """Start a new tracking session."""
    return tracker.start()


@app.post("/stop")
def api_stop():
    """Stop the current tracking session."""
    return tracker.stop()


@app.get("/status")
def api_status():
    """Get the current tracker status."""
    return {
        "running": tracker.is_running,
        "session_id": tracker.session_id,
    }


# =============================================================================
#  STANDALONE ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Study Tracker — Gaze Detection")
    print("  Press 'q' in the preview window or Ctrl+C to stop")
    print("=" * 60)
    result = tracker.start()
    print(f"  Session {result['session_id']} started")
    try:
        # Keep main thread alive while tracker runs
        while tracker.is_running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        tracker.stop()
    print("  Session ended. Logs written to:", LOG_PATH)

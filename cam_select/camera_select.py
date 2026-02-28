import cv2
import json
import threading
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import messagebox
from PIL import Image, ImageTk

# ─── Aurelius Design Tokens ──────────────────────────────────────────────────
CANVAS         = "#F9F8F5"
SURFACE        = "#FDFCFA"
TEXT_PRIMARY   = "#1A1A1A"
TEXT_SECONDARY = "#666666"
ACCENT_TRUST   = "#2C3E50"
ACCENT_METAL   = "#D7C3B3"
PLATINUM       = "#A8A9AD"
POSITIVE       = "#2E7D32"
NEGATIVE       = "#C62828"
BORDER         = "#E8E6E1"

FONT_FAMILY    = "Inter"
FONT_FALLBACK  = "Segoe UI"

# ─── Config ───────────────────────────────────────────────────────────────────
CONFIG_FILE     = "cameras.txt"
SCAN_LIMIT      = 4
MAX_CAMERAS     = 4
GRID_COLS       = 2
THUMB_W         = 256
THUMB_H         = 152
FILTER_VIRTUAL  = True
TICK_MS         = 33       # ~30 fps is plenty for thumbnails (was 16/60fps)
GRABBER_SLEEP   = 0.01     # Avoid 100% CPU spin in grabber thread

VIRTUAL_KEYWORDS = [
    "obs", "nvidia broadcast", "nvidia rtx", "virtual", "droidcam",
    "epoccam", "iriun", "snap camera", "xsplit", "manycam", "camo",
    "ndi", "streamlabs", "lgs", "logitech capture", "ivcam",
]

# ─── Cache pygrabber devices once at import time (if available) ───────────────
_DEVICE_NAMES: list[str] | None = None

def _load_device_names():
    """Fetch DirectShow device names once and cache them."""
    global _DEVICE_NAMES
    if _DEVICE_NAMES is not None:
        return _DEVICE_NAMES
    try:
        from pygrabber.dshow_graph import FilterGraph
        graph = FilterGraph()
        _DEVICE_NAMES = graph.get_input_devices()
    except Exception:
        _DEVICE_NAMES = []
    return _DEVICE_NAMES


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _font(size, weight="normal"):
    return (FONT_FAMILY, size, weight)


# ─── Camera detection ─────────────────────────────────────────────────────────

def get_camera_name(index: int) -> str:
    devices = _load_device_names()
    if index < len(devices):
        return devices[index]
    return f"Camera {index}"


def is_virtual(name: str) -> bool:
    low = name.lower()
    return any(kw in low for kw in VIRTUAL_KEYWORDS)


def _probe_camera(i: int) -> dict | None:
    """Try to open a single camera index. Returns camera dict or None."""
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(i)
    if not cap.isOpened():
        cap.release()
        return None

    ret, _ = cap.read()
    if not ret:
        cap.release()
        return None

    name = get_camera_name(i)
    if FILTER_VIRTUAL and is_virtual(name):
        cap.release()
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return {"id": i, "name": name, "cap": cap}


def detect_cameras_parallel() -> list[dict]:
    """Probe all camera indices simultaneously using a thread pool."""
    results: dict[int, dict] = {}

    # Pre-fetch device names on this thread before spawning workers
    _load_device_names()

    with ThreadPoolExecutor(max_workers=SCAN_LIMIT) as executor:
        futures = {executor.submit(_probe_camera, i): i for i in range(SCAN_LIMIT)}
        for future in as_completed(futures):
            idx = futures[future]
            cam = future.result()
            if cam is not None:
                results[idx] = cam

    # Return in index order, capped at MAX_CAMERAS
    return [results[k] for k in sorted(results)[:MAX_CAMERAS]]


# ─── Frame grabber ─────────────────────────────────────────────────────────────

class FrameGrabber:
    def __init__(self, cap):
        self.cap   = cap
        self.frame = None
        self.lock  = threading.Lock()
        self._stop = threading.Event()
        self._t    = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self):
        while not self._stop.is_set():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (THUMB_W, THUMB_H))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                with self.lock:
                    self.frame = frame
            else:
                # No frame available — sleep briefly to avoid spinning
                time.sleep(GRABBER_SLEEP)

    def get_frame(self):
        with self.lock:
            return self.frame

    def stop(self):
        self._stop.set()
        self._t.join(timeout=1)


# ─── Camera card widget ────────────────────────────────────────────────────────

class CameraCard(tk.Frame):
    """A single camera preview card with role selection buttons."""

    def __init__(self, parent, cam, grabber, on_select):
        super().__init__(parent, bd=0, bg=SURFACE,
                         highlightbackground=BORDER, highlightthickness=1)
        self.cam     = cam
        self.grabber = grabber
        self._role   = None
        self._imref  = None

        inner = tk.Frame(self, bg=SURFACE)
        inner.pack(padx=12, pady=12)
        self._inner = inner

        self.canvas = tk.Canvas(inner, width=THUMB_W, height=THUMB_H,
                                bg="#EDECEA", highlightthickness=0)
        self.canvas.pack()

        info = tk.Frame(inner, bg=SURFACE)
        info.pack(fill="x", pady=(8, 0))

        self._name_label = tk.Label(
            info, text=cam["name"],
            bg=SURFACE, fg=TEXT_PRIMARY,
            font=_font(10, "bold"), anchor="w",
        )
        self._name_label.pack(side="left")

        self._badge = tk.Label(
            info, text="", bg=SURFACE, fg=ACCENT_METAL,
            font=_font(9, "bold"), anchor="e",
        )
        self._badge.pack(side="right")

        btn_frame = tk.Frame(inner, bg=SURFACE)
        btn_frame.pack(fill="x", pady=(8, 0))
        self._btn_frame = btn_frame

        self._btn_pri = tk.Button(
            btn_frame, text="PRIMARY", width=10,
            command=lambda: on_select(self, "primary"),
            bg=ACCENT_TRUST, fg="#F9F8F5", relief="flat", cursor="hand2",
            font=_font(8, "bold"), pady=4,
            activebackground="#1F2E3D", activeforeground="#F9F8F5",
        )
        self._btn_pri.pack(side="left", padx=(0, 8))

        self._btn_sec = tk.Button(
            btn_frame, text="SECONDARY", width=12,
            command=lambda: on_select(self, "secondary"),
            bg=SURFACE, fg=ACCENT_TRUST, relief="solid", cursor="hand2",
            font=_font(8, "bold"), bd=1, pady=4,
            activebackground=CANVAS, activeforeground=ACCENT_TRUST,
        )
        self._btn_sec.pack(side="left")

    def refresh(self):
        frame = self.grabber.get_frame()
        if frame is not None:
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            self.canvas.create_image(0, 0, anchor="nw", image=img)
            self._imref = img

    def set_role(self, role):
        self._role = role
        if role == "primary":
            self.config(highlightbackground=ACCENT_TRUST, highlightthickness=2)
            self._badge.config(text="✦ PRIMARY", fg=ACCENT_TRUST)
        elif role == "secondary":
            self.config(highlightbackground=ACCENT_METAL, highlightthickness=2)
            self._badge.config(text="✦ SECONDARY", fg=ACCENT_METAL)
        else:
            self.config(highlightbackground=BORDER, highlightthickness=1)
            self._badge.config(text="", fg=ACCENT_METAL)


# ─── Loading overlay ──────────────────────────────────────────────────────────

class LoadingOverlay(tk.Frame):
    """Animated "Scanning…" overlay shown while cameras are being detected."""

    _DOTS = ["", ".", "..", "..."]

    def __init__(self, parent):
        super().__init__(parent, bg=CANVAS)
        self._step = 0
        self._after_id = None

        self._label = tk.Label(
            self, text="Scanning cameras",
            font=_font(13), bg=CANVAS, fg=TEXT_SECONDARY,
        )
        self._label.pack(expand=True)
        self._animate()

    def _animate(self):
        dots = self._DOTS[self._step % len(self._DOTS)]
        self._label.config(text=f"Scanning cameras{dots}")
        self._step += 1
        self._after_id = self.after(400, self._animate)

    def destroy(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        super().destroy()


# ─── Main application ──────────────────────────────────────────────────────────

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("AURELIUS  —  Camera Setup")
        self.root.configure(bg=CANVAS)
        self.root.resizable(False, False)

        self.cameras   = []
        self.grabbers  = []
        self.cards     = []
        self.primary   = None
        self.secondary = None

        self._build_header()
        self._build_body()
        self._build_footer()

        # Show the window immediately, then scan in a background thread
        self._overlay = LoadingOverlay(self.card_frame)
        self._overlay.pack(expand=True, fill="both")
        self.status.config(text="Scanning cameras…", fg=TEXT_SECONDARY)

        threading.Thread(target=self._scan_bg, daemon=True).start()
        self._tick()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=CANVAS)
        hdr.pack(fill="x", padx=24, pady=(16, 0))

        tk.Label(
            hdr, text="AURELIUS",
            bg=CANVAS, fg=ACCENT_METAL,
            font=_font(10, "bold"),
        ).pack(anchor="w")

        title_row = tk.Frame(self.root, bg=CANVAS)
        title_row.pack(fill="x", padx=24, pady=(2, 0))

        tk.Label(
            title_row, text="Camera Setup",
            font=_font(18, "bold"), bg=CANVAS, fg=TEXT_PRIMARY,
        ).pack(side="left")

        tk.Button(
            title_row, text="↻  RESCAN",
            command=self._rescan,
            bg=CANVAS, fg=ACCENT_TRUST, relief="solid", cursor="hand2",
            font=_font(8, "bold"), bd=1, padx=12, pady=3,
            activebackground=SURFACE, activeforeground=ACCENT_TRUST,
        ).pack(side="right")

        tk.Label(
            self.root,
            text="Select a primary camera for gaze tracking and an optional secondary camera.",
            font=_font(10), bg=CANVAS, fg=TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(2, 0))

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        self.card_frame = tk.Frame(self.root, bg=CANVAS)
        self.card_frame.pack(padx=24, pady=12, fill="both", expand=True)
        for c in range(GRID_COLS):
            self.card_frame.columnconfigure(c, weight=1)

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self):
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=24)

        ftr = tk.Frame(self.root, bg=CANVAS)
        ftr.pack(fill="x", padx=24, pady=12)

        tk.Button(
            ftr, text="SAVE CONFIGURATION",
            command=self._save,
            bg=ACCENT_TRUST, fg="#F9F8F5", relief="flat", cursor="hand2",
            font=_font(10, "bold"), padx=24, pady=8,
            activebackground="#1F2E3D", activeforeground="#F9F8F5",
        ).pack(side="right")

        self.status = tk.Label(
            ftr, text="", bg=CANVAS, fg=TEXT_SECONDARY, font=_font(10),
        )
        self.status.pack(side="left")

    # ── Camera scanning (background) ──────────────────────────────────────────

    def _scan_bg(self):
        """Run in a worker thread; posts results back to the main thread."""
        cameras = detect_cameras_parallel()
        # Schedule UI update on the main thread
        self.root.after(0, lambda: self._scan_done(cameras))

    def _scan_done(self, cameras):
        """Called on the main thread once camera detection finishes."""
        # Remove loading overlay
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None

        self.cameras = cameras

        for idx, cam in enumerate(self.cameras):
            grabber = FrameGrabber(cam["cap"])
            self.grabbers.append(grabber)
            card = CameraCard(self.card_frame, cam, grabber, self._on_select)
            row, col = divmod(idx, GRID_COLS)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.cards.append(card)

        if not self.cameras:
            tk.Label(
                self.card_frame, text="No cameras detected.",
                bg=CANVAS, fg=NEGATIVE, font=_font(13),
            ).grid(row=0, column=0, columnspan=GRID_COLS, pady=48)
            self.status.config(text="No cameras found.", fg=NEGATIVE)
        else:
            n = len(self.cameras)
            self.status.config(
                text=f"{n} camera{'s' if n != 1 else ''} detected.",
                fg=TEXT_SECONDARY,
            )

    def _rescan(self):
        self._teardown()
        for w in self.card_frame.winfo_children():
            w.destroy()
        self.cards.clear()
        self.primary = self.secondary = None

        self._overlay = LoadingOverlay(self.card_frame)
        self._overlay.pack(expand=True, fill="both")
        self.status.config(text="Scanning cameras…", fg=TEXT_SECONDARY)
        threading.Thread(target=self._scan_bg, daemon=True).start()

    def _teardown(self):
        for g in self.grabbers:
            g.stop()
        for cam in self.cameras:
            cam["cap"].release()
        self.grabbers.clear()
        self.cameras.clear()

    # ── Selection ─────────────────────────────────────────────────────────────

    def _on_select(self, card, role):
        current = self.primary if role == "primary" else self.secondary
        if current and current is not card:
            current.set_role(None)

        if role == "primary" and self.secondary is card:
            self.secondary = None
        if role == "secondary" and self.primary is card:
            self.primary = None

        if role == "primary":
            self.primary = card
        else:
            self.secondary = card
        card.set_role(role)

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self):
        config = {}
        if self.primary:
            c = self.primary.cam
            config["primary"] = {"id": c["id"], "name": c["name"]}
        if self.secondary:
            c = self.secondary.cam
            config["secondary"] = {"id": c["id"], "name": c["name"]}

        if not config:
            messagebox.showwarning(
                "Nothing Selected",
                "Please select at least a primary camera.",
            )
            return

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        self.status.config(text=f"✔  Saved to {CONFIG_FILE}", fg=POSITIVE)
        self.root.after(500, lambda: (self.cleanup(), self.root.destroy()))

    # ── Render loop ───────────────────────────────────────────────────────────

    def _tick(self):
        for card in self.cards:
            card.refresh()
        self.root.after(TICK_MS, self._tick)

    def cleanup(self):
        self._teardown()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()
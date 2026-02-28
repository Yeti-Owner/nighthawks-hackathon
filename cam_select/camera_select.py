import cv2
import json
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

# ─── Aurelius Design Tokens ──────────────────────────────────────────────────
CANVAS       = "#F9F8F5"       # Warm Pearl page background
SURFACE      = "#FFFFFF"       # Card surface (solid fallback — tk can't do rgba)
TEXT_PRIMARY  = "#1A1A1A"       # Off-Black Charcoal
TEXT_SECONDARY = "#666666"     # Slate
ACCENT_TRUST  = "#2C3E50"      # Midnight Blue — primary accent
ACCENT_METAL  = "#D7C3B3"      # Rose Gold — secondary / decorative accent
PLATINUM      = "#A8A9AD"      # Brushed Platinum
POSITIVE      = "#2E7D32"      # Muted green — success
NEGATIVE      = "#C62828"      # Muted red — errors
POSITIVE_BG   = "#E8F5E9"

FONT_FAMILY   = "Inter"        # Aurelius body font (falls back gracefully)
FONT_FALLBACK = "Segoe UI"

# ─── Config ───────────────────────────────────────────────────────────────────
CONFIG_FILE     = "cameras.txt"
SCAN_LIMIT      = 8
MAX_CAMERAS     = 6
THUMB_W         = 320
THUMB_H         = 200
FILTER_VIRTUAL  = True

VIRTUAL_KEYWORDS = [
    "obs", "nvidia broadcast", "nvidia rtx", "virtual", "droidcam",
    "epoccam", "iriun", "snap camera", "xsplit", "manycam", "camo",
    "ndi", "streamlabs", "lgs", "logitech capture", "ivcam",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _font(size, weight="normal"):
    """Return a font tuple preferring Inter, falling back to Segoe UI."""
    return (FONT_FAMILY, size, weight)


# ─── Camera detection ─────────────────────────────────────────────────────────

def get_camera_name(index):
    """Use pygrabber/Windows to get real device name; fallback to generic."""
    try:
        from pygrabber.dshow_graph import FilterGraph
        graph = FilterGraph()
        devices = graph.get_input_devices()
        if index < len(devices):
            return devices[index]
    except Exception:
        pass
    return f"Camera {index}"


def is_virtual(name: str) -> bool:
    low = name.lower()
    return any(kw in low for kw in VIRTUAL_KEYWORDS)


def detect_cameras():
    cameras = []
    for i in range(SCAN_LIMIT):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(i)
        if not cap.isOpened():
            cap.release()
            continue

        ret, _ = cap.read()
        if not ret:
            cap.release()
            continue

        name = get_camera_name(i)

        if FILTER_VIRTUAL and is_virtual(name):
            cap.release()
            continue

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        cameras.append({"id": i, "name": name, "cap": cap})
        if len(cameras) >= MAX_CAMERAS:
            break

    return cameras


# ─── Per-camera frame grabber (background thread) ──────────────────────────────

class FrameGrabber:
    """Continuously grabs frames in a daemon thread; UI reads latest."""

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

    def get_frame(self):
        with self.lock:
            return self.frame

    def stop(self):
        self._stop.set()
        self._t.join(timeout=1)


# ─── Camera card widget ────────────────────────────────────────────────────────

class CameraCard(tk.Frame):
    ROLE_COLORS = {
        None:        SURFACE,
        "primary":   ACCENT_TRUST,
        "secondary": ACCENT_METAL,
    }
    ROLE_TEXT_COLORS = {
        None:        TEXT_PRIMARY,
        "primary":   "#F9F8F5",
        "secondary": TEXT_PRIMARY,
    }

    def __init__(self, parent, cam, grabber, on_select):
        super().__init__(parent, bd=0, bg=SURFACE,
                         highlightbackground=PLATINUM, highlightthickness=1)
        self.cam     = cam
        self.grabber = grabber
        self._role   = None
        self._imref  = None

        # Preview canvas
        self.canvas = tk.Canvas(self, width=THUMB_W, height=THUMB_H,
                                bg=CANVAS, highlightthickness=0)
        self.canvas.pack(padx=8, pady=(8, 0))

        # Camera name label (micro-label style)
        self._label = tk.Label(
            self, text=cam['name'].upper(),
            bg=SURFACE, fg=TEXT_SECONDARY,
            font=_font(9, "bold"),
        )
        self._label.pack(pady=(8, 4))

        # Button row
        btn_frame = tk.Frame(self, bg=SURFACE)
        btn_frame.pack(pady=(0, 12))
        self._btn_frame = btn_frame

        # Primary button — solid Midnight Blue
        self._btn_primary = tk.Button(
            btn_frame, text="PRIMARY", width=10,
            command=lambda: on_select(self, "primary"),
            bg=ACCENT_TRUST, fg="#F9F8F5", relief="flat", cursor="hand2",
            font=_font(9, "bold"), activebackground="#1F2E3D",
            activeforeground="#F9F8F5",
        )
        self._btn_primary.pack(side="left", padx=4)

        # Secondary button — ghost / outlined
        self._btn_secondary = tk.Button(
            btn_frame, text="SECONDARY", width=11,
            command=lambda: on_select(self, "secondary"),
            bg=SURFACE, fg=ACCENT_TRUST, relief="solid", cursor="hand2",
            font=_font(9, "bold"), bd=1,
            activebackground=CANVAS, activeforeground=ACCENT_TRUST,
        )
        self._btn_secondary.pack(side="left", padx=4)

    def refresh(self):
        frame = self.grabber.get_frame()
        if frame is not None:
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            self.canvas.create_image(0, 0, anchor="nw", image=img)
            self._imref = img

    def set_role(self, role):
        self._role = role
        border_color = self.ROLE_COLORS[role] if role else PLATINUM
        text_color = self.ROLE_TEXT_COLORS[role]
        bg = SURFACE

        self.config(highlightbackground=border_color,
                    highlightthickness=2 if role else 1, bg=bg)
        self._btn_frame.config(bg=bg)
        self._label.config(bg=bg)

        suffix = {"primary": "  ✦ PRIMARY", "secondary": "  ✦ SECONDARY", None: ""}
        role_color = self.ROLE_COLORS[role] if role else TEXT_SECONDARY
        self._label.config(
            text=f"{self.cam['name'].upper()}{suffix[role]}",
            fg=role_color,
        )


# ─── Main application ──────────────────────────────────────────────────────────

class App:
    def __init__(self, root):
        self.root     = root
        self.root.title("AURELIUS  —  Camera Setup")
        self.root.configure(bg=CANVAS)

        self.cameras  = []
        self.grabbers = []
        self.cards    = []
        self.primary  = None
        self.secondary = None

        self._build_header()
        self.card_frame = tk.Frame(self.root, bg=CANVAS)
        self.card_frame.pack(padx=24, pady=8, fill="both", expand=True)
        self._build_footer()

        self._scan()
        self._tick()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=CANVAS)
        hdr.pack(fill="x", padx=24, pady=(24, 0))

        # Brand micro-label
        tk.Label(
            hdr, text="AURELIUS", bg=CANVAS, fg=ACCENT_METAL,
            font=_font(10, "bold"),
        ).pack(side="left")

        # Title
        title_frame = tk.Frame(self.root, bg=CANVAS)
        title_frame.pack(fill="x", padx=24, pady=(4, 0))
        tk.Label(
            title_frame, text="Camera Setup",
            font=_font(20, "bold"), bg=CANVAS, fg=TEXT_PRIMARY,
        ).pack(side="left")

        # Subtitle
        sub_frame = tk.Frame(self.root, bg=CANVAS)
        sub_frame.pack(fill="x", padx=24, pady=(2, 0))
        tk.Label(
            sub_frame,
            text="Select a primary camera for gaze tracking and an optional secondary camera.",
            font=_font(11), bg=CANVAS, fg=TEXT_SECONDARY,
        ).pack(side="left")

        # Refresh button — ghost style
        tk.Button(
            hdr, text="↻  RESCAN", command=self._rescan,
            bg=CANVAS, fg=ACCENT_TRUST, relief="solid", cursor="hand2",
            font=_font(9, "bold"), bd=1, padx=12, pady=4,
            activebackground=SURFACE, activeforeground=ACCENT_TRUST,
        ).pack(side="right")

    def _build_footer(self):
        # Separator line
        sep = tk.Frame(self.root, bg=PLATINUM, height=1)
        sep.pack(fill="x", padx=24, pady=(16, 0))

        ftr = tk.Frame(self.root, bg=CANVAS)
        ftr.pack(fill="x", padx=24, pady=16)

        # Save button — primary "Expensive" style
        tk.Button(
            ftr, text="SAVE CONFIGURATION",
            command=self._save,
            bg=ACCENT_TRUST, fg="#F9F8F5", relief="flat", cursor="hand2",
            font=_font(11, "bold"), padx=24, pady=8,
            activebackground="#1F2E3D", activeforeground="#F9F8F5",
        ).pack(side="right")

        self.status = tk.Label(
            ftr, text="", bg=CANVAS, fg=TEXT_SECONDARY,
            font=_font(10),
        )
        self.status.pack(side="left")

    # ── Camera scanning ───────────────────────────────────────────────────────

    def _scan(self):
        self.status.config(text="Scanning cameras…", fg=TEXT_SECONDARY)
        self.root.update()

        self.cameras = detect_cameras()

        cols = min(max(len(self.cameras), 1), 3)
        for idx, cam in enumerate(self.cameras):
            grabber = FrameGrabber(cam["cap"])
            self.grabbers.append(grabber)
            card = CameraCard(self.card_frame, cam, grabber, self._on_select)
            card.grid(row=idx // cols, column=idx % cols, padx=12, pady=12)
            self.cards.append(card)

        if not self.cameras:
            tk.Label(
                self.card_frame, text="No cameras detected.",
                bg=CANVAS, fg=NEGATIVE, font=_font(12),
            ).pack(pady=48)
            self.status.config(text="No cameras found.", fg=NEGATIVE)
        else:
            self.status.config(
                text=f"{len(self.cameras)} camera(s) detected.",
                fg=TEXT_SECONDARY,
            )

    def _rescan(self):
        self._teardown()
        for w in self.card_frame.winfo_children():
            w.destroy()
        self.cards.clear()
        self.primary = self.secondary = None
        self._scan()

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

    # ── Render loop ───────────────────────────────────────────────────────────

    def _tick(self):
        for card in self.cards:
            card.refresh()
        self.root.after(16, self._tick)

    def cleanup(self):
        self._teardown()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()
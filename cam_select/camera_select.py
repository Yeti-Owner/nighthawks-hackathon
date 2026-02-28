import cv2
import json
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

# ─── Config ───────────────────────────────────────────────────────────────────
CONFIG_FILE     = "cameras.txt"
SCAN_LIMIT      = 8          # How many indices to probe
MAX_CAMERAS     = 6          # Cap on cameras shown
THUMB_W         = 320
THUMB_H         = 200
FILTER_VIRTUAL  = True       # Skip virtual cameras (OBS, NVIDIA Broadcast, etc.)

VIRTUAL_KEYWORDS = [
    "obs", "nvidia broadcast", "nvidia rtx", "virtual", "droidcam",
    "epoccam", "iriun", "snap camera", "xsplit", "manycam", "camo",
    "ndi", "streamlabs", "lgs", "logitech capture", "ivcam",
]

# ─── Camera detection (run once at startup) ────────────────────────────────────

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
        # Try DSHOW first, fall back to ANY
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
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency

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
    COLORS = {None: "#1e1e1e", "primary": "#00c853", "secondary": "#2979ff"}

    def __init__(self, parent, cam, grabber, on_select):
        super().__init__(parent, bd=2, relief="groove", bg="#1e1e1e")
        self.cam     = cam
        self.grabber = grabber
        self._role   = None
        self._imref  = None

        self.canvas = tk.Canvas(self, width=THUMB_W, height=THUMB_H,
                                bg="#111", highlightthickness=0)
        self.canvas.pack()

        self._label = tk.Label(self, text=f"[{cam['id']}] {cam['name']}",
                               bg="#1e1e1e", fg="white",
                               font=("Helvetica", 9, "bold"))
        self._label.pack(pady=(4, 2))

        btn_frame = tk.Frame(self, bg="#1e1e1e")
        btn_frame.pack(pady=(0, 8))
        self._btn_frame = btn_frame

        tk.Button(btn_frame, text="Set Primary", width=11,
                  command=lambda: on_select(self, "primary"),
                  bg="#333", fg="white", relief="flat", cursor="hand2"
                  ).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Set Secondary", width=12,
                  command=lambda: on_select(self, "secondary"),
                  bg="#333", fg="white", relief="flat", cursor="hand2"
                  ).pack(side="left", padx=4)

    def refresh(self):
        frame = self.grabber.get_frame()
        if frame is not None:
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            self.canvas.create_image(0, 0, anchor="nw", image=img)
            self._imref = img  # prevent GC

    def set_role(self, role):
        self._role = role
        color = self.COLORS[role]
        self.config(bg=color)
        self._btn_frame.config(bg=color)
        self._label.config(bg=color)
        suffix = {"primary": "  ✔ PRIMARY", "secondary": "  ✔ SECONDARY", None: ""}
        self._label.config(text=f"[{self.cam['id']}] {self.cam['name']}{suffix[role]}")


# ─── Main application ──────────────────────────────────────────────────────────

class App:
    def __init__(self, root):
        self.root     = root
        self.root.title("Camera Selector")
        self.root.configure(bg="#121212")

        self.cameras  = []
        self.grabbers = []
        self.cards    = []
        self.primary  = None
        self.secondary = None

        self._build_header()
        self.card_frame = tk.Frame(self.root, bg="#121212")
        self.card_frame.pack(padx=16, pady=8, fill="both", expand=True)
        self._build_footer()

        self._scan()
        self._tick()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self.root, bg="#121212")
        hdr.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(hdr, text="Camera Selector", font=("Helvetica", 16, "bold"),
                 bg="#121212", fg="white").pack(side="left")
        tk.Button(hdr, text="⟳  Refresh", command=self._rescan,
                  bg="#333", fg="white", relief="flat", cursor="hand2",
                  font=("Helvetica", 10), padx=10, pady=4).pack(side="right")

    def _build_footer(self):
        ftr = tk.Frame(self.root, bg="#121212")
        ftr.pack(fill="x", padx=16, pady=12)
        tk.Button(ftr, text="Save Configuration", command=self._save,
                  bg="#4CAF50", fg="white", relief="flat", cursor="hand2",
                  font=("Helvetica", 11, "bold"), padx=20, pady=6).pack(side="right")
        self.status = tk.Label(ftr, text="", bg="#121212", fg="#aaaaaa",
                               font=("Helvetica", 10))
        self.status.pack(side="left")

    # ── Camera scanning ───────────────────────────────────────────────────────

    def _scan(self):
        self.status.config(text="Scanning cameras...", fg="#aaaaaa")
        self.root.update()

        self.cameras = detect_cameras()

        cols = min(max(len(self.cameras), 1), 3)
        for idx, cam in enumerate(self.cameras):
            grabber = FrameGrabber(cam["cap"])
            self.grabbers.append(grabber)
            card = CameraCard(self.card_frame, cam, grabber, self._on_select)
            card.grid(row=idx // cols, column=idx % cols, padx=10, pady=10)
            self.cards.append(card)

        if not self.cameras:
            tk.Label(self.card_frame, text="No cameras detected.",
                     bg="#121212", fg="#ff5252",
                     font=("Helvetica", 12)).pack(pady=40)
            self.status.config(text="No cameras found.", fg="#ff5252")
        else:
            self.status.config(
                text=f"{len(self.cameras)} camera(s) found.",
                fg="#aaaaaa"
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
        # Clear whoever previously held this role
        current = self.primary if role == "primary" else self.secondary
        if current and current is not card:
            current.set_role(None)

        # If this card held the OTHER role, clear that slot too
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
            messagebox.showwarning("Nothing selected",
                                   "Please select at least a primary camera.")
            return

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        self.status.config(text=f"✔  Saved to {CONFIG_FILE}", fg="#69f0ae")

    # ── Render loop ───────────────────────────────────────────────────────────

    def _tick(self):
        for card in self.cards:
            card.refresh()
        self.root.after(16, self._tick)  # ~60 fps UI poll

    def cleanup(self):
        self._teardown()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()
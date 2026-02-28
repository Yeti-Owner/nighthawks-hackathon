import cv2
import json
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

CONFIG_FILE = "cameras.txt"
MAX_CAMERAS = 6
THUMB_W, THUMB_H = 320, 200
SCAN_LIMIT = 8


def detect_cameras():
    """Scan for cameras using CAP_DSHOW to avoid backend errors on Windows."""
    cameras = []
    for i in range(SCAN_LIMIT):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                cameras.append({"id": i, "cap": cap})
            else:
                cap.release()
        else:
            cap.release()
        if len(cameras) >= MAX_CAMERAS:
            break
    return cameras


class CameraCard(tk.Frame):
    COLORS = {"primary": "#00c853", "secondary": "#2979ff", None: "#1e1e1e"}

    def __init__(self, parent, cam, on_select):
        super().__init__(parent, bd=2, relief="groove", bg="#1e1e1e")
        self.cam = cam
        self.on_select = on_select
        self.selected_as = None
        self._img_ref = None

        self.canvas = tk.Canvas(self, width=THUMB_W, height=THUMB_H,
                                bg="black", highlightthickness=0)
        self.canvas.pack()

        self.label = tk.Label(self, text=f"Camera {cam['id']}",
                              bg="#1e1e1e", fg="white",
                              font=("Helvetica", 10, "bold"))
        self.label.pack(pady=(4, 2))

        btn_frame = tk.Frame(self, bg="#1e1e1e")
        btn_frame.pack(pady=(0, 8))
        self._btn_frame = btn_frame

        self.pri_btn = tk.Button(btn_frame, text="Set Primary", width=11,
                                 command=lambda: on_select(self, "primary"),
                                 bg="#333", fg="white", relief="flat", cursor="hand2")
        self.pri_btn.pack(side="left", padx=4)

        self.sec_btn = tk.Button(btn_frame, text="Set Secondary", width=12,
                                 command=lambda: on_select(self, "secondary"),
                                 bg="#333", fg="white", relief="flat", cursor="hand2")
        self.sec_btn.pack(side="left", padx=4)

    def update_frame(self):
        ret, frame = self.cam["cap"].read()
        if ret:
            frame = cv2.resize(frame, (THUMB_W, THUMB_H))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            self.canvas.create_image(0, 0, anchor="nw", image=img)
            self._img_ref = img

    def set_highlight(self, role):
        self.selected_as = role
        color = self.COLORS[role]
        self.config(bg=color)
        self._btn_frame.config(bg=color)
        self.label.config(bg=color)

        role_text = {
            None: f"Camera {self.cam['id']}",
            "primary": f"Camera {self.cam['id']}  ✔ PRIMARY",
            "secondary": f"Camera {self.cam['id']}  ✔ SECONDARY",
        }
        self.label.config(text=role_text[role])


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera Selector")
        self.root.configure(bg="#121212")
        self.root.resizable(True, True)

        self.cameras = []
        self.cards = []
        self.primary_card = None
        self.secondary_card = None

        self._build_header()

        self.card_frame = tk.Frame(self.root, bg="#121212")
        self.card_frame.pack(padx=16, pady=8, fill="both", expand=True)

        self._build_footer()
        self._scan_cameras()
        self._tick()

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
        self.status.pack(side="left", anchor="w")

    def _scan_cameras(self):
        self.status.config(text="Scanning cameras...", fg="#aaaaaa")
        self.root.update()

        self.cameras = detect_cameras()
        for card in self.cards:
            card.destroy()
        self.cards.clear()
        self.primary_card = None
        self.secondary_card = None

        if not self.cameras:
            tk.Label(self.card_frame, text="No cameras detected.",
                     bg="#121212", fg="#ff5252",
                     font=("Helvetica", 12)).pack(pady=40)
            self.status.config(text="No cameras found.", fg="#ff5252")
            return

        cols = min(len(self.cameras), 3)
        for idx, cam in enumerate(self.cameras):
            card = CameraCard(self.card_frame, cam, self._on_select)
            card.grid(row=idx // cols, column=idx % cols, padx=10, pady=10)
            self.cards.append(card)

        self.status.config(
            text=f"{len(self.cameras)} camera(s) found. Click a card to set primary / secondary.",
            fg="#aaaaaa"
        )

    def _rescan(self):
        for cam in self.cameras:
            cam["cap"].release()
        for widget in self.card_frame.winfo_children():
            widget.destroy()
        self._scan_cameras()

    def _on_select(self, card, role):
        # Clear previous holder of this role
        if role == "primary" and self.primary_card and self.primary_card is not card:
            self.primary_card.set_highlight(None)
        if role == "secondary" and self.secondary_card and self.secondary_card is not card:
            self.secondary_card.set_highlight(None)

        # If card already had the other role, clear it
        if role == "primary" and self.secondary_card is card:
            self.secondary_card = None
        if role == "secondary" and self.primary_card is card:
            self.primary_card = None

        if role == "primary":
            self.primary_card = card
        else:
            self.secondary_card = card

        card.set_highlight(role)

    def _save(self):
        config = {}
        if self.primary_card:
            cid = self.primary_card.cam["id"]
            config["primary"] = {"id": cid, "name": f"Camera {cid}"}
        if self.secondary_card:
            cid = self.secondary_card.cam["id"]
            config["secondary"] = {"id": cid, "name": f"Camera {cid}"}

        if not config:
            messagebox.showwarning("Nothing selected",
                                   "Please select at least a primary camera.")
            return

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        self.status.config(text=f"✔  Saved to {CONFIG_FILE}", fg="#69f0ae")

    def _tick(self):
        for card in self.cards:
            card.update_frame()
        self.root.after(33, self._tick)  # ~30 fps

    def cleanup(self):
        for cam in self.cameras:
            cam["cap"].release()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()
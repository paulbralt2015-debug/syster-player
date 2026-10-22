"""Lecteur vidéo avec décodage en temps réel du brouillage par permutation de lignes."""
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk

import cv2
from PIL import Image, ImageTk

from core import Descrambler

QUALITES = {"Rapide": 16, "Normal": 8, "Précis": 2}


class Lecteur:
    def __init__(self, root, chemin=None):
        self.root = root
        root.title("Syster Player")
        root.geometry("960x640")
        root.minsize(480, 360)

        # état partagé avec le thread de lecture
        self.cap = None
        self.fps = 25.0
        self.total = 0
        self.pos = 0
        self.playing = False
        self.decode = tk.BooleanVar(value=True)
        self.flip = tk.BooleanVar(value=False)
        self.qualite = tk.StringVar(value="Normal")
        self.pending_open = None
        self.pending_seek = None
        self.latest = None          # image RGB à afficher
        self.proc_fps = 0.0
        self.running = True
        self.dragging = False
        self.desc = Descrambler(QUALITES["Normal"])

        self._build_ui()
        threading.Thread(target=self._worker, daemon=True).start()
        self.root.after(15, self._refresh)
        root.protocol("WM_DELETE_WINDOW", self._close)
        if chemin:
            self.pending_open = chemin

    # ---------- interface ----------
    def _build_ui(self):
        self.video = tk.Label(self.root, bg="black")
        self.video.pack(fill="both", expand=True)

        self.slider = ttk.Scale(self.root, from_=0, to=1000)
        self.slider.pack(fill="x", padx=8, pady=(4, 0))
        self.slider.bind("<ButtonPress-1>", lambda e: setattr(self, "dragging", True))
        self.slider.bind("<ButtonRelease-1>", self._slider_release)

        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(bar, text="Ouvrir…", command=self.ouvrir).pack(side="left")
        self.btn = ttk.Button(bar, text="▶ Lecture", command=self.toggle)
        self.btn.pack(side="left", padx=6)
        ttk.Checkbutton(bar, text="Décoder (D)", variable=self.decode,
                        command=self._reset_decoder).pack(side="left", padx=6)
        ttk.Checkbutton(bar, text="Inverser haut/bas (F)",
                        variable=self.flip).pack(side="left", padx=6)
        ttk.Label(bar, text="Qualité :").pack(side="left", padx=(12, 2))
        cb = ttk.Combobox(bar, textvariable=self.qualite, values=list(QUALITES),
                          width=8, state="readonly")
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", self._change_qualite)

        self.status = ttk.Label(bar, text="Aucun fichier")
        self.status.pack(side="right")

        self.root.bind("<space>", lambda e: self.toggle())
        self.root.bind("d", lambda e: self._toggle_var(self.decode, True))
        self.root.bind("f", lambda e: self._toggle_var(self.flip, False))
        self.root.bind("<Left>", lambda e: self._seek_rel(-5))
        self.root.bind("<Right>", lambda e: self._seek_rel(5))

    def _toggle_var(self, var, reset):
        var.set(not var.get())
        if reset:
            self._reset_decoder()

    def _reset_decoder(self):
        self.desc.reset()

    def _change_qualite(self, _=None):
        self.desc = Descrambler(QUALITES[self.qualite.get()])

    def ouvrir(self):
        p = filedialog.askopenfilename(
            filetypes=[("Vidéos", "*.mp4 *.mkv *.avi *.mov *.webm *.ts"),
                       ("Tous", "*.*")])
        if p:
            self.pending_open = p

    def toggle(self):
        if self.cap is None:
            return
        self.playing = not self.playing
        self.btn.config(text="⏸ Pause" if self.playing else "▶ Lecture")

    def _seek_rel(self, secondes):
        if self.cap is not None:
            self.pending_seek = max(0, int(self.pos + secondes * self.fps))

    def _slider_release(self, _):
        self.dragging = False
        if self.total:
            self.pending_seek = int(self.slider.get() / 1000 * self.total)

    def _refresh(self):
        img = self.latest
        if img is not None:
            w = max(self.video.winfo_width(), 2)
            h = max(self.video.winfo_height(), 2)
            ih, iw = img.shape[:2]
            s = min(w / iw, h / ih)
            pil = Image.fromarray(img).resize((max(1, int(iw * s)), max(1, int(ih * s))))
            self.photo = ImageTk.PhotoImage(pil)
            self.video.config(image=self.photo)
        if self.total and not self.dragging:
            self.slider.set(self.pos / self.total * 1000)
        if self.cap is not None:
            t = self.pos / self.fps if self.fps else 0
            self.status.config(
                text=f"{int(t // 60):02d}:{int(t % 60):02d}  |  calcul : {self.proc_fps:.1f} img/s"
                     f"  |  {'DÉCODÉ' if self.decode.get() else 'BRUT'}")
            self.btn.config(text="⏸ Pause" if self.playing else "▶ Lecture")
        if self.running:
            self.root.after(15, self._refresh)

    def _close(self):
        self.running = False
        self.root.destroy()

    # ---------- thread de lecture ----------
    def _traiter(self, frame):
        if self.decode.get():
            frame = self.desc.process(frame)
        if self.flip.get():
            frame = frame[::-1]
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def _worker(self):
        t0, base = time.time(), 0
        reset_clock = True
        derniere = time.time()
        while self.running:
            if self.pending_open:
                p, self.pending_open = self.pending_open, None
                if self.cap is not None:
                    self.cap.release()
                cap = cv2.VideoCapture(p)
                if cap.isOpened():
                    self.cap = cap
                    self.fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                    self.total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.pos = 0
                    self.desc.reset()
                    self.pending_seek = 0
                    self.playing = True
                    self.root.title(f"Syster Player — {p.split('/')[-1].split(chr(92))[-1]}")
                else:
                    self.cap = None

            if self.cap is None:
                time.sleep(0.05)
                continue

            if self.pending_seek is not None:
                n, self.pending_seek = self.pending_seek, None
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, n)
                self.pos = n
                self.desc.reset()
                reset_clock = True
                if not self.playing:         # prévisualisation en pause
                    ok, f = self.cap.read()
                    if ok:
                        self.latest = self._traiter(f)
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, n)
                continue

            if not self.playing:
                reset_clock = True
                time.sleep(0.03)
                continue

            if reset_clock:
                t0, base, reset_clock = time.time(), self.pos, False

            # rester en temps réel : sauter des images si le calcul est trop lent
            cible = base + int((time.time() - t0) * self.fps)
            while self.pos < cible - 1:
                if not self.cap.grab():
                    break
                self.pos += 1

            ok, frame = self.cap.read()
            if not ok:
                self.playing = False
                self.pending_seek = 0
                continue
            self.pos += 1
            self.latest = self._traiter(frame)

            now = time.time()
            inst = 1.0 / max(now - derniere, 1e-6)
            self.proc_fps = 0.8 * self.proc_fps + 0.2 * inst
            derniere = now

            # cadence : attendre si on est en avance
            echeance = t0 + (self.pos - base) / self.fps
            delai = echeance - time.time()
            if delai > 0:
                time.sleep(delai)


def main():
    import sys
    root = tk.Tk()
    Lecteur(root, sys.argv[1] if len(sys.argv) > 1 else None)
    root.mainloop()


if __name__ == "__main__":
    main()

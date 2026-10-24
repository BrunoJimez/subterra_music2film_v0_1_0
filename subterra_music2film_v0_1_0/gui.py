from __future__ import annotations

import os
import random
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


ROOT = Path(__file__).resolve().parent


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SUBTERRA — Music to Film")
        self.geometry("860x620")
        self.audio = tk.StringVar()
        self.output = tk.StringVar(value=str(ROOT / "output" / "subterra_film.mp4"))
        self.resolution = tk.StringVar(value="1080p")
        self.seed = tk.StringVar(value=str(random.randint(1, 2_147_483_647)))
        self.style = tk.StringVar(value="auto")
        self.render_scale = tk.StringVar(value="0.75")
        self.audio_mode = tk.StringVar(value="preserve")
        self.media: list[str] = []
        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 7}
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        ttk.Label(frame, text="SUBTERRA", font=("Arial", 22, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(frame, text="Música → filme techno underground, local e sem API paga").grid(row=1, column=0, columnspan=3, sticky="w", **pad)

        ttk.Label(frame, text="Áudio").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(frame, textvariable=self.audio, width=72).grid(row=2, column=1, sticky="ew", **pad)
        ttk.Button(frame, text="Selecionar", command=self.pick_audio).grid(row=2, column=2, **pad)

        ttk.Label(frame, text="Saída").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(frame, textvariable=self.output, width=72).grid(row=3, column=1, sticky="ew", **pad)
        ttk.Button(frame, text="Salvar como", command=self.pick_output).grid(row=3, column=2, **pad)

        ttk.Label(frame, text="Resolução").grid(row=4, column=0, sticky="w", **pad)
        ttk.Combobox(frame, textvariable=self.resolution, values=["draft", "720p", "1080p", "2k", "4k", "reel", "tiktok", "square", "cinema_2k", "cinema_4k"], state="readonly").grid(row=4, column=1, sticky="w", **pad)

        ttk.Label(frame, text="Estilo").grid(row=5, column=0, sticky="w", **pad)
        ttk.Combobox(frame, textvariable=self.style, values=["auto", "industrial_tunnel", "vector_field", "particle_ritual", "pixel_corruption", "halftone_signal", "machine_vision", "liquid_feedback"], state="readonly", width=30).grid(row=5, column=1, sticky="w", **pad)

        ttk.Label(frame, text="Seed").grid(row=6, column=0, sticky="w", **pad)
        sf = ttk.Frame(frame); sf.grid(row=6, column=1, sticky="w", **pad)
        ttk.Entry(sf, textvariable=self.seed, width=20).pack(side="left")
        ttk.Button(sf, text="Nova história", command=lambda: self.seed.set(str(random.randint(1, 2_147_483_647)))).pack(side="left", padx=8)

        ttk.Label(frame, text="Escala interna").grid(row=7, column=0, sticky="w", **pad)
        ttk.Combobox(frame, textvariable=self.render_scale, values=["0.5", "0.65", "0.75", "1.0"], state="readonly", width=10).grid(row=7, column=1, sticky="w", **pad)

        ttk.Label(frame, text="Áudio final").grid(row=8, column=0, sticky="w", **pad)
        ttk.Combobox(frame, textvariable=self.audio_mode, values=["preserve", "normalize"], state="readonly", width=15).grid(row=8, column=1, sticky="w", **pad)

        mf = ttk.Frame(frame); mf.grid(row=9, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Button(mf, text="Adicionar imagens/vídeos base", command=self.pick_media).pack(side="left")
        self.media_label = ttk.Label(mf, text="Nenhuma mídia base")
        self.media_label.pack(side="left", padx=10)

        bf = ttk.Frame(frame); bf.grid(row=10, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Button(bf, text="Diagnóstico do PC", command=self.run_diagnose).pack(side="left")
        ttk.Button(bf, text="Renderizar filme", command=self.run_render).pack(side="left", padx=10)

        self.log = tk.Text(frame, height=15, bg="#101014", fg="#e8e8e8", insertbackground="white")
        self.log.grid(row=11, column=0, columnspan=3, sticky="nsew", **pad)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(11, weight=1)

    def pick_audio(self):
        p = filedialog.askopenfilename(filetypes=[("Áudio", "*.wav *.flac *.mp3 *.m4a *.aac *.ogg"), ("Todos", "*.*")])
        if p: self.audio.set(p)

    def pick_output(self):
        p = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4"), ("MKV", "*.mkv"), ("AVI", "*.avi")])
        if p: self.output.set(p)

    def pick_media(self):
        files = filedialog.askopenfilenames(filetypes=[("Mídia", "*.jpg *.jpeg *.png *.webp *.mp4 *.mov *.mkv *.avi"), ("Todos", "*.*")])
        self.media = list(files)
        self.media_label.config(text=f"{len(self.media)} arquivo(s)")

    def _run(self, cmd: list[str]):
        self.log.delete("1.0", "end")
        self.log.insert("end", "$ " + " ".join(cmd) + "\n\n")
        def worker():
            try:
                proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                assert proc.stdout
                for line in proc.stdout:
                    self.after(0, self.log.insert, "end", line)
                    self.after(0, self.log.see, "end")
                code = proc.wait()
                self.after(0, lambda: messagebox.showinfo("SUBTERRA", "Concluído." if code == 0 else f"Processo terminou com código {code}."))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("SUBTERRA", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def run_diagnose(self):
        self._run([sys.executable, "subterra.py", "diagnose", "--output", str(ROOT / "hardware_report.json")])

    def run_render(self):
        if not self.audio.get():
            messagebox.showwarning("SUBTERRA", "Selecione um arquivo de áudio.")
            return
        Path(self.output.get()).parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "subterra.py", "render", self.audio.get(), self.output.get(), "--resolution", self.resolution.get(), "--seed", self.seed.get(), "--style", self.style.get(), "--render-scale", self.render_scale.get(), "--audio-mode", self.audio_mode.get()]
        for p in self.media:
            cmd.extend(["--media", p])
        self._run(cmd)


if __name__ == "__main__":
    App().mainloop()

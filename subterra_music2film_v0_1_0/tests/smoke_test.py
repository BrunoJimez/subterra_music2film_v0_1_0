from __future__ import annotations

import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tests" / "_tmp"
TMP.mkdir(exist_ok=True)
audio = TMP / "test.wav"
out = TMP / "test.mp4"

sr = 22050
duration = 3.0
t = np.arange(int(sr * duration)) / sr
signal = (0.25 * np.sin(2 * math.pi * 55 * t) + 0.12 * np.sin(2 * math.pi * 220 * t))
for beat in np.arange(0, duration, 0.5):
    idx = int(beat * sr)
    n = min(int(sr * 0.08), len(signal) - idx)
    if n > 0:
        signal[idx:idx+n] += 0.65 * np.exp(-np.arange(n) / (sr * 0.015)) * np.sin(2 * math.pi * 80 * np.arange(n) / sr)
pcm = np.int16(np.clip(signal, -1, 1) * 32767)
with wave.open(str(audio), "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())

cmd = [sys.executable, str(ROOT / "subterra.py"), "render", str(audio), str(out), "--resolution", "draft", "--fps", "12", "--render-scale", "0.5", "--preview-seconds", "2", "--seed", "123"]
print("RUN", " ".join(cmd))
subprocess.run(cmd, check=True, cwd=ROOT)
assert out.exists() and out.stat().st_size > 1000
print("OK", out, out.stat().st_size)

from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from .config import RenderConfig
from .media import MediaPool


class FeatureStream:
    def __init__(self, npz_path: str | Path):
        d = np.load(npz_path)
        self.times = d["times"]
        self.channels = {k: d[k] for k in d.files if k not in {"times", "beat_times", "section_bounds"}}
        self.beat_times = d["beat_times"]
        self.section_bounds = d["section_bounds"]

    def value(self, name: str, t: float) -> float:
        arr = self.channels[name]
        return float(np.interp(t, self.times, arr))

    def beat_pulse(self, t: float, decay: float = 9.0) -> float:
        if len(self.beat_times) == 0:
            return 0.0
        i = np.searchsorted(self.beat_times, t, side="right") - 1
        if i < 0:
            return 0.0
        return float(math.exp(-max(0.0, t - float(self.beat_times[i])) * decay))

    def scene_index(self, t: float) -> int:
        return max(0, min(len(self.section_bounds) - 2, int(np.searchsorted(self.section_bounds, t, side="right") - 1)))


class FilmRenderer:
    def __init__(
        self,
        config: RenderConfig,
        features_path: str | Path,
        story_path: str | Path,
        media_paths: list[str] | None = None,
    ):
        self.cfg = config
        self.features = FeatureStream(features_path)
        self.story = json.loads(Path(story_path).read_text(encoding="utf-8"))
        self.rng = np.random.default_rng(config.seed)
        self.iw = max(320, int(round(config.width * config.render_scale / 2) * 2))
        self.ih = max(180, int(round(config.height * config.render_scale / 2) * 2))
        self.media = MediaPool(media_paths or [], self.iw, self.ih)
        self.feedback = np.zeros((self.ih, self.iw, 3), np.uint8)
        self.yy, self.xx = np.mgrid[0:self.ih, 0:self.iw].astype(np.float32)
        self.nx = (self.xx - self.iw / 2) / max(self.iw, self.ih)
        self.ny = (self.yy - self.ih / 2) / max(self.iw, self.ih)
        self.radius = np.sqrt(self.nx**2 + self.ny**2)
        self.angle = np.arctan2(self.ny, self.nx)
        self.particles = self._init_particles(1800 if self.iw >= 1280 else 900)

    def _init_particles(self, count: int) -> np.ndarray:
        p = np.zeros((count, 4), np.float32)
        p[:, 0] = self.rng.uniform(0, self.iw, count)
        p[:, 1] = self.rng.uniform(0, self.ih, count)
        p[:, 2] = self.rng.uniform(-1, 1, count)
        p[:, 3] = self.rng.uniform(0.2, 1.0, count)
        return p

    def _palette(self, frame: np.ndarray, shift: float, brightness: float) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if shift > 0.35:
            out = cv2.applyColorMap(gray, cv2.COLORMAP_TWILIGHT_SHIFTED)
        elif shift < -0.35:
            out = cv2.applyColorMap(gray, cv2.COLORMAP_BONE)
        else:
            out = cv2.applyColorMap(gray, cv2.COLORMAP_OCEAN)
        mix = 0.32 + 0.42 * brightness
        return cv2.addWeighted(frame, 1.0 - mix, out, mix, 0)

    def _tunnel(self, t: float, e: float, impact: float, bright: float) -> np.ndarray:
        phase = 12.0 * self.radius - t * (1.8 + 5.0 * e)
        rings = (np.sin(phase * math.pi * 2) * 0.5 + 0.5)
        spokes = (np.sin(self.angle * (6 + int(10 * bright)) + t * 0.7) * 0.5 + 0.5)
        img = np.clip((rings * 0.72 + spokes * 0.28) * (110 + 145 * impact), 0, 255).astype(np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    def _vector_field(self, t: float, e: float, impact: float, bright: float) -> np.ndarray:
        x = self.nx * (8 + 8 * bright)
        y = self.ny * (8 + 8 * bright)
        field = np.sin(x + np.cos(y * 1.7 + t)) + np.cos(y - np.sin(x * 1.3 - t * 1.2))
        field += np.sin((x + y) * 0.7 + t * (1 + 2 * e)) * impact
        img = np.clip((field + 3) / 6 * 255, 0, 255).astype(np.uint8)
        edges = cv2.Canny(img, 40, 120)
        return cv2.cvtColor(cv2.addWeighted(img, 0.65, edges, 0.8, 0), cv2.COLOR_GRAY2BGR)

    def _particles(self, t: float, e: float, impact: float, bright: float) -> np.ndarray:
        p = self.particles
        cx, cy = self.iw / 2, self.ih / 2
        dx = p[:, 0] - cx
        dy = p[:, 1] - cy
        dist = np.sqrt(dx * dx + dy * dy) + 1e-4
        swirl = 0.25 + 1.8 * e
        p[:, 0] += (-dy / dist) * swirl * p[:, 3] + dx / dist * impact * 8
        p[:, 1] += (dx / dist) * swirl * p[:, 3] + dy / dist * impact * 8
        p[:, 2] += 0.015 * (bright - 0.5)
        out = (p[:, 0] < 0) | (p[:, 0] >= self.iw) | (p[:, 1] < 0) | (p[:, 1] >= self.ih)
        n = int(out.sum())
        if n:
            a = self.rng.uniform(0, math.tau, n)
            r = self.rng.uniform(2, min(self.iw, self.ih) * 0.15, n)
            p[out, 0] = cx + np.cos(a) * r
            p[out, 1] = cy + np.sin(a) * r
        frame = np.zeros((self.ih, self.iw, 3), np.uint8)
        coords = p[:, :2].astype(np.int32)
        valid = (coords[:, 0] >= 0) & (coords[:, 0] < self.iw) & (coords[:, 1] >= 0) & (coords[:, 1] < self.ih)
        intensity = np.clip(90 + 165 * (p[:, 3] * (0.4 + e)), 0, 255).astype(np.uint8)
        frame[coords[valid, 1], coords[valid, 0]] = np.stack([intensity[valid]] * 3, axis=1)
        frame = cv2.GaussianBlur(frame, (0, 0), 0.8 + 2.0 * impact)
        return frame

    def _halftone(self, base: np.ndarray, e: float, bright: float) -> np.ndarray:
        gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
        cell = max(3, int(13 - 8 * bright))
        small = cv2.resize(gray, (max(1, self.iw // cell), max(1, self.ih // cell)), interpolation=cv2.INTER_AREA)
        small = cv2.threshold(small, int(90 + 70 * (1 - e)), 255, cv2.THRESH_BINARY)[1]
        return cv2.cvtColor(cv2.resize(small, (self.iw, self.ih), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)

    def _pixel_corrupt(self, base: np.ndarray, impact: float, density: float) -> np.ndarray:
        out = base.copy()
        bands = 2 + int(impact * 18 + density * 8)
        for _ in range(bands):
            y = int(self.rng.integers(0, self.ih))
            h = int(self.rng.integers(2, max(3, self.ih // 24)))
            shift = int(self.rng.integers(-max(2, self.iw // 8), max(3, self.iw // 8)))
            out[y:y + h] = np.roll(out[y:y + h], shift, axis=1)
        if impact > 0.55:
            channel = int(self.rng.integers(0, 3))
            out[:, :, channel] = np.roll(out[:, :, channel], int((impact - 0.5) * 25), axis=1)
        return out

    def _scanlines(self, frame: np.ndarray, strength: float) -> np.ndarray:
        if strength <= 0:
            return frame
        out = frame.copy()
        step = 3 if self.ih < 1200 else 4
        out[::step] = (out[::step].astype(np.float32) * (0.55 + 0.25 * (1 - strength))).astype(np.uint8)
        return out

    def _feedback_mix(self, frame: np.ndarray, e: float, impact: float) -> np.ndarray:
        center = (self.iw / 2, self.ih / 2)
        scale = 1.002 + 0.012 * e + 0.02 * impact
        angle = (impact - 0.35) * 0.8
        m = cv2.getRotationMatrix2D(center, angle, scale)
        fb = cv2.warpAffine(self.feedback, m, (self.iw, self.ih), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        out = cv2.addWeighted(frame, 0.72, fb, 0.48, -4)
        self.feedback = out.copy()
        return out

    def frame(self, t: float) -> np.ndarray:
        e = self.features.value("energy", t)
        impact = max(self.features.value("impact", t), self.features.beat_pulse(t))
        bright = self.features.value("brightness", t)
        texture = self.features.value("texture", t)
        scene_idx = self.features.scene_index(t)
        scene = self.story["scenes"][scene_idx % len(self.story["scenes"])]
        archetype = scene["archetype"]
        density = float(scene["glitch_density"])
        shift = float(scene["palette_shift"])
        media = self.media.get(scene_idx, t)

        if archetype == "industrial_tunnel":
            base = self._tunnel(t, e, impact, bright)
        elif archetype == "vector_field":
            base = self._vector_field(t, e, impact, bright)
        elif archetype == "particle_ritual":
            base = self._particles(t, e, impact, bright)
        elif archetype == "halftone_signal":
            source = media if media is not None else self._vector_field(t, e, impact, bright)
            base = self._halftone(source, e, bright)
        elif archetype == "pixel_corruption":
            source = media if media is not None else self._tunnel(t, e, impact, bright)
            base = self._pixel_corrupt(source, impact, density)
        elif archetype == "machine_vision":
            source = media if media is not None else self._particles(t, e, impact, bright)
            gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
            edge = cv2.Canny(gray, int(20 + 70 * (1 - e)), int(90 + 100 * bright))
            base = cv2.cvtColor(edge, cv2.COLOR_GRAY2BGR)
        else:
            source = media if media is not None else self._vector_field(t, e, impact, bright)
            base = self._feedback_mix(source, e, impact)

        if media is not None and archetype not in {"halftone_signal", "pixel_corruption", "machine_vision", "liquid_feedback"}:
            mix = float(scene["media_mix"]) * (0.35 + 0.65 * e)
            base = cv2.addWeighted(base, 1.0 - mix, media, mix, 0)

        base = self._feedback_mix(base, e, impact)
        if density > 0.25 and (impact > 0.35 or self.rng.random() < density * 0.012):
            base = self._pixel_corrupt(base, impact, density)
        base = self._palette(base, shift, bright)
        base = self._scanlines(base, 0.35 + texture * 0.5)

        # Strobe is intentionally capped to reduce photosensitive-risk.
        strobe = min(max(self.cfg.strobe, 0.0), 0.45)
        if strobe > 0 and impact > 0.86 and self.rng.random() < strobe * 0.15:
            base = cv2.addWeighted(base, 1.0 - strobe, np.full_like(base, 255), strobe, 0)

        if (self.iw, self.ih) != (self.cfg.width, self.cfg.height):
            base = cv2.resize(base, (self.cfg.width, self.cfg.height), interpolation=cv2.INTER_CUBIC)
        return base

    def close(self) -> None:
        self.media.close()


def _ffmpeg_encoder_args(cfg: RenderConfig, output: Path) -> list[str]:
    ext = output.suffix.lower()
    encoder = cfg.encoder
    if ext == ".avi":
        return ["-c:v", "mpeg4", "-q:v", "2", "-c:a", "libmp3lame", "-b:a", "320k"]
    if encoder in {"h264_nvenc", "hevc_nvenc", "h264_amf", "hevc_amf", "h264_qsv", "hevc_qsv"}:
        return ["-c:v", encoder, "-preset", "p5", "-cq", str(cfg.crf), "-c:a", "aac", "-b:a", "320k"]
    if encoder in {"libx265", "libx264"}:
        return ["-c:v", encoder, "-preset", cfg.preset, "-crf", str(cfg.crf), "-c:a", "aac", "-b:a", "320k"]
    return ["-c:v", "libx264", "-preset", cfg.preset, "-crf", str(cfg.crf), "-c:a", "aac", "-b:a", "320k"]


def render_film(
    audio_path: str | Path,
    output_path: str | Path,
    features_path: str | Path,
    story_path: str | Path,
    config: RenderConfig,
    duration: float,
    media_paths: list[str] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg não foi encontrado no PATH.")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    total_frames = max(1, int(math.ceil(duration * config.fps)))
    audio_filter: list[str] = []
    if config.audio_mode == "normalize":
        audio_filter = ["-af", "loudnorm=I=-14:TP=-1.0:LRA=11"]

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{config.width}x{config.height}", "-r", str(config.fps), "-i", "-",
        "-i", str(Path(audio_path)),
        "-map", "0:v:0", "-map", "1:a:0",
        *_ffmpeg_encoder_args(config, output),
        *audio_filter,
        "-pix_fmt", "yuv420p", "-t", f"{duration:.6f}", "-shortest", str(output),
    ]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    renderer = FilmRenderer(config, features_path, story_path, media_paths)
    try:
        assert process.stdin is not None
        for frame_index in range(total_frames):
            t = min(duration, frame_index / config.fps)
            process.stdin.write(renderer.frame(t).tobytes())
            if progress and (frame_index % max(1, int(config.fps)) == 0 or frame_index == total_frames - 1):
                progress(frame_index + 1, total_frames)
        process.stdin.close()
        code = process.wait()
        if code != 0:
            raise RuntimeError(f"FFmpeg encerrou com código {code}.")
    except BrokenPipeError as exc:
        raise RuntimeError("FFmpeg interrompeu o render. Verifique codec, espaço em disco e formato de saída.") from exc
    finally:
        renderer.close()
        if process.poll() is None:
            process.terminate()

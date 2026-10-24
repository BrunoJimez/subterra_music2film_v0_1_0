from __future__ import annotations

from dataclasses import dataclass


RESOLUTION_PRESETS: dict[str, tuple[int, int]] = {
    "draft": (640, 360),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "2k": (2560, 1440),
    "4k": (3840, 2160),
    "reel": (1080, 1920),
    "tiktok": (1080, 1920),
    "square": (1080, 1080),
    "cinema_2k": (2048, 1080),
    "cinema_4k": (4096, 2160),
}


@dataclass(frozen=True)
class RenderConfig:
    width: int
    height: int
    fps: float = 30.0
    seed: int = 0
    style: str = "auto"
    quality: str = "high"
    render_scale: float = 1.0
    strobe: float = 0.20
    audio_mode: str = "preserve"
    encoder: str = "libx264"
    crf: int = 18
    preset: str = "medium"

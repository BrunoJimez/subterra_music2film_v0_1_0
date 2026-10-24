from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def cover_resize(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    h, w = frame.shape[:2]
    scale = max(width / max(w, 1), height / max(h, 1))
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    x = max(0, (nw - width) // 2)
    y = max(0, (nh - height) // 2)
    return resized[y:y + height, x:x + width].copy()


class MediaPool:
    def __init__(self, paths: list[str], width: int, height: int):
        self.width = width
        self.height = height
        self.items: list[dict] = []
        for raw in paths:
            p = Path(raw)
            ext = p.suffix.lower()
            if ext in _IMAGE_EXTS:
                image = cv2.imread(str(p), cv2.IMREAD_COLOR)
                if image is not None:
                    self.items.append({"kind": "image", "path": p, "frame": cover_resize(image, width, height)})
            elif ext in _VIDEO_EXTS:
                cap = cv2.VideoCapture(str(p))
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
                    self.items.append({"kind": "video", "path": p, "cap": cap, "fps": fps, "frames": max(1, frames)})

    def get(self, index: int, t: float) -> np.ndarray | None:
        if not self.items:
            return None
        item = self.items[index % len(self.items)]
        if item["kind"] == "image":
            return item["frame"].copy()
        cap = item["cap"]
        frame_index = int(t * item["fps"]) % item["frames"]
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        return cover_resize(frame, self.width, self.height) if ok else None

    def close(self) -> None:
        for item in self.items:
            if item["kind"] == "video":
                item["cap"].release()

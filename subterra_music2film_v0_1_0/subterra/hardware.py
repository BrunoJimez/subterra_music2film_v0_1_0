from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil


@dataclass
class HardwareReport:
    os: str
    os_version: str
    machine: str
    cpu: str
    logical_cores: int
    physical_cores: int | None
    ram_gb: float
    gpu_name: str
    vram_gb: float | None
    ffmpeg: bool
    ffprobe: bool
    free_disk_gb: float
    recommended_tier: str
    recommended_resolution: str
    recommended_render_scale: float
    notes: list[str]


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=8).strip()
    except Exception:
        return ""


def _detect_nvidia() -> tuple[str, float | None]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return "", None
    out = _run([
        exe,
        "--query-gpu=name,memory.total",
        "--format=csv,noheader,nounits",
    ])
    if not out:
        return "", None
    first = out.splitlines()[0]
    parts = [p.strip() for p in first.rsplit(",", 1)]
    if len(parts) != 2:
        return first, None
    try:
        return parts[0], round(float(parts[1]) / 1024.0, 2)
    except ValueError:
        return parts[0], None


def _detect_windows_gpu() -> tuple[str, float | None]:
    if platform.system() != "Windows":
        return "", None
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return "", None
    script = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object -First 1 Name,AdapterRAM | ConvertTo-Json -Compress"
    )
    out = _run([ps, "-NoProfile", "-Command", script])
    try:
        data = json.loads(out)
        ram = data.get("AdapterRAM")
        return str(data.get("Name") or ""), round(float(ram) / (1024**3), 2) if ram else None
    except Exception:
        return "", None


def diagnose(target_path: str | Path = ".") -> HardwareReport:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path(target_path).resolve().anchor or "/"))
    gpu, vram = _detect_nvidia()
    if not gpu:
        gpu, vram = _detect_windows_gpu()
    if not gpu:
        gpu = "GPU não identificada automaticamente"

    ram = round(vm.total / (1024**3), 2)
    notes: list[str] = []
    tier = "low"
    resolution = "720p"
    scale = 0.5

    if (vram or 0) >= 12 and ram >= 32:
        tier, resolution, scale = "ultra", "4k", 1.0
    elif (vram or 0) >= 8 and ram >= 16:
        tier, resolution, scale = "high", "2k", 1.0
    elif (vram or 0) >= 4 and ram >= 12:
        tier, resolution, scale = "medium", "1080p", 0.75
    elif ram >= 8:
        tier, resolution, scale = "low", "720p", 0.65
    else:
        notes.append("RAM abaixo de 8 GB: use 640x360 ou 720p com render_scale 0.5.")

    if not shutil.which("ffmpeg"):
        notes.append("FFmpeg não encontrado no PATH; a exportação de vídeo não funcionará.")
    if vram is None:
        notes.append("VRAM não detectada; a recomendação foi conservadora.")
    if disk.free / (1024**3) < 20:
        notes.append("Menos de 20 GB livres: renders longos em alta resolução podem falhar.")

    return HardwareReport(
        os=platform.system(),
        os_version=platform.version(),
        machine=platform.machine(),
        cpu=platform.processor() or platform.uname().processor or "não identificado",
        logical_cores=psutil.cpu_count(logical=True) or 1,
        physical_cores=psutil.cpu_count(logical=False),
        ram_gb=ram,
        gpu_name=gpu,
        vram_gb=vram,
        ffmpeg=bool(shutil.which("ffmpeg")),
        ffprobe=bool(shutil.which("ffprobe")),
        free_disk_gb=round(disk.free / (1024**3), 2),
        recommended_tier=tier,
        recommended_resolution=resolution,
        recommended_render_scale=scale,
        notes=notes,
    )


def save_report(report: HardwareReport, path: str | Path) -> None:
    Path(path).write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")

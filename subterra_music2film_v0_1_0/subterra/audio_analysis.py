from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import librosa
import numpy as np
from scipy.signal import find_peaks


@dataclass
class AudioSummary:
    source: str
    duration_seconds: float
    sample_rate: int
    estimated_bpm: float
    estimated_key: str
    beats: int
    sections: list[dict[str, Any]]
    energy_mean: float
    energy_peak: float
    brightness_mean: float
    percussiveness: float
    mood_tags: list[str]


_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    lo, hi = np.nanpercentile(x, [2, 98]) if x.size else (0.0, 1.0)
    if hi <= lo + 1e-9:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def _estimate_key(chroma: np.ndarray) -> str:
    avg = np.mean(chroma, axis=1)
    avg = (avg - avg.mean()) / (avg.std() + 1e-8)
    candidates: list[tuple[float, str]] = []
    for root in range(12):
        maj = np.roll(_MAJOR_PROFILE, root)
        min_ = np.roll(_MINOR_PROFILE, root)
        candidates.append((float(np.corrcoef(avg, maj)[0, 1]), f"{_NOTES[root]} major"))
        candidates.append((float(np.corrcoef(avg, min_)[0, 1]), f"{_NOTES[root]} minor"))
    return max(candidates, key=lambda x: x[0])[1]


def _section_boundaries(features: np.ndarray, times: np.ndarray, duration: float) -> np.ndarray:
    if features.shape[1] < 4:
        return np.array([0.0, duration])
    smooth = np.vstack([np.convolve(row, np.ones(9) / 9, mode="same") for row in features])
    delta = np.linalg.norm(np.diff(smooth, axis=1, prepend=smooth[:, :1]), axis=0)
    delta = _normalize(delta)
    frame_gap = max(1, int(7.0 / max(times[1] - times[0], 1e-3))) if len(times) > 1 else 1
    peaks, props = find_peaks(delta, distance=frame_gap, prominence=0.18)
    ranked = peaks[np.argsort(props.get("prominences", np.ones(len(peaks))))[::-1]] if len(peaks) else peaks
    max_sections = max(2, min(14, int(duration // 18) + 2))
    selected = sorted(ranked[: max_sections - 1].tolist())
    bounds = [0.0] + [float(times[min(i, len(times) - 1)]) for i in selected] + [float(duration)]
    cleaned = [bounds[0]]
    for b in bounds[1:]:
        if b - cleaned[-1] >= 4.0 or b == duration:
            cleaned.append(b)
    if cleaned[-1] != duration:
        cleaned.append(duration)
    return np.array(cleaned, dtype=np.float32)


def analyze_audio(audio_path: str | Path, output_dir: str | Path) -> tuple[AudioSummary, Path, Path]:
    audio_path = Path(audio_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    if y.size == 0:
        raise ValueError("O arquivo de áudio está vazio ou não pôde ser decodificado.")
    duration = float(librosa.get_duration(y=y, sr=sr))
    hop = 512

    harmonic, percussive = librosa.effects.hpss(y)
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    onset = librosa.onset.onset_strength(y=percussive, sr=sr, hop_length=hop)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop, roll_percent=0.90)[0]
    flatness = librosa.feature.spectral_flatness(y=y, hop_length=hop)[0]
    chroma = librosa.feature.chroma_cens(y=harmonic, sr=sr, hop_length=hop)
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=hop)
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)

    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=hop)
    bpm = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)

    min_len = min(len(rms), len(onset), len(centroid), len(bandwidth), len(rolloff), len(flatness), chroma.shape[1], contrast.shape[1])
    times = times[:min_len]
    rms = rms[:min_len]
    onset = onset[:min_len]
    centroid = centroid[:min_len]
    bandwidth = bandwidth[:min_len]
    rolloff = rolloff[:min_len]
    flatness = flatness[:min_len]
    chroma = chroma[:, :min_len]
    contrast = contrast[:, :min_len]

    energy = _normalize(rms)
    impact = _normalize(onset)
    brightness = _normalize(centroid)
    texture = _normalize(flatness)
    width = _normalize(bandwidth)
    high = _normalize(rolloff)
    harmonicity = _normalize(np.mean(chroma, axis=0))
    contrast_mean = _normalize(np.mean(contrast, axis=0))

    struct_features = np.vstack([chroma, energy[None, :], brightness[None, :], impact[None, :]])
    bounds = _section_boundaries(struct_features, times, duration)

    sections: list[dict[str, Any]] = []
    for idx in range(len(bounds) - 1):
        start, end = float(bounds[idx]), float(bounds[idx + 1])
        mask = (times >= start) & (times < end)
        if not np.any(mask):
            mask = np.array([True] * len(times))
        e = float(np.mean(energy[mask]))
        imp = float(np.mean(impact[mask]))
        bri = float(np.mean(brightness[mask]))
        sections.append({
            "index": idx,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "energy": round(e, 4),
            "impact": round(imp, 4),
            "brightness": round(bri, 4),
            "role": "climax" if e > 0.72 and imp > 0.55 else "breakdown" if e < 0.28 else "development",
        })

    perc_ratio = float(np.sqrt(np.mean(percussive**2)) / (np.sqrt(np.mean(y**2)) + 1e-9))
    mood: list[str] = []
    mood.append("aggressive" if np.mean(impact) > 0.38 else "hypnotic")
    mood.append("bright" if np.mean(brightness) > 0.52 else "dark")
    mood.append("dense" if np.mean(texture) > 0.45 else "spacious")
    if bpm >= 125:
        mood.append("driving")

    summary = AudioSummary(
        source=str(audio_path.resolve()),
        duration_seconds=round(duration, 4),
        sample_rate=sr,
        estimated_bpm=round(bpm, 3),
        estimated_key=_estimate_key(chroma),
        beats=int(len(beat_times)),
        sections=sections,
        energy_mean=round(float(np.mean(energy)), 4),
        energy_peak=round(float(np.max(energy)), 4),
        brightness_mean=round(float(np.mean(brightness)), 4),
        percussiveness=round(perc_ratio, 4),
        mood_tags=mood,
    )

    json_path = output_dir / "analysis.json"
    npz_path = output_dir / "features.npz"
    json_path.write_text(json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    np.savez_compressed(
        npz_path,
        times=times.astype(np.float32),
        energy=energy.astype(np.float32),
        impact=impact.astype(np.float32),
        brightness=brightness.astype(np.float32),
        texture=texture.astype(np.float32),
        width=width.astype(np.float32),
        high=high.astype(np.float32),
        harmonicity=harmonicity.astype(np.float32),
        contrast=contrast_mean.astype(np.float32),
        beat_times=np.asarray(beat_times, dtype=np.float32),
        section_bounds=bounds.astype(np.float32),
    )
    return summary, json_path, npz_path

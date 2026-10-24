from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


ARCHETYPES = [
    "industrial_tunnel",
    "vector_field",
    "particle_ritual",
    "pixel_corruption",
    "halftone_signal",
    "machine_vision",
    "liquid_feedback",
]


def build_story(analysis_json: str | Path, seed: int, output_path: str | Path, style: str = "auto") -> dict[str, Any]:
    data = json.loads(Path(analysis_json).read_text(encoding="utf-8"))
    rng = np.random.default_rng(seed)
    sections = data["sections"]
    order = list(rng.permutation(ARCHETYPES))
    scenes: list[dict[str, Any]] = []
    for i, section in enumerate(sections):
        role = section["role"]
        archetype = style if style != "auto" else order[i % len(order)]
        if role == "climax" and style == "auto":
            archetype = rng.choice(["particle_ritual", "pixel_corruption", "industrial_tunnel"])
        elif role == "breakdown" and style == "auto":
            archetype = rng.choice(["halftone_signal", "machine_vision", "liquid_feedback"])
        scenes.append({
            "scene": i,
            "start": section["start"],
            "end": section["end"],
            "role": role,
            "archetype": str(archetype),
            "camera_mode": str(rng.choice(["push", "orbit", "handheld", "locked", "reverse"])),
            "glitch_density": round(float(rng.uniform(0.12, 0.85)), 3),
            "media_mix": round(float(rng.uniform(0.18, 0.72)), 3),
            "palette_shift": round(float(rng.uniform(-1.0, 1.0)), 3),
        })
    story = {
        "seed": int(seed),
        "title": "SUBTERRA procedural film",
        "audio": data["source"],
        "duration_seconds": data["duration_seconds"],
        "bpm": data["estimated_bpm"],
        "key": data["estimated_key"],
        "mood": data["mood_tags"],
        "visual_language": [
            "techno underground",
            "industrial",
            "cybernetic decay",
            "brutalist typography",
            "procedural motion",
        ],
        "scenes": scenes,
    }
    Path(output_path).write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    return story

from __future__ import annotations

import html
import json
from pathlib import Path


def write_html_report(analysis_path: str | Path, story_path: str | Path, output_path: str | Path) -> None:
    analysis = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    story = json.loads(Path(story_path).read_text(encoding="utf-8"))
    rows = "".join(
        f"<tr><td>{s['index']}</td><td>{s['start']:.2f}</td><td>{s['end']:.2f}</td><td>{html.escape(s['role'])}</td><td>{s['energy']:.2f}</td></tr>"
        for s in analysis["sections"]
    )
    scenes = "".join(
        f"<tr><td>{s['scene']}</td><td>{s['start']:.2f}</td><td>{s['end']:.2f}</td><td>{html.escape(s['archetype'])}</td><td>{html.escape(s['camera_mode'])}</td></tr>"
        for s in story["scenes"]
    )
    content = f"""<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>SUBTERRA report</title>
<style>body{{font-family:Arial,sans-serif;background:#0b0b0d;color:#e8e8ea;max-width:1100px;margin:40px auto;padding:0 20px}}table{{border-collapse:collapse;width:100%;margin-bottom:32px}}td,th{{border:1px solid #333;padding:8px;text-align:left}}code{{color:#b8ffdf}}.tag{{display:inline-block;background:#222;padding:5px 8px;margin:3px;border-radius:4px}}</style></head><body>
<h1>SUBTERRA — relatório do filme</h1><p><b>Áudio:</b> <code>{html.escape(analysis['source'])}</code></p>
<p><b>Duração:</b> {analysis['duration_seconds']:.2f}s · <b>BPM:</b> {analysis['estimated_bpm']:.2f} · <b>Tom:</b> {html.escape(analysis['estimated_key'])}</p>
<p>{''.join(f"<span class='tag'>{html.escape(t)}</span>" for t in analysis['mood_tags'])}</p>
<h2>Estrutura musical</h2><table><tr><th>#</th><th>Início</th><th>Fim</th><th>Função</th><th>Energia</th></tr>{rows}</table>
<h2>Plano visual</h2><p><b>Seed:</b> {story['seed']}</p><table><tr><th>#</th><th>Início</th><th>Fim</th><th>Arquétipo</th><th>Câmera</th></tr>{scenes}</table>
</body></html>"""
    Path(output_path).write_text(content, encoding="utf-8")

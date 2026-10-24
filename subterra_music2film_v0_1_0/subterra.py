from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path

from subterra.audio_analysis import analyze_audio
from subterra.config import RESOLUTION_PRESETS, RenderConfig
from subterra.hardware import diagnose, save_report
from subterra.narrative import ARCHETYPES, build_story
from subterra.renderer import render_film
from subterra.report import write_html_report


def positive_int(value: str) -> int:
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError("deve ser maior que zero")
    return n


def resolve_resolution(args: argparse.Namespace) -> tuple[int, int]:
    if args.width and args.height:
        return args.width, args.height
    return RESOLUTION_PRESETS[args.resolution]


def cmd_diagnose(args: argparse.Namespace) -> int:
    report = diagnose(args.path)
    save_report(report, args.output)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    print(f"\nRelatório salvo em: {Path(args.output).resolve()}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    summary, json_path, npz_path = analyze_audio(args.audio, args.workdir)
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    print(f"\nAnálise: {json_path.resolve()}\nFeatures: {npz_path.resolve()}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    audio = Path(args.audio)
    if not audio.exists():
        raise FileNotFoundError(f"Áudio não encontrado: {audio}")
    output = Path(args.output)
    workdir = Path(args.workdir or output.parent / f"{output.stem}_project")
    workdir.mkdir(parents=True, exist_ok=True)
    seed = args.seed if args.seed is not None else random.SystemRandom().randint(1, 2_147_483_647)
    width, height = resolve_resolution(args)

    print("[1/4] Analisando áudio...")
    summary, analysis_path, features_path = analyze_audio(audio, workdir)
    duration = min(summary.duration_seconds, args.preview_seconds) if args.preview_seconds else summary.duration_seconds

    print("[2/4] Criando narrativa procedural...")
    story_path = workdir / "story.json"
    build_story(analysis_path, seed, story_path, args.style)
    write_html_report(analysis_path, story_path, workdir / "report.html")

    cfg = RenderConfig(
        width=width,
        height=height,
        fps=args.fps,
        seed=seed,
        style=args.style,
        quality=args.quality,
        render_scale=args.render_scale,
        strobe=args.strobe,
        audio_mode=args.audio_mode,
        encoder=args.encoder,
        crf=args.crf,
        preset=args.ffmpeg_preset,
    )
    (workdir / "render_config.json").write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[3/4] Renderizando {width}x{height} @ {args.fps:g} fps | seed={seed}")
    last_pct = -1
    def progress(done: int, total: int) -> None:
        nonlocal last_pct
        pct = int(done * 100 / total)
        if pct != last_pct:
            print(f"  {pct:3d}% ({done}/{total} frames)", flush=True)
            last_pct = pct

    render_film(audio, output, features_path, story_path, cfg, duration, args.media, progress)
    print("[4/4] Finalizado.")
    print(f"Vídeo: {output.resolve()}\nProjeto: {workdir.resolve()}\nSeed: {seed}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SUBTERRA — transforma música em filme techno underground localmente.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_diag = sub.add_parser("diagnose", help="Analisa hardware, FFmpeg e espaço em disco.")
    p_diag.add_argument("--path", default=".", help="Disco/pasta de destino para checar espaço livre.")
    p_diag.add_argument("--output", default="hardware_report.json")
    p_diag.set_defaults(func=cmd_diagnose)

    p_an = sub.add_parser("analyze", help="Analisa profundamente um arquivo de áudio.")
    p_an.add_argument("audio")
    p_an.add_argument("--workdir", default="analysis_output")
    p_an.set_defaults(func=cmd_analyze)

    p = sub.add_parser("render", help="Analisa o áudio, cria uma narrativa e exporta o filme.")
    p.add_argument("audio", help="Arquivo de áudio: WAV, FLAC, MP3, M4A etc.")
    p.add_argument("output", help="Saída .mp4, .mkv ou .avi")
    p.add_argument("--media", action="append", default=[], help="Imagem/vídeo base. Pode ser repetido.")
    p.add_argument("--resolution", choices=sorted(RESOLUTION_PRESETS), default="1080p")
    p.add_argument("--width", type=positive_int)
    p.add_argument("--height", type=positive_int)
    p.add_argument("--fps", type=float, default=30.0)
    p.add_argument("--seed", type=int)
    p.add_argument("--style", choices=["auto", *ARCHETYPES], default="auto")
    p.add_argument("--quality", choices=["draft", "high"], default="high")
    p.add_argument("--render-scale", type=float, default=1.0, help="0.5 a 1.0 reduz custo interno e mantém resolução final.")
    p.add_argument("--strobe", type=float, default=0.20, help="0 a 0.45. Use 0 para desativar flashes.")
    p.add_argument("--audio-mode", choices=["preserve", "normalize"], default="preserve")
    p.add_argument("--encoder", default="libx264", choices=["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "h264_amf", "hevc_amf", "h264_qsv", "hevc_qsv"])
    p.add_argument("--crf", type=int, default=18)
    p.add_argument("--ffmpeg-preset", default="medium")
    p.add_argument("--preview-seconds", type=float, help="Renderiza apenas os primeiros N segundos para teste.")
    p.add_argument("--workdir")
    p.set_defaults(func=cmd_render)
    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

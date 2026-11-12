#!/usr/bin/env python3
"""Genera la mascota "Guante Verde" (formato Codex / petdex / OpenPets v1).

Anima el logo real del guante verde como si fuera una pegatina viva:
rebote, inclinaciones, salto con estiramiento y giro a "pulgar abajo".

Salida: atlas 8x9 de celdas 192x208 (1536x1872 px) con las 9 filas fijas
idle, running-right, running-left, waving, jumping, failed, waiting,
running y review, más frames sueltos, hoja de contactos y GIF de prueba.

Uso:
    python generar_atlas.py --logo guante-verde.webp --salida ./salida
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

CELL_W, CELL_H = 192, 208
COLS, ROWS = 8, 9
BASELINE = 200   # y donde apoya el puño del guante dentro de la celda
SPRITE_H = 150   # alto del guante en reposo
MARGIN = 2       # píxeles libres mínimos hasta el borde de la celda
PAD = 96         # lienzo extra para detectar recortes antes de cortar la celda

# Orden y duración fijados por el formato Codex/petdex (no cambiar el orden).
ROW_SPECS: tuple[tuple[str, int, int], ...] = (
    ("idle", 6, 5500),
    ("running-right", 8, 1060),
    ("running-left", 8, 1060),
    ("waving", 4, 700),
    ("jumping", 5, 840),
    ("failed", 8, 1220),
    ("waiting", 6, 1010),
    ("running", 6, 820),
    ("review", 6, 1030),
)


@dataclass(frozen=True)
class Pose:
    sx: float = 1.0          # escala horizontal
    sy: float = 1.0          # escala vertical
    angle: float = 0.0       # grados; positivo = antihorario (inclina a la izquierda)
    dx: float = 0.0          # desplazamiento horizontal en px
    dy: float = 0.0          # desplazamiento vertical en px (negativo = arriba)
    ground: bool = False     # True: gira sobre el centro y apoya el bbox en el suelo
    sat: float = 1.0         # saturación (1 = original)
    bright: float = 1.0      # brillo (1 = original)


def poses_idle(n: int) -> list[Pose]:
    return [
        Pose(
            sx=1 - 0.015 * math.sin(2 * math.pi * i / n),
            sy=1 + 0.03 * math.sin(2 * math.pi * i / n),
            angle=1.5 * math.cos(2 * math.pi * i / n),
        )
        for i in range(n)
    ]


def poses_run(n: int, direction: int) -> list[Pose]:
    """Dos saltitos por ciclo inclinado hacia la dirección; direction 1=derecha."""
    poses = []
    for i in range(n):
        h = abs(math.sin(math.pi * i / (n / 2)))
        first_hop = i < n // 2
        lean = -10 if first_hop else -6
        wobble = -3 * h if first_hop else 3 * h
        contact = h < 0.01
        poses.append(
            Pose(
                sx=1.07 if contact else 1 - 0.03 * h,
                sy=0.92 if contact else 1 + 0.04 * h,
                angle=(lean + wobble) * direction,
                dx=3 * h * direction,
                dy=-18 * h,
            )
        )
    return poses


def poses_waving(_: int) -> list[Pose]:
    return [Pose(angle=a, dy=d) for a, d in ((0, 0), (14, -4), (0, 0), (-14, -4))]


def poses_jumping(_: int) -> list[Pose]:
    return [
        Pose(sx=1.10, sy=0.86),
        Pose(sx=0.94, sy=1.08, dy=-18, angle=3),
        Pose(dy=-40, angle=6),
        Pose(sx=0.96, sy=1.05, dy=-16, angle=2),
        Pose(sx=1.08, sy=0.90),
    ]


def poses_failed(_: int) -> list[Pose]:
    angles = (0, 40, 95, 150, 180, 188, 174, 180)
    sats = (1, 1, 0.9, 0.8, 0.65, 0.55, 0.55, 0.55)
    brights = (1, 1, 1, 0.95, 0.9, 0.85, 0.85, 0.85)
    squash = ((1, 1), (1, 1), (1, 1), (1, 1), (1, 1), (1.04, 0.93), (1.02, 0.96), (1.03, 0.94))
    return [
        Pose(sx=s[0], sy=s[1], angle=a, ground=True, sat=sa, bright=b)
        for a, sa, b, s in zip(angles, sats, brights, squash)
    ]


def poses_waiting(_: int) -> list[Pose]:
    angles = (0, -9, -2, -9, 0, 2)
    return [
        Pose(angle=a, sx=1.04 if a == -9 else 1, sy=0.96 if a == -9 else 1)
        for a in angles
    ]


def poses_working(_: int) -> list[Pose]:
    dxs = (-3, 3, -3, 3, -2, 2)
    angles = (-4, 4, -5, 5, -3, 3)
    sys_ = (1, 1.03, 1, 1.03, 1, 1.02)
    return [Pose(dx=d, angle=a, sy=s, sx=2 - s) for d, a, s in zip(dxs, angles, sys_)]


def poses_review(n: int) -> list[Pose]:
    poses = []
    for i in range(n):
        c = math.cos(2 * math.pi * i / n)
        poses.append(Pose(angle=5 - 5 * c, sy=1 - 0.0075 * (1 - c)))
    return poses


POSE_BUILDERS = {
    "idle": poses_idle,
    "running-right": lambda n: poses_run(n, 1),
    "running-left": lambda n: poses_run(n, -1),
    "waving": poses_waving,
    "jumping": poses_jumping,
    "failed": poses_failed,
    "waiting": poses_waiting,
    "running": poses_working,
    "review": poses_review,
}


def load_sprite(logo: Path) -> Image.Image:
    img = Image.open(logo).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"El logo {logo} no tiene píxeles visibles")
    img = img.crop(bbox)
    scale = SPRITE_H / img.height
    size = (round(img.width * scale), SPRITE_H)
    return img.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")


def adjust_color(img: Image.Image, sat: float, bright: float) -> Image.Image:
    if sat == 1 and bright == 1:
        return img
    rgb, alpha = img.convert("RGB"), img.getchannel("A")
    rgb = ImageEnhance.Color(rgb).enhance(sat)
    rgb = ImageEnhance.Brightness(rgb).enhance(bright)
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def clear_hidden_rgb(img: Image.Image) -> Image.Image:
    """Devuelve copia con RGB a cero en píxeles 100 % transparentes (lo exige el validador)."""
    mask = img.getchannel("A").point(lambda a: 255 if a > 0 else 0)
    cleared = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cleared.paste(img, (0, 0), mask)
    return cleared


def transform(sprite: Image.Image, pose: Pose) -> tuple[Image.Image, tuple[float, float]]:
    """Escala y gira el sprite. Devuelve lienzo cuadrado y punto pivote en él."""
    w = max(1, round(sprite.width * pose.sx))
    h = max(1, round(sprite.height * pose.sy))
    scaled = sprite.convert("RGBa").resize((w, h), Image.Resampling.LANCZOS)
    pivot = (w / 2, h / 2) if pose.ground else (w / 2, h)
    side = int(2 * math.hypot(w, h)) + 4
    canvas = Image.new("RGBa", (side, side), (0, 0, 0, 0))
    center = side / 2
    canvas.paste(scaled, (round(center - pivot[0]), round(center - pivot[1])))
    rotated = canvas.rotate(pose.angle, resample=Image.Resampling.BICUBIC, center=(center, center))
    out = adjust_color(rotated.convert("RGBA"), pose.sat, pose.bright)
    return out, (center, center)


def visible_bbox(img: Image.Image, pose: Pose) -> tuple[int, int, int, int]:
    box = img.getchannel("A").getbbox()
    if box is None:
        raise ValueError(f"La pose {pose} no deja ningún píxel visible")
    return box


def render_cell(sprite: Image.Image, pose: Pose) -> tuple[Image.Image, list[int], bool]:
    """Coloca la pose en una celda. Devuelve celda, bbox en coordenadas de celda y si se recorta."""
    art, (px, py) = transform(sprite, pose)
    padded = Image.new("RGBA", (CELL_W + 2 * PAD, CELL_H + 2 * PAD), (0, 0, 0, 0))
    if pose.ground:
        art = art.crop(visible_bbox(art, pose))
        x = PAD + CELL_W / 2 + pose.dx - art.width / 2
        y = PAD + BASELINE + pose.dy - art.height
    else:
        x = PAD + CELL_W / 2 + pose.dx - px
        y = PAD + BASELINE + pose.dy - py
    padded.alpha_composite(art, (round(x), round(y)))
    x0, y0, x1, y1 = visible_bbox(padded, pose)
    bbox = [x0 - PAD, y0 - PAD, x1 - PAD, y1 - PAD]
    clipped = (
        bbox[0] < MARGIN or bbox[1] < MARGIN
        or bbox[2] > CELL_W - MARGIN or bbox[3] > CELL_H - MARGIN
    )
    cell = clear_hidden_rgb(padded.crop((PAD, PAD, PAD + CELL_W, PAD + CELL_H)))
    return cell, bbox, clipped


def build(logo: Path, out_dir: Path) -> dict:
    sprite = load_sprite(logo)
    atlas = Image.new("RGBA", (COLS * CELL_W, ROWS * CELL_H), (0, 0, 0, 0))
    report: dict[str, list[dict]] = {}
    for row, (state, frames, _) in enumerate(ROW_SPECS):
        poses = POSE_BUILDERS[state](frames)
        if len(poses) != frames:
            raise ValueError(f"{state}: {len(poses)} poses para {frames} frames")
        frame_dir = out_dir / "frames" / state
        frame_dir.mkdir(parents=True, exist_ok=True)
        report[state] = []
        for col, pose in enumerate(poses):
            cell, bbox, clipped = render_cell(sprite, pose)
            cell.save(frame_dir / f"{col:02d}.png")
            atlas.alpha_composite(cell, (col * CELL_W, row * CELL_H))
            report[state].append({"frame": col, "bbox": bbox, "recortado": clipped})
    atlas.save(out_dir / "spritesheet.png")
    atlas.save(out_dir / "spritesheet.webp", lossless=True, quality=100, method=6, exact=True)
    return report


def contact_sheet(out_dir: Path) -> None:
    atlas = Image.open(out_dir / "spritesheet.png")
    bg = Image.new("RGBA", atlas.size, (58, 58, 64, 255))
    bg.alpha_composite(atlas)
    draw = ImageDraw.Draw(bg)
    for c in range(1, COLS):
        draw.line([(c * CELL_W, 0), (c * CELL_W, bg.height)], fill=(90, 90, 98, 255))
    for r in range(ROWS):
        y = r * CELL_H
        draw.line([(0, y), (bg.width, y)], fill=(90, 90, 98, 255))
        draw.text((6, y + 4), ROW_SPECS[r][0], fill=(235, 235, 235, 255))
    qa = out_dir / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    bg.resize((bg.width // 2, bg.height // 2), Image.Resampling.LANCZOS).save(qa / "contact-sheet.png")


def previews(out_dir: Path) -> None:
    prev = out_dir / "qa" / "previews"
    prev.mkdir(parents=True, exist_ok=True)
    for state, frames, duration in ROW_SPECS:
        imgs = []
        for i in range(frames):
            cell = Image.open(out_dir / "frames" / state / f"{i:02d}.png")
            bg = Image.new("RGBA", cell.size, (58, 58, 64, 255))
            bg.alpha_composite(cell)
            imgs.append(bg.convert("RGB"))
        imgs[0].save(
            prev / f"{state}.gif", save_all=True, append_images=imgs[1:],
            duration=max(20, round(duration / frames)), loop=0,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--logo", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    if not args.logo.is_file():
        parser.error(f"No existe el logo: {args.logo}")
    args.salida.mkdir(parents=True, exist_ok=True)
    report = build(args.logo, args.salida)
    contact_sheet(args.salida)
    previews(args.salida)
    (args.salida / "qa" / "informe.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    clipped = [(s, f["frame"]) for s, fs in report.items() for f in fs if f["recortado"]]
    print(f"atlas={args.salida / 'spritesheet.webp'} frames={sum(len(v) for v in report.values())}")
    print("recortes=" + (", ".join(f"{s}#{i}" for s, i in clipped) if clipped else "ninguno"))
    return 1 if clipped else 0


if __name__ == "__main__":
    raise SystemExit(main())

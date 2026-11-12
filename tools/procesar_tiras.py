#!/usr/bin/env python3
"""Convierte tiras generadas (fondo magenta) en el atlas 8x9 del avatar de Ángel.

Cada tira es una fila de N poses sobre magenta. El script:
1. quita el fondo (croma) y limpia el borde magenta,
2. separa las N poses por columnas vacías,
3. las escala con UNA escala por fila para que el personaje mida lo mismo en todas,
4. apoya los pies en la misma línea de suelo (el salto conserva su altura),
5. monta el atlas 1536x1872 (celdas 192x208) y genera hoja de contactos y GIF.

Uso:
    python procesar_tiras.py --tiras run/higgsfield --salida salida [--medir]
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

CELL_W, CELL_H = 192, 208
COLS, ROWS = 8, 9
BASELINE = 203          # y de los pies dentro de la celda
TARGET_H = 172          # alto del personaje de pie, en px
MARGIN = 1
ALPHA_LO, ALPHA_HI = 50.0, 120.0   # distancia al croma: transparente / opaco

# (estado, frames, duración ms, origen). origen "mirror:<estado>" = espejo de otra fila.
ROW_SPECS: tuple[tuple[str, int, int, str], ...] = (
    ("idle", 6, 5500, "tira"),
    ("running-right", 8, 1060, "tira"),
    ("running-left", 8, 1060, "mirror:running-right"),
    ("waving", 4, 700, "tira"),
    ("jumping", 5, 840, "tira"),
    ("failed", 8, 1220, "tira"),
    ("waiting", 6, 1010, "tira"),
    ("running", 6, 820, "tira"),
    ("review", 6, 1030, "tira"),
)

# Cómo estimar la altura "de pie" de cada fila: (frame de referencia o None=máximo, factor).
# En el salto ningún frame está de pie: se usa el frame 1 (impulso) corregido.
ROW_REF: dict[str, tuple[int | None, float]] = {
    "jumping": (0, 1.0),     # frame 0 de pie; luego gestos de OK y saltito
    "waving": (None, 1.09),  # la mano levantada sobresale ~9 % por encima de la cabeza
    "waiting": (0, 1.0),     # frame 0 de pie; luego levanta el brazo por encima de la cabeza
    "review": (0, 1.0),      # frame 0 de pie; luego alza el puntero
}

# Tira de origen de cada fila (sin extensión). Por defecto "tira-<estado>".
ROW_SOURCE: dict[str, str] = {
    "idle": "tira-pasear",           # paseo de ida y vuelta (ver WALK_PATH)
    "running-right": "tira-coche",   # va en su coche rojo
    "jumping": "tira-ok",            # «todo OK»: seña de OK, pulgares arriba y saltito
    "waiting": "tira-levantar-mano",
    "review": "tira-puntero",        # señala con el puntero del guante verde
}

# Filas que no son una persona de pie (el coche): se escalan para caber en la celda.
ROW_FIT: dict[str, tuple[int, int]] = {"running-right": (CELL_W - 8, 150)}

# Paseo en reposo: (pose de la tira, desplazamiento x en px, mirando a la izquierda).
# Va a la derecha en 3 pasos, se gira y vuelve en 2; el bucle cierra en el frame 0.
WALK_PATH: tuple[tuple[int, int, bool], ...] = (
    (0, -36, False), (1, -12, False), (2, 12, False),
    (3, 36, True), (4, 12, True), (5, -12, True),
)


@dataclass(frozen=True)
class Pose:
    rgba: Image.Image   # recorte RGBA de la pose
    bottom: int         # y del borde inferior en la tira
    height: int


def key_color(arr: np.ndarray) -> np.ndarray:
    h, w, _ = arr.shape
    patches = [arr[:20, :20], arr[:20, w - 20:], arr[h - 20:, :20], arr[h - 20:, w - 20:]]
    return np.median(np.concatenate([p.reshape(-1, 3) for p in patches]), axis=0)


def remove_chroma(img: Image.Image) -> np.ndarray:
    """Devuelve array RGBA float [0,1] con el croma quitado y el borde sin tinte magenta."""
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    dist = np.linalg.norm(arr - key_color(arr), axis=2)
    alpha = np.clip((dist - ALPHA_LO) / (ALPHA_HI - ALPHA_LO), 0.0, 1.0)
    edge = alpha < 0.98
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    spill = np.clip(np.minimum(r, b) - g, 0, None) * edge
    rgb = np.stack([r - spill, g, b - spill], axis=2) / 255.0
    alpha = np.where(alpha < 0.08, 0.0, alpha)
    return np.dstack([rgb, alpha])


def segment(alpha: np.ndarray, n: int) -> list[tuple[int, int]]:
    """Separa n poses por columnas vacías; fusiona o parte tramos hasta tener n."""
    occ = (alpha > 0.5).sum(axis=0)
    filled = occ > 2
    segs: list[list[int]] = []
    start = None
    for x, on in enumerate(filled):
        if on and start is None:
            start = x
        elif not on and start is not None:
            segs.append([start, x - 1])
            start = None
    if start is not None:
        segs.append([start, len(filled) - 1])
    total = occ.sum()
    segs = [s for s in segs if occ[s[0]:s[1] + 1].sum() > 0.002 * total]
    while len(segs) > n:
        gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
        i = int(np.argmin(gaps))
        segs[i:i + 2] = [[segs[i][0], segs[i + 1][1]]]
    while len(segs) < n:
        i = int(np.argmax([s[1] - s[0] for s in segs]))
        x0, x1 = segs[i]
        lo, hi = x0 + (x1 - x0) // 5, x1 - (x1 - x0) // 5
        cut = lo + int(np.argmin(occ[lo:hi]))
        segs[i:i + 1] = [[x0, cut - 1], [cut + 1, x1]]
    return [(a, b) for a, b in segs]


def pose_masks(alpha: np.ndarray, n: int) -> list[np.ndarray]:
    """Asigna cada pieza (componente conexo) a la pose cuyo tramo de columnas la contiene.

    Así un guante que invade las columnas de la pose vecina sigue con su dueño.
    Una pieza demasiado ancha (dos poses tocándose) se reparte por columnas.
    """
    segs = segment(alpha, n)
    centers = np.array([(a + b) / 2 for a, b in segs])
    widths = np.array([b - a + 1 for a, b in segs])
    labels, count = ndimage.label(alpha > 0.05)
    objects = ndimage.find_objects(labels)
    masks = [np.zeros(alpha.shape, dtype=bool) for _ in segs]
    for idx, sl in enumerate(objects, start=1):
        if sl is None:
            continue
        comp = labels[sl] == idx
        if comp.sum() < 40:
            continue
        xs = np.where(comp.any(axis=0))[0] + sl[1].start
        if xs[-1] - xs[0] > 1.5 * np.median(widths):
            for k, (a, b) in enumerate(segs):
                cols = slice(max(a, sl[1].start), min(b + 1, sl[1].stop))
                if cols.start < cols.stop:
                    masks[k][sl[0], cols] |= labels[sl[0], cols] == idx
            continue
        cx = float(np.average(np.where(comp)[1])) + sl[1].start
        k = int(np.argmin(np.abs(centers - cx)))
        masks[k][sl] |= comp
    return masks


def extract_poses(path: Path, n: int) -> list[Pose]:
    rgba = remove_chroma(Image.open(path))
    poses = []
    for mask in pose_masks(rgba[..., 3], n):
        solid = mask & (rgba[..., 3] > 0.5)
        rows, cols = np.where(solid.any(axis=1))[0], np.where(solid.any(axis=0))[0]
        y0, y1, x0, x1 = int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1])
        part = rgba[y0:y1 + 1, x0:x1 + 1].copy()
        part[..., 3] *= mask[y0:y1 + 1, x0:x1 + 1]
        crop = (part * 255).round().astype(np.uint8)
        poses.append(Pose(Image.fromarray(crop, "RGBA"), y1, y1 - y0 + 1))
    return poses


def tira_path(tiras: Path, state: str) -> Path | None:
    """Ruta de la tira de un estado, en .png o .webp; None si no existe."""
    stem = ROW_SOURCE.get(state, f"tira-{state}")
    for ext in (".png", ".webp"):
        path = tiras / f"{stem}{ext}"
        if path.is_file():
            return path
    return None


def row_scale(state: str, poses: list[Pose]) -> float:
    if state in ROW_FIT:
        max_w, max_h = ROW_FIT[state]
        return min(max_w / max(p.rgba.width for p in poses), max_h / max(p.height for p in poses))
    idx, factor = ROW_REF.get(state, (None, 1.0))
    ref = poses[idx].height if idx is not None else max(p.height for p in poses)
    return TARGET_H / (ref / factor)


def torso_anchor_x(img: Image.Image) -> float:
    """Mediana x del torso (35-60 % del alto): ancla horizontal estable."""
    a = np.asarray(img.getchannel("A"))
    h = a.shape[0]
    band = a[int(h * 0.35):int(h * 0.60)] > 128
    xs = np.where(band.any(axis=0))[0]
    if xs.size == 0:
        return img.width / 2
    weights = band.sum(axis=0)[xs]
    return float(np.average(xs, weights=weights))


def clear_hidden_rgb(img: Image.Image) -> Image.Image:
    mask = img.getchannel("A").point(lambda v: 255 if v > 0 else 0)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def place(
    pose: Pose, scale: float, ground: int, dx: int = 0, flip: bool = False
) -> tuple[Image.Image, list[int], bool]:
    w, h = max(1, round(pose.rgba.width * scale)), max(1, round(pose.rgba.height * scale))
    art = pose.rgba.convert("RGBa").resize((w, h), Image.Resampling.LANCZOS).convert("RGBA")
    if flip:
        art = art.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    lift = round((ground - pose.bottom) * scale)
    y = BASELINE - lift - h
    y = max(MARGIN, y)
    x = round(CELL_W / 2 + dx - torso_anchor_x(art))
    x = min(max(x, MARGIN), CELL_W - MARGIN - w) if w <= CELL_W - 2 * MARGIN else x
    cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    cell.paste(art, (x, y), art)
    bbox = [x, y, x + w, y + h]
    clipped = x < 0 or y < 0 or x + w > CELL_W or y + h > CELL_H
    return clear_hidden_rgb(cell), bbox, clipped


def build(tiras: Path, out: Path, measure: bool) -> dict:
    atlas = Image.new("RGBA", (COLS * CELL_W, ROWS * CELL_H), (0, 0, 0, 0))
    cells: dict[str, list[Image.Image]] = {}
    report: dict[str, list[dict]] = {}
    for row, (state, frames, _, source) in enumerate(ROW_SPECS):
        if source.startswith("mirror:"):
            base = cells[source.split(":", 1)[1]]
            row_cells = [c.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for c in base]
            report[state] = [{"frame": i, "espejo_de": source[7:]} for i in range(frames)]
        else:
            path = tira_path(tiras, state)
            if path is None:
                raise FileNotFoundError(f"Falta la tira de {state} en {tiras}")
            poses = extract_poses(path, frames)
            scale = row_scale(state, poses)
            ground = max(p.bottom for p in poses)
            if measure:
                print(state, "escala=%.4f" % scale, "alturas=", [p.height for p in poses],
                      "anchos=", [p.rgba.width for p in poses])
            row_cells, report[state] = [], []
            plan = WALK_PATH if state == "idle" else tuple((i, 0, False) for i in range(frames))
            for i, (src, dx, flip) in enumerate(plan):
                cell, bbox, clipped = place(poses[src], scale, ground, dx, flip)
                row_cells.append(cell)
                report[state].append({"frame": i, "bbox": bbox, "recortado": clipped})
        cells[state] = row_cells
        frame_dir = out / "frames" / state
        frame_dir.mkdir(parents=True, exist_ok=True)
        for i, cell in enumerate(row_cells):
            cell.save(frame_dir / f"{i:02d}.png")
            atlas.alpha_composite(cell, (i * CELL_W, row * CELL_H))
    atlas.save(out / "spritesheet.png")
    atlas.save(out / "spritesheet.webp", lossless=True, quality=100, method=6, exact=True)
    return report


def qa_media(out: Path) -> None:
    qa = out / "qa"
    (qa / "previews").mkdir(parents=True, exist_ok=True)
    atlas = Image.open(out / "spritesheet.png")
    bg = Image.new("RGBA", atlas.size, (58, 58, 64, 255))
    bg.alpha_composite(atlas)
    draw = ImageDraw.Draw(bg)
    for r, (state, *_rest) in enumerate(ROW_SPECS):
        draw.line([(0, r * CELL_H), (bg.width, r * CELL_H)], fill=(90, 90, 98, 255))
        draw.line([(0, r * CELL_H + BASELINE), (bg.width, r * CELL_H + BASELINE)], fill=(80, 80, 88, 255))
        draw.text((6, r * CELL_H + 4), state, fill=(235, 235, 235, 255))
    bg.save(qa / "contact-sheet.png")
    for state, frames, duration, _ in ROW_SPECS:
        imgs = []
        for i in range(frames):
            cell = Image.open(out / "frames" / state / f"{i:02d}.png")
            frame_bg = Image.new("RGBA", cell.size, (58, 58, 64, 255))
            frame_bg.alpha_composite(cell)
            imgs.append(frame_bg.convert("RGB"))
        imgs[0].save(qa / "previews" / f"{state}.gif", save_all=True, append_images=imgs[1:],
                     duration=max(20, round(duration / frames)), loop=0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tiras", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--medir", action="store_true", help="imprime alturas y escalas por fila")
    args = parser.parse_args()
    missing = [s for s, _, _, src in ROW_SPECS if src == "tira" and tira_path(args.tiras, s) is None]
    if missing:
        parser.error("Faltan tiras: " + ", ".join(missing))
    args.salida.mkdir(parents=True, exist_ok=True)
    report = build(args.tiras, args.salida, args.medir)
    qa_media(args.salida)
    (args.salida / "qa" / "informe.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    clipped = [f"{s}#{f['frame']}" for s, fs in report.items() for f in fs if f.get("recortado")]
    print("recortes=" + (", ".join(clipped) if clipped else "ninguno"))
    return 1 if clipped else 0


if __name__ == "__main__":
    raise SystemExit(main())

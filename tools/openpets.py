#!/usr/bin/env python3
"""Prepara las mascotas para OpenPets (openpets.dev).

Subcomandos:
  actividades  crea openpets/<id>/ con pet.json + spritesheet.webp + activities/*.webp
  zip          crea dist/<id>.zip (base: 2 archivos) y dist/<id>-completo.zip (con actividades)
  validar      comprueba paquetes y ZIP con las reglas de OpenPets (portadas de
               packages/pet-format/src/{metadata,activities}.ts y docs/catalog.md)

Uso (desde la raíz del repo):
  python tools/openpets.py actividades
  python tools/openpets.py zip
  python tools/openpets.py validar
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import generar_atlas as ga
import procesar_tiras as pt
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CELL_W, CELL_H = 192, 208
ATLAS_V1 = (1536, 1872)
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
ACTIVITY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
MAX_ACTIVITY_BYTES = 2 * 1024 * 1024
MAX_ACTIVITIES_TOTAL = 16 * 1024 * 1024


@dataclass(frozen=True)
class Activity:
    id: str
    name: str
    fps: int
    frames: tuple[Image.Image, ...]


# ---------------------------------------------------------------- Ángel ----

def _travel(n_poses: int, steps: int, span: int) -> list[tuple[int, int, bool]]:
    """Ida y vuelta: `steps` frames hacia la derecha y `steps` de vuelta en espejo."""
    out = []
    for i in range(steps):
        out.append((i % n_poses, round(-span + 2 * span * i / (steps - 1)), False))
    for i in range(steps):
        out.append((i % n_poses, round(span - 2 * span * i / (steps - 1)), True))
    return out


def _angel_frames(name: str, n: int, plan: list[tuple[int, int, bool]],
                  ref: tuple[int | None, float] = (None, 1.0)) -> tuple[Image.Image, ...]:
    """Recorta la tira `name`, la escala al alto del atlas y coloca cada frame del plan."""
    poses = pt.extract_poses(ROOT / "fuentes" / "angel-gaitan" / f"{name}.webp", n)
    idx, factor = ref
    height = poses[idx].height if idx is not None else max(p.height for p in poses)
    scale = pt.TARGET_H / (height / factor)
    ground = max(p.bottom for p in poses)
    frames = []
    for src, dx, flip in plan:
        cell, _, clipped = pt.place(poses[src], scale, ground, dx, flip)
        if clipped:
            raise ValueError(f"{name}: un frame se sale de la celda (dx={dx})")
        frames.append(cell)
    return tuple(frames)


def angel_activities() -> list[Activity]:
    return [
        Activity("pasear", "Pasear", 8,
                 _angel_frames("extra-pasear", 6, _travel(6, 8, 46))),
        Activity("trotar", "Trotar", 10,
                 _angel_frames("tira-running-right", 8, _travel(8, 8, 46))),
        Activity("pulgar-arriba", "Pulgar arriba", 5,
                 _angel_frames("extra-salto-pulgar", 5, [(i, 0, False) for i in range(5)], (1, 0.93))),
        Activity("pensar", "Pensar", 5,
                 _angel_frames("extra-pensar", 6, [(i, 0, False) for i in (0, 1, 2, 3, 4, 5, 4, 3, 2, 1)])),
        Activity("preguntar", "Preguntar", 4,
                 _angel_frames("extra-preguntar", 6, [(i, 0, False) for i in range(6)])),
    ]


# --------------------------------------------------------------- Guante ----

def _glove_frames(poses: list[ga.Pose]) -> tuple[Image.Image, ...]:
    sprite = ga.load_sprite(ROOT / "tools" / "guante-verde-logo.webp")
    frames = []
    for pose in poses:
        cell, _, clipped = ga.render_cell(sprite, pose)
        if clipped:
            raise ValueError(f"guante: un frame se sale de la celda ({pose})")
        frames.append(cell)
    return tuple(frames)


def glove_activities() -> list[Activity]:
    saltitos = []
    for i in range(16):
        forward = i < 8
        k = i if forward else i - 8
        dx = -28 + 56 * k / 7 if forward else 28 - 56 * k / 7
        hop = abs(math.sin(math.pi * k / 2))
        saltitos.append(ga.Pose(angle=-8 if forward else 8, dx=dx, dy=-12 * hop,
                                sx=1.05 - 0.07 * hop, sy=0.94 + 0.09 * hop))
    baile = []
    for i in range(12):
        t = 2 * math.pi * i / 12
        baile.append(ga.Pose(angle=12 * math.sin(2 * t), dx=6 * math.sin(t),
                             sx=1 - 0.04 * math.sin(4 * t), sy=1 + 0.06 * math.sin(4 * t)))
    voltereta = [ga.Pose(angle=360 * i / 12, ground=True, dy=-28 * math.sin(math.pi * i / 12))
                 for i in range(12)]
    return [
        Activity("saltitos", "Saltitos", 8, _glove_frames(saltitos)),
        Activity("baile", "Baile", 10, _glove_frames(baile)),
        Activity("voltereta", "Voltereta", 12, _glove_frames(voltereta)),
    ]


# ---------------------------------------------------------- empaquetado ----

def write_package(pet_id: str, activities: list[Activity]) -> Path:
    src = ROOT / "pets" / pet_id
    out = ROOT / "openpets" / pet_id
    act_dir = out / "activities"
    if act_dir.exists():
        for old in act_dir.glob("*.webp"):
            old.unlink()
    act_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src / "spritesheet.webp", out / "spritesheet.webp")
    meta = json.loads((src / "pet.json").read_text(encoding="utf-8"))
    entries = []
    for act in activities:
        strip = Image.new("RGBA", (CELL_W * len(act.frames), CELL_H), (0, 0, 0, 0))
        for i, frame in enumerate(act.frames):
            strip.alpha_composite(frame, (i * CELL_W, 0))
        strip = pt.clear_hidden_rgb(strip)
        strip.save(act_dir / f"{act.id}.webp", lossless=True, quality=100, method=6, exact=True)
        entries.append({
            "id": act.id, "displayName": act.name, "outfitId": "default",
            "spritesheetPath": f"activities/{act.id}.webp",
            "frameCount": len(act.frames), "fps": act.fps,
        })
    full_meta = {**meta, "activities": entries}
    (out / "pet.json").write_text(json.dumps(full_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def build_zips() -> list[Path]:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    made = []
    for pkg in sorted((ROOT / "openpets").iterdir()):
        if not pkg.is_dir():
            continue
        pet_id = pkg.name
        base = dist / f"{pet_id}.zip"
        with zipfile.ZipFile(base, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(ROOT / "pets" / pet_id / "pet.json", f"{pet_id}/pet.json")
            zf.write(ROOT / "pets" / pet_id / "spritesheet.webp", f"{pet_id}/spritesheet.webp")
        full = dist / f"{pet_id}-completo.zip"
        with zipfile.ZipFile(full, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(pkg.rglob("*")):
                if f.is_file():
                    zf.write(f, f"{pet_id}/{f.relative_to(pkg).as_posix()}")
        made += [base, full]
    return made


# ------------------------------------------------------------- validar ----

def _check_meta(meta: dict, folder: str) -> list[str]:
    errs = []
    if not isinstance(meta.get("id"), str) or meta["id"] != folder or not ID_RE.match(meta["id"]):
        errs.append("id inválido o distinto del nombre de carpeta")
    if not isinstance(meta.get("displayName"), str) or not meta["displayName"].strip() or len(meta["displayName"]) > 80:
        errs.append("displayName inválido (1-80)")
    if not isinstance(meta.get("description"), str) or not meta["description"].strip() or len(meta["description"]) > 500:
        errs.append("description inválida (1-500)")
    if meta.get("spritesheetPath") != "spritesheet.webp":
        errs.append("spritesheetPath debe ser spritesheet.webp")
    if "spriteVersionNumber" in meta and meta["spriteVersionNumber"] != 2:
        errs.append("spriteVersionNumber solo puede ser 2")
    return errs


def _check_activity(a: dict, files: dict[str, bytes]) -> tuple[list[str], int]:
    aid = str(a.get("id", ""))
    errs = []
    if not 1 <= len(str(a.get("displayName", "")).strip()) <= 40:
        errs.append(f"{aid}: displayName 1-40")
    if a.get("outfitId") != "default":
        errs.append(f"{aid}: outfitId debe ser default")
    path = f"activities/{aid}.webp"
    if a.get("spritesheetPath") != path:
        errs.append(f"{aid}: spritesheetPath debe ser {path}")
    n, fps = a.get("frameCount"), a.get("fps")
    if not isinstance(n, int) or not 4 <= n <= 32 or not isinstance(fps, int) or not 1 <= fps <= 12:
        return errs + [f"{aid}: frameCount 4-32 y fps 1-12"], 0
    if not 1000 <= n * 1000 / fps <= 12000:
        errs.append(f"{aid}: duración {n * 1000 / fps:.0f} ms fuera de 1000-12000")
    data = files.get(path)
    if data is None:
        return errs + [f"{aid}: falta {path}"], 0
    if len(data) > MAX_ACTIVITY_BYTES:
        errs.append(f"{aid}: {len(data)} bytes > 2 MiB")
    img = Image.open(io.BytesIO(data))
    if img.format != "WEBP" or getattr(img, "n_frames", 1) != 1:
        errs.append(f"{aid}: debe ser WebP estático")
    if img.size != (CELL_W * n, CELL_H):
        errs.append(f"{aid}: tamaño {img.size} != {(CELL_W * n, CELL_H)}")
    return errs, len(data)


def _check_activities(meta: dict, files: dict[str, bytes]) -> list[str]:
    acts = meta.get("activities", [])
    if not isinstance(acts, list) or len(acts) > 16:
        return ["activities debe ser una lista de 16 como máximo"]
    errs, total, ids = [], 0, set()
    for a in acts:
        aid = a.get("id", "")
        if not ACTIVITY_ID_RE.match(str(aid)) or aid in ids:
            errs.append(f"actividad {aid!r}: id inválido o repetido")
        ids.add(aid)
        found, size = _check_activity(a, files)
        errs += found
        total += size
    if total > MAX_ACTIVITIES_TOTAL:
        errs.append("actividades > 16 MiB en total")
    extra = {p for p in files if p.startswith("activities/")} - {f"activities/{i}.webp" for i in ids}
    if extra:
        errs.append(f"archivos de actividad no declarados: {sorted(extra)}")
    return errs


def _check_files(files: dict[str, bytes], folder: str, full: bool) -> list[str]:
    if "pet.json" not in files:
        return ["falta pet.json"]
    meta = json.loads(files["pet.json"])
    errs = _check_meta(meta, folder)
    sheet = files.get("spritesheet.webp")
    if sheet is None:
        errs.append("falta spritesheet.webp")
    elif Image.open(io.BytesIO(sheet)).size != ATLAS_V1:
        errs.append(f"el atlas debe medir {ATLAS_V1}")
    others = set(files) - {"pet.json", "spritesheet.webp"}
    if full:
        return errs + _check_activities(meta, files)
    if others:
        errs.append(f"el ZIP base solo puede tener 2 archivos; sobran {sorted(others)}")
    if "activities" in meta or "wardrobe" in meta:
        errs.append("el pet.json del ZIP base no puede declarar activities ni wardrobe")
    return errs


def _zip_files(path: Path) -> tuple[dict[str, bytes], str]:
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        tops = {n.split("/")[0] for n in names}
        if len(tops) == 1 and all("/" in n for n in names):
            top = tops.pop()
            return {n[len(top) + 1:]: zf.read(n) for n in names}, top
        return {n: zf.read(n) for n in names}, path.stem.removesuffix("-completo")


def validate() -> int:
    problems = 0
    for pkg in sorted((ROOT / "openpets").iterdir()):
        if pkg.is_dir():
            files = {f.relative_to(pkg).as_posix(): f.read_bytes() for f in pkg.rglob("*") if f.is_file()}
            errs = _check_files(files, pkg.name, full=True)
            print(f"carpeta openpets/{pkg.name}: {'OK' if not errs else errs}")
            problems += len(errs)
    for z in sorted((ROOT / "dist").glob("*.zip")):
        files, folder = _zip_files(z)
        errs = _check_files(files, folder, full=z.stem.endswith("-completo"))
        print(f"zip {z.name}: {'OK' if not errs else errs}")
        problems += len(errs)
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("comando", choices=("actividades", "zip", "validar"))
    args = parser.parse_args()
    if args.comando == "actividades":
        for pet_id, acts in (("angel-gaitan", angel_activities()), ("guante-verde", glove_activities())):
            out = write_package(pet_id, acts)
            print(f"{out.relative_to(ROOT)}: " + ", ".join(f"{a.id}({len(a.frames)}f@{a.fps})" for a in acts))
        return 0
    if args.comando == "zip":
        for z in build_zips():
            print(f"{z.relative_to(ROOT)} {z.stat().st_size // 1024} KiB")
        return 0
    return validate()


if __name__ == "__main__":
    sys.exit(main())

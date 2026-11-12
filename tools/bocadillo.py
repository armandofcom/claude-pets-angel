"""Bocadillo de cómic con texto para las celdas de las mascotas (p. ej. «¡Hola, compañero!»).

Se dibuja a 3x y se reduce, para que el borde y el texto salgan suaves a 192x208.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SUPERSAMPLE = 3
WHITE = (255, 255, 255, 255)
BLACK = (17, 17, 17, 255)
FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",          # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/ariblk.ttf",                                  # Windows
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",         # Linux
)


@dataclass(frozen=True)
class Bubble:
    lines: tuple[str, ...]              # texto, una entrada por línea
    box: tuple[int, int, int, int]      # x0, y0, x1, y1 del globo en la celda
    tail: tuple[int, int]               # punta de la cola (hacia la boca o la cabeza)
    max_font: int = 15                  # tamaño máximo; se reduce si no cabe


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    raise FileNotFoundError("No hay fuente para el bocadillo: instala Arial Black o DejaVu Sans")


def _fit_font(draw: ImageDraw.ImageDraw, bubble: Bubble) -> tuple[ImageFont.FreeTypeFont, int]:
    """Mayor fuente (a escala 3x) cuyas líneas caben dentro del globo con margen."""
    x0, y0, x1, y1 = bubble.box
    inner_w = (x1 - x0 - 14) * SUPERSAMPLE
    inner_h = (y1 - y0 - 10) * SUPERSAMPLE
    for size in range(bubble.max_font, 7, -1):
        font = load_font(size * SUPERSAMPLE)
        widths = [draw.textlength(line, font=font) for line in bubble.lines]
        line_h = int(size * SUPERSAMPLE * 1.08)
        if max(widths) <= inner_w and line_h * len(bubble.lines) <= inner_h:
            return font, line_h
    font = load_font(8 * SUPERSAMPLE)
    return font, int(8 * SUPERSAMPLE * 1.08)


def draw_bubble(cell: Image.Image, bubble: Bubble) -> Image.Image:
    """Devuelve una copia de la celda con el bocadillo encima."""
    s = SUPERSAMPLE
    layer = Image.new("RGBA", (cell.width * s, cell.height * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = (v * s for v in bubble.box)
    tx, ty = (v * s for v in bubble.tail)
    base_x = x0 + (x1 - x0) // 5
    stroke = 3 * s
    draw.polygon([(base_x - 5 * s, y1 - s), (base_x + 9 * s, y1 - s), (tx, ty)],
                 fill=WHITE, outline=BLACK, width=stroke)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=14 * s, fill=WHITE, outline=BLACK, width=stroke)
    draw.polygon([(base_x - 2 * s, y1 - 2 * s), (base_x + 6 * s, y1 - 2 * s), (tx, ty)], fill=WHITE)
    draw.line([(base_x - 2 * s, y1 - stroke // 2), (base_x + 6 * s, y1 - stroke // 2)], fill=WHITE, width=stroke)
    font, line_h = _fit_font(draw, bubble)
    total_h = line_h * len(bubble.lines)
    cy = (y0 + y1) // 2 - total_h // 2
    for i, line in enumerate(bubble.lines):
        width = draw.textlength(line, font=font)
        draw.text(((x0 + x1) / 2 - width / 2, cy + i * line_h), line, font=font, fill=BLACK)
    small = layer.resize(cell.size, Image.Resampling.LANCZOS)
    out = cell.copy()
    out.alpha_composite(small)
    return out

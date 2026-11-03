"""Laying out one sheet: for each window a time ruler, the waveform, the spectrogram, and one row of labelled boxes per source, all on one time axis where a column is a time."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1500
WAVE_H = 70
SPECTRUM_H = 200
ROW_H = 24
RULER_H = 18
GAP = 10
COLOURS = [(90, 200, 120), (240, 180, 70), (230, 110, 200), (110, 170, 255)]
GRID = (255, 255, 0)
# Word boxes may hold Hangul, which Pillow's default face lacks.
HANGUL_FACE = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def _font():
    try:
        return ImageFont.truetype(HANGUL_FACE, 13)
    except OSError:
        return ImageFont.load_default(size=13)


@dataclass
class Row:
    source: str
    items: list[dict]


@dataclass
class Window:
    start: float
    end: float
    wave: Path
    spectrum: Path
    rows: list[Row]


def _clipped(text: str, room: float, font) -> str:
    """What fits inside a box; a box too narrow for one character stays empty, since a letter spilling over would read as the next word's."""
    while text and font.getlength(text) > room:
        text = text[:-1]
    return text


def _draw_row(draw: ImageDraw.ImageDraw, row: Row, colour: tuple, y: int, x_of, font) -> None:
    for item in row.items:
        x0, x1 = max(x_of(item["start"]), 0), min(x_of(item["end"]), WIDTH - 1)
        draw.rectangle((x0, y + 2, max(x1, x0), y + ROW_H - 3), outline=colour)
        draw.text((x0 + 2, y + 3), _clipped(item["text"], x1 - x0 - 3, font), fill=colour, font=font)
    label = row.source
    width = font.getlength(label) + 8
    draw.rectangle((WIDTH - width, y + 2, WIDTH - 1, y + ROW_H - 3), fill=(40, 40, 46))
    draw.text((WIDTH - width + 4, y + 3), label, fill=colour, font=font)


def compose(windows: list[Window], out: Path) -> list[dict]:
    """Writes the sheet and returns each window's panels as y ranges, `[top, bottom)` in sheet pixels."""
    height = sum(RULER_H + WAVE_H + SPECTRUM_H + ROW_H * len(w.rows) + GAP for w in windows)
    sheet = Image.new("RGB", (WIDTH, height), (16, 16, 20))
    draw = ImageDraw.Draw(sheet)
    font = _font()
    places = []
    y = 0
    for w in windows:
        def x_of(t: float, w=w) -> int:
            return round((t - w.start) / (w.end - w.start) * WIDTH)

        wave_y = y + RULER_H
        spectrum_y = wave_y + WAVE_H
        rows_y = spectrum_y + SPECTRUM_H
        bottom = rows_y + ROW_H * len(w.rows)
        sheet.paste(Image.open(w.wave).convert("RGB"), (0, wave_y))
        sheet.paste(Image.open(w.spectrum).convert("RGB"), (0, spectrum_y))
        step = 1 if w.end - w.start <= 20 else 5
        t = math.ceil(w.start)
        while t <= w.end:
            x = x_of(t)
            draw.line((x, y + RULER_H - 4, x, bottom - 1), fill=GRID)
            if t % step == 0:
                draw.text((x + 2, y + 1), f"{t}s", fill=GRID, font=font)
            t += 1
        for k, row in enumerate(w.rows):
            _draw_row(draw, row, COLOURS[k % len(COLOURS)], rows_y + k * ROW_H, x_of, font)
        places.append({"wave": [wave_y, spectrum_y], "spectrum": [spectrum_y, rows_y], "rows": [rows_y, bottom]})
        y = bottom + GAP
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return places

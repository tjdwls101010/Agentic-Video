"""The contact sheet."""

from __future__ import annotations

from pathlib import Path

SHEET = "contact-sheet.html"
STAMP = ".sheet-stamp.js"


def publish(folder: Path) -> Path:
    return folder / SHEET

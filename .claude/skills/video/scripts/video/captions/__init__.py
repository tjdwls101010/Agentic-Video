"""Captions laid out to the subtitle rules and to the width FilmCraft will burn them at: from the active sequence's transcript (words already in sequence time), from a transcript line with no project (words in media time), or from cues written elsewhere such as a translation. Writes SubRip for captions.import."""

from __future__ import annotations

import shlex
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from video import subrip
from video.errors import InputError
from video.filmcraft import Source, read_transcript_line, read_words
from video.subrip import Cue
from video.timecode import Rate, seconds

from .fonts import measure_for
from .layout import Word, layout, relayout, violations
from .rules import HELP, RULE_PROFILES, Rules, units

__all__ = ["Word", "Cue", "Rules", "RULE_PROFILES", "units", "layout", "relayout", "violations", "make", "HELP", "DEFAULT_FONT", "style_defaults"]

DEFAULT_FONT = "Apple SD Gothic Neo"


def style_defaults(width: int, height: int) -> dict:
    """Landscape: size 54 at the bottom, 8 % up. Vertical: size 40, raised to 40 % so two lines clear every platform's bottom UI and the Reels corner block (see frames --help)."""
    if height > width:
        return {"size": 40.0, "margin": 0.40}
    return {"size": 54.0, "margin": 0.08}


def make(out: Path, *, project: Path | None = None, bridge: str | None = None, cues_file: Path | None = None, transcript: Path | None = None, fps: float | None = None, frame: tuple[int, int] | None = None,
         font: str | None = None, size: float | None = None, margin: float | None = None, anchor: str = "bottom", profile: str = "ko", lines: int | None = None, cps: float | None = None,
         min_s: float | None = None, max_s: float | None = None) -> dict:
    """Rules start from `profile`; each of `lines`, `cps`, `min_s`, `max_s` given replaces that one value."""
    chosen = {k: v for k, v in {"lines": lines, "cps": cps, "min_s": min_s, "max_s": max_s}.items() if v is not None}
    rules = replace(RULE_PROFILES[profile], **chosen)
    notes: list[str] = []
    if cues_file is None and transcript is None:
        source = Source(project=project, bridge=bridge)
        seq, seq_words = read_words(source)
        if not seq_words:
            raise InputError("the active sequence has no transcript words; apply one with transcribe first (transcript.set)")
        rate, (w, h) = seq.rate, (seq.width, seq.height)
        words = [Word(x.text, seconds(x.start), seconds(x.end), x.speaker, x.clip) for x in seq_words]
    else:
        rate = Rate.parse(str(fps or 30))
        w, h = frame or (1920, 1080)
        if fps is None:
            notes.append("no --fps: cue times aligned to 30 fps; FilmCraft snaps them to the sequence rate on import")
        if transcript is not None:
            words = [Word(x.text, x.start, x.end, x.speaker) for x in read_transcript_line(transcript)]
            if not words:
                raise InputError(f"{transcript}: the transcript has no words")
    d = style_defaults(w, h)
    style = {"font": font or DEFAULT_FONT, "size": float(size if size is not None else d["size"]), "margin": float(margin if margin is not None else d["margin"]), "anchor": anchor}
    m = measure_for(style["font"], style["size"], w, h)
    if m.source == "estimate":
        notes.append(f"no installed face of {style['font']!r} found; line widths estimated, so check a render (frames --project)")
    fr = Fraction(rate.num, rate.den)
    result = relayout(subrip.read(cues_file), rules, fr, m.fits) if cues_file is not None else layout(words, rules, fr, m.fits)
    subrip.write(result, out)
    # in the app, the edit lands in the open project and saving it stays the user's call (an untitled project would open a save dialog)
    where = f"--project {shlex.quote(str(project))} --save" if project is not None else f"--bridge {shlex.quote(bridge)}" if bridge else "--project <P.fcproj> --save"
    style_args = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in style.items())
    return {
        "cues": len(result),
        "style": style,
        "max_line_units": min(rules.max_units, m.units_per_line()),
        "width": {"source": m.source, "face": m.face, "px": round(m.px, 1), "max_line_px": round(m.max_px)},
        "violations": violations(result, rules, m.fits),
        "out": str(out),
        "notes": notes,
        "next": [str(out)] if transcript is not None else [
            f"filmcraft-cli {where} exec captions.import path={shlex.quote(str(out))}",
            f"filmcraft-cli {where} exec captions.setStyle track=<track from the import result> {style_args}"],
    }

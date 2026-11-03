"""Looking at the sound, since it cannot be heard: stretches of a media file's audio drawn as a waveform and a spectrogram, with transcripts or captions as boxes on the same time axis, and the same speech measurement `transcribe` uses in numbers."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

from video import ffmpeg, subrip
from video.errors import InputError
from video.filmcraft import read_transcript_line
from video.timecode import Rate

from .sheet import WIDTH, SPECTRUM_H, WAVE_H, Row, Window, compose

__all__ = ["sheet", "MAX_WINDOWS", "MAX_WINDOW_SECONDS", "MAX_SOURCES"]

MAX_WINDOWS = 8
MAX_WINDOW_SECONDS = 60
MAX_SOURCES = 4
PAST_END = 0.05


def _time(text: str, rate: Rate) -> float:
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return rate.seconds_of(rate.frame_of_timecode(text))
    except ValueError:
        raise InputError(f"--at: {text!r} is neither seconds (12.5) nor a timecode (00:00:12:15)") from None


def _windows(at: list[str], rate: Rate, seconds: float | None) -> list[tuple[float, float]]:
    if len(at) > MAX_WINDOWS:
        raise InputError(f"{len(at)} windows asked for; a sheet holds {MAX_WINDOWS}")
    out = []
    for text in at:
        parts = text.split("-")
        if len(parts) != 2:
            raise InputError(f"--at: {text!r} is not a window such as 137.5-140")
        a, b = _time(parts[0], rate), _time(parts[1], rate)
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a < b):
            raise InputError(f"--at: {text!r} must start before it ends")
        if b - a > MAX_WINDOW_SECONDS:
            raise InputError(f"--at: {text!r} is {b - a:.0f} s; a window shows at most {MAX_WINDOW_SECONDS} s, beyond which words stop being readable")
        if seconds is not None and b > seconds + PAST_END:
            raise InputError(f"--at: {text!r} runs past the end of the media at {seconds:.2f} s")
        out.append((a, b))
    return out


def _items(path: Path) -> list[dict]:
    """One format for transcripts and one for captions; a raw engine reply becomes the first with `transcribe --from-json`."""
    if path.suffix.lower() == ".srt":
        return [{"text": " ".join(c.lines), "start": round(c.start, 3), "end": round(c.end, 3)} for c in subrip.read(path)]
    return [{"text": w.text, "start": round(w.start, 3), "end": round(w.end, 3)} for w in read_transcript_line(path)]


def sheet(media: Path, at: list[str], words: list[Path], out: Path) -> dict:
    info = ffmpeg.probe(media)
    if not info.audio:
        raise InputError(f"{media}: no audio stream")
    if len(words) > MAX_SOURCES:
        raise InputError(f"{len(words)} --words files asked for; a sheet compares at most {MAX_SOURCES}")
    fps = info.video[0].fps if info.video and info.video[0].fps else None
    rate = Rate(fps.numerator, fps.denominator) if fps else Rate(30)
    windows = _windows(at, rate, info.duration)
    sources = [(path.name, _items(path)) for path in words]
    speech = ffmpeg.measured_speech(media)
    notes: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        drawn = []
        for k, (a, b) in enumerate(windows):
            rows = [Row(name, [i for i in items if i["end"] > a and i["start"] < b]) for name, items in sources]
            notes += [f"{row.source} has nothing in {a:g}-{b:g} s: it may belong to other media" for row in rows if not row.items]
            drawn.append(Window(a, b, ffmpeg.wave_picture(media, a, b, WIDTH, WAVE_H, Path(tmp) / f"w{k}.png"), ffmpeg.spectrum_picture(media, a, b, WIDTH, SPECTRUM_H, Path(tmp) / f"s{k}.png"), rows))
        places = compose(drawn, out)
    return {
        "sheet": str(out), "width": WIDTH,
        "windows": [{"start": w.start, "end": w.end, "y": y, "speech": [[round(max(s, w.start), 3), round(min(e, w.end), 3)] for s, e in speech if e > w.start and s < w.end],
                     "rows": [{"source": r.source, "items": r.items} for r in w.rows]} for w, y in zip(drawn, places)],
        "notes": notes,
    }

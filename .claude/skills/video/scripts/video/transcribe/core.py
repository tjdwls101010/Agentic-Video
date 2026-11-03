"""Word edges against measured speech: which speech each word belongs to, moving edges onto it when that helps, and the tidying every transcript gets. Pure: lists in, lists out."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass
class Word:
    text: str
    start: float
    end: float
    prob: float | None = 1.0
    segment: int = -1
    speaker: int | None = None


def _normalized(words: list[Word]) -> list[Word]:
    out = sorted((replace(w, text=w.text.strip(), end=max(w.end, w.start)) for w in words if w.text.strip()), key=lambda w: (w.start, w.end))
    for i in range(1, len(out)):
        if out[i - 1].end > out[i].start:
            out[i - 1].end = max(out[i].start, out[i - 1].start)
    return out


def _owners(ws: list[Word], spans: list[tuple[float, float]]) -> list[int | None]:
    """The speech span each word overlaps most; a zero-length word belongs to the span its start is in."""
    owner: list[int | None] = []
    for w in ws:
        best, best_ov = None, 0.0
        for k, (a, b) in enumerate(spans):
            if w.start == w.end:
                if a <= w.start < b:
                    best = k
                continue
            ov = min(w.end, b) - max(w.start, a)
            if ov > best_ov:
                best, best_ov = k, ov
        owner.append(best)
    return owner


def _tidied(words: list[Word], min_dur: float) -> None:
    """Every word starts no earlier than the previous one ends and lasts at least `min_dur`, so every word stays selectable by frame-based cuts (FilmCraft itself accepts shorter words)."""
    prev_end = float("-inf")
    for w in words:
        w.start = max(w.start, prev_end)
        w.end = max(w.end, w.start + min_dur)
        prev_end = w.end


def keep_times(words: list[Word], spans: list[tuple[float, float]], min_dur: float) -> tuple[list[Word], dict]:
    """No edge moves onto speech; words are still put in order, kept from overlapping and given a minimum length, and the ones over no speech are still reported."""
    ws = _normalized(words)
    owner = _owners(ws, spans)
    out = [replace(w) for w in ws]
    _tidied(out, min_dur)
    return out, {"snapped": 0, "unmatched": [i for i, k in enumerate(owner) if k is None]}


def snap(words: list[Word], spans: list[tuple[float, float]], max_shift: float, min_dur: float) -> tuple[list[Word], dict]:
    """Each word belongs to the speech span it overlaps most. An edge Whisper put in silence moves inward to the span edge (it stays inside the word, so order cannot break); the first word of a span may start earlier, and the last may end later, by at most `max_shift`. A word overlapping no speech keeps its edges and is reported. Last, every word (reported ones included) is tidied."""
    ws = _normalized(words)
    owner = _owners(ws, spans)
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    for i, k in enumerate(owner):
        if k is not None:
            first.setdefault(k, i)
            last[k] = i
    out: list[Word] = []
    for i, (w, k) in enumerate(zip(ws, owner)):
        if k is None:
            out.append(replace(w))
            continue
        a, b = spans[k]
        s, e = w.start, w.end
        if s < a < e:
            s = a
        elif a < s and first[k] == i and s - a <= max_shift:
            s = a
        if s < b < e:
            e = b
        elif e < b and last[k] == i and b - e <= max_shift:
            e = b
        out.append(replace(w, start=s, end=e))
    _tidied(out, min_dur)
    snapped = sum(1 for a, b in zip(ws, out) if abs(a.start - b.start) > 1e-6 or abs(a.end - b.end) > 1e-6)
    return out, {"snapped": snapped, "unmatched": [i for i, k in enumerate(owner) if k is None]}

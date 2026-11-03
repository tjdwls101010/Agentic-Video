"""Where to split a recording too long for one request. Pure: numbers in, numbers out."""

from __future__ import annotations

import math

# The provider documents a limit of 25 MB on JSON requests for most routes.
MAX_BASE64 = 24_000_000
UNEVEN_BITRATE = 0.9
# A piece this short is a request of its own that a provider may refuse, so it stays with the piece before it.
MIN_TAIL = 1.0


def auto_chunk(size: int, seconds: float) -> float | None:
    """The piece length that keeps each request under the limit when a file of `size` bytes is too big to send whole, or None when it fits: the limit's share of the length, less a tenth because the bitrate is not even."""
    encoded = math.ceil(size / 3) * 4
    if encoded <= MAX_BASE64:
        return None
    return seconds * MAX_BASE64 / encoded * UNEVEN_BITRATE


def chunk_limit(chunk: float | None, size: int, seconds: float) -> float | None:
    """The longest piece to send: what was asked for, but never more than fits one request; None when the whole file can go."""
    fits = auto_chunk(size, seconds)
    return min(chunk, fits) if chunk is not None and fits is not None else chunk if fits is None else fits


def plan_chunks(duration: float, spans: list[tuple[float, float]], limit: float, window: float = 30.0) -> tuple[list[tuple[float, float]], int]:
    """Consecutive pieces no longer than `limit` (the last may run a second over, rather than leave a sliver), and how many cuts had no silence to land in. Each cut goes in the middle of the longest silence in the last `window` seconds before the limit (and never in the first half of a piece, so a piece cannot end right after it starts); with no silence there, or none measured at all, the cut is at the limit."""
    edges = [0.0, *(t for span in spans for t in span), duration]
    # no spans means the level never varied (continuous music or tone), not that all of it is silent
    silences = [(edges[i], edges[i + 1]) for i in range(0, len(edges) - 1, 2)] if spans else []
    chunks: list[tuple[float, float]] = []
    start, forced = 0.0, 0
    while duration - start > limit + MIN_TAIL:
        end = start + limit
        lo = max(start + limit / 2, end - window)
        best, longest = None, 0.0
        for a, b in silences:
            a, b = max(a, lo), min(b, end)
            if b - a > longest:
                best, longest = (a + b) / 2, b - a
        if best is None:
            best, forced = end, forced + 1
        chunks.append((start, best))
        start = best
    chunks.append((start, duration))
    return chunks, forced

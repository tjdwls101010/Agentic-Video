"""The level of a media file's sound over time: RMS in dBFS per short window, from the first audio stream mixed to mono, and where speech is from that level."""

from __future__ import annotations

import math
import subprocess
from array import array
from pathlib import Path

from video.errors import InputError, ToolError

from .probe import FROM_CONTAINER_START, tool

RATE = 16000
FLOOR_DB = -100.0
MEASURE_HOP = 0.01


def envelope(path: Path, hop: float = 0.01) -> list[float]:
    """One value per `hop` seconds from the start; digital silence reads as -100 dBFS."""
    cmd = [tool("ffmpeg"), "-v", "error", "-i", str(path), "-map", "0:a:0", "-af", FROM_CONTAINER_START, "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=3600)
    if r.returncode != 0:
        msg = r.stderr.decode(errors="replace")
        if "matches no streams" in msg or "Stream map" in msg:
            raise InputError(f"{path}: no audio stream")
        raise ToolError(f"ffmpeg could not decode the audio of {path}", msg, cmd)
    pcm = array("f")
    pcm.frombytes(r.stdout[: len(r.stdout) // 4 * 4])
    n = max(1, round(hop * RATE))
    out = []
    for i in range(0, len(pcm), n):
        chunk = pcm[i:i + n]
        ms = sum(x * x for x in chunk) / len(chunk)
        out.append(10 * math.log10(ms) if ms > 1e-10 else FLOOR_DB)
    return out


def speech_spans(env_db: list[float], hop: float, min_gap: float = 0.12, min_span: float = 0.08) -> list[tuple[float, float]]:
    """Stretches louder than a threshold set 30 % of the way from the noise floor (10th percentile, at least -70 dBFS) to the speech level (95th), joined across dips shorter than `min_gap`. Under continuous music nothing drops below the threshold, so speech comes back as one long stretch and only its outer edges can snap."""
    if not env_db:
        return []
    ordered = sorted(env_db)
    # digital silence would put the floor at -100 dBFS and the threshold among resampler ringing; nothing below -70 is audible speech
    floor = max(ordered[int(0.10 * (len(ordered) - 1))], -70.0)
    peak = ordered[int(0.95 * (len(ordered) - 1))]
    if peak - floor < 6:
        return []
    threshold = floor + 0.3 * (peak - floor)
    runs: list[list[int]] = []
    for i, v in enumerate(env_db):
        if v > threshold:
            if runs and i - runs[-1][1] - 1 < round(min_gap / hop):
                runs[-1][1] = i
            else:
                runs.append([i, i])
    return [(a * hop, (b + 1) * hop) for a, b in runs if (b + 1 - a) * hop >= min_span]


def measured_speech(path: Path) -> tuple[list[tuple[float, float]], float]:
    """Where a media file has speech, by the one measurement `transcribe` and `waveform` both report, and how long its sound runs, which a file may not record."""
    level = envelope(path, MEASURE_HOP)
    return speech_spans(level, MEASURE_HOP), len(level) * MEASURE_HOP

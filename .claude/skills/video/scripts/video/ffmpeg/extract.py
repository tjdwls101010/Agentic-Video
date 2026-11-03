"""Still frames and speech audio out of a media file."""

from __future__ import annotations

import subprocess
from pathlib import Path

from video.errors import ToolError

from .probe import tool


def extract_frame(path: Path, seconds: float, out: Path, width: int) -> Path:
    """The frame whose presentation time is the first at or after `seconds`, scaled to `width` (rotation metadata applied). HDR sources are not tone-mapped: this ffmpeg build may lack zscale, so colours of PQ/HLG frames look flat."""
    cmd = [tool("ffmpeg"), "-v", "error", "-y", "-ss", f"{max(seconds, 0):.6f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={width}:-2", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not Path(out).exists():
        raise ToolError(f"ffmpeg could not extract a frame at {seconds:.3f} s from {path}", r.stderr, cmd)
    return out


def extract_audio(path: Path, out: Path, start: float | None = None, end: float | None = None) -> Path:
    """The first audio stream as mono 16 kHz Opus at 24 kbit/s in an Ogg file, small enough to send whole: all of it, or from `start` to `end` seconds. Seeking decodes, so a piece starts where it says."""
    cmd = [tool("ffmpeg"), "-v", "error", "-y", *(["-ss", f"{start:.6f}"] if start else []), "-i", str(path), *(["-t", f"{end - (start or 0):.6f}"] if end is not None else []),
           "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libopus", "-b:a", "24k", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if r.returncode != 0 or not Path(out).exists():
        raise ToolError(f"ffmpeg could not prepare the audio of {path}", r.stderr, cmd)
    return out

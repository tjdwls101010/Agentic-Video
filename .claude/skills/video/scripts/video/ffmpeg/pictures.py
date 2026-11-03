"""Pictures of a stretch of sound. A column means a time only if the picture spans exactly that stretch at a known rate: the sound is padded to the stretch's length (a stream can end before its movie) and resampled to 48 kHz first, because a spectrogram drawn at a low source rate slides right by tens of milliseconds."""

from __future__ import annotations

import subprocess
from pathlib import Path

from video.errors import ToolError

from .probe import FROM_CONTAINER_START, tool


def _picture(path: Path, start: float, end: float, draw: str, out: Path) -> Path:
    seconds = end - start
    graph = f"[0:a:0]{FROM_CONTAINER_START},aformat=channel_layouts=mono,aresample=48000,apad=whole_dur={seconds:.6f},{draw}[v]"
    cmd = [tool("ffmpeg"), "-v", "error", "-y", "-ss", f"{start:.6f}", "-t", f"{seconds:.6f}", "-i", str(path), "-filter_complex", graph, "-map", "[v]", "-frames:v", "1", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not Path(out).exists():
        raise ToolError(f"ffmpeg could not draw the audio of {path} from {start:.3f} to {end:.3f} s", r.stderr, cmd)
    return out


def wave_picture(path: Path, start: float, end: float, width: int, height: int, out: Path) -> Path:
    return _picture(path, start, end, f"showwavespic=s={width}x{height}:colors=white", out)


def spectrum_picture(path: Path, start: float, end: float, width: int, height: int, out: Path) -> Path:
    """0 to 8 kHz with the low end at the bottom, which keeps unvoiced sounds such as `s` in view. Without `legend=0` ffmpeg adds axis margins and a column stops meaning a time."""
    return _picture(path, start, end, f"showspectrumpic=s={width}x{height}:legend=0:stop=8000:scale=log", out)

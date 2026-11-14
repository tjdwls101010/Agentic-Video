"""What the suites need to drive the installed filmcraft-cli and effectcraft-cli and the skill's real entry point: where the binaries are, a runner for each, and media made with ffmpeg so expectations come from the generator's own parameters."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO / ".claude/skills/video"
CLI = SKILL_DIR / "scripts/cli.py"
TICKS = 254_016_000_000

FILMCRAFT = shutil.which("filmcraft-cli") or (str(Path.home() / ".local/bin/filmcraft-cli") if (Path.home() / ".local/bin/filmcraft-cli").exists() else None)
FFMPEG = shutil.which("ffmpeg")

needs_filmcraft = pytest.mark.skipif(FILMCRAFT is None, reason="filmcraft-cli is not installed (cli.py doctor gives the command)")
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg is not installed")

EFFECTCRAFT = shutil.which("effectcraft-cli") or (str(Path.home() / ".local/bin/effectcraft-cli") if (Path.home() / ".local/bin/effectcraft-cli").exists() else None)
# Where the app keeps downloaded models on macOS; each test's private data dir links to it, so a model installed on this Mac is found and none is downloaded.
EC_MODELS = Path.home() / "Library/Application Support/EffectCraft/models"

needs_effectcraft = pytest.mark.skipif(EFFECTCRAFT is None, reason="effectcraft-cli is not installed (cli.py doctor gives the command)")
needs_mobilesam = pytest.mark.skipif(not (EC_MODELS / "mobile_sam.pt").exists(), reason="the MobileSAM model is not installed (effectcraft-cli exec roto.model.download --params '{\"id\":\"mobilesam\",\"wait\":true}' downloads it); the tests do not download it")


def fc(*args: str, project: Path | None = None, save: bool = False, stdin: str | None = None, cwd: Path | None = None, check: bool = True):
    """Run filmcraft-cli with a private data dir; returns the CompletedProcess. With check, a non-zero exit fails the test with its stderr."""
    cmd = [FILMCRAFT, "--compact"]
    if project is not None:
        cmd += ["--project", str(project)]
    if save:
        cmd.append("--save")
    cmd += list(args)
    env = dict(os.environ, FILMCRAFT_DATA_DIR=str((cwd or Path.cwd()) / ".fcdata"))
    r = subprocess.run(cmd, input=stdin, capture_output=True, text=True, cwd=cwd, env=env, timeout=600)
    if check and r.returncode != 0:
        raise AssertionError(f"{' '.join(cmd)} exited {r.returncode}\nstdout: {r.stdout[-2000:]}\nstderr: {r.stderr[-2000:]}")
    return r


def fc_json(*args: str, **kw):
    return json.loads(fc(*args, **kw).stdout)


def fc_run(lines: list[dict], project: Path, save: bool = True, cwd: Path | None = None, check: bool = True) -> list[dict]:
    """Run commands as one `run -` session; returns each line's result object."""
    r = fc("run", "-", project=project, save=save, stdin="\n".join(json.dumps(l, ensure_ascii=False) for l in lines) + "\n", cwd=cwd, check=check)
    return [json.loads(l) for l in r.stdout.splitlines() if l.strip()]


def ec(*args: str, cwd: Path, check: bool = True):
    """Run effectcraft-cli in `cwd` with a private data dir (settings, preferences) whose `models` links to this Mac's models; returns the CompletedProcess. With check, a non-zero exit fails the test with its stderr."""
    data = Path(cwd) / ".ecdata"
    data.mkdir(exist_ok=True)
    if not (data / "models").exists() and EC_MODELS.exists():
        (data / "models").symlink_to(EC_MODELS)
    cmd = [EFFECTCRAFT, *args]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=dict(os.environ, EFFECTCRAFT_CONFIG_DIR=str(data)), timeout=900)
    if check and r.returncode != 0:
        raise AssertionError(f"{' '.join(cmd)} exited {r.returncode}\nstdout: {r.stdout[-2000:]}\nstderr: {r.stderr[-2000:]}")
    return r


def ec_json(*args: str, cwd: Path, check: bool = True):
    return json.loads(ec(*args, "--json", cwd=cwd, check=check).stdout)


def ec_run(project: Path, steps: list[tuple[str, dict]], cwd: Path, save: bool = True) -> list:
    """Run commands in order as one session (`run <id> <json> …`) on `project`; returns each step's result."""
    args = [a for c, p in steps for a in (c, json.dumps(p, ensure_ascii=False))]
    out = ec_json("--project", str(project), *(["--save"] if save else []), "run", *args, cwd=cwd)
    return [r["result"] for r in (out["result"] if isinstance(out, dict) else out)]   # with --save the steps sit under "result" next to "saved"


def skill(*args: str, cwd: Path | None = None, via_uv: bool = False, input: str | None = None, env: dict | None = None):
    """Run the skill's cli.py the way the model does (via_uv) or with this interpreter (same file, faster). `input` is its stdin (none: an empty one); `env` is added to this process's environment. Returns (returncode, parsed stdout or None, stdout, stderr)."""
    cmd = (["uv", "run", "-q", str(CLI)] if via_uv else [sys.executable, str(CLI)]) + list(args)
    env = {**os.environ, **(env or {})}
    if cwd is not None:
        env["FILMCRAFT_DATA_DIR"] = str(Path(cwd) / ".fcdata")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env, input=input if input is not None else "", timeout=1200)
    try:
        out = json.loads(r.stdout) if r.stdout.strip() else None
    except json.JSONDecodeError:
        out = None
    return r.returncode, out, r.stdout, r.stderr


def ffmpeg(*args: str):
    subprocess.run([FFMPEG, "-v", "error", "-y", *args], check=True, capture_output=True, timeout=600)


def make_av(path: Path, seconds: float, rate: str = "30000/1001", size: str = "1920x1080", tone: int = 440, src: str = "testsrc2", audio: bool = True) -> Path:
    """A test-pattern movie with a sine tone; `rate` is an ffmpeg rational."""
    args = ["-f", "lavfi", "-i", f"{src}=size={size}:rate={rate}:duration={seconds}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency={tone}:sample_rate=48000:duration={seconds}", "-c:a", "aac", "-shortest"]
    ffmpeg(*args, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path))
    return path

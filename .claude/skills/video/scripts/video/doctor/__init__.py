"""What stands between this machine and the first command: each system reports its own fact, and one pure judgment says which are required, why each matters, and the commands that fix what is required. It installs nothing and uses no network, so the commands stay the model's to run, under the usual permission checks."""

from __future__ import annotations

from dataclasses import dataclass

from video import chrome, ffmpeg, filmcraft, openrouter, whisper

__all__ = ["Facts", "judge", "report"]

_RELEASES = "https://github.com/storytold/filmcraft/releases"
_BREW_FFMPEG = "brew install ffmpeg"
_BREW_UV = "brew install uv"


@dataclass
class Facts:
    cli_version: str | None
    app_version: str | None
    ffmpeg: bool
    ffprobe: bool
    uvx: bool
    whisper_cached: bool
    key_source: str
    chrome: bool


def _check(name: str, ok: bool, required: bool, value, why: str) -> dict:
    return {"name": name, "ok": ok, "required": required, "value": value, "why": why}


def _filmcraft(f: Facts) -> tuple[dict, list[str]]:
    if f.cli_version is None and f.app_version is None:
        return _check("filmcraft_cli", False, True, "not installed, and no app to match", f"Every edit goes through filmcraft-cli. Install the FilmCraft app and its matching filmcraft-cli from {_RELEASES} (repository storytold/filmcraft)."), []
    if f.app_version is None:
        return _check("filmcraft_cli", True, True, f"{f.cli_version} (no app: headless only)", "Headless work needs no app."), []
    if f.cli_version == f.app_version:
        return _check("filmcraft_cli", True, True, f"{f.cli_version} (app {f.app_version})", "The CLI matches the app."), []
    value = f"{f.cli_version or 'not installed'} (app {f.app_version})"
    return _check("filmcraft_cli", False, True, value, "Install the CLI that matches the app: a project saved by a CLI newer than the app can have a schema the app cannot open."), filmcraft.install_steps(f.app_version)


def judge(f: Facts) -> dict:
    cli, steps = _filmcraft(f)
    checks = [
        cli,
        _check("ffmpeg", f.ffmpeg, True, "installed" if f.ffmpeg else "not installed", "Measures and draws sound, and extracts frames."),
        _check("ffprobe", f.ffprobe, True, "installed" if f.ffprobe else "not installed", "Reads what a media file holds."),
        _check("uvx", f.uvx, True, "installed" if f.uvx else "not installed", "Runs the local speech model in its own environment."),
        _check("whisper_model", f.whisper_cached, False, "cached" if f.whisper_cached else "not cached", "Without it, the first transcribe --engine local downloads a large model." if not f.whisper_cached else "transcribe --engine local starts without a download."),
        _check("openrouter_key", f.key_source != "none", False, f.key_source, f"Needed only by transcribe --engine openrouter. It is read from OPENROUTER_API_KEY when that is set, otherwise from {openrouter.KEY_FILE}."),
        _check("chrome", f.chrome, False, "installed" if f.chrome else "not installed", "Needed only by graphic, which renders pages in Google Chrome."),
    ]
    if not (f.ffmpeg and f.ffprobe):
        steps = [*steps, _BREW_FFMPEG]
    if not f.uvx:
        steps = [*steps, _BREW_UV]
    return {"ok": all(c["ok"] for c in checks if c["required"]), "checks": checks, "next": steps}


def report() -> dict:
    cli, app = filmcraft.versions()
    tools = ffmpeg.installed()
    return judge(Facts(cli, app, tools["ffmpeg"], tools["ffprobe"], whisper.uvx_installed(), whisper.model_cached(), openrouter.key_source(), chrome.installed()))

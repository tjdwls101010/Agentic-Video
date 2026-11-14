"""What stands between this machine and the first command: each system reports its own fact, and one pure judgment says which are required, why each matters, and the commands that fix what is required. The one optional item whose fix cannot be guessed (EffectCraft's CLI, a release asset of its own) carries its command in its own check, so `next` stays the list of what the first command needs. It installs nothing and uses no network, so the commands stay the model's to run, under the usual permission checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from video import chrome, codex, effectcraft, ffmpeg, filmcraft, openrouter, whisper

__all__ = ["Facts", "judge", "report"]

_RELEASES = "https://github.com/storytold/filmcraft/releases"
_BREW_FFMPEG = "brew install ffmpeg"
_BREW_REINSTALL_FFMPEG = "brew reinstall ffmpeg"
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
    ec_cli_version: str | None
    ec_app_version: str | None
    codex: bool
    broken: dict[str, str] = field(default_factory=dict)  # a tool that is there but does not run, and why; its bool above is False


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


def _effectcraft(f: Facts) -> dict:
    """Optional: only EffectCraft compositions need it, so it never fails the whole check and its command stays out of `next`; a CLI that is missing beside the app or does not match it still gets a command in the check, since the asset's name cannot be guessed and a mismatch shows only when the user opens a project in the app."""
    cli, app = f.ec_cli_version, f.ec_app_version
    if cli is None and app is None:
        return _check("effectcraft_cli", False, False, "not installed", "Needed only for EffectCraft compositions (compositing, tracking, mattes, keying).")
    if cli is None:
        return {**_check("effectcraft_cli", False, False, f"not installed (app {app})", "effectcraft-cli is a separate release asset, not part of the app; needed only for EffectCraft compositions."), "next": effectcraft.install_steps(app)}
    if app is None:
        return _check("effectcraft_cli", True, False, f"{cli} (no app: headless only)", "Headless work needs no app.")
    if cli == app:
        return _check("effectcraft_cli", True, False, f"{cli} (app {app})", "The CLI matches the app.")
    return {**_check("effectcraft_cli", False, False, f"{cli} (app {app})", "When the task needs EffectCraft, install the CLI that matches the app: the app refuses to open a project saved with a newer schema, and nothing says so until the user opens it."), "next": effectcraft.install_steps(app)}


def _ffmpeg_tool(f: Facts, name: str, ok: bool, why: str) -> dict:
    value = "installed" if ok else f"installed but does not run: {f.broken[name]}" if name in f.broken else "not installed"
    return _check(name, ok, True, value, why)


def judge(f: Facts) -> dict:
    cli, steps = _filmcraft(f)
    checks = [
        cli,
        _ffmpeg_tool(f, "ffmpeg", f.ffmpeg, "Measures and draws sound, and extracts frames."),
        _ffmpeg_tool(f, "ffprobe", f.ffprobe, "Reads what a media file holds."),
        _check("uvx", f.uvx, True, "installed" if f.uvx else "not installed", "Runs the local speech model in its own environment."),
        _check("whisper_model", f.whisper_cached, False, "cached" if f.whisper_cached else "not cached", "Without it, the first transcribe --engine local downloads a large model." if not f.whisper_cached else "transcribe --engine local starts without a download."),
        _check("openrouter_key", f.key_source != "none", False, f.key_source, f"Needed by transcribe's default engine, openrouter; without it, use --engine local. It is read from OPENROUTER_API_KEY when that is set, otherwise from {openrouter.KEY_FILE}."),
        _check("chrome", f.chrome, False, "installed" if f.chrome else "not installed", "Needed only by graphic, which renders pages in Google Chrome."),
        _check("codex", f.codex, False, "installed" if f.codex else "not installed", "Needed only by imagegen, which generates pictures through the Codex CLI and the user's ChatGPT login. Whether it is logged in is checked by imagegen when it runs, since running any codex command writes into the user's Codex folder."),
        _effectcraft(f),
    ]
    tools = {"ffmpeg": f.ffmpeg, "ffprobe": f.ffprobe}
    if any(not ok and name not in f.broken for name, ok in tools.items()):
        steps = [*steps, _BREW_FFMPEG]
    if any(not ok and name in f.broken for name, ok in tools.items()):
        steps = [*steps, _BREW_REINSTALL_FFMPEG]
    if not f.uvx:
        steps = [*steps, _BREW_UV]
    return {"ok": all(c["ok"] for c in checks if c["required"]), "checks": checks, "next": steps}


def report() -> dict:
    cli, app = filmcraft.versions()
    ec_cli, ec_app = effectcraft.versions()
    tools = ffmpeg.status()
    broken = {name: state for name, state in tools.items() if state not in ("ok", "missing")}
    return judge(Facts(cli, app, tools["ffmpeg"] == "ok", tools["ffprobe"] == "ok", whisper.uvx_installed(), whisper.model_cached(), openrouter.key_source(), chrome.installed(), ec_cli, ec_app, codex.executable() is not None, broken))

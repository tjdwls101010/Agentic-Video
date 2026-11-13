"""The installed effectcraft-cli and EffectCraft app: where the CLI is, which versions are installed, and how to install the CLI that matches the app. On macOS the CLI is a release asset of its own, not part of the app."""

from __future__ import annotations

import plistlib
import shutil
import subprocess
from pathlib import Path

from video.errors import ToolError

__all__ = ["binary", "versions", "install_steps"]

_APP_DIRS = [Path("/Applications"), Path.home() / "Applications"]


def binary() -> str:
    found = shutil.which("effectcraft-cli")
    if found:
        return found
    local = Path.home() / ".local/bin/effectcraft-cli"
    if local.exists():
        return str(local)
    raise ToolError("effectcraft-cli is not installed; `doctor` gives the command that installs the version matching the app")


def versions() -> tuple[str | None, str | None]:
    """The installed CLI's version and the app's, each None when it is not installed. Nothing is opened or written."""
    cli = None
    try:
        r = subprocess.run([binary(), "--version"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.split():
            cli = r.stdout.split()[-1]
    except (ToolError, OSError, subprocess.TimeoutExpired):
        pass
    app = None
    for root in _APP_DIRS:
        try:
            app = plistlib.loads((root / "EffectCraft.app/Contents/Info.plist").read_bytes())["CFBundleShortVersionString"]
            break
        except (OSError, KeyError, plistlib.InvalidFileException):
            continue
    return cli, app


def install_steps(version: str) -> list[str]:
    """One command that fetches the release of `version`, checks it against the published sums and installs the CLI, working in a temporary folder."""
    name = f"effectcraft-cli-{version}-macos-universal"
    return [f"cd \"$(mktemp -d)\" && gh release download v{version} -R storytold/effectcraft -p '{name}.zip' -p SHA256SUMS.txt && shasum -a 256 -c --ignore-missing SHA256SUMS.txt && unzip -q {name}.zip && mkdir -p ~/.local/bin && install -m 755 {name}/effectcraft-cli ~/.local/bin/effectcraft-cli"]

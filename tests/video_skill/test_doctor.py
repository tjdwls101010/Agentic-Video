"""`doctor`: what must be fixed before the first command. The judgment is a pure function of facts, so its cases are worked by hand here (release file names as published for v0.14.0); the facts themselves are read once from this machine through the real entry point."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from video import doctor, effectcraft, filmcraft, openrouter, whisper
from support import CLI, skill

FAKE_KEY = "sk-test-doctor-0123456789-SECRET"


def facts(**over):
    base = dict(cli_version="0.14.0", app_version="0.14.0", ffmpeg=True, ffprobe=True, uvx=True, whisper_cached=True, key_source="file", chrome=True, ec_cli_version="0.24.1", ec_app_version="0.24.1")
    return doctor.Facts(**{**base, **over})


def check(result, name):
    return next(c for c in result["checks"] if c["name"] == name)


def test_everything_present_is_ok_with_nothing_to_do():
    r = doctor.judge(facts())
    assert r["ok"] is True and r["next"] == []
    assert [c["name"] for c in r["checks"]] == ["filmcraft_cli", "ffmpeg", "ffprobe", "uvx", "whisper_model", "openrouter_key", "chrome", "effectcraft_cli"]
    assert {c["name"]: c["required"] for c in r["checks"]} == {"filmcraft_cli": True, "ffmpeg": True, "ffprobe": True, "uvx": True, "whisper_model": False, "openrouter_key": False, "chrome": False, "effectcraft_cli": False}


def test_a_cli_behind_the_app_fails_and_next_installs_the_apps_version():
    r = doctor.judge(facts(cli_version="0.14.0", app_version="0.17.0"))
    assert r["ok"] is False and check(r, "filmcraft_cli")["ok"] is False
    assert "0.14.0" in check(r, "filmcraft_cli")["value"] and "0.17.0" in check(r, "filmcraft_cli")["value"]
    joined = " ".join(r["next"])
    assert "filmcraft-cli-0.17.0-macos-universal.zip" in joined and "v0.17.0" in joined and "0.14.0" not in joined


def test_a_cli_ahead_of_the_app_fails_too_because_the_app_may_not_open_its_projects():
    r = doctor.judge(facts(cli_version="0.18.0", app_version="0.17.0"))
    assert r["ok"] is False and "open" in check(r, "filmcraft_cli")["why"]
    assert "filmcraft-cli-0.17.0-macos-universal.zip" in " ".join(r["next"])


def test_a_missing_cli_with_an_app_installs_the_apps_version():
    r = doctor.judge(facts(cli_version=None, app_version="0.17.0"))
    assert r["ok"] is False and "filmcraft-cli-0.17.0-macos-universal.zip" in " ".join(r["next"])


def test_a_cli_without_an_app_passes_because_headless_work_needs_no_app():
    r = doctor.judge(facts(app_version=None))
    c = check(r, "filmcraft_cli")
    assert r["ok"] is True and c["ok"] is True and "no app" in c["value"]


def test_no_cli_and_no_app_fails_and_says_where_they_come_from():
    r = doctor.judge(facts(cli_version=None, app_version=None))
    assert r["ok"] is False and "storytold/filmcraft" in check(r, "filmcraft_cli")["why"]


@pytest.mark.parametrize("name, field", [("ffmpeg", "ffmpeg"), ("ffprobe", "ffprobe"), ("uvx", "uvx")])
def test_a_missing_required_tool_fails_with_a_command_to_fix_it(name, field):
    r = doctor.judge(facts(**{field: False}))
    assert r["ok"] is False and check(r, name)["ok"] is False
    assert r["next"] and any("brew install" in n for n in r["next"])


def test_a_tool_that_is_there_but_does_not_run_fails_with_its_reason_and_a_reinstall():
    r = doctor.judge(facts(ffmpeg=False, broken={"ffmpeg": "Library not loaded: libopus.0.dylib"}))
    assert r["ok"] is False and check(r, "ffmpeg")["ok"] is False
    assert "does not run" in check(r, "ffmpeg")["value"] and "libopus" in check(r, "ffmpeg")["value"]
    assert r["next"] == ["brew reinstall ffmpeg"]


def test_one_tool_missing_and_one_broken_gets_both_commands():
    r = doctor.judge(facts(ffmpeg=False, ffprobe=False, broken={"ffprobe": "exit 1"}))
    assert check(r, "ffmpeg")["value"] == "not installed"
    assert r["next"] == ["brew install ffmpeg", "brew reinstall ffmpeg"]


@pytest.mark.parametrize("over", [{"whisper_cached": False}, {"key_source": "none"}, {"chrome": False}])
def test_a_missing_optional_item_does_not_fail(over):
    r = doctor.judge(facts(**over))
    assert r["ok"] is True and r["next"] == []
    failed = [c for c in r["checks"] if not c["ok"]]
    assert len(failed) == 1 and failed[0]["required"] is False and failed[0]["why"]


def test_the_key_check_says_what_goes_without_a_key():
    why = check(doctor.judge(facts(key_source="none")), "openrouter_key")["why"]
    assert "--engine local" in why and "default" in why


@pytest.mark.parametrize("source", ["env", "file", "none"])
def test_the_key_check_reports_only_where_the_key_is(source):
    assert check(doctor.judge(facts(key_source=source)), "openrouter_key")["value"] == source


# -- EffectCraft: optional, so it never fails the whole check, but a CLI that does not match the app still gets its install command ----

def test_no_effectcraft_at_all_is_optional_with_nothing_to_run():
    r = doctor.judge(facts(ec_cli_version=None, ec_app_version=None))
    c = check(r, "effectcraft_cli")
    assert r["ok"] is True and r["next"] == []
    assert c["ok"] is False and c["required"] is False and c["value"] == "not installed" and "EffectCraft" in c["why"]


def test_an_effectcraft_app_without_its_cli_gets_the_apps_release_asset():
    """The CLI is a separate release asset, which is why its install command is named even though the item is optional."""
    r = doctor.judge(facts(ec_cli_version=None, ec_app_version="0.24.1"))
    c = check(r, "effectcraft_cli")
    assert r["ok"] is True and c["ok"] is False and c["value"] == "not installed (app 0.24.1)" and "separate" in c["why"]
    assert "effectcraft-cli-0.24.1-macos-universal.zip" in " ".join(r["next"])


def test_an_effectcraft_cli_without_the_app_passes_for_headless_work():
    r = doctor.judge(facts(ec_cli_version="0.24.1", ec_app_version=None))
    c = check(r, "effectcraft_cli")
    assert r["ok"] is True and c["ok"] is True and c["value"] == "0.24.1 (no app: headless only)" and r["next"] == []


def test_a_matching_effectcraft_cli_passes():
    c = check(doctor.judge(facts()), "effectcraft_cli")
    assert c["ok"] is True and c["value"] == "0.24.1 (app 0.24.1)"


@pytest.mark.parametrize("cli", ["0.25.0", "0.23.0"])
def test_a_mismatched_effectcraft_cli_fails_its_item_only_and_next_installs_the_apps_version(cli):
    r = doctor.judge(facts(ec_cli_version=cli, ec_app_version="0.24.1"))
    c = check(r, "effectcraft_cli")
    assert r["ok"] is True and c["ok"] is False and c["value"] == f"{cli} (app 0.24.1)" and "open" in c["why"]
    joined = " ".join(r["next"])
    assert "effectcraft-cli-0.24.1-macos-universal.zip" in joined and "v0.24.1" in joined and cli not in joined


def test_effectcraft_steps_follow_filmcrafts_and_do_not_hide_them():
    r = doctor.judge(facts(cli_version="0.14.0", app_version="0.17.0", ec_cli_version=None, ec_app_version="0.24.1"))
    assert r["ok"] is False
    assert ["filmcraft-cli-0.17.0" in n for n in r["next"]] == [True, False] and "effectcraft-cli-0.24.1" in r["next"][1]


def test_effectcraft_install_steps_are_one_command_from_a_temporary_folder():
    [step] = effectcraft.install_steps("0.24.1")
    assert step.startswith('cd "$(mktemp -d)" && ')
    for part in ("gh release download v0.24.1 -R storytold/effectcraft", "-p 'effectcraft-cli-0.24.1-macos-universal.zip'", "-p SHA256SUMS.txt", "shasum -a 256 -c --ignore-missing SHA256SUMS.txt",
                 "unzip -q effectcraft-cli-0.24.1-macos-universal.zip", "~/.local/bin/effectcraft-cli"):
        assert part in step


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("gh") is None, reason="gh is needed to read the release")
def test_effectcraft_install_steps_name_assets_the_installed_release_publishes():
    """Network: the asset names in the command are checked against the release of the installed app (or CLI), so a renamed asset fails here rather than at the user's install."""
    cli, app = effectcraft.versions()
    version = app or cli
    if version is None:
        pytest.skip("no EffectCraft installed to name a release")
    r = subprocess.run(["gh", "release", "view", f"v{version}", "-R", "storytold/effectcraft", "--json", "assets"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    published = {a["name"] for a in json.loads(r.stdout)["assets"]}
    [step] = effectcraft.install_steps(version)
    download = next(part for part in step.split(" && ") if part.startswith("gh release download"))
    named = set(re.findall(r"-p '?([^' ]+)'?", download))
    assert named and named <= published, (named, published)
    folder = re.search(r"install -m 755 (\S+)/effectcraft-cli", step).group(1)
    assert f"{folder}.zip" in published


def test_install_steps_are_one_command_from_a_temporary_folder():
    [step] = filmcraft.install_steps("0.17.0")
    assert step.startswith('cd "$(mktemp -d)" && ')
    for part in ("gh release download v0.17.0 -R storytold/filmcraft", "-p 'filmcraft-cli-0.17.0-macos-universal.zip'", "-p SHA256SUMS.txt", "shasum -a 256 -c --ignore-missing SHA256SUMS.txt",
                 "unzip -q filmcraft-cli-0.17.0-macos-universal.zip", "install -m 755 filmcraft-cli-0.17.0-macos-universal/filmcraft-cli ~/.local/bin/filmcraft-cli"):
        assert part in step


# -- the facts each system owns -----------------------------------------------------------------------------------------------

def test_the_key_source_never_needs_the_key(tmp_path):
    f = tmp_path / ".env"
    f.write_text("OPENROUTER_API_KEY=abc\n")
    assert openrouter.key_source(env={"OPENROUTER_API_KEY": "x"}, file=f) == "env"
    assert openrouter.key_source(env={"OPENROUTER_API_KEY": ""}, file=f) == "none"
    assert openrouter.key_source(env={}, file=f) == "file"
    assert openrouter.key_source(env={}, file=tmp_path / "none") == "none"


def test_a_whisper_model_is_cached_when_its_snapshot_has_files(tmp_path):
    env = {"HF_HOME": str(tmp_path)}
    assert whisper.model_cached("a/b", env) is False
    snapshot = tmp_path / "hub/models--a--b/snapshots/abc"
    snapshot.mkdir(parents=True)
    assert whisper.model_cached("a/b", env) is False
    (snapshot / "weights.npz").write_text("x")
    assert whisper.model_cached("a/b", env) is True


# -- the real entry point ---------------------------------------------------------------------------------------------------------

def test_the_real_entry_point_agrees_with_this_machine(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    code, res, raw, err = skill("doctor")
    assert code == (0 if res["ok"] else 1)
    assert FAKE_KEY not in raw + err and FAKE_KEY[:12] not in raw + err
    assert check(res, "openrouter_key")["value"] == "env"
    assert check(res, "ffmpeg")["ok"] is (shutil.which("ffmpeg") is not None)
    assert check(res, "uvx")["ok"] is (shutil.which("uvx") is not None)
    ec = check(res, "effectcraft_cli")
    assert ec["required"] is False and (ec["value"] != "not installed") is (shutil.which("effectcraft-cli") is not None or Path("/Applications/EffectCraft.app").exists() or (Path.home() / ".local/bin/effectcraft-cli").exists())


@pytest.mark.parametrize("body, reason", [("echo 'Library not loaded: libopus' >&2; exit 134", "libopus"), ("exit 3", "exit 3")])
def test_a_tool_that_cannot_run_fails_through_the_entry_point(tmp_path, monkeypatch, body, reason):
    """The tool is found on PATH, which is all `which` can see; only running it shows the dynamic linker's failure."""
    fake = tmp_path / "ffmpeg"
    fake.write_text(f"#!/bin/sh\n{body}\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    code, res, raw, err = skill("doctor")
    assert code == 1 and res["ok"] is False and check(res, "ffmpeg")["ok"] is False
    assert reason in check(res, "ffmpeg")["value"]
    assert "brew reinstall ffmpeg" in res["next"]


def test_a_missing_tool_says_install_through_the_entry_point(tmp_path, monkeypatch):
    """A PATH with only what the rest of doctor can do without, so neither ffmpeg nor ffprobe is found."""
    monkeypatch.setenv("PATH", str(tmp_path))
    code, res, raw, err = skill("doctor")
    assert code == 1 and check(res, "ffmpeg")["value"] == "not installed" and "brew install ffmpeg" in res["next"]
    assert "brew reinstall ffmpeg" not in res["next"]


def test_a_tool_that_hangs_fails_through_the_entry_point(tmp_path, monkeypatch):
    """Takes as long as doctor waits for one tool, about 10 s."""
    fake = tmp_path / "ffmpeg"
    fake.write_text("#!/bin/sh\nexec sleep 60\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    code, res, raw, err = skill("doctor")
    assert code == 1 and res["ok"] is False and "timed out" in check(res, "ffmpeg")["value"]
    assert "brew reinstall ffmpeg" in res["next"]


def test_a_mismatched_cli_exits_one_through_the_entry_point(tmp_path, monkeypatch):
    fake = tmp_path / "filmcraft-cli"
    fake.write_text("#!/bin/sh\necho 'filmcraft-cli 0.0.1'\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    code, res, raw, err = skill("doctor")
    if check(res, "filmcraft_cli")["value"].endswith("no app: headless only"):
        pytest.skip("this machine has no FilmCraft app to mismatch")
    assert code == 1 and res["ok"] is False and "0.0.1" in check(res, "filmcraft_cli")["value"] and res["next"]


def test_doctor_takes_no_arguments():
    code, res, raw, err = skill("doctor", "--fix")
    assert code == 2


@pytest.mark.skipif(shutil.which("sandbox-exec") is None, reason="macOS sandbox-exec is needed to forbid network and writes")
def test_it_uses_no_network_and_writes_nothing():
    """Under a sandbox that denies both, the result is the same as without one."""
    policy = '(version 1)(allow default)(deny network*)(deny file-write* (subpath "/Users")(subpath "/private")(subpath "/tmp"))'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    denied = subprocess.run(["sandbox-exec", "-p", policy, sys.executable, str(CLI), "doctor"], capture_output=True, text=True, env=env, timeout=120)
    free = subprocess.run([sys.executable, str(CLI), "doctor"], capture_output=True, text=True, env=env, timeout=120)
    assert denied.returncode == free.returncode, denied.stderr
    assert json.loads(denied.stdout) == json.loads(free.stdout)


def test_help_explains_every_field():
    code, _, raw, err = skill("doctor", "--help")
    assert code == 0
    for word in ("filmcraft_cli", "whisper_model", "openrouter_key", "chrome", "effectcraft_cli", "next", "Prints:", "Exits:"):
        assert word in raw, word

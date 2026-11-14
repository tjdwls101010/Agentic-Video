"""`imagegen` and `imagenote` through the real entry point, with a fake `codex` (tests/support/fake_codex.py, written to the shapes measured from codex-cli 0.167.1) and a fake `open` first on PATH and a private CODEX_HOME, so no test reaches OpenAI, the user's Codex folder or their browser. What is promised is what a caller sees (stdout, stderr, the exit code) and what stays on disk (the pictures, imagegen.json, contact-sheet.html), since the model reads the ledger and the user reads the sheet.

The real Codex is behind the double: its event and rollout formats are checked only by the gated test at the end (FILMCRAFT_TEST_CODEX=1), and only on the success path."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

from support import CLI, REPO, skill

FAKE = REPO / "tests/support/fake_codex.py"
PROMPT = "Landscape 16:9 aspect ratio, wider than it is tall. A brass microphone on a stand against a flat teal ground (#0f4c5c). No text."


class Env:
    def __init__(self, root: Path):
        self.root = root
        self.bin = root / "bin"
        self.bin.mkdir()
        self.codex_home = root / "codex-home"
        self.codex_home.mkdir()
        self.dir = root / "piece" / "graphics" / "imagegen"
        (self.bin / "codex").write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n')
        (self.bin / "open").write_text(f'#!/bin/sh\necho "$@" >> "{root}/open-calls.txt"\nsleep ${{FAKE_OPEN_DELAY:-0}}\nexit ${{FAKE_OPEN_EXIT:-0}}\n')
        for f in ("codex", "open"):
            (self.bin / f).chmod(0o755)
        self.vars = {"PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "CODEX_HOME": str(self.codex_home), "FAKE_CODEX_SCENARIO": "ok"}

    def env(self, **over) -> dict:
        return {**self.vars, **{k: str(v) for k, v in over.items()}}

    def gen(self, *args, prompt: str | None = PROMPT, name: str = "mic", **over):
        return skill("imagegen", name, "--dir", str(self.dir), *args, input=prompt, env=self.env(**over))

    def note(self, target, *args, **over):
        return skill("imagenote", target, "--dir", str(self.dir), *args, env=self.env(**over))

    def calls(self) -> list[dict]:
        f = self.codex_home / "fake-calls.jsonl"
        return [json.loads(l) for l in f.read_text().splitlines()] if f.exists() else []

    def starts(self) -> list[dict]:
        return [c for c in self.calls() if c["event"] == "start"]

    def ledger(self) -> dict:
        return json.loads((self.dir / "imagegen.json").read_text())

    def attempts(self, name: str = "mic") -> list[dict]:
        entry = next(e for e in self.ledger()["names"] if e["name"] == name)
        return [a for r in entry["requests"] for a in r["attempts"]]

    def opened(self) -> list[str]:
        f = self.root / "open-calls.txt"
        return f.read_text().splitlines() if f.exists() else []


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# -- the success path ---------------------------------------------------------------------------------------------------

def test_a_picture_lands_in_the_folder_with_its_ledger_row(env):
    code, out, raw, err = env.gen(FAKE_CODEX_SIZE="1672x941")
    assert code == 0, raw + err
    png = env.dir / "mic-1.png"
    assert png.is_file()
    with Image.open(png) as im:
        assert im.size == (1672, 941)
    assert out["name"] == "mic" and out["request"] == 1
    assert out["results"] == [{"image": "mic-1", "file": str(png), "status": "ok", "w": 1672, "h": 941, "verbatim": "exact"}]
    assert out["summary"] == "1 requested · 1 ok"
    assert out["ledger"] == str(env.dir / "imagegen.json") and out["sheet"] == str(env.dir / "contact-sheet.html")
    [row] = env.attempts()
    assert row["status"] == "ok" and row["file"] == "mic-1.png" and (row["w"], row["h"]) == (1672, 941) and row["verbatim"] == "exact" and "pid" not in row
    [request] = env.ledger()["names"][0]["requests"]
    assert request["prompt"] == PROMPT and request["refs"] == [] and request["transparent"] is False
    [call] = env.starts()
    assert call["prompt"] == PROMPT and call["refs"] == [] and call["transparent"] is False
    assert "mic-1" in err and "ok" in err


# -- nothing already there is overwritten -------------------------------------------------------------------------------

def test_every_run_takes_new_numbers_and_leaves_earlier_pictures_byte_for_byte(env):
    assert env.gen("--n", "2")[0] == 0
    before = {p.name: sha(p) for p in env.dir.glob("mic-*.png")}
    code, out, raw, err = env.gen(prompt="Square 1:1 aspect ratio. Another microphone.")
    assert code == 0 and out["request"] == 2 and [x["image"] for x in out["results"]] == ["mic-3"]
    assert {p.name: sha(p) for p in env.dir.glob("mic-*.png") if p.name != "mic-3.png"} == before
    assert sorted(p.name for p in env.dir.glob("mic-*.png")) == ["mic-1.png", "mic-2.png", "mic-3.png"]
    assert [a["id"] for a in env.attempts()] == ["mic-1", "mic-2", "mic-3"]


def test_a_picture_file_outside_the_ledger_is_left_alone_and_only_that_try_fails(env):
    env.dir.mkdir(parents=True)
    stranger = env.dir / "mic-1.png"
    stranger.write_bytes(b"someone else's file")
    code, out, raw, err = env.gen("--n", "2")
    assert stranger.read_bytes() == b"someone else's file"
    by_id = {x["image"]: x for x in out["results"]}
    assert by_id["mic-1"]["status"] == "executor_error" and "file" not in by_id["mic-1"]
    assert by_id["mic-2"]["status"] == "ok" and code == 0
    row = next(a for a in env.attempts() if a["id"] == "mic-1")
    assert "already exist" in row["detail"]["message"] and "file" not in row


# -- what a folder must hold before anything is written --------------------------------------------------------------

def snapshot(folder: Path) -> dict:
    return {p.name: p.read_bytes() for p in folder.iterdir()} if folder.exists() else {}


@pytest.mark.parametrize("files", [
    {"imagegen.json": '{"version": 3, "items": []}'},
    {"imagegen.json": '{"schema": 1, "created": "x", "names": [], "extra": true}'},
    {"imagegen.json": "{not json"},
    {"contact-sheet.html": "<html>someone's sheet</html>"},
])
def test_a_folder_holding_someone_elses_files_is_refused_before_anything_is_written(env, files):
    env.dir.mkdir(parents=True)
    for n, text in files.items():
        (env.dir / n).write_text(text)
    before = snapshot(env.dir)
    code, out, raw, err = env.gen()
    assert code == 2 and out["error"]
    assert snapshot(env.dir) == before
    assert env.starts() == []


@pytest.mark.parametrize("name", ["", " ", "a/b", "mic-2", ".hidden", "tab\tname", "a:b"])
def test_a_name_that_cannot_be_a_file_name_is_refused(env, name):
    code, out, raw, err = env.gen(name=name)
    assert code == 2 and out["error"] and env.starts() == []


def test_a_name_differing_only_in_case_from_one_in_the_folder_is_refused(env):
    assert env.gen()[0] == 0
    code, out, raw, err = env.gen(name="MIC")
    assert code == 2 and "case" in out["error"]


def test_a_korean_name_with_a_space_works_and_is_stored_as_nfc(env):
    import unicodedata
    nfd = unicodedata.normalize("NFD", "마이크 왼쪽")
    code, out, raw, err = env.gen(name=nfd)
    assert code == 0, raw + err
    nfc = unicodedata.normalize("NFC", "마이크 왼쪽")
    assert out["name"] == nfc and (env.dir / f"{nfc}-1.png").is_file()
    assert env.ledger()["names"][0]["name"] == nfc


# -- references and --again ---------------------------------------------------------------------------------------------

def make_ref(path: Path, colour=(10, 120, 200)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 48), colour).save(path)
    return path


def test_a_reference_is_sent_by_path_and_recorded_relative_to_the_folder_with_its_hash(env):
    ref = make_ref(env.root / "piece" / "assets" / "참조 그림 🌙" / "밤 하늘.png")
    code, out, raw, err = env.gen("--ref", str(ref))
    assert code == 0, raw + err
    [request] = env.ledger()["names"][0]["requests"]
    assert request["refs"] == [{"path": os.path.relpath(ref, env.dir), "sha256": sha(ref)}]
    assert request["refs"][0]["path"] == "../../assets/참조 그림 🌙/밤 하늘.png"
    [call] = env.starts()
    assert call["refs"] == [str(ref)]
    assert "refs_sent" not in env.attempts()[0].get("detail", {})


def test_a_reference_codex_received_with_another_hash_is_recorded_on_the_try(env):
    ref = make_ref(env.root / "ref.png")
    code, out, raw, err = env.gen("--ref", str(ref), FAKE_CODEX_SCENARIO="ref_hash_wrong")
    assert code == 0
    [row] = env.attempts()
    assert row["detail"]["refs_sent"] == [{"path": str(ref), "sha256": "0" * 64}]


def test_a_missing_reference_is_refused_before_anything_is_written(env):
    code, out, raw, err = env.gen("--ref", str(env.root / "nope.png"))
    assert code == 2 and "nope.png" in out["error"] and env.starts() == [] and not env.dir.exists()


def test_again_adds_tries_to_the_same_request_with_the_recorded_prompt_and_reads_no_stdin(env):
    ref = make_ref(env.root / "ref.png")
    assert env.gen("--ref", str(ref), "--transparent", "--label", "first look")[0] == 0
    code, out, raw, err = env.gen("--again", "mic-1", "--n", "2", prompt="a different prompt that must not be read")
    assert code == 0, raw + err
    assert out["request"] == 1 and [x["image"] for x in out["results"]] == ["mic-2", "mic-3"]
    [request] = env.ledger()["names"][0]["requests"]
    assert [a["id"] for a in request["attempts"]] == ["mic-1", "mic-2", "mic-3"] and request["label"] == "first look"
    assert [(c["prompt"], c["refs"], c["transparent"]) for c in env.starts()] == [(PROMPT, [str(ref)], True)] * 3


@pytest.mark.parametrize("extra", [["--ref", "x.png"], ["--transparent"], ["--label", "x"]])
def test_again_refuses_request_flags(env, extra):
    assert env.gen()[0] == 0
    code, out, raw, err = env.gen("--again", "mic-1", *extra)
    assert code == 2 and "--again" in out["error"] and len(env.starts()) == 1


@pytest.mark.parametrize("image", ["mic-9", "sky-1", "nonsense"])
def test_again_on_a_picture_not_under_this_name_is_refused(env, image):
    assert env.gen()[0] == 0
    code, out, raw, err = env.gen("--again", image)
    assert code == 2 and len(env.starts()) == 1


@pytest.mark.parametrize("change", ["delete", "rewrite"])
def test_again_refuses_when_a_reference_is_gone_or_changed(env, change):
    ref = make_ref(env.root / "ref.png")
    assert env.gen("--ref", str(ref))[0] == 0
    if change == "delete":
        ref.unlink()
    else:
        make_ref(ref, colour=(1, 2, 3))
    code, out, raw, err = env.gen("--again", "mic-1")
    assert code == 2 and "ref.png" in out["error"] and len(env.starts()) == 1
    assert [a["id"] for a in env.attempts()] == ["mic-1"]


# -- how a try can end ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("scenario, stage, message", [
    ("refuse_input", "input", "rejected by the safety system"),
    ("refuse_output", "output", "rejected by the safety system"),
    ("refuse_unknown", "unknown", "Rejected."),
])
def test_a_refusal_is_recorded_with_its_stage_and_codexs_words(env, scenario, stage, message):
    code, out, raw, err = env.gen(FAKE_CODEX_SCENARIO=scenario)
    assert code == 1 and out["error"] and out["results"] == [{"image": "mic-1", "status": "refused", "verbatim": "exact"}]
    [row] = env.attempts()
    assert row["status"] == "refused" and row["detail"]["stage"] == stage and message in row["detail"]["message"]
    assert row["detail"]["log"].endswith(".jsonl") and "file" not in row
    assert "refused" in err and f"stage {stage}" in err
    assert not (env.dir / "mic-1.png").exists()


def test_a_failed_try_still_takes_its_number(env):
    assert env.gen(FAKE_CODEX_SCENARIO="refuse_input")[0] == 1
    code, out, raw, err = env.gen()
    assert code == 0 and out["results"][0]["image"] == "mic-2" and (env.dir / "mic-2.png").is_file()


@pytest.mark.parametrize("scenario, status, words", [
    ("exit_nonzero", "executor_error", "something broke"),
    ("no_last", "executor_error", "no final message"),
    ("failed_no_reason", "no_image", "no reason"),
    ("saved_missing", "no_image", "does not exist"),
    ("two_pngs", "no_image", "2 PNGs"),
    ("no_thread", "no_image", "no thread id"),
])
def test_codex_failing_or_making_nothing_is_recorded_with_why(env, scenario, status, words):
    code, out, raw, err = env.gen(FAKE_CODEX_SCENARIO=scenario)
    assert code == 1 and out["results"][0]["status"] == status
    [row] = env.attempts()
    assert row["status"] == status and words in row["detail"].get("message", "") + row["detail"].get("note", "")
    assert status in err


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(out) and not out.startswith("Z")


def test_a_try_past_its_timeout_ends_codex_and_its_children(env):
    t0 = time.monotonic()
    code, out, raw, err = env.gen("--timeout", "2", FAKE_CODEX_SCENARIO="hang_stubborn")
    took = time.monotonic() - t0
    assert code == 1 and out["results"][0]["status"] == "timeout" and took < 15
    pids = [int(x) for line in (env.codex_home / "children.txt").read_text().split("\n") if line for x in line.split()]
    time.sleep(0.5)
    assert pids and not any(alive(p) for p in pids)
    assert "timeout" in err


def test_the_retry_gets_only_what_is_left_of_the_tries_timeout(env):
    """The first call takes 2.5 s of a 4 s budget and the retry hangs: ended at about 4 s, not 4 s after the retry began."""
    t0 = time.monotonic()
    code, out, raw, err = env.gen("--timeout", "4", FAKE_CODEX_SCENARIO="rewrite,hang", FAKE_CODEX_DELAY="2.5,0")
    took = time.monotonic() - t0
    assert out["results"][0]["status"] == "timeout" and len(env.starts()) == 2
    assert took < 6.0, took


def test_exit_zero_needs_only_one_ok_and_the_summary_counts_the_rest(env):
    code, out, raw, err = env.gen("--n", "3", FAKE_CODEX_SCENARIO="ok,refuse_input,exit_nonzero")
    assert code == 0 and "error" not in out
    assert sorted(x["status"] for x in out["results"]) == ["executor_error", "ok", "refused"]
    assert out["summary"].startswith("3 requested · 1 ok") and "1 refused" in out["summary"] and "1 executor_error" in out["summary"]


# -- what reached image_gen: the observation decides, Codex's own report only admits a change --------------------------

@pytest.mark.parametrize("scenario, status, verbatim, calls, retried", [
    ("ok", "ok", "exact", 1, False),
    ("normalized", "ok", "normalized", 1, False),
    ("rewrite,ok", "ok", "exact", 2, True),
    ("rewrite,rewrite", "prompt_altered", "mismatch", 2, True),
    ("report_lies", "ok", "exact", 1, False),
    ("no_observation", "ok", "unverified", 1, False),
    ("no_rollout", "ok", "unverified", 1, False),
    ("no_observation_mismatch,ok", "ok", "exact", 2, True),
    ("no_observation_mismatch,no_observation_mismatch", "prompt_altered", "mismatch", 2, True),
    ("broken_line", "ok", "exact", 1, False),
])
def test_the_verbatim_gate(env, scenario, status, verbatim, calls, retried):
    code, out, raw, err = env.gen(FAKE_CODEX_SCENARIO=scenario)
    [row] = env.attempts()
    assert (row["status"], row["verbatim"], len(env.starts()), "retried" in row) == (status, verbatim, calls, retried)
    assert [c["stronger"] for c in env.starts()] == [False, True][:calls]
    assert (env.dir / "mic-1.png").is_file() and row["file"] == "mic-1.png"
    assert code == (0 if status == "ok" else 1)
    if retried:
        assert row["retried"]["verbatim"] == "mismatch" and "trying once more" in err


def test_a_picture_no_generation_names_is_unverified_even_when_a_failed_generation_was_observed(env):
    code, out, raw, err = env.gen(FAKE_CODEX_SCENARIO="failed_then_png")
    [row] = env.attempts()
    assert row["status"] == "ok" and row["verbatim"] == "unverified"


def test_an_unverified_picture_says_why_there_was_no_observation(env):
    env.gen(FAKE_CODEX_SCENARIO="no_observation")
    [row] = env.attempts()
    assert "unverified" in row["detail"]["note"] and "no generation in the rollout" in row["detail"]["note"]


def test_with_two_generations_in_one_call_the_last_is_taken_and_counted(env):
    code, out, raw, err = env.gen(FAKE_CODEX_SCENARIO="two_generations", FAKE_CODEX_SIZE="800x600")
    [row] = env.attempts()
    assert code == 0 and (row["w"], row["h"]) == (800, 600) and row["detail"]["generations"] == 2


# -- stopping and dying ---------------------------------------------------------------------------------------------------

def start_cli(env, *args, scenario="hang"):
    proc = subprocess.Popen([sys.executable, str(CLI), "imagegen", "mic", "--dir", str(env.dir), *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env={**os.environ, **env.env(FAKE_CODEX_SCENARIO=scenario)}, text=True)
    proc.stdin.write(PROMPT)
    proc.stdin.close()
    proc.stdin = None   # so communicate() does not touch it again
    return proc


def wait_for(predicate, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return False


def codex_pids(env) -> list[int]:
    return [c["pid"] for c in env.starts()] + [int(x) for line in ((env.codex_home / "children.txt").read_text().splitlines() if (env.codex_home / "children.txt").exists() else []) for x in line.split()]


@pytest.mark.parametrize("sig, scenario", [(signal.SIGTERM, "hang"), (signal.SIGINT, "hang"), (signal.SIGTERM, "hang_stubborn")])
def test_stopping_the_command_ends_every_codex_group_and_closes_the_tries_as_interrupted(env, sig, scenario):
    proc = start_cli(env, "--n", "3", scenario=scenario)
    assert wait_for(lambda: (env.codex_home / "children.txt").exists() and len((env.codex_home / "children.txt").read_text().splitlines()) == 3)
    proc.send_signal(sig)
    stdout, stderr = proc.communicate(timeout=30)
    assert proc.returncode == 1, stderr
    out = json.loads(stdout)
    assert [x["status"] for x in out["results"]] == ["interrupted"] * 3 and "stopped" in out["error"]
    assert [a["status"] for a in env.attempts()] == ["interrupted"] * 3 and not any("pid" in a for a in env.attempts())
    time.sleep(0.5)
    assert not [p for p in codex_pids(env) if alive(p)]


def test_a_stop_after_the_tries_are_opened_and_before_codex_starts_still_closes_them(env):
    """The sheet is opened (here a fake `open` that takes 5 s) after the tries are in the ledger and before any Codex call."""
    proc = subprocess.Popen([sys.executable, str(CLI), "imagegen", "mic", "--dir", str(env.dir), "--n", "2"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env={**os.environ, **env.env(FAKE_OPEN_DELAY="5")}, text=True)
    proc.stdin.write(PROMPT)
    proc.stdin.close()
    proc.stdin = None
    assert wait_for(lambda: env.opened())
    proc.send_signal(signal.SIGTERM)
    stdout, stderr = proc.communicate(timeout=30)
    assert proc.returncode == 1, stderr
    assert [a["status"] for a in env.attempts()] == ["interrupted", "interrupted"] and env.starts() == []


def test_a_killed_command_leaves_running_tries_that_the_next_reader_closes(env):
    proc = start_cli(env, "--n", "2")
    try:
        assert wait_for(lambda: len(env.starts()) == 2)
        proc.kill()
        proc.wait(timeout=10)
        assert [a["status"] for a in env.attempts()] == ["running", "running"]
    finally:
        for p in codex_pids(env):   # what SIGKILL leaves behind runs on; the test cleans it up
            try:
                os.killpg(p, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    code, out, raw, err = env.gen()
    assert code == 0 and out["results"][0]["image"] == "mic-3"
    assert [a["status"] for a in env.attempts()] == ["interrupted", "interrupted", "ok"]


# -- several at once ------------------------------------------------------------------------------------------------------

def overlap(calls: list[dict]) -> int:
    edges = sorted([(c["t"], 1) for c in calls if c["event"] == "start"] + [(c["t"], -1) for c in calls if c["event"] == "end"], key=lambda e: (e[0], e[1]))
    level = top = 0
    for _, d in edges:
        level += d
        top = max(top, level)
    return top


def test_one_command_runs_its_tries_at_once(env):
    t0 = time.monotonic()
    code, out, raw, err = env.gen("--n", "6", FAKE_CODEX_DELAY="1.5")
    assert code == 0 and len(out["results"]) == 6 and overlap(env.calls()) == 6
    assert time.monotonic() - t0 < 1.5 * 6


def test_commands_run_at_once_on_one_folder_lose_no_row_and_share_no_number(env):
    def launch(name, n, prompt):
        p = subprocess.Popen([sys.executable, str(CLI), "imagegen", name, "--dir", str(env.dir), "--n", str(n), "--no-open"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env={**os.environ, **env.env(FAKE_CODEX_DELAY="0.5")}, text=True)
        p.stdin.write(prompt)
        p.stdin.close()
        p.stdin = None
        return p
    procs = [launch("mic", 3, PROMPT), launch("mic", 3, PROMPT + " Second."), launch("sky", 2, "Portrait 9:16 aspect ratio. A night sky.")]
    outs = [json.loads(p.communicate(timeout=60)[0]) for p in procs]
    assert all(p.returncode == 0 for p in procs)
    mic = sorted(a["id"] for a in env.attempts("mic"))
    assert mic == sorted(f"mic-{k}" for k in range(1, 7)) and len(env.attempts("sky")) == 2
    assert sorted(x["image"] for o in outs[:2] for x in o["results"]) == mic
    assert sorted(o["request"] for o in outs[:2]) == [1, 2]
    from video import imageledger
    assert imageledger.validate(env.ledger()) == []
    assert sorted(p.name for p in env.dir.glob("*.png")) == sorted([f"{m}.png" for m in mic] + ["sky-1.png", "sky-2.png"])


# -- what the picture is ---------------------------------------------------------------------------------------------------

def test_a_transparent_request_reports_the_alpha_it_got(env):
    code, out, raw, err = env.gen("--transparent", FAKE_CODEX_SIZE="400x200")
    assert out["results"][0]["alpha"] == {"has_alpha": True, "transparent_share": 0.75}
    assert env.attempts()[0]["alpha"] == {"has_alpha": True, "transparent_share": 0.75} and "75% transparent" in err
    assert env.starts()[0]["transparent"] is True


def test_a_transparent_request_that_came_back_opaque_says_so(env):
    code, out, raw, err = env.gen("--transparent", FAKE_CODEX_NO_ALPHA="1")
    assert code == 0 and out["results"][0]["alpha"] == {"has_alpha": False, "transparent_share": 0.0} and "no alpha" in err


def test_an_opaque_request_reports_no_alpha_field(env):
    code, out, raw, err = env.gen()
    assert "alpha" not in out["results"][0] and "alpha" not in env.attempts()[0]


# -- no Codex ---------------------------------------------------------------------------------------------------------------

def test_without_codex_nothing_is_attempted(env):
    (env.bin / "codex").unlink()
    path = os.pathsep.join([str(env.bin)] + [d for d in os.environ["PATH"].split(os.pathsep) if not (Path(d) / "codex").exists()])
    code, out, raw, err = env.gen(PATH=path)
    assert code == 1 and "codex" in out["error"].lower() and not env.dir.exists()


def test_logged_out_nothing_is_attempted_and_the_message_names_codex_login(env):
    code, out, raw, err = env.gen(FAKE_CODEX_SCENARIO="logged_out")
    assert code == 1 and "codex login" in out["error"] and "browser" in out["error"]
    assert env.starts() == [] and not env.dir.exists()


# -- the ledger protects itself ---------------------------------------------------------------------------------------------

def dead_pid() -> int:
    p = subprocess.Popen(["true"])
    p.wait()
    return p.pid


def add_running_row(env, attempt_id: str, pid: int):
    doc = env.ledger()
    doc["names"][0]["requests"][-1]["attempts"].append({"id": attempt_id, "status": "running", "started": "2026-01-01T00:00:00+09:00", "pid": pid})
    (env.dir / "imagegen.json").write_text(json.dumps(doc, ensure_ascii=False))


@pytest.mark.parametrize("damage", ["truncate", "unknown_key", "wrong_type"])
def test_a_damaged_ledger_is_never_written_over(env, damage):
    assert env.gen()[0] == 0
    f = env.dir / "imagegen.json"
    doc = env.ledger()
    if damage == "truncate":
        f.write_text(f.read_text()[:40])
    else:
        if damage == "unknown_key":
            doc["names"][0]["requests"][0]["attempts"][0]["colour"] = "red"
        else:
            doc["names"][0]["requests"][0]["transparent"] = "no"
        f.write_text(json.dumps(doc))
    before = f.read_bytes()
    code, out, raw, err = env.gen()
    assert code == 2 and "nothing was written" in out["error"]
    assert f.read_bytes() == before and len(env.starts()) == 1


@pytest.mark.parametrize("damage", ["gap_in_numbers", "id_not_a_string", "file_not_a_string"])
def test_a_ledger_damaged_in_its_numbering_or_types_is_refused_with_a_reason(env, damage):
    assert env.gen("--n", "2")[0] == 0
    doc = env.ledger()
    attempts = doc["names"][0]["requests"][0]["attempts"]
    if damage == "gap_in_numbers":
        del attempts[0]
    elif damage == "id_not_a_string":
        attempts[0]["id"] = ["mic-1"]
    else:
        attempts[0]["file"] = ["mic-1.png"]
    f = env.dir / "imagegen.json"
    f.write_text(json.dumps(doc))
    before = f.read_bytes()
    code, out, raw, err = env.gen()
    assert code == 2 and "nothing was written" in out["error"] and f.read_bytes() == before, raw + err


def test_a_try_whose_process_died_is_closed_as_interrupted_by_the_next_reader(env):
    assert env.gen()[0] == 0
    add_running_row(env, "mic-2", dead_pid())
    assert env.gen()[0] == 0
    rows = {a["id"]: a for a in env.attempts()}
    assert rows["mic-2"]["status"] == "interrupted" and "file" not in rows["mic-2"] and "pid" not in rows["mic-2"]
    assert rows["mic-3"]["status"] == "ok"


def test_a_picture_placed_just_before_the_process_died_is_kept_on_the_interrupted_row(env):
    assert env.gen()[0] == 0
    add_running_row(env, "mic-2", dead_pid())
    shutil.copyfile(env.dir / "mic-1.png", env.dir / "mic-2.png")
    assert env.gen()[0] == 0
    rows = {a["id"]: a for a in env.attempts()}
    assert rows["mic-2"]["status"] == "interrupted" and rows["mic-2"]["file"] == "mic-2.png"
    assert "mic-2.png" in (env.dir / "contact-sheet.html").read_text()


def test_a_running_row_of_a_live_process_is_left_running(env):
    assert env.gen()[0] == 0
    sleeper = subprocess.Popen(["sleep", "30"])
    try:
        add_running_row(env, "mic-2", sleeper.pid)
        doc = env.ledger()
        doc["names"][0]["requests"][-1]["attempts"][-1]["started"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        doc["names"][0]["requests"][-1]["attempts"][-1]["started"] = doc["names"][0]["requests"][-1]["attempts"][-1]["started"][:-2] + ":" + doc["names"][0]["requests"][-1]["attempts"][-1]["started"][-2:]
        (env.dir / "imagegen.json").write_text(json.dumps(doc))
        assert env.gen()[0] == 0
        assert {a["id"]: a["status"] for a in env.attempts()}["mic-2"] == "running"
    finally:
        sleeper.kill()


# -- the contact sheet --------------------------------------------------------------------------------------------------------

def sheet_html(env) -> str:
    return (env.dir / "contact-sheet.html").read_text()


def stamp(env) -> str:
    return re.search(r'"([0-9a-f]{12})"', (env.dir / ".sheet-stamp.js").read_text())[1]


def test_the_sheet_shows_every_try_with_its_request_and_follows_the_ledger(env):
    ref = make_ref(env.root / "참조 1.png")
    assert env.gen("--ref", str(ref), "--label", "놋쇠 마이크, 청록 바탕", "--n", "2")[0] == 0
    html = sheet_html(env)
    first = stamp(env)
    assert first in html
    for word in ("mic", "놋쇠 마이크, 청록 바탕", "mic-1", "mic-2", "1672×941", f"프롬프트 ({len(PROMPT)}자)", "참조 1장", str(env.dir)):
        assert word in html, word
    for src in re.findall(r'<img src="([^"]+)"', html):
        from urllib.parse import unquote
        assert (env.dir / unquote(src)).resolve().is_file(), src
    assert "%EC%B0%B8%EC%A1%B0%201.png" in html   # 참조 1.png, URL-encoded
    assert env.gen(FAKE_CODEX_SCENARIO="refuse_input")[0] == 1
    html = sheet_html(env)
    assert stamp(env) != first and "실패 1건" in html and "refused" in html and "stage=input" in html


def test_the_sheet_escapes_what_it_quotes(env):
    code, out, raw, err = env.gen("--label", "<b>bold</b>", prompt=PROMPT + " <script>alert(1)</script>")
    html = sheet_html(env)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>bold</b>" not in html


def test_a_picture_that_cannot_be_chosen_is_still_shown_and_marked(env):
    assert env.gen(FAKE_CODEX_SCENARIO="rewrite,rewrite")[0] == 1
    html = sheet_html(env)
    assert 'src="mic-1.png"' in html and "prompt_altered" in html and "고를 수 없음" in html


def test_a_transparent_picture_shows_its_alpha_over_a_checkerboard(env):
    assert env.gen("--transparent")[0] == 0
    html = sheet_html(env)
    assert "투명 75%" in html and "repeating-conic-gradient" in html


def test_the_sheet_opens_once_and_only_when_asked(env):
    assert env.gen("--no-open")[0] == 0
    assert env.opened() == [] and "sheet_opened" not in env.ledger()
    assert env.gen()[0] == 0
    assert env.opened() == [str(env.dir / "contact-sheet.html")] and "sheet_opened" in env.ledger()
    assert env.gen()[0] == 0
    assert len(env.opened()) == 1


def test_a_sheet_that_could_not_be_opened_is_tried_again_next_time(env):
    code, out, raw, err = env.gen(FAKE_OPEN_EXIT="1")
    assert code == 0 and len(env.opened()) == 1 and "sheet_opened" not in env.ledger()
    assert "contact-sheet.html" in err
    assert env.gen()[0] == 0
    assert len(env.opened()) == 2 and "sheet_opened" in env.ledger()


# -- imagenote --------------------------------------------------------------------------------------------------------------

def test_choosing_noting_and_assessing_a_picture_reach_the_ledger_and_the_sheet(env):
    assert env.gen("--n", "2")[0] == 0
    code, out, raw, err = env.note("mic-2", "--choose", "--note", "왼쪽 것이 더 낫다, 금색이 덜 탁해서", "--critique", "Brass reads warm; the stand is cut off at the bottom.")
    assert code == 0, raw + err
    assert out["sheet"] == str(env.dir / "contact-sheet.html") and out["ledger"] == str(env.dir / "imagegen.json") and len(out["written"]) == 3
    row = {a["id"]: a for a in env.attempts()}["mic-2"]
    assert row["chosen"] is True and [n["text"] for n in row["notes"]] == ["왼쪽 것이 더 낫다, 금색이 덜 탁해서"] and row["critique"].startswith("Brass reads warm")
    html = sheet_html(env)
    assert "선택" in html and "왼쪽 것이 더 낫다, 금색이 덜 탁해서" in html and "Brass reads warm" in html and "선택 mic-2" in html


def test_notes_append_and_a_critique_replaces(env):
    assert env.gen()[0] == 0
    env.note("mic-1", "--note", "first", "--critique", "old view")
    env.note("mic-1", "--note", "second", "--critique", "new view")
    row = env.attempts()[0]
    assert [n["text"] for n in row["notes"]] == ["first", "second"] and row["critique"] == "new view"
    html = sheet_html(env)
    assert "new view" in html and "old view" not in html


def test_a_name_takes_notes_only(env):
    assert env.gen()[0] == 0
    code, out, raw, err = env.note("mic", "--note", "이 소품은 화면 오른쪽 아래에 작게")
    assert code == 0 and [n["text"] for n in env.ledger()["names"][0]["notes"]] == ["이 소품은 화면 오른쪽 아래에 작게"]
    assert "이 소품은 화면 오른쪽 아래에 작게" in sheet_html(env)
    for flag in (["--choose"], ["--unchoose"], ["--critique", "x"]):
        code, out, raw, err = env.note("mic", *flag)
        assert code == 2 and "name" in out["error"]


def test_choosing_again_or_unchoosing_an_unchosen_picture_succeeds_and_changes_nothing(env):
    assert env.gen()[0] == 0
    code, out, raw, err = env.note("mic-1", "--unchoose")
    assert code == 0 and "already" in out["written"][0] and "chosen" not in env.attempts()[0]
    before = stamp(env)
    assert env.note("mic-1", "--unchoose")[0] == 0 and stamp(env) == before
    assert env.note("mic-1", "--choose")[0] == 0 and env.note("mic-1", "--choose")[1]["written"] == ["mic-1: chosen (already)"]
    assert env.note("mic-1", "--unchoose")[0] == 0 and "chosen" not in env.attempts()[0]


@pytest.mark.parametrize("scenario", ["rewrite,rewrite", "refuse_input"])
def test_only_an_ok_picture_can_be_chosen(env, scenario):
    env.gen(FAKE_CODEX_SCENARIO=scenario)
    before = (env.dir / "imagegen.json").read_bytes()
    code, out, raw, err = env.note("mic-1", "--choose")
    assert code == 2 and "not ok" in out["error"] and (env.dir / "imagegen.json").read_bytes() == before


@pytest.mark.parametrize("args, words", [
    (["mic-1"], "nothing to write"),
    (["mic-9", "--note", "x"], "neither"),
    (["sky", "--note", "x"], "neither"),
])
def test_imagenote_refuses_what_it_cannot_write(env, args, words):
    assert env.gen()[0] == 0
    before = (env.dir / "imagegen.json").read_bytes()
    code, out, raw, err = env.note(*args)
    assert code == 2 and words in out["error"] and (env.dir / "imagegen.json").read_bytes() == before


def test_imagenote_without_a_ledger_is_refused_and_writes_nothing(env):
    env.dir.mkdir(parents=True)
    code, out, raw, err = env.note("mic-1", "--choose")
    assert code == 2 and "imagegen.json" in out["error"] and list(env.dir.iterdir()) == []


def test_choose_and_unchoose_cannot_go_together(env):
    assert env.gen()[0] == 0
    code, out, raw, err = env.note("mic-1", "--choose", "--unchoose")
    assert code == 2


def test_a_note_written_while_imagegen_runs_is_kept(env):
    assert env.gen()[0] == 0
    p = subprocess.Popen([sys.executable, str(CLI), "imagegen", "mic", "--dir", str(env.dir), "--n", "4", "--no-open"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env={**os.environ, **env.env(FAKE_CODEX_DELAY="1.0")}, text=True)
    p.stdin.write(PROMPT)
    p.stdin.close()
    p.stdin = None
    assert wait_for(lambda: len(env.starts()) >= 3)
    for i in range(5):
        assert env.note("mic-1", "--note", f"note {i}")[0] == 0
    p.communicate(timeout=60)
    assert p.returncode == 0
    row = env.attempts()[0]
    assert [n["text"] for n in row["notes"]] == [f"note {i}" for i in range(5)]
    assert [a["status"] for a in env.attempts()] == ["ok"] * 5

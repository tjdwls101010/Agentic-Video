"""The Codex CLI as an image generator: one `codex exec` per picture through its built-in image_gen tool (gpt-image), on the user's Codex login.

What this unit hands back is a `Run` in the skill's terms: the picture file if one was made, the prompt image_gen received and whether that was observed or only reported by Codex, the hashes of the reference images it received, and, when there is no picture, whether moderation blocked it and at which stage. Codex's event shapes, file layout and error encoding stay inside.

The observation comes first: the thread's rollout records each generation with the prompt the tool received (`rollout`). Codex's own report in its final message is used only as an admission that it changed the prompt; it never stands in for an observation. Without an observation the picture is the one PNG in the thread's folder, or none.

image_gen takes a prompt, optional referenced_image_paths and an optional transparent_background, and nothing else: no size, quality, mask, seed or output path.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import envelope, rollout

__all__ = ["Run", "run", "executable", "login_status", "home", "terminate_all"]

_GRACE_S = 3.0


@dataclass
class Run:
    elapsed_s: float
    thread_id: str | None = None
    returncode: int | None = None
    timed_out: bool = False
    interrupted: bool = False   # terminate_all stopped it
    error: str | None = None    # Codex itself failed: could not start, non-zero exit, no final message
    image: Path | None = None
    passed: str | None = None   # the prompt image_gen received
    observed: bool = False      # `passed` comes from the rollout
    reported: str | None = None  # the prompt Codex says it passed (its own report)
    inputs: list[dict] | None = None  # observed reference images: [{path, sha256}]
    refused: bool = False
    stage: str | None = None    # input | output, when moderation said
    reason: dict = field(default_factory=dict)  # code, message, categories
    generations: int = 0        # completed generations in the thread
    log: str | None = None      # the thread's rollout
    note: str | None = None     # why there is no picture or no observation, when nothing else says
    agent_message: str | None = None


def home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def executable() -> str | None:
    return shutil.which("codex")


def login_status() -> tuple[bool, str]:
    try:
        r = subprocess.run(["codex", "login", "status"], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"codex login status failed: {exc}"
    text = (r.stdout + r.stderr).strip()
    return r.returncode == 0 and "Logged in" in text, text


# Codex runs in its own session so its children can be stopped as a group; that also means they do not die with this process. Every live run is registered here so a stop signal can end them all.
_live: dict[int, subprocess.Popen] = {}
_live_lock = threading.Lock()
_stopping = threading.Event()
_signalled: set[int] = set()   # groups terminate_all ended; a run that finished before it is not among them


def _kill_group(pid: int, sig: int) -> None:
    try:
        os.killpg(pid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def _stop(proc: subprocess.Popen) -> None:
    """SIGTERM to the group, a grace period, then SIGKILL to the group whether or not the parent already exited, since its children can outlive it."""
    _kill_group(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=_GRACE_S)
    except subprocess.TimeoutExpired:
        pass
    _kill_group(proc.pid, signal.SIGKILL)
    try:
        proc.wait(timeout=_GRACE_S)
    except subprocess.TimeoutExpired:
        pass


def terminate_all() -> None:
    """End every running Codex group: SIGTERM to all, one shared grace period, then SIGKILL to all. Runs started afterwards do not start. Safe to call from a signal handler: it takes no file lock."""
    _stopping.set()
    with _live_lock:
        procs = list(_live.values())
        _signalled.update(p.pid for p in procs)
    for p in procs:
        _kill_group(p.pid, signal.SIGTERM)
    deadline = time.monotonic() + _GRACE_S
    for p in procs:
        try:
            p.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for p in procs:
        _kill_group(p.pid, signal.SIGKILL)


def _observe(result: Run, started: float) -> None:
    folder = home() / "generated_images" / result.thread_id
    path = rollout.find(home(), result.thread_id, datetime.date.fromtimestamp(started))
    record = None
    if path is not None:
        result.log = str(path)
        try:
            record = rollout.read(path)
        except OSError as exc:
            result.note = f"the rollout could not be read ({exc})"
    gens = record.generations if record else []
    done = [g for g in gens if g.status == "completed" and g.saved is not None and g.saved.is_file()]
    if done:
        chosen = done[-1]
        result.image, result.inputs, result.generations = chosen.saved, chosen.inputs, len(done)
        if chosen.prompt is not None:
            result.passed, result.observed = chosen.prompt, True
        return
    failed = [g for g in gens if g.status != "completed" and g.prompt is not None]
    if failed:
        result.passed, result.observed, result.inputs = failed[-1].prompt, True, failed[-1].inputs
    if record and record.errors:
        chosen_err = next((e for e in record.errors if rollout.stage(e) == "output"), record.errors[-1])
        result.reason = {k: str(chosen_err[k])[:500] for k in ("code", "message") if chosen_err.get(k)}
        cats = (chosen_err.get("moderation_details") or {}).get("categories") if isinstance(chosen_err.get("moderation_details"), dict) else None
        if isinstance(cats, list) and cats:
            result.reason["categories"] = [str(c) for c in cats]
        result.refused = chosen_err.get("code") == "moderation_blocked"
        result.stage = rollout.stage(chosen_err)
        return
    missing = [g for g in gens if g.status == "completed"]
    pngs = sorted(folder.glob("*.png")) if folder.is_dir() else []
    if len(pngs) == 1:
        result.image = pngs[0]
        result.note = "the rollout names a picture that does not exist; the one PNG in the thread's folder was taken unverified" if missing else "no generation in the rollout; the one PNG in the thread's folder was taken unverified"
    elif len(pngs) > 1:
        result.note = f"no generation in the rollout and {len(pngs)} PNGs in the thread's folder; none was taken because which one this run made cannot be told"
    elif missing:
        result.note = f"the rollout names {missing[-1].saved}, which does not exist"
    elif failed:
        result.note = "the generation failed and Codex recorded no reason"
    elif path is None:
        result.note = "no rollout for this thread and no picture in its folder"
    else:
        result.note = "no generation in the rollout and no picture in the thread's folder"


def run(prompt: str, *, refs: list[Path], transparent: bool, stronger: bool, timeout: float) -> Run:
    """One `codex exec` asking image_gen for one picture, ended after `timeout` seconds. The envelope, events and last message live in a temporary folder that is removed afterwards; the thread's rollout stays in Codex's folder and is named in `log`."""
    started = time.time()
    result = Run(elapsed_s=0)
    if _stopping.is_set():
        result.interrupted = True
        return result
    work = Path(tempfile.mkdtemp(prefix="imagegen-"))
    try:
        schema_file, last_file = work / "schema.json", work / "last.json"
        schema_file.write_text(json.dumps(envelope.SCHEMA), encoding="utf-8")
        text = envelope.build(prompt, refs, transparent, stronger).encode("utf-8")
        argv = ["codex", "exec", "--json", "--skip-git-repo-check", "-s", "read-only", "--output-schema", str(schema_file), "-o", str(last_file), "-"]
        try:
            proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work, start_new_session=True)
        except OSError as exc:
            result.error = f"could not start codex: {exc}"
            return result
        with _live_lock:
            _live[proc.pid] = proc
        try:
            if _stopping.is_set():
                with _live_lock:
                    _signalled.add(proc.pid)
                _stop(proc)
            try:
                out, err = proc.communicate(input=text, timeout=max(0.1, timeout))
            except subprocess.TimeoutExpired:
                result.timed_out = True
                _stop(proc)
                out, err = proc.communicate()
        finally:
            with _live_lock:
                _live.pop(proc.pid, None)
        result.elapsed_s = round(time.time() - started, 1)
        result.returncode = proc.returncode
        if proc.pid in _signalled and not result.timed_out:
            result.interrupted = True

        messages = []
        for line in out.decode("utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
                result.thread_id = result.thread_id or event["thread_id"]
            item = event.get("item") or {}
            if isinstance(item, dict) and item.get("type") == "agent_message" and item.get("text"):
                messages.append(item["text"])
        if messages:
            result.agent_message = messages[-1][:300]
        if result.timed_out or result.interrupted:
            return result
        if proc.returncode != 0:
            result.error = f"codex exited {proc.returncode}: {err.decode(errors='replace')[-400:].strip()}"
            return result
        if not last_file.exists():
            result.error = "codex produced no final message"
            return result
        try:
            payload = json.loads(last_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("prompt_passed"), str):
            result.reported = payload["prompt_passed"]
        if result.thread_id is None:
            result.note = "codex reported no thread id, so neither its record nor its picture folder can be found"
            return result
        _observe(result, started)
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)

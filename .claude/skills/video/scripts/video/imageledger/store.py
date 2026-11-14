"""Reading and writing imagegen.json: one lock per folder across processes and threads, a full check before every write, an atomic rename, and closing attempts whose process has died."""

from __future__ import annotations

import datetime
import fcntl
import json
import os
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from video.errors import InputError

from .schema import SCHEMA, validate

PROCESS_STARTED = time.time()

LEDGER = "imagegen.json"
LOCK = ".imagegen.lock"


def now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


@contextmanager
def _locked(folder: Path):
    # flock is held per open file description, so threads of one process exclude each other as well as other processes.
    with open(folder / LOCK, "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _load(folder: Path) -> dict:
    path = folder / LEDGER
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InputError(f"{path} is not valid JSON ({exc}); nothing was written. It is this tool's ledger only if it reads as one: repair it from the sheet or move it aside") from exc
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise InputError(f"{path} is not an imagegen ledger (schema {SCHEMA}); nothing was written. Give imagegen a folder of its own")
    problems = validate(doc)
    if problems:
        raise InputError(f"{path} does not match the imagegen ledger schema; nothing was written: {'; '.join(problems[:5])}")
    return doc


def _write(folder: Path, doc: dict) -> None:
    problems = validate(doc)
    if problems:
        raise RuntimeError("refusing to write imagegen.json, it would not validate: " + "; ".join(problems[:5]))
    tmp = folder / f".{LEDGER}.{os.getpid()}.{threading.get_ident()}.tmp"
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, folder / LEDGER)


def _alive(pid: int, started: str) -> bool:
    """Whether the process that opened an attempt still runs. A live pid that started after the attempt is a reused pid, not the writer."""
    try:
        attempt_start = datetime.datetime.fromisoformat(started).timestamp()
    except ValueError:
        attempt_start = None
    if pid == os.getpid():
        return attempt_start is None or attempt_start >= PROCESS_STARTED - 5
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    if attempt_start is None:
        return True
    try:
        ps = subprocess.run(["ps", "-o", "etime=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return True
    out = ps.stdout.strip()
    if ps.returncode != 0 or not out:
        return True  # the pid answered kill(0); without its age it cannot be called someone else's
    days, _, clock = out.rpartition("-")
    parts = [int(x) for x in clock.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    elapsed = (int(days) if days else 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]
    return time.time() - elapsed <= attempt_start + 5


def close_as_interrupted(folder: Path, attempt: dict) -> None:
    """A running attempt that will never finish. A PNG under its name means the process died between placing it and closing the row: the row claimed that name, so no one else wrote it, but where it came from was never checked."""
    attempt["status"] = "interrupted"
    attempt.pop("pid", None)
    if (folder / f"{attempt['id']}.png").is_file():
        attempt["file"] = f"{attempt['id']}.png"


def _close_dead(folder: Path, doc: dict) -> bool:
    changed = False
    for entry in doc["names"]:
        for request in entry["requests"]:
            for attempt in request["attempts"]:
                if attempt["status"] == "running" and not _alive(attempt.get("pid", 0), attempt.get("started", "")):
                    close_as_interrupted(folder, attempt)
                    changed = True
    return changed


def exists(folder: Path) -> bool:
    return (folder / LEDGER).is_file()


def check_folder(folder: Path) -> None:
    """Refuse, writing nothing (not even the lock file), a folder whose imagegen.json is not a valid ledger of this schema."""
    if exists(folder):
        _load(folder)


def read(folder: Path) -> dict:
    if not exists(folder):
        raise InputError(f"no {LEDGER} in {folder}: imagegen has made nothing there yet")
    with _locked(folder):
        doc = _load(folder)
        if _close_dead(folder, doc):
            _write(folder, doc)
        return doc


@contextmanager
def edit(folder: Path, create: bool = False):
    """Read, change and write under the folder's lock. Nothing is written if the body raises. With `create`, a folder with no ledger starts an empty one."""
    if not create and not exists(folder):
        raise InputError(f"no {LEDGER} in {folder}: imagegen has made nothing there yet")
    folder.mkdir(parents=True, exist_ok=True)
    with _locked(folder):
        doc = _load(folder) if exists(folder) else {"schema": SCHEMA, "created": now(), "names": []}
        _close_dead(folder, doc)
        yield doc
        _write(folder, doc)

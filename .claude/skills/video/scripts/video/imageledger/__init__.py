"""The picture ledger, imagegen.json: one per folder, holding every request and every try made there, and the user's and Claude's judgments of them.

Every write holds the folder's lock, checks the whole document against the schema and replaces the file atomically. Reading closes attempts left `running` by a process that has died, as `interrupted`.

A name (`mic`) holds requests in order; a request is one prompt with its references, and its attempts are the tries made from it. An attempt's id and file name, `<name>-<k>`, count every try under that name, failed ones included, so no run ever reuses a file name. A running attempt changes to its result exactly once.
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from video.errors import InputError

from .schema import ATTEMPT_ID, SCHEMA, STATUSES, validate
from .store import LEDGER, LOCK, check_folder, close_as_interrupted, edit, exists, now, read

__all__ = ["LEDGER", "LOCK", "SCHEMA", "STATUSES", "check_name", "check_folder", "exists", "read", "validate", "open_request", "open_again", "finish", "interrupt", "judge", "find_attempt"]

_TRAILING_NUMBER = re.compile(r".*-\d+")


def check_name(raw: str) -> str:
    """The NFC form of a picture's name, or InputError. A name becomes the file name `<name>-<k>.png`, so it may not be empty, hold a path separator or a control character, start with a dot, or end in -<digits> (which reads as an attempt id)."""
    name = unicodedata.normalize("NFC", raw)
    if not name.strip():
        raise InputError("NAME is empty")
    if name != name.strip():
        raise InputError(f"NAME {raw!r} starts or ends with a space")
    if "/" in name or "\\" in name or ":" in name or any(unicodedata.category(c).startswith("C") for c in name):
        raise InputError(f"NAME {raw!r} holds a path separator or a control character; it becomes part of a file name")
    if name.startswith("."):
        raise InputError(f"NAME {raw!r} starts with a dot, which hides the file")
    if _TRAILING_NUMBER.fullmatch(name):
        raise InputError(f"NAME {raw!r} ends in -<number>, which reads as a picture id such as mic-2; choose another name")
    return name


def _entry(doc: dict, name: str, create: bool) -> dict | None:
    for entry in doc["names"]:
        if entry["name"] == name:
            return entry
        if entry["name"].casefold() == name.casefold():
            raise InputError(f"NAME {name!r} differs from {entry['name']!r}, already in this folder, only in case; on macOS their files would be the same file")
    if not create:
        return None
    entry = {"name": name, "notes": [], "requests": []}
    doc["names"].append(entry)
    return entry


def _new_attempts(entry: dict, request: dict, n: int) -> list[dict]:
    k = sum(len(r["attempts"]) for r in entry["requests"])
    rows = []
    for i in range(n):
        row = {"id": f"{entry['name']}-{k + i + 1}", "status": "running", "started": now(), "pid": os.getpid()}
        request["attempts"].append(row)
        rows.append(dict(row))
    return rows


def open_request(folder: Path, name: str, *, prompt: str, refs: list[dict], transparent: bool, label: str | None, n: int) -> tuple[int, list[dict]]:
    """Record a new request under `name` and open `n` running attempts for it, in one locked write, so two commands run at once never get the same numbers. Returns the request number and the attempt rows."""
    with edit(folder, create=True) as doc:
        entry = _entry(doc, name, create=True)
        request = {"r": len(entry["requests"]) + 1, "created": now(), "prompt": prompt, "refs": refs, "transparent": transparent, "attempts": []}
        if label:
            request["label"] = label
        entry["requests"].append(request)
        rows = _new_attempts(entry, request, n)
        return request["r"], rows


def find_attempt(doc: dict, attempt_id: str) -> tuple[dict, dict, dict]:
    """(name entry, request, attempt) for an id such as mic-2, or InputError."""
    for entry in doc["names"]:
        for request in entry["requests"]:
            for attempt in request["attempts"]:
                if attempt["id"] == attempt_id:
                    return entry, request, attempt
    raise InputError(f"no picture {attempt_id!r} in this folder's {LEDGER}")


def open_again(folder: Path, attempt_id: str, n: int, check=None) -> tuple[dict, list[dict]]:
    """Open `n` more attempts on the request that made `attempt_id`. `check(request)` runs under the lock first and may raise to refuse. Returns a copy of the request and the new rows."""
    with edit(folder) as doc:
        entry, request, _ = find_attempt(doc, attempt_id)
        if check is not None:
            check(request)
        rows = _new_attempts(entry, request, n)
        return {k: v for k, v in request.items() if k != "attempts"}, rows


def finish(folder: Path, attempt_id: str, fields: dict) -> dict:
    """Turn a running attempt into its result; `fields` holds the final `status`. A row that is no longer running (closed as interrupted by another reader) is left as it is and returned."""
    with edit(folder) as doc:
        _, _, attempt = find_attempt(doc, attempt_id)
        if attempt["status"] == "running":
            attempt.pop("pid", None)
            attempt.update(fields)
        return dict(attempt)


def interrupt(folder: Path, attempt_ids: list[str]) -> None:
    """Close the given attempts that are still running as interrupted (the command was stopped)."""
    with edit(folder) as doc:
        for aid in attempt_ids:
            _, _, attempt = find_attempt(doc, aid)
            if attempt["status"] == "running":
                close_as_interrupted(folder, attempt)


def judge(folder: Path, target: str, *, choose: bool | None, notes: list[str], critique: str | None) -> list[str]:
    """Write the user's choice, their words and Claude's assessment. `target` is a picture id or a name; `choose` True picks, False unpicks, None leaves it. Returns what was written, in words."""
    with edit(folder) as doc:
        if ATTEMPT_ID.fullmatch(target) and _is_attempt(doc, target):
            _, _, attempt = find_attempt(doc, target)
            written = []
            if choose is True:
                if attempt["status"] != "ok":
                    raise InputError(f"{target} is {attempt['status']}, not ok: only an ok picture can be chosen")
                written.append(f"{target}: chosen" + (" (already)" if attempt.get("chosen") else ""))
                attempt["chosen"] = True
            elif choose is False:
                written.append(f"{target}: not chosen" + ("" if attempt.pop("chosen", None) else " (already)"))
            for text in notes:
                attempt.setdefault("notes", []).append({"text": text, "at": now()})
                written.append(f"{target}: note added")
            if critique is not None:
                attempt["critique"] = critique
                written.append(f"{target}: critique replaced")
            return written
        entry = _entry(doc, unicodedata.normalize("NFC", target), create=False)
        if entry is None:
            raise InputError(f"{target!r} is neither a picture id nor a name in this folder's {LEDGER}")
        if choose is not None or critique is not None:
            raise InputError(f"{target!r} is a name; --choose, --unchoose and --critique belong to one picture such as {target}-1")
        for text in notes:
            entry["notes"].append({"text": text, "at": now()})
        return [f"{target}: note added"] * len(notes)


def _is_attempt(doc: dict, target: str) -> bool:
    return any(a["id"] == target for e in doc["names"] for r in e["requests"] for a in r["attempts"])

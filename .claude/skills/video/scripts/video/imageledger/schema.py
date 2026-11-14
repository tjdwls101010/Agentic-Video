"""The shape of imagegen.json (schema 1), checked in full before every write.

Unknown keys are errors: the ledger grows by decision, not by a typo that silently drops a field from the sheet.
"""

from __future__ import annotations

import re

SCHEMA = 1

STATUSES = ("running", "ok", "prompt_altered", "refused", "no_image", "executor_error", "timeout", "interrupted")
VERBATIM = ("exact", "normalized", "mismatch", "unverified")
STAGES = ("input", "output", "unknown")

# key: (type or tuple of types, required)
TOP = {"schema": (int, True), "created": (str, True), "sheet_opened": (str, False), "names": (list, True)}
NAME = {"name": (str, True), "notes": (list, True), "requests": (list, True)}
NOTE = {"text": (str, True), "at": (str, True)}
REQUEST = {"r": (int, True), "created": (str, True), "prompt": (str, True), "refs": (list, True), "transparent": (bool, True), "label": (str, False), "attempts": (list, True)}
REF = {"path": (str, True), "sha256": (str, True)}
ATTEMPT = {"id": (str, True), "status": (str, True), "started": (str, True), "pid": (int, False), "elapsed_s": ((int, float), False), "file": (str, False), "w": (int, False), "h": (int, False),
           "alpha": (dict, False), "verbatim": (str, False), "retried": (dict, False), "thread_id": (str, False), "detail": (dict, False),
           "chosen": (bool, False), "critique": (str, False), "notes": (list, False)}
ALPHA = {"has_alpha": (bool, True), "transparent_share": ((int, float), True)}
RETRIED = {"thread_id": (str, False), "elapsed_s": ((int, float), False), "verbatim": (str, False)}
DETAIL = {"stage": (str, False), "code": (str, False), "message": (str, False), "categories": (list, False), "generations": (int, False), "returncode": (int, False),
          "agent_message": (str, False), "log": (str, False), "observed": (bool, False), "refs_sent": (list, False), "note": (str, False)}

ATTEMPT_ID = re.compile(r"(?P<name>.+)-(?P<k>[1-9]\d*)")


def _shape(where: str, obj, spec: dict, errors: list) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{where}: expected an object, got {type(obj).__name__}")
        return False
    for key, (kind, required) in spec.items():
        if key not in obj:
            if required:
                errors.append(f"{where}: missing required key '{key}'")
            continue
        value = obj[key]
        if isinstance(value, bool) and kind in (int, (int, float)):
            errors.append(f"{where}: '{key}' must be a number, got bool")
        elif not isinstance(value, kind):
            names = kind.__name__ if isinstance(kind, type) else "/".join(k.__name__ for k in kind)
            errors.append(f"{where}: '{key}' must be {names}, got {type(value).__name__}")
    for key in sorted(set(obj) - set(spec)):
        errors.append(f"{where}: unknown key '{key}'")
    return True


def _notes(where: str, notes, errors: list) -> None:
    for i, note in enumerate(notes if isinstance(notes, list) else []):
        _shape(f"{where}.notes[{i}]", note, NOTE, errors)


def validate(doc) -> list[str]:
    errors: list[str] = []
    if not _shape("ledger", doc, TOP, errors):
        return errors
    if doc.get("schema") != SCHEMA:
        errors.append(f"ledger: schema must be {SCHEMA}, got {doc.get('schema')!r}")
    seen_names: set[str] = set()
    ids: set[str] = set()
    files: set[str] = set()
    for entry in doc.get("names") if isinstance(doc.get("names"), list) else []:
        where = f"names[{entry.get('name')!r}]" if isinstance(entry, dict) else "names[]"
        if not _shape(where, entry, NAME, errors):
            continue
        name = entry.get("name")
        if isinstance(name, str):
            if name.casefold() in seen_names:
                errors.append(f"{where}: another name differs from it only in case")
            seen_names.add(name.casefold())
        _notes(where, entry.get("notes"), errors)
        numbers = []
        order: list = []
        for request in entry.get("requests") if isinstance(entry.get("requests"), list) else []:
            rw = f"{where}.requests[r={request.get('r')}]" if isinstance(request, dict) else f"{where}.requests[]"
            if not _shape(rw, request, REQUEST, errors):
                continue
            numbers.append(request.get("r"))
            for i, ref in enumerate(request.get("refs") if isinstance(request.get("refs"), list) else []):
                _shape(f"{rw}.refs[{i}]", ref, REF, errors)
            for attempt in request.get("attempts") if isinstance(request.get("attempts"), list) else []:
                aw = f"{rw}.attempts[{attempt.get('id')!r}]" if isinstance(attempt, dict) else f"{rw}.attempts[]"
                if not _shape(aw, attempt, ATTEMPT, errors):
                    continue
                aid = attempt.get("id")
                order.append(aid)
                m = ATTEMPT_ID.fullmatch(aid) if isinstance(aid, str) else None
                if not m or m["name"] != name:
                    errors.append(f"{aw}: id must be {name}-<k>")
                if isinstance(aid, str):
                    if aid in ids:
                        errors.append(f"{aw}: duplicate attempt id")
                    ids.add(aid)
                status = attempt.get("status")
                if status not in STATUSES:
                    errors.append(f"{aw}: status must be one of {list(STATUSES)}, got {status!r}")
                if status == "running" and "pid" not in attempt:
                    errors.append(f"{aw}: a running attempt needs its pid")
                if status in ("ok", "prompt_altered") and "file" not in attempt:
                    errors.append(f"{aw}: a {status} attempt needs its file")
                if attempt.get("verbatim") is not None and attempt["verbatim"] not in VERBATIM:
                    errors.append(f"{aw}: verbatim must be one of {list(VERBATIM)}")
                if "chosen" in attempt and (attempt["chosen"] is not True or status != "ok"):
                    errors.append(f"{aw}: only an ok attempt can be chosen, and chosen is written only as true")
                if "alpha" in attempt:
                    _shape(f"{aw}.alpha", attempt["alpha"], ALPHA, errors)
                if "retried" in attempt:
                    _shape(f"{aw}.retried", attempt["retried"], RETRIED, errors)
                if "detail" in attempt and _shape(f"{aw}.detail", attempt["detail"], DETAIL, errors):
                    stage = attempt["detail"].get("stage")
                    if stage is not None and stage not in STAGES:
                        errors.append(f"{aw}.detail: stage must be one of {list(STAGES)}")
                _notes(aw, attempt.get("notes"), errors)
                f = attempt.get("file")
                if isinstance(f, str):
                    if f in files:
                        errors.append(f"{aw}: file {f!r} already belongs to another attempt")
                    files.add(f)
        if numbers != list(range(1, len(numbers) + 1)):
            errors.append(f"{where}: requests must be numbered 1, 2, … in order, got {numbers}")
        # Every try under a name takes the next number, failed ones included, so the ids in order are exactly name-1 … name-N; a gap would make the next try reuse a number.
        if isinstance(name, str) and order != [f"{name}-{k}" for k in range(1, len(order) + 1)]:
            errors.append(f"{where}: attempts must be numbered {name}-1, {name}-2, … in order across its requests")
    return errors

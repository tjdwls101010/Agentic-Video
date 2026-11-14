"""What a thread's rollout records about its image generations: the generation items in order, and the reason a generation failed.

The rollout is Codex's own session transcript, `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<time>-<thread id>.jsonl`, written in full by the time `codex exec` exits. A generation is an `event_msg` line whose `payload.item` has `kind: image_gen.generation` and `revisedPrompt` (the prompt the tool received), `savedPath`, `inputImages` and `status`. A failed generation carries `failure: null`; its reason is in the tool's output text as the API's error object, serialised as a JSON string inside Rust's `Some(...)`. The reason is read by structure, not by a known code, so a code never seen before still arrives with its message. This is an internal format, not an interface Codex documents.
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

MARKER = "image generation failed:"
KIND = "image_gen.generation"


@dataclass
class Generation:
    status: str | None
    prompt: str | None
    saved: Path | None
    inputs: list[dict] | None


@dataclass
class Record:
    path: Path
    generations: list[Generation] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    unreadable_lines: int = 0


def _strings(node) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


def _parse_error(text: str) -> dict | None:
    at = text.find(MARKER)
    if at < 0:
        return None
    tail = text[at + len(MARKER):].strip()
    if "Some(" in tail:
        body = tail[tail.index("Some(") + 5:].rstrip()
        if body.endswith(")"):
            body = body[:-1]
        try:
            payload = json.loads(body)
            if isinstance(payload, str):
                payload = json.loads(payload)
        except (json.JSONDecodeError, ValueError):
            payload = None
        if isinstance(payload, dict):
            err = payload.get("error", payload)
            if isinstance(err, dict):
                return err
    # The wrapper is Codex's and can change; the reason is still in the text, so keep it verbatim.
    return {"message": tail}


def _generation(item: dict) -> Generation:
    saved = item.get("savedPath")
    inputs = item.get("inputImages")
    return Generation(status=item.get("status") if isinstance(item.get("status"), str) else None,
                      prompt=item.get("revisedPrompt") if isinstance(item.get("revisedPrompt"), str) else None,
                      saved=Path(saved) if isinstance(saved, str) and saved else None,
                      inputs=[{"path": str(i.get("path")), "sha256": str(i.get("sha256"))} for i in inputs if isinstance(i, dict)] if isinstance(inputs, list) else None)


def find(codex_home: Path, thread_id: str, around: datetime.date) -> Path | None:
    """The thread's rollout file. Day folders around the run's date are searched first; the whole sessions tree only if they hold none."""
    sessions = codex_home / "sessions"
    for day in (around, around - datetime.timedelta(days=1), around + datetime.timedelta(days=1)):
        hits = sorted((sessions / day.strftime("%Y/%m/%d")).glob(f"rollout-*{thread_id}.jsonl"))
        if hits:
            return hits[-1]
    try:
        hits = sorted(sessions.glob(f"**/rollout-*{thread_id}.jsonl"))
    except OSError:
        return None
    return hits[-1] if hits else None


def read(path: Path) -> Record:
    record = Record(path=path)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            record.unreadable_lines += 1
            continue
        payload = event.get("payload") if isinstance(event, dict) else None
        item = payload.get("item") if isinstance(payload, dict) else None
        if isinstance(item, dict) and item.get("kind") == KIND:
            record.generations.append(_generation(item))
            continue
        if MARKER in line:
            record.errors += [e for e in (_parse_error(t) for t in _strings(event)) if e is not None]
    return record


def stage(err: dict) -> str | None:
    mod = err.get("moderation_details")
    value = mod.get("moderation_stage") if isinstance(mod, dict) else None
    return str(value) if isinstance(value, (str, int)) else None

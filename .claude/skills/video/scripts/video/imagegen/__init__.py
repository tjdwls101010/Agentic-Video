"""Generating pictures with gpt-image through Codex, and recording what was made and how it was judged.

`generate` is a queue: one request's tries are opened in the ledger together, at most CONCURRENCY Codex calls run at once, every prompt passes a verbatim gate, every try gets a picture name no run reuses, and every try ends as one ledger row whatever happened. Each try is reported on stderr the moment it ends, because a batch takes minutes and silence reads as a hang.
"""

from __future__ import annotations

import concurrent.futures
import os
import re
import signal
import sys
import threading
import time
import unicodedata
from pathlib import Path

from video import codex, imageledger
from video.errors import InputError, ToolError

from . import facts, sheet

__all__ = ["generate", "note", "TIMEOUT_S", "CONCURRENCY"]

TIMEOUT_S = 300
# Six calls have run together without failures (design's work and this skill's measurement); more is unmeasured.
CONCURRENCY = 6


def classify_verbatim(written: str, passed: str | None) -> str:
    if passed is None:
        return "unverified"
    if passed == written:
        return "exact"
    if " ".join(passed.split()) == " ".join(written.split()):
        return "normalized"
    return "mismatch"


ADVICE = {
    "executor_error": "Codex itself failed, or this try did, not the prompt: read the message, and run doctor if Codex will not start.",
    "timeout": "no answer within {timeout:g}s; one picture normally takes 30 s to a minute, so see whether Codex is slow right now before raising --timeout.",
    "prompt_altered": "Codex changed the prompt even after a retry: the picture is kept and on the sheet, and cannot be chosen.",
    "no_image": "no picture: the reason above is Codex's own, and its record of the try (log) may say more.",
    "interrupted": "the command was stopped before this try ended.",
}
REFUSAL = {
    "input": "the prompt was blocked: change what it asks for or how; the same words are refused again.",
    "output": "the picture made was blocked, not the prompt: rewording does not help, another try can.",
    "unknown": "moderation did not say which stage it blocked; read the message and decide.",
}


def _say(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


def _line(row: dict, timeout: float) -> str:
    status, secs = row["status"], f"{round(row.get('elapsed_s', 0))}s"
    if status == "ok":
        bits = [row["id"], "ok", f"{row['w']}x{row['h']}", f"verbatim {row['verbatim']}"]
        if row.get("retried"):
            bits.append("after one retry")
        if "alpha" in row:
            bits.append(f"{row['alpha']['transparent_share']:.0%} transparent" if row["alpha"]["has_alpha"] else "WARNING no alpha channel")
        bits.append(secs)
        return "  ".join(bits)
    d = row.get("detail") or {}
    head = [row["id"], "FAILED", status]
    if status == "refused":
        head.append(f"stage {d.get('stage', 'unknown')}")
    lines = ["  ".join([*head, secs])]
    said = d.get("message") or d.get("note")
    if said:
        lines.append("    " + " ".join(said.split())[:300])
    lines.append("    " + (REFUSAL.get(d.get("stage"), REFUSAL["unknown"]) if status == "refused" else ADVICE.get(status, "").format(timeout=timeout)))
    if d.get("log"):
        lines.append(f"    log: {d['log']}")
    return "\n".join(lines)


def _verbatim(written: str, res: codex.Run) -> str | None:
    """What reached image_gen against what was written. Only the observation can say exact or normalized; Codex's own report counts only when it admits a change."""
    if res.error or res.timed_out or res.interrupted:
        return None
    if res.observed:
        return classify_verbatim(written, res.passed)
    if res.reported is not None and classify_verbatim(written, res.reported) == "mismatch":
        return "mismatch"
    return "unverified"


def _one(folder: Path, request: dict, row: dict, timeout: float, stop: threading.Event) -> dict:
    if stop.is_set():
        return imageledger.finish(folder, row["id"], {"status": "interrupted"})
    prompt = request["prompt"]
    refs = [_ref_path(folder, r["path"]) for r in request["refs"]]
    deadline = time.monotonic() + timeout
    res = codex.run(prompt, refs=refs, transparent=request["transparent"], stronger=False, timeout=timeout)
    elapsed = res.elapsed_s
    verbatim = _verbatim(prompt, res)
    retried = None
    late = None
    if verbatim == "mismatch" and not stop.is_set():
        left = deadline - time.monotonic()
        if left <= 0:
            late = f"Codex changed the prompt, and no time was left within --timeout {timeout:g}s for the retry"
        else:
            _say(f"{row['id']}  Codex changed the prompt; trying once more with a stronger instruction")
            retried = {"verbatim": "mismatch", "elapsed_s": res.elapsed_s}
            if res.thread_id:
                retried["thread_id"] = res.thread_id
            res = codex.run(prompt, refs=refs, transparent=request["transparent"], stronger=True, timeout=left)
            elapsed += res.elapsed_s
            verbatim = _verbatim(prompt, res)

    if res.interrupted:
        status = "interrupted"
    elif res.timed_out:
        status = "timeout"
    elif res.error:
        status = "executor_error"
    elif verbatim == "mismatch" and res.image is not None:
        status = "prompt_altered"
    elif res.image is not None:
        status = "ok"
    else:
        status = "refused" if res.refused else "no_image"

    fields: dict = {"status": status, "elapsed_s": round(elapsed, 1)}
    if res.thread_id:
        fields["thread_id"] = res.thread_id
    if verbatim:
        fields["verbatim"] = verbatim
    if retried:
        fields["retried"] = retried
    detail: dict = {}
    if status == "refused":
        detail["stage"] = res.stage if res.stage in ("input", "output") else "unknown"
    detail.update({k: v for k, v in res.reason.items() if k in ("code", "message", "categories")})
    if res.error:
        detail["message"] = res.error
    if res.returncode not in (None, 0):
        detail["returncode"] = res.returncode
    if res.generations > 1:
        detail["generations"] = res.generations
    notes = [x for x in (res.note, late) if x]
    if notes:
        detail["note"] = "; ".join(notes)
    if status != "ok":
        if res.log:
            detail["log"] = res.log
        if res.agent_message and status in ("no_image", "executor_error"):
            detail["agent_message"] = res.agent_message
        detail["observed"] = res.observed
    if res.inputs is not None and sorted(i["sha256"] for i in res.inputs) != sorted(r["sha256"] for r in request["refs"]):
        detail["refs_sent"] = res.inputs
    if detail:
        fields["detail"] = detail
    if status in ("ok", "prompt_altered"):
        dest = folder / f"{row['id']}.png"
        facts.place_new(res.image, dest)
        fields["file"] = dest.name
        fields.update(facts.measure(dest, request["transparent"]))
    return imageledger.finish(folder, row["id"], fields)


def _result(folder: Path, row: dict) -> dict:
    out = {"image": row["id"]}
    if row.get("file"):
        out["file"] = str(folder / row["file"])
    out.update({k: row[k] for k in ("status", "w", "h", "alpha", "verbatim") if k in row})
    if row["status"] == "executor_error":
        out["error"] = (row.get("detail") or {}).get("message", "")
    return out


def _check_folder(folder: Path) -> None:
    """The ledger, the sheet and its stamp are files this command rewrites, so a folder holding someone else's under those names is refused before anything is written."""
    imageledger.check_folder(folder)
    if not imageledger.exists(folder):
        foreign = [f for f in (sheet.SHEET, sheet.STAMP) if (folder / f).exists()]
        if foreign:
            raise InputError(f"{folder} holds {', '.join(foreign)} but no {imageledger.LEDGER}: they are not this tool's, and it would overwrite them. Give imagegen a folder of its own")


def _guarded(folder: Path, request: dict, row: dict, timeout: float, stop: threading.Event) -> dict:
    try:
        finished = _one(folder, request, row, timeout, stop)
    except Exception as exc:  # noqa: BLE001 -- a crash must still close the try, or it stays running until the process dies
        message = f"{exc} already exists and is not in the ledger; it was left alone" if isinstance(exc, facts.Taken) else f"{type(exc).__name__}: {exc}"[:500]
        finished = imageledger.finish(folder, row["id"], {"status": "executor_error", "detail": {"message": message}})
    _say(_line(finished, timeout))
    _redraw(folder)
    return finished


def _redraw(folder: Path) -> Path:
    try:
        return sheet.publish(folder)
    except Exception as exc:  # noqa: BLE001 -- the try is recorded; a sheet that will not draw must not lose it
        _say(f"warning: the contact sheet could not be redrawn ({type(exc).__name__}: {exc})")
        return folder / sheet.SHEET


class _Stopped(Exception):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def _run_queue(folder: Path, request: dict, rows: list[dict], timeout: float, stop: threading.Event) -> str | None:
    """Run the tries, at most CONCURRENCY at once. Returns the signal's name when a stop came while they ran; each try has then closed itself (a stopped Codex call, or a try that never started, ends as interrupted)."""
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY)
    futures = []
    stopped_by = None
    try:
        try:
            for row in rows:
                futures.append(pool.submit(_guarded, folder, request, row, timeout, stop))
            for f in futures:
                f.result()
        except _Stopped as exc:
            stopped_by = exc.name
            for f in futures:
                f.result()
    finally:
        pool.shutdown(wait=True)
    return stopped_by


def _ref_path(folder: Path, stored: str) -> Path:
    return Path(os.path.normpath(folder / stored))


def _codex_ready() -> None:
    if not codex.executable():
        raise ToolError("codex is not on PATH: imagegen needs the Codex CLI, logged in with the user's ChatGPT account (doctor checks whether it is installed)")
    logged_in, said = codex.login_status()
    if not logged_in:
        raise ToolError(f"codex is not logged in ({said}): the user has to run `codex login`, which signs in through their browser, before anything can be generated")


def _open(folder: Path, name: str, *, prompt: str | None, refs: list[Path], transparent: bool, label: str | None, again: str | None, n: int) -> tuple[int, dict, list[dict]]:
    """Record the request (or find the one --again repeats) and open its tries; nothing is written when the arguments cannot work."""
    if again is None:
        missing = [str(p) for p in refs if not p.is_file()]
        if missing:
            raise InputError(f"--ref not found: {', '.join(missing)}")
        _check_folder(folder)
        _codex_ready()
        stored = [{"path": os.path.relpath(p, folder), "sha256": facts.sha256(p)} for p in refs]
        r, rows = imageledger.open_request(folder, name, prompt=prompt, refs=stored, transparent=transparent, label=label, n=n)
        return r, {"prompt": prompt, "refs": stored, "transparent": transparent}, rows
    m = re.fullmatch(r"(.+)-[1-9]\d*", again)
    if not m or unicodedata.normalize("NFC", m[1]) != name:
        raise InputError(f"--again {again!r} is not a picture of {name!r} (one such as {name}-1)")
    _check_folder(folder)
    if not imageledger.exists(folder):
        raise InputError(f"no {imageledger.LEDGER} in {folder}, so there is no {again} to repeat")

    def unchanged(request: dict) -> None:
        for ref in request["refs"]:
            path = _ref_path(folder, ref["path"])
            if not path.is_file():
                raise InputError(f"{again}'s reference {path} no longer exists, so the request cannot be repeated as it was; make a new request")
            if facts.sha256(path) != ref["sha256"]:
                raise InputError(f"{again}'s reference {path} has changed since the request was made, so it cannot be repeated as it was; make a new request")

    _codex_ready()
    request, rows = imageledger.open_again(folder, unicodedata.normalize("NFC", again), n, unchanged)
    return request["r"], request, rows


def generate(folder: Path, name: str, *, prompt: str | None, refs: list[Path], transparent: bool, label: str | None, again: str | None, n: int, timeout: float) -> dict:
    name = imageledger.check_name(name)
    stop = threading.Event()

    def handler(signum, frame):
        # Runs on the main thread, which may hold a file lock at that moment, so it takes none: it ends every Codex group and unwinds; the tries are closed after the locks are released.
        if stop.is_set():
            return
        stop.set()
        codex.terminate_all()
        raise _Stopped(signal.Signals(signum).name)

    previous = {s: signal.signal(s, handler) for s in _SIGNALS}
    rows: list[dict] = []
    stopped_by = None
    try:
        try:
            signal.pthread_sigmask(signal.SIG_BLOCK, _SIGNALS)
            try:
                r, request, rows = _open(folder, name, prompt=prompt, refs=refs, transparent=transparent, label=label, again=again, n=n)
            finally:
                signal.pthread_sigmask(signal.SIG_UNBLOCK, _SIGNALS)   # a stop that came while the tries were being opened is taken here, once their ids are known
            sheet_path = _redraw(folder)
            sheet.open_once(folder, sheet_path)
            _say(f"{name}: {len(rows)} tr{'y' if len(rows) == 1 else 'ies'} of request {r}, at most {CONCURRENCY} at once; contact sheet: {sheet_path}")
            stopped_by = _run_queue(folder, request, rows, timeout, stop)
        except _Stopped as exc:
            stopped_by = exc.name
        if stopped_by:
            if not rows:
                raise ToolError(f"stopped by {stopped_by} before any try was opened; nothing was generated")
            imageledger.interrupt(folder, [row["id"] for row in rows])
    finally:
        for s, h in previous.items():
            signal.signal(s, h)
    finished = [imageledger.find_attempt(imageledger.read(folder), row["id"])[2] for row in rows]
    results = [_result(folder, row) for row in finished]
    counts: dict[str, int] = {}
    for x in results:
        counts[x["status"]] = counts.get(x["status"], 0) + 1
    summary = f"{len(results)} requested · " + " · ".join(f"{c} {s}" for s, c in sorted(counts.items(), key=lambda kv: (kv[0] != "ok", kv[0])))
    out = {"summary": summary, "name": name, "request": r, "results": results, "sheet": str(_redraw(folder)), "ledger": str(folder / imageledger.LEDGER)}
    if stopped_by:
        out["error"] = f"stopped by {stopped_by}: its Codex calls were ended and the tries they had not finished are interrupted"
    elif not counts.get("ok"):
        out["error"] = "no picture came out ok; each result's status and the stderr lines say why"
    if not counts.get("ok"):
        out["_exit"] = 1
    return out


def note(folder: Path, target: str, *, choose: bool | None, notes: list[str], critique: str | None) -> dict:
    """Write the user's choice and words and Claude's assessment under the ledger's lock, then redraw the sheet."""
    if not imageledger.exists(folder):
        raise InputError(f"no {imageledger.LEDGER} in {folder}: imagegen has made nothing there")
    imageledger.check_folder(folder)
    written = imageledger.judge(folder, unicodedata.normalize("NFC", target), choose=choose, notes=notes, critique=critique)
    return {"written": written, "sheet": str(_redraw(folder)), "ledger": str(folder / imageledger.LEDGER)}

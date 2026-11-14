"""A stand-in for the Codex CLI that writes what the measured `codex-cli 0.167.1` writes (plan video-imagegen.md, 측정 원장 M1·M4), driven by FAKE_CODEX_SCENARIO.

It accepts only the argv the skill sends, reads the envelope from stdin, and writes: JSON events on stdout (no tool call among them, as measured), the last message to the -o file, the image under $CODEX_HOME/generated_images/<thread id>/, and a rollout under $CODEX_HOME/sessions/YYYY/MM/DD/ whose `image_gen.generation` item and `custom_tool_call_output` have the measured shape. Every exec appends start/end records to $CODEX_HOME/fake-calls.jsonl, so tests can see what was passed and how calls overlapped.

FAKE_CODEX_SCENARIO is a comma-separated list read by call number (the last entry repeats), so "rewrite,ok" alters the first call's prompt and not the retry's. Scenarios:
  ok                 observed and reported prompts equal the one sent
  normalized         image_gen received the prompt with whitespace changed
  rewrite            image_gen received a restructured prompt, and the report says so
  report_lies        image_gen received the prompt as sent, but the report claims a restructured one
  no_observation     the rollout holds no generation item; one PNG in the thread folder; the report matches
  no_observation_mismatch   as no_observation, but the report claims a restructured prompt
  no_rollout         no rollout file at all; one PNG in the thread folder
  no_thread          no thread.started event
  saved_missing      the generation item names a savedPath that does not exist, and no PNG is written
  two_generations    two completed generation items; the first picture is half size, the second full size
  broken_line        one unrelated rollout line is not JSON
  two_pngs           no generation item and two PNGs in the thread folder
  ref_hash_wrong     the observed inputImages carry a different sha256
  refuse_input       measured: moderation_blocked at the input stage
  refuse_output      the same shape with moderation_stage output (shape not measured: never reproduced)
  refuse_unknown     moderation_blocked without moderation_details
  failed_no_reason   a failed generation item and no reason anywhere
  failed_then_png    a failed generation item with no reason, and one PNG in the thread folder that no item names
  exit_nonzero       codex exits 1 after thread.started
  no_last            codex exits 0 without writing the last message
  hang / hang_stubborn   never answers; hang_stubborn's child ignores SIGTERM
  logged_out         `codex login status` fails
FAKE_CODEX_SIZE (WxH, default 1672x941), FAKE_CODEX_DELAY (seconds before answering, default 0.2; a comma-separated list is read by call number like the scenario), FAKE_CODEX_NO_ALPHA (a transparent request gets an RGB image), FAKE_CODEX_ALPHA (any request gets an RGBA image).
"""

from __future__ import annotations

import datetime
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

HOME = Path(os.environ["CODEX_HOME"])
EXPECTED = ["exec", "--json", "--skip-git-repo-check", "-s", "read-only", "--output-schema"]
RESTRUCTURED = "Use case: illustration\nPrimary request: "
MARKER = "image generation failed: http 400 Bad Request: "


def log(record: dict) -> None:
    with open(HOME / "fake-calls.jsonl", "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def call_number() -> int:
    with open(HOME / "fake-counter", "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        n = int(fh.read() or 0) + 1
        fh.seek(0)
        fh.truncate()
        fh.write(str(n))
    return n


def scenario(n: int) -> str:
    names = [s.strip() for s in os.environ.get("FAKE_CODEX_SCENARIO", "ok").split(",") if s.strip()] or ["ok"]
    return names[min(n, len(names)) - 1]


def write_png(path: Path, transparent: bool, scale: int = 1) -> None:
    from PIL import Image

    w, h = (int(x) // scale for x in os.environ.get("FAKE_CODEX_SIZE", "1672x941").split("x"))
    path.parent.mkdir(parents=True, exist_ok=True)
    if (transparent and not os.environ.get("FAKE_CODEX_NO_ALPHA")) or os.environ.get("FAKE_CODEX_ALPHA"):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        im.paste((200, 40, 40, 255), (0, 0, w // 2, h // 2))   # a quarter opaque: transparent share 0.75
    else:
        im = Image.new("RGB", (w, h), (250, 220, 0))
    im.save(path)


def event(kind: str, payload: dict) -> str:
    return json.dumps({"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "type": kind, "payload": payload}, ensure_ascii=False)


def generation(tid: str, status: str, revised: str, transparent, saved: Path | None, inputs: list | None) -> str:
    item = {"type": "Extension", "kind": "image_gen.generation", "id": f"exec-{uuid.uuid4()}", "status": status, "revisedPrompt": revised, "result": "iVBORw0KGgo=" if saved else "",
            "transparentBackground": transparent, "failure": None, "generationId": str(uuid.uuid4()) if saved else None}
    if saved is not None:
        item["savedPath"] = str(saved)
    if inputs:
        item["inputImages"] = inputs
    now = int(time.time() * 1000)
    return event("event_msg", {"type": "item_completed", "thread_id": tid, "turn_id": "t", "item": item, "started_at_ms": now - 1000, "completed_at_ms": now})


def refusal_output(error: dict) -> str:
    """Measured: the tool's error text carries the API error as a JSON string inside Rust's Some(...), inside the call output."""
    inner = json.dumps({"error": error}, indent=2)
    text = f"Script error:\n{MARKER}Some({json.dumps(inner)})"
    return event("response_item", {"type": "custom_tool_call_output", "call_id": "call_x", "output": [{"type": "input_text", "text": "Script failed\nWall time 1.3 seconds\nOutput:\n"}, {"type": "input_text", "text": text}]})


REFUSALS = {
    "refuse_input": {"message": "Your request was rejected by the safety system.", "type": "image_generation_user_error", "param": None, "code": "moderation_blocked", "moderation_details": {"moderation_stage": "input", "categories": ["other"]}},
    "refuse_output": {"message": "Your request was rejected by the safety system.", "type": "image_generation_user_error", "param": None, "code": "moderation_blocked", "moderation_details": {"moderation_stage": "output", "categories": ["violence"]}},
    "refuse_unknown": {"message": "Rejected.", "type": "image_generation_user_error", "param": None, "code": "moderation_blocked"},
}


def main() -> int:
    argv = sys.argv[1:]
    if argv == ["--version"]:
        print("codex-cli 0.167.1")
        return 0
    n = call_number() if argv[:1] == ["exec"] else 0
    if argv[:2] == ["login", "status"]:
        if os.environ.get("FAKE_CODEX_SCENARIO", "").startswith("logged_out"):
            print("Not logged in", file=sys.stderr)
            return 1
        print("Logged in using ChatGPT")
        return 0
    if argv[:6] != EXPECTED or len(argv) != 10 or argv[7] != "-o" or argv[9] != "-":
        print(f"fake codex: unexpected argv {argv}", file=sys.stderr)
        return 2
    sc = scenario(n)
    schema_file, last_file = Path(argv[6]), Path(argv[8])
    json.loads(schema_file.read_text())
    envelope = sys.stdin.read()
    m = re.search(r"<PROMPT>\n(.*)\n</PROMPT>", envelope, re.S)
    prompt = m.group(1) if m else ""
    transparent = "transparent_background" in envelope
    refs_m = re.search(r"referenced_image_paths: (\[.*?\])", envelope)
    refs = json.loads(refs_m.group(1)) if refs_m else []
    tid = str(uuid.uuid4())
    log({"event": "start", "t": time.time(), "pid": os.getpid(), "thread_id": tid, "transparent": transparent, "refs": refs, "prompt": prompt, "call": n, "scenario": sc, "stronger": "PREVIOUS ATTEMPT" in envelope})

    if sc != "no_thread":
        print(json.dumps({"type": "thread.started", "thread_id": tid}), flush=True)
    print(json.dumps({"type": "item.completed", "item": {"id": "item_0", "type": "error", "message": "Codex is ignoring 1 unrecognized configuration setting."}}), flush=True)
    print(json.dumps({"type": "turn.started"}), flush=True)
    if sc == "exit_nonzero":
        print("fatal: something broke", file=sys.stderr)
        return 1
    if sc in ("hang", "hang_stubborn"):
        child = subprocess.Popen(["sh", "-c", "trap '' TERM; while :; do sleep 1; done"] if sc == "hang_stubborn" else ["sleep", "600"])
        with open(HOME / "children.txt", "a") as fh:
            fh.write(f"{os.getpid()} {child.pid}\n")
        if sc == "hang_stubborn":
            import signal
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        time.sleep(600)
        return 0
    delays = [d.strip() for d in os.environ.get("FAKE_CODEX_DELAY", "0.2").split(",") if d.strip()] or ["0.2"]
    time.sleep(float(delays[min(n, len(delays)) - 1]))

    rollout_dir = HOME / "sessions" / datetime.date.today().strftime("%Y/%m/%d")
    rollout_dir.mkdir(parents=True, exist_ok=True)
    rollout = rollout_dir / f"rollout-{datetime.datetime.now():%Y-%m-%dT%H-%M-%S}-{tid}.jsonl"
    lines = [json.dumps({"timestamp": "x", "type": "session_meta", "payload": {"id": tid, "cli_version": "0.167.1"}})]
    if sc == "broken_line":
        lines.append('{"type": "event_msg", "payload": ')
    lines.append(event("response_item", {"type": "custom_tool_call", "name": "exec", "input": f"const r = await tools.image_gen__imagegen({{prompt:{json.dumps(prompt)}}});"}))

    folder = HOME / "generated_images" / tid
    image = folder / f"exec-{uuid.uuid4()}.png"
    altered = RESTRUCTURED + prompt
    received = {"normalized": prompt.replace(" ", "  ", 1), "rewrite": altered}.get(sc, prompt)
    reported = {"normalized": received, "rewrite": altered, "report_lies": altered, "no_observation_mismatch": altered}.get(sc, prompt)
    inputs = [{"path": r, "sha256": hashlib.sha256(Path(r).read_bytes()).hexdigest()} for r in refs] if refs else None
    if sc == "ref_hash_wrong" and inputs:
        inputs[0]["sha256"] = "0" * 64
    path_reported = str(image)

    if sc in REFUSALS:
        lines.append(generation(tid, "failed", received, None, None, inputs))
        lines.append(refusal_output(REFUSALS[sc]))
        path_reported = ""
    elif sc == "failed_no_reason":
        lines.append(generation(tid, "failed", received, None, None, inputs))
        path_reported = ""
    elif sc == "failed_then_png":
        lines.append(generation(tid, "failed", received, None, None, inputs))
        write_png(image, transparent)
    elif sc == "saved_missing":
        lines.append(generation(tid, "completed", received, transparent, image, inputs))
    elif sc in ("no_observation", "no_observation_mismatch", "no_rollout"):
        write_png(image, transparent)
    elif sc == "two_pngs":
        write_png(image, transparent)
        write_png(folder / f"exec-{uuid.uuid4()}.png", transparent)
    elif sc == "two_generations":
        first = folder / f"exec-{uuid.uuid4()}.png"
        write_png(first, transparent, scale=2)   # half size, so the later one can be told apart
        lines.append(generation(tid, "completed", received, transparent, first, inputs))
        time.sleep(0.05)
        write_png(image, transparent)
        lines.append(generation(tid, "completed", received, transparent, image, inputs))
    else:
        write_png(image, transparent)
        lines.append(generation(tid, "completed", received, transparent, image, inputs))
    if sc != "no_rollout":
        rollout.write_text("\n".join(lines) + "\n")

    text = json.dumps({"prompt_passed": reported, "image_path": path_reported}, ensure_ascii=False)
    if sc != "no_last":
        last_file.write_text(text)
    print(json.dumps({"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": text}}), flush=True)
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}}), flush=True)
    log({"event": "end", "t": time.time(), "pid": os.getpid(), "thread_id": tid, "call": n})
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Speech to a word-timed FilmCraft transcript, from Whisper on this machine or a model reached through OpenRouter: the words, written as one `transcript.set` line for `filmcraft-cli run`, the words a person should check listed for review, and what the engine returned kept next to it."""

from __future__ import annotations

import json
import shlex
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from video import ffmpeg, openrouter, whisper
from video.errors import InputError
from video.filmcraft import TranscriptWord, write_transcript_line

from .chunks import auto_chunk, plan_chunks
from .core import Word, keep_times, snap
from .review import COMPRESSED_RATE, COMPRESSED_WINDOW, LOW_PROB, flags

__all__ = ["Word", "snap", "keep_times", "plan_chunks", "auto_chunk", "transcribe", "WHISPER_MODEL", "OPENROUTER_MODEL", "LOW_PROB", "COMPRESSED_RATE", "COMPRESSED_WINDOW", "REVIEW_SHOWN"]

WHISPER_MODEL = whisper.DEFAULT_MODEL
OPENROUTER_MODEL = openrouter.DEFAULT_MODEL
REVIEW_SHOWN = 40
CONCURRENT_REQUESTS = 4


def _refuse_existing(*paths: Path) -> None:
    """A corrected transcript and a paid reply are not replaced by accident."""
    for p in paths:
        if p.exists():
            raise InputError(f"{p} already exists and may hold corrections or a paid reply: give another --out or delete it first")


def _recognise_local(media: Path, out: Path, raw_json: Path, language: str | None, model: str):
    print(f"transcribing {media.name} with {model} (first use downloads the model) …", file=sys.stderr)
    produced = whisper.recognise(media, out.parent / (out.stem + ".whisper"), language, model)
    shutil.move(produced, raw_json)
    shutil.rmtree(out.parent / (out.stem + ".whisper"), ignore_errors=True)
    return whisper.read(raw_json)


def _recognise_openrouter(media: Path, out: Path, raw_json: Path, seconds: float, spans: list, chunk: float | None, model: str, language: str | None, diarize: bool, zdr: bool, notes: list[str]):
    """One request when the file fits and no length was asked for, otherwise several at once over pieces cut at silences, merged back into one reply. The temporary audio goes whatever happens."""
    with tempfile.TemporaryDirectory(dir=out.parent, prefix=".transcribe-audio-") as tmp:
        whole = Path(tmp) / "audio.ogg"
        limit = chunk
        if limit is None:
            limit = auto_chunk(ffmpeg.extract_audio(media, whole).stat().st_size, seconds)
        if limit is None or seconds <= limit:
            if not whole.exists():
                ffmpeg.extract_audio(media, whole)
            print(f"sending {media.name} to {model} …", file=sys.stderr)
            reply = openrouter.transcribe(whole, model, language, diarize, zdr, seconds)
            raw, cost = reply.raw, reply.cost_usd
            rec = reply.recognition
        else:
            pieces, forced = plan_chunks(seconds, spans, limit)
            if forced:
                notes.append(f"{forced} cuts between pieces fell in speech, with no silence near the limit: a word at a cut may be split or lost")
            if diarize:
                notes.append("speaker numbers restart in each piece, so one person can have different numbers across the file")
            print(f"sending {media.name} to {model} in {len(pieces)} pieces …", file=sys.stderr)

            def send(k: int):
                a, b = pieces[k]
                piece = Path(tmp) / f"{k}.ogg"
                ffmpeg.extract_audio(media, piece, a, b)
                return openrouter.transcribe(piece, model, language, diarize, zdr, b - a)

            with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as pool:
                replies = list(pool.map(send, range(len(pieces))))
            raw = openrouter.merge([(a, b, r.raw) for (a, b), r in zip(pieces, replies)])
            rec = openrouter.read(raw, seconds)
            costs = [r.cost_usd for r in replies]
            cost = sum(costs) if None not in costs else None
    raw_json.write_text(json.dumps(raw, ensure_ascii=False))
    return rec, cost


def _read_saved(path: Path, seconds: float):
    """A reply kept from an earlier run: which engine it came from shows in its shape."""
    try:
        d = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise InputError(f"{path}: cannot be read as JSON ({e})") from None
    if openrouter.recognizes(d):
        return "openrouter", openrouter.read(path, seconds)
    if whisper.recognizes(d):
        return "local", whisper.read(path)
    raise InputError(f"{path}: neither mlx-whisper JSON nor an OpenRouter reply")


def _lines_text(words: list[Word], events) -> str:
    """One line per recognised line and per named sound, in time order: `[w<first>-w<last>] start-end text`, with the word indices FilmCraft's transcript commands take."""
    by_line: dict[int, list[int]] = {}
    for i, w in enumerate(words):
        by_line.setdefault(w.segment, []).append(i)
    rows = []
    for _, ix in sorted(by_line.items()):
        first, last = words[ix[0]], words[ix[-1]]
        who = f"Speaker {first.speaker}: " if first.speaker is not None else ""
        rows.append((first.start, f"[w{ix[0]}-w{ix[-1]}] {first.start:8.2f}-{last.end:8.2f}  {who}{' '.join(words[i].text for i in ix)}\n"))
    rows += [(e.start, f"[sound] {e.start:8.2f}-{e.end:8.2f}  {e.text}\n") for e in events]
    return "".join(row for _, row in sorted(rows, key=lambda r: r[0]))


def transcribe(media: Path, out: Path, *, engine: str | None = None, from_json: Path | None = None, item: int | None = None, language: str | None = None, model: str | None = None,
               diarize: bool = False, zdr: bool = True, snap_mode: str = "auto", max_shift: float = 0.5, chunk: float | None = None) -> dict:
    info = ffmpeg.probe(media)
    if not info.audio:
        raise InputError(f"{media}: no audio stream")
    raw_json = out.with_suffix(".openrouter.json" if engine == "openrouter" else ".whisper.json")
    _refuse_existing(out, *([raw_json] if engine else []))
    if engine == "openrouter":
        openrouter.ready()
    out.parent.mkdir(parents=True, exist_ok=True)

    spans = ffmpeg.measured_speech(media)
    seconds = info.duration or (spans[-1][1] if spans else 0.0)
    notes: list[str] = []
    cost: float | None = 0
    if engine == "local":
        model = model or WHISPER_MODEL
        rec = _recognise_local(media, out, raw_json, language, model)
    elif engine == "openrouter":
        model = model or OPENROUTER_MODEL
        rec, cost = _recognise_openrouter(media, out, raw_json, seconds, spans, chunk, model, language, diarize, zdr, notes)
    else:
        engine, rec = _read_saved(from_json, seconds)
        raw_json = from_json

    words = [Word(w.text, w.start, w.end, w.prob, k, w.speaker) for k, s in enumerate(rec.segments) for w in s.words]
    fps = info.video[0].fps if info.video and info.video[0].fps else 30
    min_dur = 1 / float(fps)
    moved = snap_mode == "on" or (snap_mode == "auto" and engine == "local")
    kept, report = snap(words, spans, max_shift=max_shift, min_dur=min_dur) if moved else keep_times(words, spans, min_dur=min_dur)
    if not kept:
        notes.append("no words came back: the engine found no speech in this media")

    lang = rec.language or language or ""
    source = {"local": "mlx-whisper", "openrouter": "openrouter"}[engine] + (f" {model.rsplit('/', 1)[-1] if engine == 'local' else model}" if model else "")
    write_transcript_line(out, item, lang, source, [TranscriptWord(w.text, w.start, w.end, w.speaker, w.prob) for w in kept])
    text_file = out.with_suffix(".txt")
    text_file.write_text(_lines_text(kept, rec.events))

    review = flags(kept, report["unmatched"], rec.segments)
    review_file = None
    if len(review) > REVIEW_SHOWN:
        review_file = out.with_suffix(".review.json")
        review_file.write_text(json.dumps(review, ensure_ascii=False, indent=0))
    quoted = shlex.quote(str(out))
    apply = f"filmcraft-cli --project <P.fcproj> --save run {quoted}"
    labelled = {w.speaker for w in kept if w.speaker is not None}
    return {
        "engine": engine, "model": model, "item": item, "language": lang, "words": len(kept), "seconds": round(info.duration or 0, 2),
        "speech_seconds": round(sum(b - a for a, b in spans), 2), "cost_usd": cost,
        "speakers": len(labelled), "audio_events": len(rec.events), "snapped": report["snapped"], "unmatched": len(report["unmatched"]),
        "has_confidence": any(w.prob is not None for w in kept),
        "review": review[:REVIEW_SHOWN], "review_total": len(review), "review_file": str(review_file) if review_file else None,
        "out": str(out), "text": str(text_file), "raw": str(raw_json),
        "next": apply if item is not None else f"Fill in params.item in {quoted} with the project item id (inspect project lists them), then apply it: {apply}",
        "notes": notes,
    }

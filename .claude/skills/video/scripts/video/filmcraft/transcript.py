"""The `transcript.set` line, FilmCraft's format for a word-timed transcript: written for `filmcraft-cli run`, and read back by the tools that work from the same file without a project. Ticks and the shape of the line stop here."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from video.errors import InputError
from video.timecode import seconds, ticks


@dataclass
class TranscriptWord:
    """Times in seconds of media."""
    text: str
    start: float
    end: float
    speaker: int | None = None
    confidence: float | None = None


def write_transcript_line(path: Path, item: int | None, language: str, source: str, words: list[TranscriptWord]) -> None:
    """`item` None is written as null, which FilmCraft refuses: the line can be read by the tools here, and must have its item filled in before it can be applied. FilmCraft also refuses `"confidence": null`, so a word without one has no such key."""
    labelled = [w.speaker for w in words if w.speaker is not None]
    speakers = [{"name": f"Speaker {n}"} for n in range(max(labelled) + 1)] if labelled else []
    rows = []
    for w in words:
        row: dict = {"text": w.text, "start": ticks(w.start), "end": ticks(w.end)}
        if w.confidence is not None:
            row["confidence"] = round(min(max(w.confidence, 0.0), 1.0), 3)
        if w.speaker is not None:
            row["speaker"] = w.speaker
        rows.append(row)
    line = {"id": "transcript.set", "params": {"item": item, "transcript": {"language": language, "source": source, "speakers": speakers, "words": rows}}}
    Path(path).write_text(json.dumps(line, ensure_ascii=False) + "\n")


def read_transcript_line(path: Path) -> list[TranscriptWord]:
    """The words of a file holding one `transcript.set` line, `item` filled in or not, in the order they were written; raises InputError for anything else."""
    try:
        lines = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
        if len(lines) != 1 or lines[0].get("id") != "transcript.set":
            raise ValueError("expected one transcript.set line")
        return [TranscriptWord(str(w["text"]), seconds(int(w["start"])), seconds(int(w["end"])), w.get("speaker"), w.get("confidence")) for w in lines[0]["params"]["transcript"]["words"]]
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
        raise InputError(f"{path}: not a transcript.set line ({e})") from None

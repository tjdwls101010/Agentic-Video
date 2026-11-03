"""A speech recogniser's output in the skill's own terms, whichever engine produced it."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawWord:
    text: str
    start: float
    end: float
    prob: float | None = None
    speaker: int | None = None


@dataclass
class Segment:
    start: float
    end: float
    text: str
    no_speech_prob: float = 0.0
    avg_logprob: float = 0.0
    compression_ratio: float = 1.0
    words: list[RawWord] = field(default_factory=list)


@dataclass
class Event:
    """A sound the engine named instead of transcribing, such as `[gentle music]`."""
    text: str
    start: float
    end: float


@dataclass
class Recognition:
    language: str
    segments: list[Segment]
    events: list[Event] = field(default_factory=list)
    duration: float | None = None

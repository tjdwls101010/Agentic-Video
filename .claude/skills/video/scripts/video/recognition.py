"""A speech recogniser's output in the skill's own terms, whichever engine produced it."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawWord:
    text: str
    start: float
    end: float
    prob: float


@dataclass
class Segment:
    start: float
    end: float
    text: str
    no_speech_prob: float
    avg_logprob: float
    compression_ratio: float
    words: list[RawWord] = field(default_factory=list)


@dataclass
class Recognition:
    language: str
    segments: list[Segment]

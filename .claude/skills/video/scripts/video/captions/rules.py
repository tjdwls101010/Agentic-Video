"""The subtitle rules this skill lays out to, Korean (Netflix Korean Timed Text Style Guide, the de facto standard for Korean streaming subtitles; Korean broadcast guidance sets no character counts) and English (Netflix English Timed Text Style Guide), and how text is counted against them."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rules:
    max_units: float = 16.0     # per line
    lines: int = 2
    cps: float = 12.0           # characters a second, spaces and punctuation included
    min_s: float = 5 / 6
    max_s: float = 7.0
    gap_frames: int = 2         # between cues that follow each other closely
    close_gap_s: float = 0.5    # a smaller gap is closed down to gap_frames
    keep_end_punct: bool = False


RULE_PROFILES = {"ko": Rules(), "en": Rules(max_units=21.0, cps=20.0, keep_end_punct=True)}


HELP = """\
Rules, --rules ko (Netflix Korean Timed Text Style Guide; Korean broadcast guidance gives no character counts) [practice]:
  a line holds 16 units: a Hangul syllable or CJK character is 1, a Latin letter, digit, space or punctuation mark 0.5, the ellipsis … 1
  at most 2 lines; when two, the bottom line is preferably the longer (pyramid), and a line breaks after a clause rather than inside one
  reading speed at most 12 characters a second (spaces and punctuation count); a fast cue stays up into the following silence to reach it
  each cue lasts 5/6 s to 7 s; cues that nearly touch are chained 2 frames apart
  no full stop or comma at the end of a line; ? and ! stay; three dots become …
  a cue ends at a speaker change and at a pause of 1.5 s, and prefers to end at a sentence end, then at a pause or a cut, then at a clause end
Rules, --rules en (Netflix English Timed Text Style Guide and General Requirements) [practice]:
  a line holds 42 characters, counted as 21 of the units above; at most 2 lines, the bottom preferably the longer
  a line or cue breaks after punctuation and before a conjunction (and, but, so, because) rather than after it
  reading speed at most 20 characters a second, the adult-program limit; each cue lasts 5/6 s to 7 s; the 2-frame chaining is this tool's, not the guide's
  punctuation stays at the end of a line; three dots become the single character …; Mr., Mrs., Ms., Dr., St., U.S., Jr. and Sr. do not end a sentence
Under both: a speaker turn shorter than the shortest cue cannot be a caption of its own, so it does not end a cue and its words join the cue around them."""


def units(text: str) -> float:
    total = 0.0
    for ch in text:
        o = ord(ch)
        if o < 0x2000:
            total += 0.5
        else:
            total += 1.0
    return total


def chars(lines: list[str]) -> int:
    return len(" ".join(lines))


_LINE_END = re.compile(r"[.,。，]+$")


def clean_line(line: str, keep_end_punct: bool = False) -> str:
    """Three dots become the ellipsis character. Unless told to keep it, no full stop or comma at a line end; an ellipsis stays."""
    line = line.strip().replace("...", "…")
    if keep_end_punct or line.endswith("…"):
        return line
    return _LINE_END.sub("", line).rstrip()


# Where a Korean clause ends: a comma or semicolon, a connective ending (also with the polite 요 speech adds: 그래서요, 있는데요),
# or a sentence-final ending speech recognisers often leave without a full stop (요, 니다, 죠).
_CLAUSE_END = re.compile(r"([,;:，、]|(?:고|서|며|면서|는데|은데|ㄴ데|지만|니까|으니까|아서|어서|해서|도록|려고|으면|면|거나|든지|다가|자마자)요?|요|니다|죠)$")
# An English clause starts at one of these, so the break goes before the word and not after it.
_CLAUSE_START = {"and", "but", "so", "because"}
_SENTENCE_END = re.compile(r"[.?!…。？！]['\"”’)]*$")
_NOT_SENTENCE_END = {"Mr.", "Mrs.", "Ms.", "Dr.", "St.", "U.S.", "Jr.", "Sr."}


def is_sentence_end(word: str) -> bool:
    return word not in _NOT_SENTENCE_END and bool(_SENTENCE_END.search(word.replace("...", "…")))


def is_clause_end(word: str, next_word: str = "") -> bool:
    """Whether a break after `word`, with `next_word` following it, falls between clauses."""
    return bool(_CLAUSE_END.search(word)) or next_word.lower() in _CLAUSE_START

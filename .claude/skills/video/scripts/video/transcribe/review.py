"""Words a person should check before the transcript drives cuts or captions: low-confidence words, words with no speech under them, the two ways Whisper hallucinates over music or silence (the same line repeated, and segments its own no-speech test rejects), and stretches with more words than anyone can say."""

from __future__ import annotations

from .core import Word

LOW_PROB = 0.5
REPEAT_RUN = 3
# Whisper's own silence rule (transcribe.py): no_speech_prob above 0.6 together with avg_logprob below -1.
NO_SPEECH_PROB, NO_SPEECH_LOGPROB = 0.6, -1.0
# Above what speech reaches: engines whose times held measured at most 5.7 words a second over 10 s, one whose times drifted 10.5.
COMPRESSED_WINDOW, COMPRESSED_RATE = 10.0, 7.0


def _norm(text: str) -> str:
    return "".join(c for c in text if c.isalnum()).lower()


def _compressed(words: list[Word]) -> list[int]:
    """The first word of each stretch where the words starting within the next 10 s run over the rate."""
    starts, j, inside = [], 0, False
    for i, w in enumerate(words):
        while j < len(words) and words[j].start < w.start + COMPRESSED_WINDOW:
            j += 1
        over = (j - i) / COMPRESSED_WINDOW > COMPRESSED_RATE
        if over and not inside:
            starts.append(i)
        inside = over
    return starts


def flags(words: list[Word], unmatched: list[int], segments) -> list[dict]:
    """`segments` are the recognition's lines with `text`, `no_speech_prob`, `avg_logprob`; `Word.segment` indexes them."""
    first_word: dict[int, int] = {}
    for i, w in enumerate(words):
        first_word.setdefault(w.segment, i)
    out = [{"i": i, "text": w.text, "start_s": round(w.start, 3), "reason": "low_prob"} for i, w in enumerate(words) if w.prob is not None and w.prob < LOW_PROB]
    out += [{"i": i, "text": words[i].text, "start_s": round(words[i].start, 3), "reason": "unmatched"} for i in unmatched]
    out += [{"i": i, "text": words[i].text, "start_s": round(words[i].start, 3), "reason": "compressed"} for i in _compressed(words)]
    texts = [_norm(s.text) for s in segments]
    k = 0
    while k < len(texts):
        j = k
        while j + 1 < len(texts) and texts[j + 1] == texts[k] and texts[k]:
            j += 1
        if j - k + 1 >= REPEAT_RUN:
            out += [{"i": first_word[s], "text": segments[s].text, "start_s": round(words[first_word[s]].start, 3), "reason": "repeat"} for s in range(k, j + 1) if s in first_word]
        k = j + 1
    for s, seg in enumerate(segments):
        if seg.no_speech_prob > NO_SPEECH_PROB and seg.avg_logprob < NO_SPEECH_LOGPROB and s in first_word:
            out.append({"i": first_word[s], "text": seg.text, "start_s": round(words[first_word[s]].start, 3), "reason": "no_speech"})
    return sorted(out, key=lambda r: (r["i"], r["reason"]))

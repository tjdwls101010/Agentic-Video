"""OpenRouter's speech-to-text endpoint: the request, its failures, and the reply read into the skill's own terms. `verbose_json`, `audio_event`, `eng` and the rest of its format stop here, and so does the API key."""

from __future__ import annotations

import base64
import http.client
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from video.errors import InputError, ToolError
from video.recognition import Event, RawWord, Recognition, Segment

__all__ = ["DEFAULT_MODEL", "KEY_FILE", "Reply", "load_key", "key_source", "ready", "transcribe", "read", "merge", "recognizes"]

DEFAULT_MODEL = "elevenlabs/scribe-v2"
KEY_FILE = Path(__file__).parent / ".env"

_KEY_NAME = "OPENROUTER_API_KEY"
_BASE_NAME = "OPENROUTER_BASE_URL"
_BASE_URL = "https://openrouter.ai/api/v1"
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}
_TIMEOUT = 600
_RETRIES = 3
_RETRY_STATUS = {408, 429}
_MAX_WAIT = 60
_THREE_LETTER = {"eng": "en", "kor": "ko", "jpn": "ja", "zho": "zh"}
_LINE_GAP = 0.7
_SENTENCE_END = re.compile(r"[.?!…。？！]['\"”’)]*$")
_MIN_TIMED = 0.9
_PAST_END = 1.0
_BEFORE_ZERO = 0.1
_BACKWARDS = 1.0
_MANY_WORDS = 4


@dataclass
class Reply:
    raw: dict
    recognition: Recognition
    cost_usd: float | None


def load_key(env=os.environ, file: Path = KEY_FILE) -> str | None:
    """The environment wins when the variable is set at all, even empty (which means no key); otherwise the `.env` file. None when there is no key."""
    if _KEY_NAME in env:
        return env[_KEY_NAME].strip() or None
    try:
        lines = Path(file).read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for line in lines:
        name, eq, value = line.strip().removeprefix("export ").partition("=")
        if eq and name.strip() == _KEY_NAME:
            return value.strip().strip("'\"") or None
    return None


def key_source(env=os.environ, file: Path = KEY_FILE) -> str:
    """Where the key would come from, `env`, `file` or `none`; the key itself goes no further than this unit."""
    if load_key(env, file) is None:
        return "none"
    return "env" if _KEY_NAME in env else "file"


def _base_url() -> str:
    """Where requests go. A local server may be plain http; anywhere else the key must travel over https."""
    url = os.environ.get(_BASE_NAME) or _BASE_URL
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == "https" and parts.hostname or parts.scheme == "http" and parts.hostname in _LOOPBACK:
        return url.rstrip("/")
    raise ToolError(f"{_BASE_NAME} must be https, or http on this machine: the API key would otherwise travel in the clear")


def ready() -> str:
    """The key to send, checked before any audio is prepared; raises when there is none or the destination is unsafe."""
    _base_url()
    key = load_key()
    if key is None:
        raise ToolError(f"no OpenRouter API key: put {_KEY_NAME}=<key> in {KEY_FILE} or set it in the environment. Nothing was sent, and nothing falls back to the local engine: --engine local runs on this machine")
    if not re.fullmatch(r"[\x21-\x7e]+", key):
        raise ToolError(f"the OpenRouter API key has spaces, line breaks or characters a key cannot have; check {KEY_FILE} or {_KEY_NAME}")
    return key


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib would carry the Authorization header to wherever a redirect points."""

    def redirect_request(self, *args, **kwargs):
        return None


def _provider_message(data: bytes, key: str) -> str:
    text = data.decode(errors="replace").replace(key, "<key>")
    try:
        return str(json.loads(text)["error"]["message"])
    except (ValueError, KeyError, TypeError):
        return text[:300]


def _wait(headers, attempt: int) -> float:
    try:
        wait = float(headers.get("Retry-After", ""))
    except ValueError:
        wait = 2.0 ** attempt
    return min(max(wait, 0.0), _MAX_WAIT) if math.isfinite(wait) else 2.0 ** attempt


def _post(body: dict, key: str, timeout: float) -> dict:
    url = _base_url()
    # 성진: 분할 실행 재개 없음, 실패하면 다시 돌린다(비용이 작아서). 비용이 커지면 재개를 넣는다
    handlers = [_NoRedirect()] + ([urllib.request.ProxyHandler({})] if urllib.parse.urlsplit(url).hostname in _LOOPBACK else [])
    opener = urllib.request.build_opener(*handlers)
    data = json.dumps(body).encode()
    for attempt in range(_RETRIES + 1):
        request = urllib.request.Request(url + "/audio/transcriptions", data=data, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with opener.open(request, timeout=timeout) as response:
                payload = response.read()
            break
        except urllib.error.HTTPError as e:
            status, message, headers = e.code, _provider_message(e.read(), key), e.headers
        except (OSError, http.client.HTTPException) as e:
            raise ToolError(f"could not reach OpenRouter: {str(e).replace(key, '<key>')}") from None
        if status in (401, 402):
            raise ToolError(f"OpenRouter refused the request ({status}): {message}")
        if 400 <= status < 500 and status not in _RETRY_STATUS:
            raise InputError(f"OpenRouter refused the request ({status}): {message}")
        if status < 400:
            raise ToolError(f"OpenRouter answered {status}, a redirect, which is not followed so the key stays with OpenRouter")
        if attempt == _RETRIES:
            raise ToolError(f"OpenRouter still failed after {_RETRIES} retries ({status}: {message}). A long file can fail like this on some models: try --chunk with a shorter length")
        print(f"OpenRouter answered {status}; retrying ({attempt + 1}/{_RETRIES}) …", file=sys.stderr)
        time.sleep(_wait(headers, attempt))
    try:
        reply = json.loads(payload)
    except ValueError:
        raise ToolError("OpenRouter answered 200 with something that is not JSON") from None
    if not isinstance(reply, dict):
        raise ToolError("OpenRouter answered 200 with JSON that is not a transcription")
    if "error" in reply:
        raise ToolError(f"OpenRouter answered 200 with an error: {_provider_message(payload, key)}")
    return reply


def transcribe(audio: Path, model: str, language: str | None, diarize: bool, zdr: bool, seconds: float | None = None, timeout: float = _TIMEOUT) -> Reply:
    """Send one Ogg file and read the reply. `seconds` is the file's length, for a reply that does not say."""
    key = ready()
    body: dict = {"model": model, "input_audio": {"data": base64.b64encode(Path(audio).read_bytes()).decode(), "format": Path(audio).suffix.lstrip(".")},
                  "response_format": "verbose_json", "timestamp_granularities": ["word", "segment"]}
    if zdr:
        body["provider"] = {"zdr": True}
    if language:
        body["language"] = language
    if diarize:
        body["diarize"] = True
    raw = _post(body, key, timeout)
    return Reply(raw, read(raw, seconds), cost_of(raw))


def cost_of(raw: dict) -> float | None:
    """`usage.cost` is what was charged; a model's listed price is not comparable across models."""
    cost = (raw.get("usage") or {}).get("cost")
    return float(cost) if isinstance(cost, (int, float)) else None


def recognizes(d) -> bool:
    """Whether a saved JSON document is one of these replies. Only OpenRouter puts `words` at the top level, or `usage` at all."""
    return isinstance(d, dict) and (isinstance(d.get("words"), list) or "usage" in d)


def _number(value) -> float:
    n = float(value)
    if not math.isfinite(n):
        raise ValueError("a word time is not a finite number")
    return n


def _speaker(word: dict) -> int | None:
    value = word.get("speaker")
    return value if isinstance(value, int) and value >= 0 else None


def _lines(words: list[RawWord]) -> list[Segment]:
    """Replies carry words at the top level and no words in their segments (Scribe's one segment spans the file), so lines are made here: at a sentence end, a gap of 0.7 s or more, and a change of speaker."""
    lines: list[list[RawWord]] = []
    for w in words:
        prev = lines[-1][-1] if lines else None
        if prev is None or _SENTENCE_END.search(prev.text) or w.start - prev.end >= _LINE_GAP or w.speaker != prev.speaker:
            lines.append([])
        lines[-1].append(w)
    return [Segment(line[0].start, line[-1].end, " ".join(w.text for w in line), words=line) for line in lines]


def _is_spoken(word: dict) -> bool:
    """Not a named sound, and more than punctuation such as a lone `...`."""
    return word.get("type") != "audio_event" and any(c.isalnum() for c in str(word.get("word", "")))


def _check_times(text: str, entries: list[dict], duration: float | None) -> None:
    """Some routes return a full `text` with a word list that is cut short or runs past the audio, and a reply can carry times no speech could have. These checks catch that whatever the model is, and passing them does not prove the times."""
    of = len(text.split())
    have = sum(len(str(w.get("word", "")).split()) for w in entries)  # a named sound such as `[gentle music]` is one entry and two words of text
    try_chunk = f"Transcribe it again with --engine openrouter --chunk {round(duration / 2)} and halve that until a reply passes" if duration else "Transcribe it again with --engine openrouter and a short --chunk"
    if of and have < _MIN_TIMED * of:
        raise ToolError(f"the reply's text has {of} words and only {have} have times, so its word list was cut short. {try_chunk}")
    last = max((_number(w["end"]) for w in entries), default=0.0)
    if duration and last > duration + _PAST_END:
        raise ToolError(f"the reply puts a word at {last:.1f} s in {duration:.1f} s of audio, so its times are broken or it belongs to other media. {try_chunk}")
    starts = [_number(w["start"]) for w in entries]
    if any(t < -_BEFORE_ZERO for t in starts):
        raise ToolError(f"the reply has a word before the start of the audio, so its times are broken. {try_chunk}")
    if any(b <= a - _BACKWARDS for a, b in zip(starts, starts[1:])):
        raise ToolError(f"the reply's word times run backwards, so they are broken. {try_chunk}")
    spoken = [w for w in entries if _is_spoken(w)]
    if len(spoken) >= _MANY_WORDS and 2 * sum(_number(w["end"]) <= _number(w["start"]) for w in spoken) > len(spoken):
        raise ToolError(f"most of the reply's words have no length, so its times are broken. {try_chunk}")


def _parse(d, duration: float | None) -> Recognition:
    if not isinstance(d, dict) or not ("text" in d or "words" in d):
        raise ValueError("no `text` or `words`")
    entries = d.get("words") or []
    if not isinstance(entries, list):
        raise ValueError("`words` is not a list")
    said = float(d["duration"]) if d.get("duration") else None
    seconds = min(said, duration) if said and duration else said or duration  # a reply does not get to vouch for its own length
    _check_times(str(d.get("text") or ""), entries, seconds)
    words, events = [], []
    for w in entries:
        text, start, end = str(w.get("word", "")).strip(), _number(w["start"]), _number(w["end"])
        if w.get("type") == "audio_event":
            events.append(Event(text, start, end))
        elif _is_spoken(w):
            prob = w.get("confidence")
            words.append(RawWord(text, start, end, _number(prob) if prob is not None else None, _speaker(w)))
    language = str(d.get("language") or "")
    return Recognition(_THREE_LETTER.get(language, language), _lines(words), events, seconds)


def read(raw: dict | Path, duration: float | None = None) -> Recognition:
    """A reply, or a file holding one, in the skill's terms; `duration` is used when the reply does not say. A reply whose word times cannot be trusted raises ToolError; one that cannot be read at all raises ToolError when it just arrived and InputError when it is a file someone named."""
    is_file = not isinstance(raw, dict)
    try:
        return _parse(json.loads(Path(raw).read_text()) if is_file else raw, duration)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
        if is_file:
            raise InputError(f"{raw}: not an OpenRouter transcription with word timestamps ({e})") from None
        raise ToolError(f"OpenRouter's reply could not be read as a transcription ({e})") from None


def merge(parts: list[tuple[float, float, dict]]) -> dict:
    """Replies to consecutive pieces of one file, each `(start, end, reply)` in file seconds, as one reply over the whole file: times shifted, text joined, length and cost added. It reads back through `read` like a single reply."""
    def shifted(entry: dict, by: float) -> dict:
        return {**entry, **{k: round(float(entry[k]) + by, 6) for k in ("start", "end") if k in entry}}

    merged = {k: v for k, v in parts[0][2].items() if k not in ("words", "segments", "usage")}
    merged["text"] = " ".join(t for t in (str(r.get("text") or "").strip() for _, _, r in parts) if t)
    merged["duration"] = round(parts[-1][0] + float(parts[-1][2].get("duration") or parts[-1][1] - parts[-1][0]), 6)
    merged["language"] = next((r["language"] for _, _, r in parts if r.get("language")), "")
    merged["segments"] = [shifted(s, a) for a, _, r in parts for s in r.get("segments") or []]
    merged["words"] = [shifted(w, a) for a, _, r in parts for w in r.get("words") or []]
    costs = [cost_of(r) for _, _, r in parts]
    merged["usage"] = {"seconds": round(sum(float((r.get("usage") or {}).get("seconds") or 0) for _, _, r in parts), 6), "cost": sum(costs) if None not in costs else None}
    return merged

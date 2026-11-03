"""`transcribe --engine openrouter`: the system unit that talks to OpenRouter, and what the command does with it.

Replies come from three places: JSON recorded from real requests on synthetic `say` speech (fixtures, so the shape is the provider's and not a guess), a local HTTP server standing in for the provider (requests, retries, every failure), and small hand-written replies where one field is the point of the test. Every test runs with a fake key, so the real one can never reach localhost. The real API is exercised only with FILMCRAFT_TEST_OPENROUTER=1."""

from __future__ import annotations

import base64
import json
import os
import shlex
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from video import openrouter, transcribe
from video.errors import ToolError
from support import TICKS, fc, fc_json, fc_run, ffmpeg, needs_ffmpeg, needs_filmcraft, skill

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_KEY = "sk-test-0123456789abcdef-SECRET"
pytestmark = needs_ffmpeg


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)


class Provider:
    """A stand-in for the API. `script` answers requests in order, the last entry repeating; an entry is (status, headers, body) or a function of the request's JSON returning one. Requests are kept for the test to read."""

    def __init__(self):
        self.requests: list[dict] = []
        self.script: list = []
        self.lock = threading.Lock()
        provider = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                with provider.lock:
                    n = len(provider.requests)
                    provider.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
                    entry = provider.script[min(n, len(provider.script) - 1)]
                status, headers, reply = entry(body) if callable(entry) else entry
                data = reply if isinstance(reply, bytes) else json.dumps(reply).encode()
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/api/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def provider(monkeypatch):
    p = Provider()
    monkeypatch.setenv("OPENROUTER_BASE_URL", p.url)
    yield p
    p.close()


def tone_bursts(path, bursts, total):
    """A 1 kHz tone exactly inside each (start, end) burst, digital silence elsewhere."""
    expr = "+".join(f"between(t\\,{a}\\,{b})" for a, b in bursts)
    ffmpeg("-f", "lavfi", "-i", f"aevalsrc=0.3*sin(2*PI*1000*t)*({expr}):s=48000:d={total}", "-c:a", "pcm_s16le", str(path))
    return path


def reply(words=(), text=None, duration=10.0, cost=0.01, language="eng", **extra):
    """A verbose_json reply in Scribe's shape: one segment for the whole file and every word at the top level."""
    words = [{"word": w[0], "start": w[1], "end": w[2], **(w[3] if len(w) > 3 else {})} for w in words]
    text = " ".join(w["word"] for w in words) if text is None else text
    return {"text": text, "usage": {"seconds": duration, "cost": cost}, "task": "transcribe", "language": language, "duration": duration,
            "segments": [{"id": 0, "start": 0, "end": duration, "text": text}], "words": words, **extra}


OK_REPLY = (200, {}, reply([("hello", 1.0, 1.5, {"confidence": 0.99}), ("world.", 1.6, 2.0, {"confidence": 0.98})], duration=3.0))
RETRY_NOW = {"Retry-After": "0"}


def read_line(path):
    [line] = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    return line


def seconds_of(line):
    return [(w["text"], round(w["start"] / TICKS, 3), round(w["end"] / TICKS, 3)) for w in line["params"]["transcript"]["words"]]


def run(tmp_path, audio, *args, out="t.jsonl"):
    return skill("transcribe", str(audio), "--out", str(tmp_path / out), *args, cwd=tmp_path)


def from_json(tmp_path, audio, raw: dict, *args, out="t.jsonl"):
    f = tmp_path / "raw.json"
    f.write_text(json.dumps(raw, ensure_ascii=False))
    return run(tmp_path, audio, "--from-json", str(f), *args, out=out)


@pytest.fixture
def audio(tmp_path):
    return tone_bursts(tmp_path / "b.wav", [(1.0, 2.0)], 3)


# -- reading a reply: recorded responses on `say` speech --------------------------------------------------------------------

SAY_LINES = ["오늘은 편집 이야기를 해볼게요.", "자막은 문장 단위로 끊어야 읽기 편합니다.", "그럼 바로 시작하겠습니다."]


def test_a_recorded_scribe_reply_reads_into_lines_with_probabilities():
    """Scribe returns one segment for the whole file; lines come from sentence ends, and its `kor` becomes `ko`."""
    rec = openrouter.read(FIXTURES / "say_ko.scribe.json")
    assert rec.language == "ko"
    assert [s.text for s in rec.segments] == SAY_LINES
    assert rec.segments[0].words[0].text == "오늘은" and rec.segments[0].words[0].start == 0.66
    assert 0 < rec.segments[0].words[0].prob <= 1
    assert rec.events == []


def test_a_recorded_nemotron_reply_has_no_probabilities():
    rec = openrouter.read(FIXTURES / "say_ko.nemotron.json")
    assert rec.language == "ko"
    assert [s.text for s in rec.segments] == SAY_LINES
    assert all(w.prob is None for s in rec.segments for w in s.words)


def test_a_word_with_no_probability_is_written_without_a_confidence_key(tmp_path, audio):
    """FilmCraft refuses `"confidence": null`, so the key is left out."""
    code, res, raw, err = run(tmp_path, audio, "--from-json", str(FIXTURES / "say_ko.nemotron.json"), "--item", "1")
    assert code == 0, raw + err
    assert res["has_confidence"] is False
    assert all("confidence" not in w for w in read_line(tmp_path / "t.jsonl")["params"]["transcript"]["words"])


def test_audio_events_and_wordless_tokens_are_not_words():
    rec = openrouter.read(reply([("[gentle music]", 0.4, 2.3, {"type": "audio_event"}), ("Um,", 2.5, 2.7), ("...", 3.0, 3.0), ("one", 3.8, 3.9), ("2,000.", 4.0, 4.4)], text="[gentle music] Um, ... one 2,000."))
    assert [w.text for s in rec.segments for w in s.words] == ["Um,", "one", "2,000."]
    assert [(e.text, e.start, e.end) for e in rec.events] == [("[gentle music]", 0.4, 2.3)]
    assert rec.language == "en"


@pytest.mark.parametrize("code, two", [("eng", "en"), ("kor", "ko"), ("jpn", "ja"), ("zho", "zh"), ("ko", "ko"), ("fra", "fra")])
def test_language_codes_become_the_two_letter_ones_we_know(code, two):
    assert openrouter.read(reply([("a", 1, 2)], language=code)).language == two


def test_lines_break_at_a_sentence_end_a_long_gap_and_a_speaker_change():
    sp0, sp1 = {"speaker": 0}, {"speaker": 1}
    rec = openrouter.read(reply([("a", 0.0, 0.2, sp0), ("b.", 0.3, 0.5, sp0), ("c", 0.6, 0.8, sp0), ("d", 1.5, 1.7, sp0), ("e", 1.8, 2.0, sp0), ("f", 2.1, 2.3, sp1)]))
    assert [[w.text for w in s.words] for s in rec.segments] == [["a", "b."], ["c"], ["d", "e"], ["f"]]
    assert [w.speaker for s in rec.segments for w in s.words] == [0, 0, 0, 0, 0, 1]


def test_a_gap_just_under_the_limit_does_not_break_a_line():
    rec = openrouter.read(reply([("c", 0.6, 0.8), ("d", 1.49, 1.7)]))
    assert len(rec.segments) == 1


def test_a_reply_without_a_duration_uses_the_length_the_caller_gives():
    raw = reply([("a", 1, 2)])
    del raw["duration"]
    assert openrouter.read(raw, duration=9.5).duration == 9.5


def test_zeros_the_provider_leaves_in_whisper_fields_do_not_read_as_silence():
    """Providers fill `no_speech_prob` and `avg_logprob` with zeros; those must not read as Whisper's silence test firing."""
    raw = json.loads((FIXTURES / "say_ko.nemotron.json").read_text())
    assert all(s.no_speech_prob == 0 for s in openrouter.read(raw).segments)


# -- refusing a reply whose times cannot be trusted ---------------------------------------------------------------------------

def words_and_text(have, of):
    return reply([(f"w{i}", i * 0.1, i * 0.1 + 0.05) for i in range(have)], text=" ".join(f"w{i}" for i in range(of)), duration=1000)


@pytest.mark.parametrize("have, of", [(297, 7973), (66, 1030), (180, 1000), (899, 1000)])
def test_a_reply_with_too_few_timed_words_is_refused(have, of):
    """The first three are the measured Nemotron ratios (50 minutes, 300 s, 360 s)."""
    with pytest.raises(ToolError, match=rf"{of} words.*{have}.*--chunk"):
        openrouter.read(words_and_text(have, of))


@pytest.mark.parametrize("have, of", [(997, 1000), (996, 1000), (900, 1000)])
def test_a_reply_with_nearly_every_word_timed_passes(have, of):
    """The first two are the measured Scribe ratios, without and with speakers."""
    assert sum(len(s.words) for s in openrouter.read(words_and_text(have, of)).segments) == have


def test_a_word_past_the_end_of_the_audio_is_refused():
    with pytest.raises(ToolError, match="--chunk"):
        openrouter.read(reply([("a", 1.0, 2.0), ("b", 555.7, 556.7)], duration=300.0))


def test_a_word_within_a_second_of_the_end_passes():
    assert openrouter.read(reply([("a", 1.0, 300.9)], duration=300.0))


def test_a_short_reply_with_a_two_word_sound_is_not_refused():
    """A named sound is one entry in `words` and two words in `text`, which alone would look like a list cut short."""
    assert openrouter.read(reply([("[gentle music]", 0.4, 2.3, {"type": "audio_event"}), ("Thanks.", 2.5, 2.9)]))


def test_text_with_no_words_at_all_is_refused():
    with pytest.raises(ToolError, match="--chunk"):
        openrouter.read(reply([], text="some text the provider heard"))


def test_a_recorded_broken_reply_is_refused():
    """Nemotron on 400 s of `say`: its last word is at 561 s, and its word list is short of its own text."""
    with pytest.raises(ToolError, match="--chunk"):
        openrouter.read(FIXTURES / "say_en_long.nemotron.json")


def test_a_recorded_broken_reply_from_a_file_exits_one_and_writes_nothing(tmp_path, audio):
    code, res, raw, err = run(tmp_path, audio, "--from-json", str(FIXTURES / "say_en_long.nemotron.json"))
    assert code == 1 and "--chunk" in res["error"]
    assert not (tmp_path / "t.jsonl").exists()


def test_a_recorded_two_voice_reply_keeps_its_speakers():
    """Two `say` voices taking turns; Scribe's labels follow the voices."""
    rec = openrouter.read(FIXTURES / "say_en_two_voices.scribe.json")
    assert [(s.words[0].speaker, s.text) for s in rec.segments][:3] == [(0, "Good morning."), (0, "What did you think of the first draft of the film?"), (1, "I thought the opening was much too slow, and the music was far too loud.")]
    assert {w.speaker for s in rec.segments for w in s.words} == {0, 1}


def test_a_refused_reply_writes_no_transcript(tmp_path, audio):
    code, res, raw, err = from_json(tmp_path, audio, words_and_text(66, 1030))
    assert code == 1
    assert "--chunk" in res["error"]
    assert not (tmp_path / "t.jsonl").exists()


def test_no_text_and_no_words_is_media_with_no_speech(tmp_path, audio):
    code, res, raw, err = from_json(tmp_path, audio, reply([], text="", duration=3.0), "--item", "1")
    assert code == 0, raw + err
    assert res["words"] == 0 and res["notes"]
    assert read_line(tmp_path / "t.jsonl")["params"]["transcript"]["words"] == []


# -- keys -----------------------------------------------------------------------------------------------------------------------

def key_file(tmp_path, text):
    f = tmp_path / ".env"
    f.write_text(text)
    return f


@pytest.mark.parametrize("text", ["OPENROUTER_API_KEY=abc\n", "# a comment\nOTHER=1\nOPENROUTER_API_KEY=abc", 'OPENROUTER_API_KEY="abc"\n', "OPENROUTER_API_KEY='abc'\n", "  OPENROUTER_API_KEY = abc  \n", "export OPENROUTER_API_KEY=abc\n"])
def test_the_key_is_read_from_the_file(tmp_path, text):
    assert openrouter.load_key(env={}, file=key_file(tmp_path, text)) == "abc"


def test_a_key_in_the_environment_wins_over_the_file(tmp_path):
    assert openrouter.load_key(env={"OPENROUTER_API_KEY": "from-env"}, file=key_file(tmp_path, "OPENROUTER_API_KEY=from-file\n")) == "from-env"


def test_an_empty_key_in_the_environment_means_no_key_even_with_a_file(tmp_path):
    """So a test can reproduce "no key" without touching the real .env."""
    assert openrouter.load_key(env={"OPENROUTER_API_KEY": ""}, file=key_file(tmp_path, "OPENROUTER_API_KEY=from-file\n")) is None


@pytest.mark.parametrize("text", ["", "# only a comment\n", "OTHER=1\n", "OPENROUTER_API_KEY=\n"])
def test_a_file_without_a_key_means_no_key(tmp_path, text):
    assert openrouter.load_key(env={}, file=key_file(tmp_path, text)) is None


def test_a_missing_file_means_no_key(tmp_path):
    assert openrouter.load_key(env={}, file=tmp_path / "none") is None


def test_no_key_stops_before_any_request_and_does_not_fall_back_to_local(tmp_path, audio, provider, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 1
    assert str(openrouter.KEY_FILE) in res["error"]
    assert provider.requests == []
    assert not (tmp_path / "t.jsonl").exists() and not (tmp_path / "t.whisper.json").exists()


def test_a_malformed_key_is_refused_without_repeating_it(tmp_path, audio, provider, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "abc\ndef")
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 1
    assert "abc" not in raw + err and provider.requests == []


def everything_written(d: Path) -> str:
    return "".join(p.read_text(errors="replace") for p in d.rglob("*") if p.is_file() and p.suffix != ".wav")


@pytest.mark.parametrize("script", [
    [(200, {}, reply([("hello", 1.0, 1.5)], duration=3.0))],
    [(400, {}, {"error": {"message": f"bad key {FAKE_KEY} refused", "code": 400}})],
    [(401, {}, {"error": {"message": f"no auth for {FAKE_KEY}", "code": 401}})],
    [(500, RETRY_NOW, {"error": {"message": f"boom {FAKE_KEY}", "code": 500}})],
    [(200, {}, f"not json {FAKE_KEY}".encode())],
], ids=["success", "400", "401", "500", "not json"])
def test_the_key_appears_nowhere(tmp_path, audio, provider, script):
    provider.script = script
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter", "--item", "1")
    assert provider.requests[0]["auth"] == f"Bearer {FAKE_KEY}"
    assert FAKE_KEY not in raw + err
    assert FAKE_KEY not in everything_written(tmp_path)


# -- the request ------------------------------------------------------------------------------------------------------------

def test_what_is_sent(tmp_path, audio, provider):
    provider.script = [OK_REPLY]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter", "--item", "3")
    assert code == 0, raw + err
    [r] = provider.requests
    assert r["path"] == "/api/v1/audio/transcriptions"
    body = r["body"]
    assert body["model"] == "elevenlabs/scribe-v2"
    assert body["response_format"] == "verbose_json"
    assert set(body["timestamp_granularities"]) == {"word", "segment"}
    assert body["provider"] == {"zdr": True}
    assert body["input_audio"]["format"] == "ogg"
    assert "language" not in body and "diarize" not in body


def test_the_audio_sent_is_mono_16k_opus_from_the_first_audio_stream(tmp_path, audio, provider):
    provider.script = [OK_REPLY]
    run(tmp_path, audio, "--engine", "openrouter")
    sent = tmp_path / "sent.ogg"
    sent.write_bytes(base64.b64decode(provider.requests[0]["body"]["input_audio"]["data"]))
    streams = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(sent)], capture_output=True, text=True).stdout)["streams"]
    assert [(s["codec_name"], s["channels"]) for s in streams] == [("opus", 1)]
    sent.unlink()


def test_language_diarize_model_and_no_zdr_reach_the_request(tmp_path, audio, provider):
    provider.script = [OK_REPLY]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter", "--language", "ko", "--diarize", "--no-zdr", "--model", "some/model")
    assert code == 0, raw + err
    body = provider.requests[0]["body"]
    assert body["language"] == "ko" and body["diarize"] is True and body["model"] == "some/model"
    assert not (body.get("provider") or {}).get("zdr")


def test_a_successful_request_reports_cost_and_keeps_the_reply(tmp_path, audio, provider):
    provider.script = [OK_REPLY]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter", "--item", "3")
    assert code == 0, raw + err
    assert res["engine"] == "openrouter" and res["model"] == "elevenlabs/scribe-v2"
    assert res["cost_usd"] == 0.01 and res["language"] == "en" and res["item"] == 3
    assert res["raw"] == str(tmp_path / "t.openrouter.json")
    assert json.loads((tmp_path / "t.openrouter.json").read_text()) == OK_REPLY[2]
    assert read_line(tmp_path / "t.jsonl")["params"]["transcript"]["source"] == "openrouter elevenlabs/scribe-v2"


def test_openrouter_times_are_kept_by_default_and_snap_on_moves_them(tmp_path, audio, provider):
    """1.0-2.0 s is the tone; the reply starts 0.2 s inside it and ends 0.5 s past it."""
    provider.script = [(200, {}, reply([("a", 1.2, 2.5, {"confidence": 0.9})], duration=3.0))]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 0, raw + err
    assert res["snapped"] == 0
    assert seconds_of(read_line(tmp_path / "t.jsonl")) == [("a", 1.2, 2.5)]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter", "--snap", "on", out="u.jsonl")
    assert code == 0, raw + err
    assert res["snapped"] == 1
    assert seconds_of(read_line(tmp_path / "u.jsonl")) == [("a", 1.0, 2.0)]


# -- failures -------------------------------------------------------------------------------------------------------------------

def no_traceback(raw, err):
    assert "Traceback" not in raw + err


def test_a_retryable_status_is_tried_again_and_can_succeed(tmp_path, audio, provider):
    provider.script = [(429, RETRY_NOW, {"error": {"message": "slow down"}}), (503, RETRY_NOW, {"error": {"message": "busy"}}), (408, RETRY_NOW, {}), OK_REPLY]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 0, raw + err
    assert len(provider.requests) == 4


def test_retries_run_out_with_a_chunk_hint(tmp_path, audio, provider):
    provider.script = [(502, RETRY_NOW, {"error": {"message": "Provider returned 500"}})]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 1
    no_traceback(raw, err)
    assert len(provider.requests) == 4
    assert "--chunk" in res["error"] and "Provider returned 500" in res["error"]


def test_retry_after_is_followed(tmp_path, audio, provider):
    provider.script = [(429, {"Retry-After": "2"}, {}), OK_REPLY]
    t = time.time()
    code, *_ = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 0
    assert time.time() - t >= 2


@pytest.mark.parametrize("status", [401, 402])
def test_no_auth_or_no_credit_is_a_tool_failure_with_the_providers_message(tmp_path, audio, provider, status):
    provider.script = [(status, {}, {"error": {"message": "the provider says why", "code": status}, "user_id": "user_abc"})]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 1 and len(provider.requests) == 1
    no_traceback(raw, err)
    assert "the provider says why" in res["error"]
    assert "user_abc" not in raw + err


@pytest.mark.parametrize("status, message", [(400, "The selected model does not support diarize."), (404, "No such model")])
def test_an_argument_the_provider_refuses_is_a_usage_error(tmp_path, audio, provider, status, message):
    provider.script = [(status, {}, {"error": {"message": message, "code": status}})]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 2 and len(provider.requests) == 1
    no_traceback(raw, err)
    assert message in res["error"]


def test_a_refused_connection_is_a_tool_failure(tmp_path, audio, monkeypatch):
    monkeypatch.setenv("OPENROUTER_BASE_URL", "http://127.0.0.1:9/api/v1")
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 1
    no_traceback(raw, err)
    assert "OpenRouter" in res["error"]


def test_a_200_that_is_not_json_is_a_tool_failure(tmp_path, audio, provider):
    provider.script = [(200, {}, b"<html>gateway</html>")]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 1
    no_traceback(raw, err)
    assert not (tmp_path / "t.jsonl").exists() and not (tmp_path / "t.openrouter.json").exists()


def test_a_slow_provider_times_out_as_a_tool_failure(tmp_path, audio, provider):
    def slow(body):
        time.sleep(1)
        return OK_REPLY
    provider.script = [slow]
    with pytest.raises(ToolError, match="OpenRouter"):
        openrouter.transcribe(audio, "m", None, False, True, timeout=0.2)


def test_a_truncated_live_reply_writes_nothing(tmp_path, audio, provider):
    provider.script = [(200, {}, words_and_text(66, 1030))]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 1
    assert "--chunk" in res["error"]
    assert not (tmp_path / "t.jsonl").exists()


def test_the_temporary_audio_is_gone_after_success_and_failure(tmp_path, audio, provider):
    provider.script = [OK_REPLY]
    run(tmp_path, audio, "--engine", "openrouter")
    provider.requests.clear()
    provider.script = [(400, {}, {"error": {"message": "no"}})]
    run(tmp_path, audio, "--engine", "openrouter", out="u.jsonl")
    left = sorted(p.name for p in tmp_path.iterdir() if p.name != ".fcdata")
    assert left == sorted(["b.wav", "t.jsonl", "t.txt", "t.openrouter.json"])


# -- where the key may go ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["http://example.com/api/v1", "ftp://example.com/", "http://127.0.0.1.example.com/api/v1"])
def test_the_key_never_travels_in_the_clear(tmp_path, audio, monkeypatch, url):
    monkeypatch.setenv("OPENROUTER_BASE_URL", url)
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 1
    no_traceback(raw, err)
    assert "OPENROUTER_BASE_URL" in res["error"]


def test_a_redirect_is_not_followed(tmp_path, audio, provider, monkeypatch):
    """urllib would otherwise carry the Authorization header to wherever a reply points."""
    other = Provider()
    try:
        other.script = [OK_REPLY]
        provider.script = [(302, {"Location": other.url + "/audio/transcriptions"}, {})]
        code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
        assert code == 1
        no_traceback(raw, err)
        assert other.requests == []
    finally:
        other.close()


# -- the command line ---------------------------------------------------------------------------------------------------------

def test_neither_engine_nor_from_json_is_a_usage_error_and_sends_nothing(tmp_path, audio, provider):
    code, res, raw, err = run(tmp_path, audio)
    assert code == 2 and "--engine" in res["error"]
    assert provider.requests == []


def test_engine_and_from_json_exclude_each_other(tmp_path, audio):
    code, *_ = run(tmp_path, audio, "--engine", "local", "--from-json", str(FIXTURES / "say_ko.scribe.json"))
    assert code == 2


@pytest.mark.parametrize("flag", [["--diarize"], ["--no-zdr"], ["--chunk", "10"]])
def test_openrouter_flags_with_local_are_a_usage_error(tmp_path, audio, flag):
    code, res, raw, err = run(tmp_path, audio, "--engine", "local", *flag)
    assert code == 2 and flag[0] in res["error"]


@pytest.mark.parametrize("flag", [["--diarize"], ["--no-zdr"], ["--chunk", "10"]])
def test_openrouter_flags_with_from_json_are_a_usage_error_because_nothing_is_sent(tmp_path, audio, flag):
    code, res, raw, err = run(tmp_path, audio, "--from-json", str(FIXTURES / "say_ko.scribe.json"), *flag)
    assert code == 2 and flag[0] in res["error"]


def test_an_existing_out_is_left_alone(tmp_path, audio, provider):
    """A corrected transcript must not be replaced by a fresh recognition that also cost money."""
    (tmp_path / "t.jsonl").write_text("corrected by hand\n")
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 2 and "t.jsonl" in res["error"]
    assert (tmp_path / "t.jsonl").read_text() == "corrected by hand\n"
    assert provider.requests == []


def test_an_existing_paid_reply_is_left_alone(tmp_path, audio, provider):
    (tmp_path / "t.openrouter.json").write_text("{}")
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 2 and "t.openrouter.json" in res["error"]
    assert (tmp_path / "t.openrouter.json").read_text() == "{}"
    assert provider.requests == []


def test_a_reply_can_be_read_again_next_to_itself_after_the_transcript_is_deleted(tmp_path, audio, provider):
    provider.script = [OK_REPLY]
    run(tmp_path, audio, "--engine", "openrouter")
    (tmp_path / "t.jsonl").unlink()
    code, res, raw, err = run(tmp_path, audio, "--from-json", str(tmp_path / "t.openrouter.json"))
    assert code == 0, raw + err
    assert res["engine"] == "openrouter" and res["cost_usd"] == 0
    assert len(provider.requests) == 1


def test_without_item_the_next_step_fills_the_item_and_never_transcribes_again(tmp_path, audio):
    """Running again would replace the corrected text, so `next` must not suggest it."""
    code, res, raw, err = from_json(tmp_path, audio, OK_REPLY[2])
    assert code == 0, raw + err
    assert res["item"] is None
    assert read_line(tmp_path / "t.jsonl")["params"]["item"] is None
    assert "params.item" in res["next"] and "run" in res["next"] and "transcribe" not in res["next"]


def test_with_item_the_next_step_is_the_run_command(tmp_path, audio):
    code, res, raw, err = from_json(tmp_path, audio, OK_REPLY[2], "--item", "4")
    assert code == 0, raw + err
    assert read_line(tmp_path / "t.jsonl")["params"]["item"] == 4
    assert shlex.split(res["next"])[-1] == str(tmp_path / "t.jsonl")


@pytest.mark.parametrize("content", ["[]", "{}", '{"text": "x"}', "not json"])
def test_an_unknown_from_json_is_a_usage_error(tmp_path, audio, content):
    f = tmp_path / "w.json"
    f.write_text(content)
    code, res, raw, err = run(tmp_path, audio, "--from-json", str(f))
    assert code == 2 and "w.json" in res["error"]


def test_a_reply_with_unreadable_word_times_from_a_file_is_a_usage_error(tmp_path, audio):
    code, res, raw, err = from_json(tmp_path, audio, reply([("a", "NaN", 2)]))
    assert code == 2 and "raw.json" in res["error"]


def test_a_live_reply_with_unreadable_word_times_is_a_tool_failure(tmp_path, audio, provider):
    provider.script = [(200, {}, {"text": "a", "words": [{"word": "a"}], "duration": 3})]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter")
    assert code == 1
    no_traceback(raw, err)


def test_a_saved_whisper_json_is_still_read_as_whisper(tmp_path):
    audio = tone_bursts(tmp_path / "b.wav", [(1.0, 2.0)], 3)
    w = tmp_path / "w.json"
    w.write_text(json.dumps({"language": "ko", "segments": [{"start": 1.1, "end": 1.9, "text": "가", "words": [{"word": " 가", "start": 1.1, "end": 1.9, "probability": 0.9}]}]}))
    code, res, raw, err = run(tmp_path, audio, "--from-json", str(w))
    assert code == 0, raw + err
    assert res["engine"] == "local" and res["snapped"] == 1
    assert seconds_of(read_line(tmp_path / "t.jsonl")) == [("가", 1.0, 2.0)]


# -- what is written -----------------------------------------------------------------------------------------------------------------

DIARIZED = reply([("[music]", 0.0, 0.5, {"type": "audio_event"}), ("Hello", 1.0, 1.2, {"speaker": 0, "confidence": 0.9}), ("there.", 1.3, 1.5, {"speaker": 0, "confidence": 0.9}), ("Hi.", 1.6, 1.9, {"speaker": 2, "confidence": 0.9})], text="[music] Hello there. Hi.", duration=3.0)


def test_speakers_and_events_are_written(tmp_path, audio):
    code, res, raw, err = from_json(tmp_path, audio, DIARIZED, "--item", "1")
    assert code == 0, raw + err
    assert res["speakers"] == 2 and res["audio_events"] == 1 and res["words"] == 3
    t = read_line(tmp_path / "t.jsonl")["params"]["transcript"]
    assert t["speakers"] == [{"name": "Speaker 0"}, {"name": "Speaker 1"}, {"name": "Speaker 2"}]
    assert [w["speaker"] for w in t["words"]] == [0, 0, 2]
    text = (tmp_path / "t.txt").read_text()
    assert "[music]" in text and "Speaker 2" in text and "[w0-w1]" in text and "Hello there." in text


def test_output_fields_come_cheap_signal_first(tmp_path, audio):
    code, res, raw, err = from_json(tmp_path, audio, OK_REPLY[2], "--item", "1")
    assert code == 0, raw + err
    assert list(res) == ["engine", "model", "item", "language", "words", "seconds", "speech_seconds", "cost_usd", "speakers", "audio_events", "snapped", "unmatched", "has_confidence", "review", "review_total", "review_file", "out", "text", "raw", "next", "notes"]


@needs_filmcraft
def test_speakers_round_trip_through_filmcraft(tmp_path):
    """The recorded two-voice reply through transcript.set to transcript.inspect: words, speakers and the paragraph break at each change of voice."""
    movie = tmp_path / "talk.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=c=gray:s=640x360:r=30:d=16", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=16", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(movie))
    p = tmp_path / "p.fcproj"
    item = json.loads(fc("--save-as", str(p), "import", str(movie), cwd=tmp_path).stdout)["items"][0]
    assert all(l["ok"] for l in fc_run([{"id": "file.newSequenceFromClip", "params": {"items": [item]}}], p, cwd=tmp_path))
    code, res, out, err = run(tmp_path, movie, "--from-json", str(FIXTURES / "say_en_two_voices.scribe.json"), "--item", str(item))
    assert code == 0, out + err
    assert res["speakers"] == 2
    fc("run", str(tmp_path / "t.jsonl"), project=p, save=True, cwd=tmp_path)
    got = fc_json("exec", "transcript.inspect", project=p, cwd=tmp_path)
    want = read_line(tmp_path / "t.jsonl")["params"]["transcript"]
    assert [w["text"] for w in got["words"]] == [w["text"] for w in want["words"]]
    assert [w["speaker"] for w in got["words"]] == [f"Speaker {w['speaker']}" for w in want["words"]]
    assert got["speakers"] == ["Speaker 0", "Speaker 1"]
    assert [q["speaker"] for q in got["paragraphs"]] == ["Speaker 0", "Speaker 1", "Speaker 0", "Speaker 1"]


@needs_filmcraft
def test_a_reply_without_confidence_applies_in_filmcraft(tmp_path):
    """FilmCraft refuses `"confidence": null`, so the key is left out, and the line goes through."""
    movie = tmp_path / "talk.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=c=gray:s=640x360:r=30:d=11", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=11", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(movie))
    p = tmp_path / "p.fcproj"
    item = json.loads(fc("--save-as", str(p), "import", str(movie), cwd=tmp_path).stdout)["items"][0]
    assert all(l["ok"] for l in fc_run([{"id": "file.newSequenceFromClip", "params": {"items": [item]}}], p, cwd=tmp_path))
    code, res, out, err = run(tmp_path, movie, "--from-json", str(FIXTURES / "say_ko.nemotron.json"), "--item", str(item))
    assert code == 0, out + err
    fc("run", str(tmp_path / "t.jsonl"), project=p, save=True, cwd=tmp_path)
    assert len(fc_json("exec", "transcript.inspect", project=p, cwd=tmp_path)["words"]) == res["words"]


# -- splitting --------------------------------------------------------------------------------------------------------------------------

def test_a_duration_under_the_limit_is_one_chunk():
    assert transcribe.plan_chunks(100.0, [(1, 2)], limit=200.0) == ([(0.0, 100.0)], 0)


def test_a_cut_lands_in_the_middle_of_the_longest_silence_before_the_limit():
    """Worked by hand. Limit 100, window 30: silences inside 70-100 are 72-74 and 80-90, so the cut is at 85. From 85 the end at 150 is within reach."""
    spans = [(0, 72), (74, 80), (90, 150)]
    assert transcribe.plan_chunks(150.0, spans, limit=100.0) == ([(0.0, 85.0), (85.0, 150.0)], 0)


def test_with_no_silence_near_the_limit_the_cut_is_at_the_limit_and_counted():
    assert transcribe.plan_chunks(250.0, [(0, 250)], limit=100.0) == ([(0.0, 100.0), (100.0, 200.0), (200.0, 250.0)], 2)


def test_no_measured_speech_is_not_treated_as_silence():
    """Continuous music or tone gives no spans at all because the level never varies; there is nowhere known to be safe to cut."""
    assert transcribe.plan_chunks(250.0, [], limit=100.0) == ([(0.0, 100.0), (100.0, 200.0), (200.0, 250.0)], 2)


def test_silence_before_the_window_is_not_used():
    spans = [(0, 10), (60, 250)]
    assert transcribe.plan_chunks(250.0, spans, limit=100.0, window=30.0) == ([(0.0, 100.0), (100.0, 200.0), (200.0, 250.0)], 2)


def test_a_limit_shorter_than_the_window_still_moves_forward():
    """Worked by hand. Limit 4: 0-3 (middle of the 2-4 silence), 3-6 (middle of 5-7), then 6-9 is within reach."""
    spans = [(1, 2), (4, 5), (7, 8)]
    assert transcribe.plan_chunks(9.0, spans, limit=4.0) == ([(0.0, 3.0), (3.0, 6.0), (6.0, 9.0)], 0)


def test_a_silence_at_the_start_of_a_chunk_cannot_stop_it_moving_forward():
    chunks, forced = transcribe.plan_chunks(30.0, [(0, 5), (5.5, 30)], limit=5.0)
    assert all(b > a for a, b in chunks) and chunks[-1][1] == 30.0
    assert all(chunks[i][1] == chunks[i + 1][0] for i in range(len(chunks) - 1))


@pytest.mark.parametrize("size, seconds, want", [
    (18_000_000, 6000.0, None),                 # base64 24 MB exactly: not over
    (15_700_000, 5186.0, None),                 # the measured 86 minutes fits whole
    (30_000_000, 1000.0, 540.0),                # base64 40 MB: 24/40 of the length, less a tenth for bitrate that is not even
])
def test_when_a_file_is_too_big_to_send_whole(size, seconds, want):
    got = transcribe.auto_chunk(size, seconds)
    assert got == (pytest.approx(want) if want else None)


def chunk_reply(body):
    """The same reply for every chunk, so where each word lands shows the chunk's offset."""
    return (200, {}, reply([("a", 0.5, 1.0, {"confidence": 0.9}), ("b.", 1.1, 1.4, {"confidence": 0.9})], duration=3.0, cost=0.5))


def test_chunks_are_sent_and_merged_in_order_with_times_costs_and_text_added(tmp_path, provider):
    audio = tone_bursts(tmp_path / "b.wav", [(1.0, 2.0), (4.0, 5.0), (7.0, 8.0)], 9)
    provider.script = [chunk_reply]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter", "--chunk", "4")
    assert code == 0, raw + err
    assert len(provider.requests) == 3
    assert seconds_of(read_line(tmp_path / "t.jsonl")) == [("a", 0.5, 1.0), ("b.", 1.1, 1.4), ("a", 3.5, 4.0), ("b.", 4.1, 4.4), ("a", 6.5, 7.0), ("b.", 7.1, 7.4)]
    assert res["cost_usd"] == 1.5
    merged = json.loads((tmp_path / "t.openrouter.json").read_text())
    assert merged["text"] == "a b. a b. a b." and merged["duration"] == 9.0 and merged["usage"]["cost"] == 1.5
    assert [s["start"] for s in merged["segments"]] == [0, 3.0, 6.0]


def test_a_merged_reply_reads_again_without_being_refused(tmp_path, provider):
    audio = tone_bursts(tmp_path / "b.wav", [(1.0, 2.0), (4.0, 5.0), (7.0, 8.0)], 9)
    provider.script = [chunk_reply]
    run(tmp_path, audio, "--engine", "openrouter", "--chunk", "4")
    code, res, raw, err = run(tmp_path, audio, "--from-json", str(tmp_path / "t.openrouter.json"), out="again.jsonl")
    assert code == 0, raw + err
    assert res["words"] == 6


def test_a_chunk_reply_too_short_is_refused_like_a_whole_one(tmp_path, provider):
    audio = tone_bursts(tmp_path / "b.wav", [(1.0, 2.0), (4.0, 5.0)], 6)
    provider.script = [(200, {}, words_and_text(66, 1030))]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter", "--chunk", "3")
    assert code == 1
    assert not (tmp_path / "t.jsonl").exists() and not (tmp_path / "t.openrouter.json").exists()


def test_a_forced_cut_is_noted(tmp_path, provider):
    audio = tone_bursts(tmp_path / "b.wav", [(0.0, 6.0)], 6)
    provider.script = [chunk_reply]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter", "--chunk", "2")
    assert code == 0, raw + err
    assert any("silence" in n for n in res["notes"])


def test_diarize_with_chunks_warns_that_speaker_numbers_restart(tmp_path, provider):
    audio = tone_bursts(tmp_path / "b.wav", [(1.0, 2.0), (4.0, 5.0)], 6)
    provider.script = [chunk_reply]
    code, res, raw, err = run(tmp_path, audio, "--engine", "openrouter", "--chunk", "3", "--diarize")
    assert code == 0, raw + err
    assert any("speaker" in n.lower() for n in res["notes"])


# -- review signals -----------------------------------------------------------------------------------------------------------------------

def reasons(res):
    return [r["reason"] for r in res["review"]]


def test_low_prob_needs_a_probability(tmp_path, audio):
    code, res, raw, err = from_json(tmp_path, audio, reply([("a", 1.0, 1.2, {"confidence": 0.2}), ("b", 1.3, 1.5)]))
    assert code == 0, raw + err
    assert reasons(res) == ["low_prob"] and res["review"][0]["text"] == "a"


def test_repeat_works_on_lines_split_from_one_segment(tmp_path, audio):
    words = [("Thanks.", 0.2 + i, 0.6 + i) for i in range(3)]
    code, res, raw, err = from_json(tmp_path, audio, reply(words))
    assert code == 0, raw + err
    assert reasons(res).count("repeat") == 3


def test_a_compressed_stretch_is_flagged_once_for_each_stretch(tmp_path, audio):
    """71 words in 10 s is over 7 a second; 70 is not. Each word is 0.05 s long and 0.14 s apart, 70 fit in 9.8 s."""
    many = [(f"w{i}", 100 + i * 0.14, 100 + i * 0.14 + 0.05, {"confidence": 0.9}) for i in range(72)]
    code, res, raw, err = from_json(tmp_path, audio, reply(many, duration=200))
    assert code == 0, raw + err
    flagged = [r for r in res["review"] if r["reason"] == "compressed"]
    assert len(flagged) == 1 and flagged[0]["start_s"] == 100.0


def test_seven_words_a_second_is_not_compressed(tmp_path, audio):
    even = [(f"w{i}", 100 + i * 0.143, 100 + i * 0.143 + 0.05, {"confidence": 0.9}) for i in range(70)]
    code, res, raw, err = from_json(tmp_path, audio, reply(even, duration=200))
    assert code == 0, raw + err
    assert "compressed" not in reasons(res)


def test_unmatched_is_a_word_with_no_speech_under_it(tmp_path, audio):
    code, res, raw, err = from_json(tmp_path, audio, reply([("a", 1.2, 1.5, {"confidence": 0.9}), ("ghost", 2.3, 2.6, {"confidence": 0.9})], duration=3.0))
    assert code == 0, raw + err
    assert res["unmatched"] == 1 and reasons(res) == ["unmatched"]


# -- the zero-length word and --snap, at the pure seam ----------------------------------------------------------------------------------------

def W(text, start, end, prob=1.0):
    return transcribe.Word(text, start, end, prob)


def test_a_zero_length_word_inside_speech_belongs_to_it_and_gets_a_frame():
    out, report = transcribe.snap([W("a", 1.5, 1.5)], [(1.0, 2.0)], max_shift=0.0, min_dur=1 / 30)
    assert report["unmatched"] == []
    assert out[0].end - out[0].start == pytest.approx(1 / 30)


def test_a_zero_length_word_in_silence_is_unmatched():
    out, report = transcribe.snap([W("a", 5.0, 5.0)], [(1.0, 2.0)], max_shift=0.0, min_dur=1 / 30)
    assert report["unmatched"] == [0]


def test_keeping_times_moves_no_edge_but_still_orders_and_reports():
    words = [W("b", 1.4, 1.8), W("a", 1.0, 1.5), W("x", 5.0, 5.2), W("z", 6.0, 6.0)]
    out, report = transcribe.keep_times(words, [(0.5, 2.5)], min_dur=1 / 30)
    assert [(w.text, w.start, round(w.end, 3)) for w in out] == [("a", 1.0, 1.4), ("b", 1.4, 1.8), ("x", 5.0, 5.2), ("z", 6.0, 6.033)]
    assert report == {"snapped": 0, "unmatched": [2, 3]}


def test_snap_off_on_whisper_leaves_its_edges(tmp_path):
    audio = tone_bursts(tmp_path / "b.wav", [(1.0, 2.0)], 3)
    w = tmp_path / "w.json"
    w.write_text(json.dumps({"language": "ko", "segments": [{"start": 1.2, "end": 2.5, "text": "가", "words": [{"word": " 가", "start": 1.2, "end": 2.5, "probability": 0.9}]}]}))
    code, res, raw, err = run(tmp_path, audio, "--from-json", str(w), "--snap", "off")
    assert code == 0, raw + err
    assert res["snapped"] == 0
    assert seconds_of(read_line(tmp_path / "t.jsonl")) == [("가", 1.2, 2.5)]


# -- help ---------------------------------------------------------------------------------------------------------------------------------------

def test_help_owns_the_engine_choice_keys_and_correction():
    code, _, raw, err = skill("transcribe", "--help")
    assert code == 0
    for word in ("--engine", "--from-json", "--diarize", "--no-zdr", "--snap", "--chunk", "--item", "compressed", "low_prob", "unmatched", "repeat", "no_speech", "cost_usd", str(openrouter.KEY_FILE.name), "params.item", "Prints:", "Exits:", "one English documentary"):
        assert word in raw, word


# -- the real API, on demand ------------------------------------------------------------------------------------------------------------------

SAY = [("오늘은 편집 이야기를 해볼게요", 0.6), ("자막은 문장 단위로 끊어야 읽기 편합니다", 0.9), ("그럼 바로 시작하겠습니다", 1.2)]


@pytest.mark.skipif(os.environ.get("FILMCRAFT_TEST_OPENROUTER") != "1", reason="set FILMCRAFT_TEST_OPENROUTER=1 to send about ten seconds of synthetic speech to OpenRouter (about a cent)")
def test_real_openrouter_round_trip(tmp_path, monkeypatch):
    """Expected phrase edges come from the generator: each phrase synthesised alone and joined after a known silence."""
    if shutil.which("say") is None:
        pytest.skip("macOS `say` is needed")
    monkeypatch.delenv("OPENROUTER_API_KEY")
    parts, edges, t = [], [], 0.0
    for i, (text, gap) in enumerate(SAY):
        aiff, wav, sil = tmp_path / f"p{i}.aiff", tmp_path / f"p{i}.wav", tmp_path / f"s{i}.wav"
        subprocess.run(["say", "-v", "Yuna", "-o", str(aiff), text], check=True)
        ffmpeg("-i", str(aiff), "-ar", "48000", "-ac", "1", str(wav))
        ffmpeg("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", str(gap), str(sil))
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)], capture_output=True, text=True).stdout)
        parts += [sil, wav]
        edges.append((t + gap, t + gap + dur))
        t += gap + dur
    speech = tmp_path / "speech.wav"
    ffmpeg(*sum((["-i", str(p)] for p in parts), []), "-filter_complex", f"concat=n={len(parts)}:v=0:a=1", str(speech))
    code, res, raw, err = run(tmp_path, speech, "--engine", "openrouter", "--language", "ko", "--item", "1")
    assert code == 0, raw + err
    assert res["language"] == "ko" and res["cost_usd"] > 0 and res["has_confidence"]
    words = read_line(tmp_path / "t.jsonl")["params"]["transcript"]["words"]
    text = " ".join(w["text"] for w in words)
    assert "편집" in text and "자막" in text
    assert abs(words[0]["start"] / TICKS - edges[0][0]) < 0.25

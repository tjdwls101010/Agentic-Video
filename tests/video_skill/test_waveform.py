"""`waveform`: the sound drawn where a model can look at it, with word boxes on the same time axis.

Everything rests on one claim: a column of the picture means the time it says. So expectations come from tone bursts at times the generator chose, and the columns are read back out of the rendered sheet: the waveform panel, the spectrogram panel and the word boxes each against the column computed from the generator, because boxes checked alone would pass with the picture shifted under them."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from support import TICKS, ffmpeg, make_av, needs_ffmpeg, skill

pytestmark = needs_ffmpeg

TONE = 1000


def tone_bursts(path, bursts, total, rate=48000):
    expr = "+".join(f"between(t\\,{a}\\,{b})" for a, b in bursts)
    ffmpeg("-f", "lavfi", "-i", f"aevalsrc=0.3*sin(2*PI*{TONE}*t)*({expr}):s={rate}:d={total}", "-c:a", "pcm_s16le", str(path))
    return path


def jsonl(path, words):
    path.write_text(json.dumps({"id": "transcript.set", "params": {"item": None, "transcript": {"language": "en", "source": "test", "speakers": [], "words": [{"text": t, "start": round(a * TICKS), "end": round(b * TICKS)} for t, a, b in words]}}}) + "\n")
    return path


def run(tmp_path, media, *args, out="w.png"):
    return skill("waveform", str(media), "--out", str(tmp_path / out), *args, cwd=tmp_path)


def grid_columns(start, end, width):
    """Whole-second grid lines are drawn over the panels; reading a column skips them."""
    cols = set()
    t = int(start)
    while t <= end:
        cols.update({round((t - start) / (end - start) * width) + d for d in (-1, 0, 1)})
        t += 1
    return cols


def energy_starts(img, y0, y1, start, end, width, floor=40):
    """Columns where the panel's brightest pixel between y0 and y1 rises past `floor`, having been below it."""
    grid = grid_columns(start, end, width)
    col = [max(img.getpixel((x, y)) for y in range(y0, y1)) for x in range(width)]
    return [x for x in range(1, width) if col[x] > floor and col[x - 1] <= floor and x not in grid and x - 1 not in grid]


def expected(t, start, end, width):
    return (t - start) / (end - start) * width


@pytest.mark.parametrize("rate", [48000, 44100, 16000])
@pytest.mark.parametrize("start, end", [(10.0, 20.0), (11.25, 13.75)])
def test_both_panels_start_their_energy_at_the_computed_column(tmp_path, rate, start, end):
    """The burst starts at 12.3 s. ±1 px at 600 px/s is under 2 ms; a spectrogram drawn at the source's own rate slides right by more than that as the rate falls."""
    audio = tone_bursts(tmp_path / "t.wav", [(12.3, 13.0), (15.7, 16.25)], 22, rate)
    code, res, raw, err = run(tmp_path, audio, "--at", f"{start}-{end}")
    assert code == 0, raw + err
    w = res["windows"][0]
    img = Image.open(res["sheet"]).convert("L")
    width = res["width"]
    want = expected(12.3, start, end, width)
    wave = energy_starts(img, *w["y"]["wave"], start, end, width)
    assert any(abs(x - want) <= 1 for x in wave), (wave, want)
    # the row of the 1 kHz band, counted from the bottom of a 0-8 kHz panel
    y0, y1 = w["y"]["spectrum"]
    band = round(y1 - (y1 - y0) * TONE / 8000)
    spec = energy_starts(img, band - 2, band + 3, start, end, width, floor=120)
    assert any(abs(x - want) <= 1 for x in spec), (spec, want)


def test_a_word_box_lands_on_the_column_of_its_energy(tmp_path):
    start, end = 10.0, 20.0
    audio = tone_bursts(tmp_path / "t.wav", [(12.3, 13.0)], 22)
    f = jsonl(tmp_path / "a.jsonl", [("word", 12.3, 13.0)])
    code, res, raw, err = run(tmp_path, audio, "--at", f"{start}-{end}", "--words", str(f))
    assert code == 0, raw + err
    w = res["windows"][0]
    img = Image.open(res["sheet"]).convert("L")
    y0, y1 = w["y"]["rows"]
    y = (y0 + y1) // 2
    width = res["width"]
    col = [img.getpixel((x, y)) for x in range(width)]
    grid = grid_columns(start, end, width)
    lit = [x for x in range(width) if col[x] > 60 and x not in grid]
    assert abs(lit[0] - expected(12.3, start, end, width)) <= 1, lit[:5]
    assert abs(lit[-1] - expected(13.0, start, end, width)) <= 1 or lit[-1] > width - 120, lit[-5:]


def test_speech_is_reported_inside_each_window_within_two_hundredths(tmp_path):
    audio = tone_bursts(tmp_path / "t.wav", [(12.3, 13.0), (15.7, 16.25)], 22)
    code, res, raw, err = run(tmp_path, audio, "--at", "10-14", "15-20", "12.5-13.5")
    assert code == 0, raw + err
    got = [w["speech"] for w in res["windows"]]
    assert got[0] == [pytest.approx([12.3, 13.0], abs=0.02)]
    assert got[1] == [pytest.approx([15.7, 16.25], abs=0.02)]
    assert got[2] == [pytest.approx([12.5, 13.0], abs=0.02)]


def test_several_windows_stack_on_one_sheet(tmp_path):
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 10)
    code, res, raw, err = run(tmp_path, audio, "--at", "0-3", "4-6")
    assert code == 0, raw + err
    a, b = res["windows"]
    assert a["y"]["wave"][1] <= b["y"]["wave"][0]
    assert Image.open(res["sheet"]).size[0] == res["width"]


def test_an_audio_stream_shorter_than_the_window_is_not_stretched(tmp_path):
    """A movie can outlast its sound; the panels must still span the whole window."""
    wav = tone_bursts(tmp_path / "t.wav", [(3.5, 4.0)], 5)
    movie = tmp_path / "m.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=c=gray:s=320x180:r=30:d=9", "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(tmp_path / "m.mov"))
    movie = tmp_path / "m.mov"
    code, res, raw, err = run(tmp_path, movie, "--at", "3.2-8.2")
    assert code == 0, raw + err
    w = res["windows"][0]
    img = Image.open(res["sheet"]).convert("L")
    want = expected(3.5, 3.2, 8.2, res["width"])
    wave = energy_starts(img, *w["y"]["wave"], 3.2, 8.2, res["width"])
    assert any(abs(x - want) <= 1 for x in wave), (wave, want)


def test_rows_report_only_what_overlaps_the_window_from_either_format(tmp_path):
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 10)
    a = jsonl(tmp_path / "a.jsonl", [("before", 0.0, 0.5), ("inside", 1.0, 1.5), ("across", 2.8, 3.2), ("after", 5.0, 5.5)])
    b = tmp_path / "b.srt"
    b.write_text("1\n00:00:01,000 --> 00:00:02,000\n자막\n둘째 줄\n\n2\n00:00:06,000 --> 00:00:07,000\n밖\n", encoding="utf-8")
    code, res, raw, err = run(tmp_path, audio, "--at", "1-3", "--words", str(a), str(b))
    assert code == 0, raw + err
    rows = res["windows"][0]["rows"]
    assert [r["source"] for r in rows] == ["a.jsonl", "b.srt"]
    assert [i["text"] for i in rows[0]["items"]] == ["inside", "across"]
    assert rows[0]["items"][1] == {"text": "across", "start": 2.8, "end": 3.2}
    assert [i["text"] for i in rows[1]["items"]] == ["자막 둘째 줄"]


def test_a_source_with_nothing_in_a_window_is_noted(tmp_path):
    """Usually the wrong file, or times from another media item."""
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 10)
    a = jsonl(tmp_path / "a.jsonl", [("far", 8.0, 8.5)])
    code, res, raw, err = run(tmp_path, audio, "--at", "1-3", "--words", str(a))
    assert code == 0, raw + err
    assert any("a.jsonl" in n for n in res["notes"])


def test_a_transcribe_line_without_an_item_is_readable(tmp_path):
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 3)
    code, res, raw, err = skill("transcribe", str(audio), "--out", str(tmp_path / "x.jsonl"), "--from-json", str(Path(__file__).parent / "fixtures/say_ko.scribe.json"), cwd=tmp_path)
    assert code == 0, raw + err
    code, res, raw, err = run(tmp_path, audio, "--at", "0-3", "--words", str(tmp_path / "x.jsonl"))
    assert code == 0, raw + err
    assert [i["text"] for i in res["windows"][0]["rows"][0]["items"]][:2] == ["오늘은", "편집"]


def test_timecodes_read_at_the_medias_rate(tmp_path):
    movie = make_av(tmp_path / "m.mp4", 5, rate="30")
    code, res, raw, err = run(tmp_path, movie, "--at", "00:00:01:15-00:00:03:00")
    assert code == 0, raw + err
    w = res["windows"][0]
    assert (w["start"], w["end"]) == (1.5, 3.0)


@pytest.mark.parametrize("at", [
    ["1-1"], ["3-2"], ["nope"], ["1"], ["1-2-3"], ["nan-2"], ["-1-2"],    # not a window
    ["0-61"],                                                             # longer than a sheet can show
    ["8-12"],                                                             # past the end of the 10 s file
    [f"{i}-{i + 0.5}" for i in range(9)],                                 # too many
])
def test_a_window_that_cannot_be_drawn_is_a_usage_error(tmp_path, at):
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 10)
    code, res, raw, err = run(tmp_path, audio, "--at", *at)
    assert code == 2 and res and res["error"]
    assert "Traceback" not in raw + err
    assert not (tmp_path / "w.png").exists()


def test_exactly_sixty_seconds_is_allowed(tmp_path):
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 61)
    code, res, raw, err = run(tmp_path, audio, "--at", "0-60")
    assert code == 0, raw + err


def test_an_at_with_no_windows_is_a_usage_error(tmp_path):
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 10)
    code, *_ = run(tmp_path, audio)
    assert code == 2


def test_more_than_four_sources_is_a_usage_error(tmp_path):
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 10)
    a = jsonl(tmp_path / "a.jsonl", [("x", 1.0, 1.5)])
    code, res, raw, err = run(tmp_path, audio, "--at", "1-2", "--words", *[str(a)] * 5)
    assert code == 2 and "4" in res["error"]


@pytest.mark.parametrize("content, name", [("not json\n", "bad.jsonl"), ('{"id": "other"}\n', "other.jsonl"), ("nope", "bad.srt")])
def test_an_unreadable_source_is_a_usage_error(tmp_path, content, name):
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 10)
    f = tmp_path / name
    f.write_text(content)
    code, res, raw, err = run(tmp_path, audio, "--at", "1-2", "--words", str(f))
    assert code == 2 and name in res["error"]


def test_a_raw_reply_is_not_a_source(tmp_path):
    """A raw reply goes through `transcribe --from-json` first, at no cost, so there is one format to read here."""
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 10)
    code, res, raw, err = run(tmp_path, audio, "--at", "1-2", "--words", str(Path(__file__).parent / "fixtures/say_ko.scribe.json"))
    assert code == 2


def test_media_without_audio_is_a_usage_error(tmp_path):
    movie = make_av(tmp_path / "m.mp4", 3, audio=False)
    code, res, raw, err = run(tmp_path, movie, "--at", "0-1")
    assert code == 2 and "audio" in res["error"]


def test_missing_media_is_a_usage_error(tmp_path):
    code, res, raw, err = run(tmp_path, tmp_path / "none.wav", "--at", "0-1")
    assert code == 2


def test_missing_ffmpeg_is_a_tool_failure(tmp_path, monkeypatch):
    audio = tone_bursts(tmp_path / "t.wav", [(1.0, 2.0)], 3)
    monkeypatch.setenv("PATH", str(tmp_path))
    code, res, raw, err = run(tmp_path, audio, "--at", "0-1")
    assert code == 1 and "ffprobe" in res["error"]


def test_help_says_how_to_read_it():
    code, _, raw, err = skill("waveform", "--help")
    assert code == 0
    for word in ("--at", "--words", "--out", "harmonics", "noise", "music", "Prints:", "Exits:", "speech", "transcribe --from-json"):
        assert word in raw, word

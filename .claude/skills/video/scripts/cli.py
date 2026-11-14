# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10", "playwright>=1.50"]
# ///
"""Tools FilmCraft lacks for editing from the shell: speech to word-timed transcripts, caption layout, pictures of sound to check them against, a compact timeline readout, frame contact sheets, delivery QC, graphics rendered from HTML pages, and pictures generated with gpt-image through Codex."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

from video import captions, doctor, frames, graphic, imagegen, openrouter, qc, timeline, transcribe, waveform
from video.errors import InputError, ToolError
from video.filmcraft import Source
from video.timecode import Rate

EXIT_OK, EXIT_TOOL, EXIT_USAGE, EXIT_QC_FAIL = 0, 1, 2, 3

ROOT_EPILOG = """\
Every command prints one JSON document on stdout; progress and diagnostics go to stderr.
Exit codes: 0 success; 1 an external tool (filmcraft-cli, ffmpeg, mlx-whisper, OpenRouter, Chrome, Codex) failed or is missing, and the JSON carries `error` and `stderr_tail`; 2 the command line must change, and the JSON carries `error` and the `help` to read; 3 only from `qc`, when a required check failed.
Commands that read a project take exactly one of --project P.fcproj (headless, the file on disk) or --bridge 127.0.0.1:PORT (the running app, including unsaved edits)."""

TIMELINE_DESC = """\
Read a sequence once and report it twice: a summary small enough to print for any clip count, and a detail file with every clip.
Prints: {"summary": {name, fps, size, duration_tc, tracks: [{name, clips, locked, muted}], clips, captions, markers, transitions}, "detail": "<--out path>"}. Tracks are named V1…, A1…, C1… as commands address them.
Detail file: {"sequence": {id, name, fps, drop_frame, size, duration_tc, duration_frames, in_tc, out_tc}, "clips": [{clip, item, name, track, start_tc, end_tc, src_in_s, src_out_s, speed, reverse, gain_db, effects, enabled, scale?, position?, opacity?}], "transitions": [{track, effect, start_tc, end_tc, from, to}], "markers": [{name, kind, start_tc, duration_frames, comment}], "captions": [{track, name, enabled, cues, font, size, anchor, margin, first_tc, last_end_tc}]}.
Timecodes count from 00:00:00:00 at the sequence's rate (drop-frame when the sequence uses it), ignoring any start timecode. end_tc is exclusive: the first frame after the clip. src_in_s/src_out_s are seconds of the source media. effects lists only effects applied on top of the built-in Motion/Opacity/Time Remapping/Volume/Channel Volume/Panner; scale, position and opacity appear only when changed from their defaults.
Exits: 0 written; 1 filmcraft-cli failed (no such project, no active sequence, the app not listening on the port); 2 the command line must change (both or neither of --project and --bridge)."""


QC_DESC = """\
Measure a rendered file (ffprobe streams, BS.1770 loudness and true peak via ffmpeg ebur128, MP4 box layout) and judge it against one delivery target. Technical QC only: whether cuts land or meaning survived is not judged.
Prints: {"file", "target", "pass", "failed": [check names], "warnings": [check names], "checks": [{name, value, expected, tolerance, level, pass, reason}]}. `pass` per check is true, false, or null when the value could not be measured (then `reason` says why).
Exits: 0 nothing required failed (warnings allowed); 3 a required check failed, named in `failed`; 2 the file is missing or not media, or the command line must change; 1 ffmpeg/ffprobe is missing or failed.
When a loudness fix is needed, re-export with the target: file.exportMedia loudnessLufs, whose -2 dBTP limiter ceiling leaves room for the true peak AAC adds (about 1 dB), or settings.effects.loudness {"enabled": true, "target_lufs", "true_peak_dbtp"} to move that ceiling (without enabled nothing is normalised, and a -1 ceiling can measure above -1 dBTP once encoded). The limiter wins over the integrated target, so a file that still misses after two re-exports is reported with its measurements instead of exported again.

"""


FRAMES_DESC = """\
Look at an edit without playing it: frames laid out as one contact sheet, each labelled with its timecode.
--project renders through FilmCraft (headless), so captions, titles and effects show as exported (captions are drawn even when an export would not burn them). --media extracts from a file with ffmpeg, for scanning source material.
To check what the running app shows, unsaved edits included: send `file.saveCopy {"path": "/abs/copy.fcproj"}` over --bridge (it leaves the app's own path and dirty state alone), then run frames --project on that copy. One frame from the app itself: the MCP tool render_frame.
Prints: {"sheet": "<--out path>", "frames": [{"t": seconds, "tc": "HH:MM:SS:FF"}], "size": "WxH of one tile", "grid": {cols, rows, tile_w, tile_h, cell_h}, "notes": [...]}. Read the sheet image to see the frames.
Exits: 0 written; 2 the command line must change (--cuts without --project, more than 100 frames, a time that cannot be read, a file that is not video); 1 filmcraft-cli or ffmpeg failed (offline media in the project, no active sequence).

"""


TRANSCRIBE_DESC = f"""\
Speech to a word-timed FilmCraft transcript, because this FilmCraft build cannot transcribe: transcript.generate is disabled, and transcript.downloadModel still downloads a model of about 290 MB that it cannot use. The words come from one of two engines (default openrouter, which sends the audio out and costs money; choose --engine local when it must not).
--engine local: Whisper on this machine ({transcribe.WHISPER_MODEL}). Nothing leaves it and it is free, but it is the slower engine and downloads a large model on first use (`doctor` says whether it is cached). Its word starts run early, often half a second in the middle of speech, and snapping only corrects edges next to real silence: a caption can rise before the voice, and a cut on a word boundary can clip the word.
--engine openrouter: sends the whole audio track of MEDIA to OpenRouter and the model's provider (only zero-retention routes unless --no-zdr, which lets them keep the audio) and costs money, known only afterwards from cost_usd (listed prices use different units across models). Word edges sit on the voice, --diarize labels speakers, fillers are kept, and the low_prob list is short and holds the misheard names. The key is read from OPENROUTER_API_KEY when that is set, otherwise from {openrouter.KEY_FILE}.
That comparison comes from one English documentary and has not been tested on Korean speech: on other material treat it as a prediction until `waveform` shows it.
--model: for openrouter, any model at https://openrouter.ai/api/v1/models?output_modalities=transcription (default {transcribe.OPENROUTER_MODEL}). Word timing belongs to the route, not the model's reputation: models that rank well on recognition have returned truncated word lists and drifting times here. A truncated reply is refused and says what to try; passing that does not prove the times.
--from-json: an earlier run's raw reply instead of a new recognition, with no cost. Which engine it came from shows in its shape.
Word edges: --snap auto moves them onto speech measured from the audio level for Whisper and leaves them for OpenRouter, whose edges are already on the voice and whose word ends would be cut short. With snapping, an edge put in silence moves inward to the speech edge, however far, staying inside the word; the first word of a stretch of speech may start earlier, and the last may end later, by at most --max-shift. Under continuous music the level never drops, so only the outer edges of that passage can move. Every word is then kept in order and at least a frame long, which can nudge a very short one.
Long files: a file too big for one request is cut at silences and sent in pieces at once, as is any file longer than --chunk; the replies are merged. A failed run keeps nothing and is run again from the start; pieces that finished have been charged.
For --out X.jsonl, writes X.jsonl as one `transcript.set` line (media-time ticks, confidence and speaker when the engine gives them), X.txt (one line per sentence or pause: [w<first>-w<last>] start-end text, with speakers and [sound] lines for sounds the engine named), and the raw reply as X.whisper.json or X.openrouter.json, reusable with --from-json, which writes no copy of it. An --out or raw reply that already exists is left alone: the command stops, so corrected words and a paid reply cannot be replaced by accident.
Before applying: correct misrecognised words (names, terms) by editing the text fields of --out in place, keeping start/end, and delete repeat or no_speech lines over music, which shifts the indices in X.txt and review: after applying, take word indices from transcript.inspect. Then apply with the `next` command; the transcript attaches to the media item, so every clip of it in every sequence gets it. Without --item the line reads as item null, which FilmCraft refuses and `captions --transcript` and `waveform --words` accept: before applying, fill in params.item in --out by hand rather than transcribing again, which would lose the corrections.
Prints: {{"engine", "model" (null when --from-json does not say), "item", "language", "words", "seconds", "speech_seconds", "cost_usd" (what OpenRouter charged this run, null if it did not say; 0 for local and --from-json), "speakers", "audio_events", "snapped" (words with an edge moved), "unmatched" (words over no speech), "has_confidence", "review": [{{"i", "text", "start_s", "reason"}}] (at most {transcribe.REVIEW_SHOWN}; the rest in review_file), "review_total", "review_file", "out", "text", "raw", "next", "notes"}}.
Review reasons: low_prob (the engine's word probability below {transcribe.LOW_PROB}, when it gives one); unmatched (no speech measured under the word); repeat (the same line in three or more consecutive lines, the usual hallucination over music or silence); no_speech (a segment Whisper's own no-speech test rejects; Whisper only); compressed (the first word of a stretch with more than {transcribe.COMPRESSED_RATE:.0f} words a second over {transcribe.COMPRESSED_WINDOW:.0f} s, which is faster than speech: the times there are wrong; passing does not prove them). Listen-free check: a repeat or no_speech line over background music is almost always invented.
Exits: 0 written; 2 the media is missing or has no audio, a --from-json that is neither engine's, an --out or raw reply that already exists, an argument the provider refused (its message says which), or the command line must change; 1 ffmpeg, uvx or mlx-whisper failed, no API key, no credit, retries ran out, or a reply whose times are broken, in which case no transcript is written.

"""


CAPTIONS_DESC = f"""\
Captions laid out to the subtitle rules below, Korean or English, and to the width FilmCraft will burn them at, written as SubRip for captions.import.
Sources: --project or --bridge reads the active sequence's transcript, whose words are already in sequence time (trims, speed changes, ripple deletes and reused clips included); --transcript reads a transcribe line with no project, for captions on the source media as it is, in media time, with `next` giving only the file; --cues reads cues written elsewhere, such as a translation you wrote as SubRip: a cue whose line count, line lengths and width meet the rules and whose time is within --max keeps its lines, with only end punctuation cleaned, and any other is laid out again; a kept cue too short or too fast shows in `violations`. Either way a cue stays inside its own time, on whole frames (a source cue shorter than a frame still gets one, reported as short), so showing a translated cue on into the silence after it is done by its times in the SubRip.
Width: FilmCraft draws captions in the track's font at SemiBold, at size x frame height / 1080 pixels (so size 54 is 96 px in a 1080x1920 frame), and wraps any line wider than 0.9 x frame width at its spaces. This command measures each line in that face (Pillow) and wraps earlier when needed, so a cue it writes stays within its lines. That holds only if the track gets the same style: captions.import makes a new track in the default style (Inter, which has no Hangul, at 54), so always follow it with the captions.setStyle in `next`. Defaults: font {captions.DEFAULT_FONT}; landscape size 54, margin 0.08; vertical size 40, margin 0.40 (two lines clear the bottom UI and the Reels corner of every platform in frames --help).
Prints: {{"cues", "style": {{font, size, margin, anchor}}, "max_line_units" (what fits a line at this size), "width": {{source: font|estimate, face, px, max_line_px}}, "violations": [{{cue, kind: cps|short|long_line, value, text}}], "out", "notes", "next": [the import command, the setStyle command]}}.
A cps violation cannot be fixed by timing when the next cue follows at once: shorten that cue's text (in --cues mode, rewrite the translation more tightly and run again). After importing, check that the import result's `warnings` is empty.
Exits: 0 written (violations do not fail); 2 no transcript in the active sequence, an unreadable or empty --cues or --transcript file, or the command line must change; 1 filmcraft-cli failed.

"""


GRAPHIC_DESC = """\
Render a local HTML page to a graphic FilmCraft composites over the edit: a transparent ProRes 4444 MOV (straight alpha, tagged BT.709, the sequence's exact frame rate, the page's sound as 48 kHz PCM), or one transparent PNG still.
Frame size and rate come from the sequence (--project, or --bridge for the running app; --sequence for one that is not active), or from --size and --fps when there is no sequence yet (a motion graphic on its own).

The page
- Viewport: the frame size in CSS pixels at device scale 1. Leave html and body without a background: what is not painted stays transparent.
- Time: frame i is captured at page time t = i / fps. Before each frame, window.seek(t) is called if the page defines it (and awaited if it returns a Promise); then every animation the page had when it finished loading (CSS @keyframes, Web Animations) is set to t, counting from the moment the page opened (delays included); then two animation frames pass and the frame is captured. Animations are frozen otherwise: nothing runs on the clock while rendering. Animations created later, for instance inside seek, are seek's to set.
- Frames are captured in any order and each must depend on t alone: not on the wall clock (Date.now, performance.now, requestAnimationFrame timestamps), unseeded randomness, or earlier frames. CSS transitions run on the wall clock and are refused (exit 1): use @keyframes or seek.
- Length (.mov): --duration S, or window.duration in seconds, set by the time the page has loaded. Frames = length x fps rounded to the nearest frame (half up), at least 1; the movie lasts frames / fps (3 s at 30000/1001 is 90 frames, 3.003 s).
- Sound (.mov): define window.renderAudio(sampleRate, seconds) returning an AudioBuffer, or a Promise of one (an OfflineAudioContext's startRendering()). It is called once, before any frame, with 48000 and the movie's length, and the buffer must be at that rate; its time 0 is the first frame. A longer buffer is cut and a shorter one padded with silence. It must not change what the page draws. Return null for no sound.
- Loading: file: and data: URLs only; paths relative to the page work. Network requests and WebSockets are blocked and listed in `blocked`, so a re-render months later draws the same frames: keep fonts and images next to the page. The first frame waits for the page's load event, its fonts and every <img>.
- Waits: loading 30 s; fonts, then images, 15 s each; each seek with the settle after it 10 s, even when the page's code never returns; renderAudio 60 s. Past that the render fails, naming the stage.
- Colour: the page is sRGB. In an HDR sequence (HLG, PQ) FilmCraft converts the render like any SDR clip, SDR white at the HDR reference level, so a page is written the same way for any sequence.

Replacing a render
--out is written beside itself and verified first; an earlier file at --out stays byte for byte until then, and on any failure. FilmCraft keeps the length and sound it read when a file was imported, so a clip placed from the earlier file plays a re-render of the same length, sound, size and rate as is; `replaced` and `next` say when it must be cleared and placed again.

Prints: {"out", "kind": "video"|"still", "size": "WxH", "fps" (.mov), "frames", "seconds" (.mov), "coverage": [{"t", "painted", "opaque"}] (first, middle and last frame; painted = share of the frame with any paint, opaque = with alpha >= 250, which is what hides the picture), "audio": {"peak_dbfs", "lufs"} or null (no sound; levels are null for silence, and a peak above 0 means the page's sound clipped), "fonts": [{"family", "drawn_by": [{"face", "glyphs"}], "fallback", "text" (when fallback)}] (visible DOM text, sampled at the start, each whole second and the end; text drawn on a canvas, generated by CSS content or inside a shadow root is not seen, so check those in the frames; fallback = the family is missing or lacks some glyphs and another face drew them; a generic family such as sans-serif is never flagged), "blocked": [urls], "replaced": null (no earlier file) or {"length_changed", "audio_changed", "size_changed", "fps_changed"}, "took_s", "next": {"steps": [filmcraft-cli commands that import and place the render, with <placeholders>], "placeholders", "if_placed" (when replacing), "note"}}.
Placing: the steps put the render on a new video track and its sound on a new audio track, leaving A1's speech alone.

Exits: 0 written; 2 the command line must change (a .mov without a length, a length that is not a positive finite number, --out not .mov or .png, --out the page itself, no page, --fps written as a decimal, --size without --fps, --sequence with --size, an --out folder that cannot be made); 1 the render failed and `error` starts with the stage: launch (Chrome or Playwright missing; the error says how to install, which is the user's to approve), load, files (a local file the page asked for is missing), fonts, images (one cannot be decoded), page (an uncaught error or unhandled rejection), seek (seek or the settle after it failed or timed out, or a CSS transition started), audio, capture, encode (ffmpeg), verify (the written movie differs from what was asked for), write (the file could not be put in place); or filmcraft-cli failed reading the sequence.
"""


DOCTOR_DESC = """\
Check this machine before the first command. It takes no arguments, installs nothing, uses no network and writes nothing.
Prints: {"ok" (every required check passed), "checks": [{"name", "ok", "required", "value", "why", "next" (only effectcraft_cli, when the CLI is missing beside the app or does not match it: the command that installs the app's version)}], "next": [commands that fix what is required, with versions filled in; with neither the FilmCraft CLI nor its app none can be named for them, and the filmcraft_cli `why` says where they come from]}.
Checks: filmcraft_cli (required; installed and the same version as the app; passes with no app, since headless work needs none), ffmpeg, ffprobe and uvx (each required; installed), whisper_model (optional; the default local model is cached, value cached or not cached), openrouter_key (optional; value env, file or none, where the key would come from; the key itself is never printed), chrome (optional; needed by graphic), codex (optional; needed only by imagegen; value installed or not installed: whether it is logged in is left to imagegen, because running any codex command writes into the user's Codex folder), effectcraft_cli (optional; needed only for EffectCraft compositions; installed and the same version as the EffectCraft app, passing with no app; the CLI is a separate release asset, so the check carries the command that installs it). An optional item matters only when the task needs it, and never fails the check.
Exits: 0 every required check passed; 1 a required check failed; 2 the command line must change.
"""


WAVEFORM_DESC = f"""\
Look at sound you cannot hear: each --at window drawn as a waveform above a 0 to 8 kHz spectrogram with a grid at each second, and each --words file as a row of labelled boxes on the same time axis. A column means a time, so a box and the sound under it can be compared directly.
Reading it: voiced sound shows as stacked harmonics; unvoiced sound such as s or f shows as noise high in the band. A word's box should start at that word's first energy. Over music or a crowd, a box and energy lining up does not prove a voice: the energy may not be the voice.
Sources: --words takes transcript.set lines (from transcribe, with or without an item) and SubRip files, and reads their times as seconds of MEDIA: a source file takes media-time transcripts, an exported file takes sequence-time captions. To see an engine's own times from a raw reply, make a line first with transcribe MEDIA --from-json RAW.json --snap off --out X.jsonl, which costs nothing.
Prints: {{"sheet", "width", "windows": [{{"start", "end", "y": {{"wave", "spectrum", "rows"}} ([top, bottom) in sheet pixels), "speech": [[start, end]] (the same speech measurement transcribe uses, in seconds, so you can often decide before opening the picture; empty for a window with no speech, or when the whole file's level is too flat to measure; a span over music proves nothing), "rows": [{{"source", "items": [{{"text", "start", "end"}}]}}]}}], "notes"}}. Read the sheet image to see it.
Exits: 0 written; 2 no window, more than {waveform.MAX_WINDOWS} windows, a window under {waveform.MIN_WINDOW_SECONDS} s, over {waveform.MAX_WINDOW_SECONDS} s or outside the media, more than {waveform.MAX_SOURCES} --words files, one that cannot be read, or media with no audio; 1 ffmpeg is missing or failed.
"""


IMAGEGEN_DESC = f"""\
Make gpt-image pictures through the user's Codex CLI and its ChatGPT login: one `codex exec` per picture, asking Codex's built-in image_gen tool. The prompt and every --ref image go to OpenAI, and each picture draws on the same Codex usage limits as the user's other Codex work. Codex also keeps its own copy of every picture ($CODEX_HOME/generated_images) and a session record of every call, outside DIR; they are left there.

The folder
DIR holds the pictures, its ledger imagegen.json and its contact sheet contact-sheet.html (with .sheet-stamp.js and lock files beside them). A picture is DIR/NAME-k.png, where k counts every try under NAME in this folder, failed ones and other requests included, so no run overwrites or changes a picture already there. The ledger and the sheet are rewritten by every run. The sheet shows every try at full size with what was said about it (imagenote); unless --no-open, the first run that can open it opens it in the browser, and an open tab refreshes itself. A DIR whose imagegen.json is not this ledger, or that holds a contact-sheet.html without one, is refused before anything is written.

Requests
A prompt on stdin makes a new request under NAME (the prompt, its --ref images, --transparent, --label) and --n tries of it. --again IMAGE makes more tries of the request that made IMAGE and reads no stdin: the prompt comes byte for byte from the ledger, and every reference must still be the file it was (same path, same sha256), or nothing is generated.

What image_gen cannot do, whatever the prompt says
- Pixel size: the model sets it, about 1.6 megapixels in every shape. Measured: 16:9 1672x941, 9:16 941x1672, 1:1 1254x1254, 4:5 1122x1402, 3:1 2172x724 (another model can differ; `w` and `h` say what came).
- Quality, seed, mask: none. A request with a --ref picture redraws the whole picture; it is not inpainting, and parts meant to stay can change.

Time
One picture usually takes 30 s to a minute (a refusal, seconds). At most {imagegen.CONCURRENCY} run at once within one command, so --n {imagegen.CONCURRENCY} takes about as long as one. --timeout bounds each try, its one retry included. Give the Bash call a timeout above --timeout, or run it in the background. Stopping the command (SIGTERM, SIGINT) ends its Codex calls and closes their tries as interrupted. A killed command (SIGKILL) cannot: its Codex calls run on to their end, using the allowance, and its tries are closed as interrupted by the next command that reads the ledger.

How the model reads a prompt: tendencies observed on this path, not laws; when a result disagrees, trust the result.
- Write the prompt as English prose. Codex passes it to image_gen word for word (see verbatim).
- State the aspect ratio in the first sentence ("Portrait 9:16 aspect ratio, taller than it is wide."); the shape is set only by the prompt, and left unsaid the model picks one.
- Whatever is named first takes more of the frame and the first look, so name the subject first.
- Listing several media keeps only some of them; to mix, name one medium and give it another's quality ("an oil painting with the flatness of a screenprint").
- Anything not supplied gets invented (names, dates, numbers, signs, slogans), differently in every picture: give every string the picture must show, Korean included, inside double quotes exactly as it must read, and close with "no other text"; a surface that must carry no text has to be called blank.
- Asked for unreadable marks, it writes readable-looking fake Hangul. Short Hangul strings come out mostly right; lettering whose strokes turn into objects breaks the letters.
- A flat ground given as a hex colour comes out close to it; colour names and comparisons drift further.
- A shape with one right answer (a flag, a symbol) comes out right when its structure is described, not its name and count.
- For material that goes over footage or into a scene (a prop, an icon, a texture, a background), say the scene's light direction and colour, and ask for --transparent or a flat ground that separates cleanly.
- Moderation can refuse the prompt (stage input: change the prompt, since the same words are refused again) or the picture made from it (stage output: rewording does not help, another try can). The same prompt can pass on one try and not another.

Prints: {{"summary": "3 requested · 2 ok · 1 refused", "name", "request" (its number under NAME, from 1), "results": [{{"image" (NAME-k), "file"? (absolute), "status", "w"?, "h"?, "alpha"?, "verbatim"?, "error"?}}], "sheet", "ledger"}}. Exit 0 needs only one picture ok, so read `summary` and each `status`.
stderr: one line per try as it ends: its status, size and seconds, or why it failed and what to do next.

status
  running         opened and not yet closed (waiting in the queue included)
  ok              the picture is in DIR and can be chosen
  prompt_altered  Codex changed the prompt even after one retry; the picture is in DIR and on the sheet, and cannot be chosen
  refused         moderation blocked it; detail.stage is input (the prompt), output (the picture made) or unknown
  no_image        Codex finished without a picture; detail.message holds Codex's reason verbatim when it gave one
  executor_error  Codex itself failed (could not start, exited non-zero, gave no final message), the try failed here (detail.message), or DIR/NAME-k.png already existed outside the ledger (left alone)
  timeout         no answer within --timeout; the Codex process group was ended
  interrupted     the command was stopped or died; a picture placed just before that has `file`, but where it came from was not checked, and it cannot be chosen
verbatim compares the prompt image_gen received, as Codex's own session record shows it, with the one written: exact; normalized (whitespace only); mismatch (Codex changed it: one more try with a stronger instruction, and if still changed, prompt_altered); unverified (no record could be read, so nothing shows what was sent; Codex's own report cannot make it exact).
alpha (--transparent only): {{"has_alpha", "transparent_share"}}: whether the PNG has an alpha channel, and the share of fully transparent pixels.

The ledger, imagegen.json: read it directly; write judgments with imagenote.
{{"schema": 1, "created", "sheet_opened"?, "names": [{{"name", "notes": [{{"text", "at"}}], "requests": [{{"r", "created", "prompt", "refs": [{{"path" (relative to DIR), "sha256"}}], "transparent", "label"?, "attempts": [{{"id", "status", "started", "pid"? (while running: the command's), "elapsed_s"?, "file"? (relative to DIR), "w"?, "h"?, "alpha"?, "verbatim"?, "retried"? {{"thread_id", "elapsed_s", "verbatim"}}, "thread_id"?, "detail"? {{"stage", "code", "message", "categories", "generations" (more than one picture in the call; the last was taken), "returncode", "agent_message", "log" (Codex's session record of the try), "observed", "refs_sent" (the references Codex received, when their hashes differ from refs), "note"}}, "chosen"?, "critique"?, "notes"?}}]}}]}}]}}

Exits: 0 at least one picture ok; 1 codex is missing or not logged in (nothing is attempted; `codex login` needs the user's browser), or no try came out ok (`error`); 2 the command line must change: no prompt on stdin, a NAME or DIR refused as above, --again with --ref, --transparent or --label, a --ref missing, a reference of --again missing or changed, or an IMAGE not in the ledger.
"""


IMAGENOTE_DESC = """\
Write a judgment of pictures imagegen made into DIR's ledger and redraw the contact sheet: which picture the user chose, what they said in their own words, and Claude's assessment. The ledger is written only under its lock, which a running imagegen also takes, and the sheet follows each write, so judgments go through this command rather than by editing imagegen.json.
TARGET is a picture id (mic-2) or a name (mic). --choose, --unchoose and --critique take a picture; --note takes either.
--choose marks the picture chosen (several under one name are allowed; only an ok picture). --unchoose clears the mark. Both succeed when the picture is already so.
--note appends, never replaces: the user's words as they said them, or a fact that must be kept.
--critique replaces Claude's current assessment of the picture.
On the sheet: a chosen picture is outlined and tagged 선택; its assessment and notes show under it, and a name's notes at the top of its section.
Prints: {"written": [what changed, in words], "sheet", "ledger"}.
Exits: 0 written (or already so); 2 nothing to write, no ledger in DIR, a TARGET not in it, --choose on a picture that is not ok, or --choose, --unchoose or --critique on a name.
"""


def size_arg(text: str) -> tuple[int, int]:
    try:
        w, h = text.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected WxH like 1080x1920, got {text!r}")


def rate_arg(text: str) -> Rate:
    """An exact frame rate: an integer (30) or a fraction (30000/1001). A decimal such as 29.97 is refused because it is not the NTSC rate 30000/1001."""
    m = re.fullmatch(r"(\d+)(?:/(\d+))?", text)
    if not m or int(m[1]) == 0 or int(m[2] or 1) == 0:
        raise argparse.ArgumentTypeError(f"expected an integer or an exact fraction such as 30000/1001, got {text!r} (a decimal is not an exact NTSC rate)")
    return Rate(int(m[1]), int(m[2] or 1))


def non_negative(text: str) -> float:
    try:
        v = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a number, got {text!r}")
    if not (v >= 0 and math.isfinite(v)):
        raise argparse.ArgumentTypeError(f"must be a finite number of at least 0, got {text}")
    return v


def positive(text: str) -> float:
    try:
        v = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a number, got {text!r}")
    if not (v > 0 and math.isfinite(v)):
        raise argparse.ArgumentTypeError(f"must be a finite number greater than 0, got {text}")
    return v


class Parser(argparse.ArgumentParser):
    """Usage errors print JSON on stdout like every other reply, naming the --help to read."""

    def error(self, message):
        print(json.dumps({"error": message, "help": f"{self.prog} --help"}, ensure_ascii=False))
        sys.exit(EXIT_USAGE)


def add_source(p: argparse.ArgumentParser) -> None:
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--project", type=Path, metavar="P.fcproj", help="read this project file headless (what is saved on disk)")
    g.add_argument("--bridge", metavar="127.0.0.1:PORT", help="read the running app started with --control PORT (includes unsaved edits)")


def source_of(a) -> Source:
    return Source(project=a.project.resolve()) if a.project is not None else Source(bridge=a.bridge)


def build_parser() -> argparse.ArgumentParser:
    fmt = argparse.RawTextHelpFormatter
    root = Parser(prog="cli.py", description=__doc__, epilog=ROOT_EPILOG, formatter_class=fmt)
    sub = root.add_subparsers(dest="command", required=True, metavar="<command>", parser_class=Parser)

    p = sub.add_parser("timeline", help="summary of a sequence on stdout, every clip in a detail file", description=TIMELINE_DESC, formatter_class=fmt)
    add_source(p)
    p.add_argument("--sequence", type=int, metavar="ITEM", help="the sequence's project item id (default: the active sequence). Naming one makes it active, which in the app brings its timeline tab to the front")
    p.add_argument("--out", type=Path, required=True, metavar="DETAIL.json", help="where to write the detail document (parent folders are created)")
    p.set_defaults(run=lambda a: timeline.report(source_of(a), a.out.resolve(), a.sequence))

    p = sub.add_parser("qc", help="technical delivery checks of a rendered file against a target", description=QC_DESC + qc.HELP_TABLE, formatter_class=fmt)
    p.add_argument("file", type=Path, metavar="FILE", help="the rendered file (MP4 expected)")
    p.add_argument("--target", required=True, choices=list(qc.TARGETS), help="which delivery the file is for")
    p.add_argument("--expect-size", type=size_arg, metavar="WxH", help="required frame size, e.g. 1920x1080 (display size, after rotation metadata)")
    p.add_argument("--expect-fps", type=float, metavar="F", help="required frame rate, e.g. 29.97 (within 0.01)")
    p.add_argument("--expect-duration", type=float, metavar="S", help="required duration in seconds, within one frame")
    p.add_argument("--lufs", type=float, metavar="L", help="the user's own integrated loudness target, replacing the target's default (same bands)")
    p.set_defaults(run=run_qc)

    p = sub.add_parser("frames", help="contact sheet of rendered or extracted frames, optionally with safe zones", description=FRAMES_DESC + frames.HELP_TABLE, formatter_class=fmt)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--project", type=Path, metavar="P.fcproj", help="render the project's active sequence through FilmCraft (headless)")
    src.add_argument("--media", type=Path, metavar="FILE", help="extract frames from a media file with ffmpeg")
    pick = p.add_mutually_exclusive_group(required=True)
    pick.add_argument("--at", nargs="+", metavar="T", help="times: seconds (12.5) or timecode (00:00:12:15) at the sequence's or file's rate")
    pick.add_argument("--cuts", action="store_true", help="the first frame of every video clip (needs --project)")
    pick.add_argument("--every", type=float, metavar="SEC", help="one frame every SEC seconds from the start")
    p.add_argument("--overlay", choices=[*frames.SAFE_ZONES, "all"], help="draw a vertical platform's UI areas and safe box (9:16 frames only)")
    p.add_argument("--cols", type=int, default=4, metavar="N", help="tiles per row (default 4)")
    p.add_argument("--width", type=int, metavar="PX", help="width of one tile (default 480 landscape, 320 vertical)")
    p.add_argument("--out", type=Path, required=True, metavar="SHEET.png", help="where to write the sheet")
    p.set_defaults(run=lambda a: frames.sheet(a.out.resolve(), project=a.project.resolve() if a.project else None, media=a.media.resolve() if a.media else None,
                                              at=a.at, every=a.every, cuts=a.cuts, overlay=a.overlay, cols=a.cols, width=a.width))

    p = sub.add_parser("captions", help="caption layout to Korean or English subtitle rules and the burn-in width, as SubRip", description=CAPTIONS_DESC + captions.HELP, formatter_class=fmt)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--project", type=Path, metavar="P.fcproj", help="read the active sequence's transcript headless")
    src.add_argument("--bridge", metavar="127.0.0.1:PORT", help="read it from the running app (unsaved edits included)")
    src.add_argument("--transcript", type=Path, metavar="X.jsonl", help="read a transcribe line with no project (its item may be empty); times are media times")
    src.add_argument("--cues", type=Path, metavar="IN.srt", help="cues written elsewhere (a translation, or captions from elsewhere): those that fit keep their lines, the rest are laid out again")
    p.add_argument("--out", type=Path, required=True, metavar="X.srt", help="where to write the SubRip file")
    p.add_argument("--font", metavar="FAMILY", help=f"caption font family, installed (fonts.list); default {captions.DEFAULT_FONT}")
    p.add_argument("--size", type=float, metavar="N", help="captions.setStyle size, relative to a 1080-line frame (default 54 landscape, 40 vertical)")
    p.add_argument("--margin", type=float, metavar="M", help="captions.setStyle margin, fraction of frame height from the anchored edge (default 0.08 landscape, 0.40 vertical)")
    p.add_argument("--anchor", choices=["bottom", "top"], default="bottom", help="captions.setStyle anchor (default bottom); top when burned-in text already occupies the bottom")
    p.add_argument("--rules", choices=list(captions.RULE_PROFILES), default="ko", help="which subtitle rules to lay out to, below (default ko)")
    p.add_argument("--lines", type=int, choices=[1, 2], help="lines a cue may have (default from --rules: 2)")
    p.add_argument("--units", type=positive, metavar="N", help="units a line may hold, counted as below (default from --rules: ko 16, en 21); a line must still fit the burn-in width")
    p.add_argument("--cps", type=positive, metavar="N", help="reading speed limit in characters a second (default from --rules: ko 12, en 20)")
    p.add_argument("--min", dest="min_s", type=positive, metavar="SEC", help="shortest cue (default from --rules: 5/6 s)")
    p.add_argument("--max", dest="max_s", type=positive, metavar="SEC", help="longest cue (default from --rules: 7 s)")
    p.add_argument("--fps", type=positive, metavar="F", help="--cues and --transcript: the sequence's frame rate, so cue times land on frames (default 30)")
    p.add_argument("--frame", type=size_arg, metavar="WxH", help="--cues and --transcript: the sequence's frame size, for the width check (default 1920x1080)")
    p.set_defaults(run=lambda a: captions.make(a.out.resolve(), project=a.project.resolve() if a.project else None, bridge=a.bridge, cues_file=a.cues.resolve() if a.cues else None, transcript=a.transcript.resolve() if a.transcript else None,
                                               fps=a.fps, frame=a.frame, font=a.font, size=a.size, margin=a.margin, anchor=a.anchor, profile=a.rules, lines=a.lines, units_per_line=a.units, cps=a.cps, min_s=a.min_s, max_s=a.max_s))

    p = sub.add_parser("transcribe", help="speech to a word-timed transcript.set line, from Whisper here or a model through OpenRouter", description=TRANSCRIBE_DESC, formatter_class=fmt)
    p.add_argument("media", type=Path, metavar="MEDIA", help="the media file the project item points at")
    p.add_argument("--out", type=Path, required=True, metavar="X.jsonl", help="where to write the transcript.set line (siblings .txt and the raw reply go next to it); must not exist yet")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--engine", choices=["local", "openrouter"], help="where the words come from (default openrouter); see above")
    src.add_argument("--from-json", type=Path, metavar="RAW.json", help="reuse a raw reply from an earlier run instead of recognising again")
    p.add_argument("--item", type=int, metavar="ID", help="its project item id (inspect project lists them). Without it, fill in params.item before applying")
    p.add_argument("--language", metavar="CODE", help="spoken language, e.g. ko or en (default: the engine detects it)")
    p.add_argument("--model", metavar="NAME", help=f"local: an mlx-whisper model (default {transcribe.WHISPER_MODEL}); openrouter: a transcription model (default {transcribe.OPENROUTER_MODEL})")
    p.add_argument("--diarize", action="store_true", help="openrouter: label speakers, where the model supports it (a model that does not refuses the request)")
    p.add_argument("--no-zdr", dest="zdr", action="store_false", help="openrouter: allow routes that keep data (by default only zero-retention routes are used)")
    p.add_argument("--chunk", type=positive, metavar="S", help="openrouter: cut the audio at silences into pieces of at most S seconds, 1 or more; the last may run a second over")
    p.add_argument("--snap", dest="snap_mode", choices=["auto", "on", "off"], default="auto", help="move word edges onto measured speech: auto does for local and not for openrouter (default auto)")
    p.add_argument("--max-shift", type=float, default=0.5, metavar="SEC", help="how far an outer edge of a stretch of speech may move outward when snapping (default 0.5)")
    p.set_defaults(run=run_transcribe)

    p = sub.add_parser("waveform", help="stretches of audio drawn as waveform and spectrogram, with word boxes on the same time axis", description=WAVEFORM_DESC, formatter_class=fmt)
    p.add_argument("media", type=Path, metavar="MEDIA", help="the media file to draw")
    p.add_argument("--at", nargs="+", required=True, metavar="A-B", help="windows, in seconds (137.5-140) or timecode at the media's rate (00:02:17:15-00:02:20:00)")
    p.add_argument("--words", nargs="+", type=Path, default=[], metavar="FILE", help="transcript.set lines or SubRip files to draw as rows, labelled with the file's name")
    p.add_argument("--out", type=Path, required=True, metavar="SHEET.png", help="where to write the sheet")
    p.set_defaults(run=lambda a: waveform.sheet(a.media.resolve(), a.at, [f.resolve() for f in a.words], a.out.resolve()))

    p = sub.add_parser("doctor", help="what must be fixed before the first command, and the commands that fix it", description=DOCTOR_DESC, formatter_class=fmt)
    p.set_defaults(run=run_doctor)

    p = sub.add_parser("graphic", help="a local HTML page rendered to a transparent MOV (with its sound) or PNG still for FilmCraft", description=GRAPHIC_DESC, formatter_class=fmt)
    p.add_argument("page", type=Path, metavar="PAGE.html", help="the page to render, a local HTML file")
    p.add_argument("--out", type=Path, required=True, metavar="X.mov|X.png", help="what to write, chosen by extension: .mov a transparent ProRes 4444 movie, .png one transparent still. An existing file is replaced only after the new one is written and verified")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--project", type=Path, metavar="P.fcproj", help="take the frame size and rate from this project's sequence (headless)")
    src.add_argument("--bridge", metavar="127.0.0.1:PORT", help="take them from the running app's sequence")
    src.add_argument("--size", type=size_arg, metavar="WxH", help="no sequence yet (a motion graphic on its own): the frame size, with --fps")
    p.add_argument("--fps", type=rate_arg, metavar="F", help="with --size: the frame rate, an integer (30) or an exact fraction (30000/1001, 24000/1001, 60000/1001); a decimal such as 29.97 is refused")
    p.add_argument("--sequence", type=int, metavar="ITEM", help="with --project or --bridge: the sequence's project item id, when it is not the active one; `next` then opens it before placing")
    p.add_argument("--duration", type=positive, metavar="S", help=".mov: length in seconds (default: the page's window.duration)")
    p.add_argument("--frame-at", type=non_negative, default=0.0, metavar="T", help=".png: the page time to capture, in seconds (default 0); page time, not a timeline position")
    p.set_defaults(run=run_graphic)

    p = sub.add_parser("imagegen", help="pictures generated with gpt-image through the user's Codex login, every try kept in a ledger and on a contact sheet", description=IMAGEGEN_DESC, formatter_class=fmt)
    p.add_argument("name", metavar="NAME", help="what the picture is (mic, sky); its files are NAME-1.png, NAME-2.png, … Refused: empty, a path separator or control character, a leading dot, a trailing -<number>, or a name that differs only in case from one already in DIR")
    p.add_argument("--dir", type=Path, required=True, metavar="DIR", help="the folder for the pictures, the ledger and the sheet (made if missing); by this skill's convention <piece>/graphics/imagegen")
    p.add_argument("--ref", type=Path, action="append", default=[], metavar="IMG", help="a picture sent with the prompt; repeatable. The model carries over a reference's palette, lettering and layout even when told to take only its style; to change one thing in a picture given as a reference, name that change and list everything that must stay, since \"keep everything else\" alone does not hold it")
    p.add_argument("--transparent", action="store_true", help="ask for a transparent background; the result reports whether the PNG has alpha")
    p.add_argument("--label", metavar="TEXT", help="one line saying what this request tries, or what it changes from the one before; the sheet shows it instead of the folded prompt")
    p.add_argument("--again", metavar="IMAGE", help="more tries of the request that made IMAGE (NAME-k); no stdin, no --ref, --transparent or --label")
    p.add_argument("--n", type=int, default=1, choices=range(1, imagegen.CONCURRENCY + 1), metavar="K", help=f"tries of this request, 1-{imagegen.CONCURRENCY} (default 1), run at once")
    p.add_argument("--timeout", type=positive, default=imagegen.TIMEOUT_S, metavar="S", help=f"seconds one try may take, its retry included (default {imagegen.TIMEOUT_S})")
    p.add_argument("--no-open", action="store_true", help="do not open the contact sheet in the browser (a later run opens it if it never was)")
    p.set_defaults(run=run_imagegen)

    p = sub.add_parser("imagenote", help="record which generated picture the user chose, what they said, and your assessment", description=IMAGENOTE_DESC, formatter_class=fmt)
    p.add_argument("target", metavar="TARGET", help="a picture id (mic-2) or a name (mic)")
    p.add_argument("--dir", type=Path, required=True, metavar="DIR", help="the folder imagegen wrote to")
    pick = p.add_mutually_exclusive_group()
    pick.add_argument("--choose", dest="choose", action="store_const", const=True, help="mark the picture as chosen by the user")
    pick.add_argument("--unchoose", dest="choose", action="store_const", const=False, help="clear that mark")
    p.add_argument("--note", action="append", default=[], metavar="TEXT", help="append a note: the user's words as said, or a fact to keep; repeatable")
    p.add_argument("--critique", metavar="TEXT", help="your current assessment of the picture, replacing the previous one")
    p.set_defaults(run=run_imagenote)
    return root


def run_transcribe(a) -> dict:
    engine = None if a.from_json else a.engine or "openrouter"
    if engine != "openrouter":
        sends = {"--diarize": a.diarize, "--no-zdr": not a.zdr, "--chunk": a.chunk is not None}
        used = [flag for flag, on in sends.items() if on]
        if used:
            raise InputError(f"{', '.join(used)} only apply to --engine openrouter, because nothing else sends a request")
    return transcribe.transcribe(a.media.resolve(), a.out.resolve(), engine=engine, from_json=a.from_json.resolve() if a.from_json else None, item=a.item, language=a.language, model=a.model,
                                 diarize=a.diarize, zdr=a.zdr, snap_mode=a.snap_mode, max_shift=a.max_shift, chunk=a.chunk)


def run_graphic(a) -> dict:
    if (a.size is None) != (a.fps is None):
        raise InputError("--size and --fps go together (no sequence yet); with --project or --bridge both come from the sequence")
    if a.sequence is not None and a.size is not None:
        raise InputError("--sequence needs --project or --bridge")
    source = source_of(a) if a.size is None else None
    return graphic.render(a.page.resolve(), a.out.resolve(), source=source, size=a.size, rate=a.fps, sequence=a.sequence, duration=a.duration, frame_at=a.frame_at)


def run_imagegen(a) -> dict:
    folder = Path(os.path.abspath(a.dir))
    if a.again is not None:
        used = [flag for flag, on in (("--ref", a.ref), ("--transparent", a.transparent), ("--label", a.label is not None)) if on]
        if used:
            raise InputError(f"{', '.join(used)} cannot go with --again, which repeats the request as it was recorded")
        prompt = None
    else:
        if sys.stdin is None or sys.stdin.isatty():
            raise InputError("the prompt is read from stdin; pipe or heredoc it in (or use --again IMAGE)")
        prompt = sys.stdin.read().strip()
        if not prompt:
            raise InputError("the prompt on stdin is empty")
    return imagegen.generate(folder, a.name, prompt=prompt, refs=[Path(os.path.abspath(r)) for r in a.ref], transparent=a.transparent, label=a.label, again=a.again, n=a.n, timeout=a.timeout, open_sheet=not a.no_open)


def run_imagenote(a) -> dict:
    if a.choose is None and not a.note and a.critique is None:
        raise InputError("nothing to write: give --choose, --unchoose, --note or --critique")
    return imagegen.note(Path(os.path.abspath(a.dir)), a.target, choose=a.choose, notes=a.note, critique=a.critique)


def run_doctor(a) -> dict:
    out = doctor.report()
    out["_exit"] = EXIT_OK if out["ok"] else EXIT_TOOL
    return out


def run_qc(a) -> dict:
    out = qc.check(a.file.resolve(), a.target, a.expect_size, a.expect_fps, a.expect_duration, a.lufs)
    out["_exit"] = EXIT_OK if out["pass"] else EXIT_QC_FAIL
    return out


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        out = args.run(args)
    except InputError as e:
        print(json.dumps({"error": str(e), "help": f"cli.py {args.command} --help"}, ensure_ascii=False))
        return EXIT_USAGE
    except ToolError as e:
        print(json.dumps(e.as_json(), ensure_ascii=False))
        return EXIT_TOOL
    code = out.pop("_exit", EXIT_OK) if isinstance(out, dict) else EXIT_OK
    print(json.dumps(out, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())

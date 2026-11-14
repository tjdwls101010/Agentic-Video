---
name: video
description: >-
  Make and edit video with FilmCraft, the open-source Premiere-style editor, and EffectCraft, its After Effects-style compositor, both installed locally and driven through `filmcraft-cli` (headless or the running app) and `effectcraft-cli` (headless), with graphics designed in code (HTML/CSS/SVG/Canvas) or as EffectCraft compositions and rendered onto the edit: cuts and transcript-based edits, vertical Shorts/Reels/TikTok, montages, titles and motion graphics, compositing, motion tracking, mattes and rotoscoping, keying, sound effects, audio mix and loudness, color, word-timed transcripts and captions (with or without an edit), QC-checked exports, and handoff to Premiere or Resolve. Use whenever the user wants a video cut, transcribed, captioned, reframed, graded, mixed, composited, given graphics or effects, or exported, or mentions FilmCraft, EffectCraft, a .fcproj or a .ecproj. Triggers include: 영상 편집, 컷편집, 자막, 전사, 받아쓰기, 화자 구분, SRT, 쇼츠, 릴스, 몽타주, 모션 그래픽, 타이틀, 효과음, 색보정, 내보내기, 합성, 트래킹, 추적, 로토, 크로마키, VFX, .fcproj, .ecproj, FilmCraft, EffectCraft. Not for downloading or summarizing a video, still images such as thumbnails or posters, slide decks, or developing FilmCraft's or EffectCraft's own source code.
allowed-tools:
  - Bash(filmcraft-cli *)
  - Bash(effectcraft-cli *)
  - Bash(uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py" *)
  - Bash(ffprobe *)
  - Bash(ffmpeg -i * -c copy -movflags +faststart *)
---

# Making video with FilmCraft and EffectCraft

`filmcraft-cli commands <filter>` and `filmcraft-cli describe <id>` own FilmCraft's commands and parameters, and `effectcraft-cli commands --filter <text>` and `effectcraft-cli exec command.describe` EffectCraft's. This skill holds what those do not say, and tools neither app has, called as `uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py" <tool> …`; its `--help` lists them and each `<tool> --help` owns its numbers, outputs and exit codes.

## Working with the user

- You edit together with the user, usually over many turns. Taste is theirs to decide and yours to offer: cut rhythm, transitions, how much pause or filler to keep, caption and title design, graphics, the look, how music ends, shot order. When a choice collides with a platform requirement or a fact below, say so once with the consequence.
- With no idea behind the order, a montage has come out cycling through the sources in file order, which gives the user nothing to judge.
- `${CLAUDE_SKILL_DIR}/data/`, when it exists, is the user's record of earlier work, and what is there is what they chose (each piece's project, the pages and compositions in its `graphics/`, the exported video), so it is where their taste can be read. An earlier piece shows what that piece needed, not a rule for the next one. By this skill's convention a new piece goes in `data/<piece>/` unless the user names another folder, so it joins that record.
- A trim, a transition, a caption style or a title's wording changes with one call and shows in one render, so a wrong one costs the user a sentence.
- Some things cost more to undo, each for its own reason: which segments a highlight or summary keeps (what matters in it is something the user knows and the footage does not, and captions, graphics and a mix built on a rejected selection are redone), the overall look, overwriting a project you were handed (`--save` has no undo across calls), and a model download (it stays on the user's machine, in an app's data folder outside the piece). A long export or analysis costs waiting, not undoing.

## Before you hand something over

- A rendered deliverable passes `qc` for its target. Its checks mix platform requirements with conventions and this skill's own decisions, which its `--help` tells apart; passing says nothing about the piece itself, and a file that is not a deliverable for that target (a silent graphic, another size) fails checks that do not apply to it.
- A cut can end a sentence early or join words into something nobody said, and no frame shows it: the final cut's words (`transcript.inspect`), read with what comes before and after them, do, though the transcript itself can be wrong. `timeline --project` summarises the `.fcproj` as saved on disk, which can differ from the app's unsaved state.
- A page or a composition can look right in its own frame and different over the edit, and one that moves differs entering, at its fullest and leaving: when FilmCraft composites it, `frames --project` shows it there. `fallback` fonts and `blocked` requests in `graphic`'s output, and a font EffectCraft substituted, change the picture.
- What a result does not show: you cannot hear the cut, so how its audio flows is unverified, and `waveform` draws signal and timing, not how it sounds.
- What the user can open and change again is the edit as its `.fcproj`, a composition as its `.ecproj` and a graphic as its page. A change ffmpeg makes to picture or sound leaves a file but is recorded in no project, so the user cannot open it to adjust it; the lossless remux `qc` names changes no picture or sound.

## Before the first command

- `doctor` says what blocks the tools on this machine and gives the commands that fix it. A CLI whose version differs from its app gives no warning when it saves; the user meets it when the app refuses a project saved with a newer schema. An optional item, EffectCraft among them, matters only when the task needs it.
- Both apps release often, so a sentence here can describe an older version: where it and the installed CLI disagree, the CLI is right.

## Headless or the running app

- Headless calls (`filmcraft-cli --project P.fcproj --save …`) change the file on disk and show nothing on screen; the running app (bridge) shows each change to whoever is watching. Headless has no autosave: what a call did without `--save` is gone when it ends.
- A project open in an app and changed on disk is overwritten by whichever saves later, losing the other's unsaved or later changes. An `.ecproj` open in EffectCraft is the same, and `effectcraft-cli`'s lock only keeps two CLI runs apart. Working headless does not rule it out, since the user may have the project open.

## How filmcraft-cli fails quietly

- Every call is a fresh session: selection, track targeting and the Source monitor do not carry over, so a command that offers ids (`clips`, `items`) acts on nothing selected without them, and `trim.*` and `source.*` work on a selection and a Source monitor a headless call does not have. A failing line stops a `run` before anything is saved.
- Unknown keys and unknown CLI options are ignored without an error. A float in `time` (ticks are integers; `seconds` takes a float) or a misspelt key gives `cuts:0`; a misspelt `--bridge` or an unsplit `$OPTS` (zsh does not split) runs on an empty "Untitled" session and exits 0. Success and exit 0 do not mean anything changed; the signs are `cuts:0`, an unchanged `durationFrames`, `path:null`, or a `null` where an id or path belongs.
- `timeline.place` puts a clip's sound on the targeted audio track (A1 by default), overwriting the speech there: pass `"audioTrack": "new"` or a free track. `graphics.newFromFile` leaves the sound out.
- `graphics.*` take `track` as a 0-based index, and a string like `"V2"` is silently ignored. `timecode` ignores the sequence's start timecode; Mark Out includes its frame.
- `clip.speedDuration` without `reverse` turns reverse playback off. Time-remapping keyframes do not render.
- Narration (`tts.*`) has English voices only; Korean text is refused with a message that does not say why.
- Text layers default to Inter, which has no Hangul, so Korean text needs an installed Korean family (`fonts.list`); a render shows whether it drew.
- A HEIC still is refused with a container error that does not name the format.
- Lumetri and FilmCraft-only effects do not travel in a handoff; say which. Importing an FCP7 XML merges it into the open project and makes its sequence the active one.

## Seeing and hearing the edit

- You cannot play anything. Picture: `frames`; one frame of a composition, `effectcraft-cli render-frame` (comp time, `--transparent` for alpha). Sound: `waveform`, which draws signal and timing with word boxes over it. The edit: `timeline` summarises it; `inspect sequence` holds everything and grows with every clip.
- Rendering 10-bit AV1/HEVC is slow per frame.

## What does not depend on taste

- A name or term on screen you are not sure of can be wrong in a public video, and the transcript alone does not settle it; the user can fix a guess only if they know it was one.
- Never splice speech into something the speaker did not mean: an answer shown without its question can read as answering something else, so keep the question when it does.
- Added text can land on burned-in subtitles or broadcast supers, and text and faces under the target platform's UI (`frames --overlay <platform>` draws it); how to resolve one is a choice to offer.
- A sequence's size and frame rate are set when it is made and every placement happens inside them: converting 60p to 30p throws motion away, and a sequence of another size than the delivery is scaled on export.

## Speech as material

- Transcribing anew with the default engine of `transcribe` sends the whole audio to a third party (OpenRouter) and costs money; `--engine local` and `--from-json` send nothing. Its `--help` compares the engines and covers correcting and applying the result.
- A transcript's times are a claim about the audio, and no check in `transcribe` proves them. When timing decides something and you have a reason to doubt it (a word start from the local engine, a `compressed` range, two transcripts that disagree, a model or language you have not checked), look with `waveform`.
- `transcript.removeFillers` removes English fillers only unless given a list (Korean ones such as 음, 어, 아, 뭐; markers such as 그러니까 or 이제 are words a speaker may mean), and still reports success. A list removes every match whatever follows it, so 그 and 저 would turn 그 사람은 into 사람은. A filler the engine left out of the transcript cannot be removed this way, and removing pauses first leaves a gap where each filler was.
- `transcript.removePauses` keeps `keepSeconds` on both sides of each pause, so set it to half the gap you want.
- Speaker labels are the engine's clustering and nothing here checks them. A wrong attribution puts words in someone's mouth, so list what you attributed for the user before captions name or colour a speaker.
- `captions` measures each line in the burn-in font and gives the import commands as `next`. The alternatives fail differently: `transcript.createCaptions` runs a short sentence into the next and does not measure width, and `captions.add`/`setTimes` refuse overlaps, while import is lenient.
- `captions` breaks lines by length and cannot tell a phrase, so a break can part a modifier from its noun: read its lines and correct them in the SubRip; `--cues` keeps the lines and cues that fit.

## Where a picture is made

When: a title, lower third, callout, number or chart, how an inserted image is shown, an intro, an effect on the footage itself, or a motion graphic on its own.

Where it is made changes what is left for the user to change, what can see the footage, and what the trip between the apps costs.

- What is left, and where it changes: FilmCraft's native text and shapes stay editable element by element in FilmCraft and are dropped from an FCP7 XML handoff. A page rendered with `graphic` (read its `--help` before the first page) changes only by editing its code and rendering again. An EffectCraft composition stays an `.ecproj` the user can open and change in EffectCraft. Inside FilmCraft a page or a composition is a rendered clip: FilmCraft can place, time and filter it, but what is inside it changes only where it was made.
- Whether it needs the footage's pixels: FilmCraft works on a clip's own pixels, with its effects, a blur or mosaic in a mask that follows a subject (`masks.track`), keying and stabilising. EffectCraft also moves one layer by a point tracked in another (a label that follows a subject) and separates a subject from its picture with a matte (text behind a person). A page sees only the files given to it, not the edit underneath it: pushing in on the person speaking works on the footage (FilmCraft's Motion, or a comp), while pushing in on one spot of an image shown on screen is movement inside the graphic.
- Layout: a page lays itself out around its text. A composition places by coordinates, and a box that follows its text's length is an expression (`sourceRectAtTime`), which works headless. Keyframing FilmCraft's native graphics takes repeated test renders.
- FilmCraft to EffectCraft: FCP7 XML (`file.exportInterchange`, then `file.importTimeline`) carries each clip's place, length, trim, Motion and a constant speed change, with its sound as layers of their own. Effects are dropped with a warning from EffectCraft only, FilmCraft's graphics with one from both, and captions with none. There is no live link: a later change to the edit is not in the comp.
- EffectCraft back to FilmCraft: what the render holds decides how it goes back. An overlay with alpha (ProRes 4444, the footage's picture off) goes on a track above the clip; a render that remakes the whole picture takes the clip's place, since on top its picture hides the original and its sound plays over or replaces the original's, depending on the audio track it lands on. A comp that came through interchange holds the edit's sound and `render` includes it unless `--audio off`, so an overlay placed with the default audio target replaces the speech on A1. A whole-comp render placed at the sequence start lines up frame for frame; a range render (`--start` to `--end`, end excluded) carries no timecode, so where it goes is a number you carry. FilmCraft keeps a placed clip's length, so a shorter render written to the same path holds its last frame to the old end without a warning. HLG footage comes back in other colours: FilmCraft tone-maps it into a Rec. 709 sequence, and a default EffectCraft project does not.
- Partial transparency: FilmCraft blends in linear light and a default EffectCraft project blends its layers in gamma (`file.projectSettings {"blendLinear": true}` changes that), so a partly transparent layer placed in FilmCraft looks different over the picture than in EffectCraft's own frame, a browser or an ffmpeg composite: a dark layer weaker and a light one stronger. The render of whatever composites it shows it.

## How effectcraft-cli fails quietly

When: driving `effectcraft-cli`. Unknown options and unknown top-level parameter keys are refused, unlike in filmcraft-cli; these are not.

- A call with no project, or whose project after the subcommand does not end in `.ecproj`, runs on the built-in demo project and exits 0; `--project` opens the path as given. `--save-as` with neither a project nor `--empty` saves the demo's compositions along with the new work. `--save` writes only after a command that can change the project (`exec`, `run`, `set`, `script`) and is ignored without a word by `render`, `render-frame`, `info`, `props` and `get`.
- Every call is a fresh session: layer and key selection, the matte model chosen with `roto.model.select`, and `prefs.set` do not carry over.
- `set --time` and the commands that add or set a key (`prop.addKey`, `prop.set`, `keys.set`) take layer time unless given `timeBase: "comp"` (`set` takes none), while other key commands say in their own description which time they take; and layer time 0 is the layer's `start`, not its In point; a trimmed clip that came through interchange has a `start` other than 0. `render-frame` and `get` take comp time, and a key's `compTime` in the result shows where it landed.
- A font that is not installed draws in Inter without an error; `file.findMissing {"what":"fonts"}` names a layer's missing font but not one set on a range of characters (`text.fonts` lists what is installed). Emoji never draw in colour: some draw as empty space (😀, ✅) and others as a plain stand-in (❤️ as an outline, a flag as two boxed letters).
- Footage the built-in decoder cannot read (H.264 4:2:2, for one) imports without an error, is not marked missing and renders black with exit 0; only a line on stderr says why.
- Most built-in templates fill the frame with layers of their own (a background, photos), so a `--transparent` render of one comes out opaque, without a warning, until those layers are removed.
- Mattes: on a subject told apart by shape rather than colour, the built-in engine's Object Matte can report every frame computed and give a matte the size of the clicked point, and its Roto Brush a partial one. A learned model runs on the CPU and stays in the user's EffectCraft data folder, outside the piece: MobileSAM by download, SAM 2 only from a weights file the user has. An Object Matte or Roto Brush matte is kept in the project only when frozen (`objectMatte.freeze`, `roto.freeze`) in the call that computed it; otherwise the call that renders it computes it again with its own engine, the built-in one, without an error. Outside an Object Matte's tracked span (`before`/`after` frames) the layer is transparent everywhere. These commands report success whatever the matte looks like; `render-frame --transparent` shows it.

## Delivery

- With marks set, an export's default range is In to Out; `range: "entire"` takes everything. A render shows captions, but whether an export burns them or writes a sidecar is set by `burnCaptions` and `captionSidecar`. The loudness target is the `qc` target's value or one the user set.
- An export with `--allow-offline` reports success while holding placeholder frames for missing media; `media.findMissing` relinks it.
- YouTube chapters go in the description as timestamps, not into the MP4.
- An H.264 MP4 rendered by EffectCraft puts `moov` at the end, and EffectCraft has no command that sets loudness: when a piece's sound has to meet a loudness target, a FilmCraft export sets it.

## Working files

- By this skill's convention every piece has the same shape, which is how a later session finds its way in: the project and its deliverables at the piece's root; `assets/` for material brought in, copied in with `cp -c`; `graphics/` for pages, compositions (`.ecproj`) and their renders; `etc/` for the rest (tool outputs, transcripts and caption drafts worth keeping), throwaway files such as frame sheets not kept. Deleting material or a render a project plays breaks the project. Both apps store media by absolute path: the folder opens in place, and moved elsewhere EffectCraft still finds its media while FilmCraft needs relinking (`media.autoRelink`). A file written elsewhere on the user's machine is one they did not ask for and will not find, and one in `/tmp` may be unreadable in a restricted session.
- The bundled tools get their dependencies through `uv run` and `uvx`; the only global installs are those `doctor` lists.
- `FilmCraft Previews/`, next to every saved project with a sequence, is FilmCraft's render cache, not an output, and so is the empty `.<name>.lock` both CLIs leave beside a project saved in place.

## Working in the running app

When: the user wants to watch or work along, or the project is open in the app.

- Connect: `nc -z 127.0.0.1 9876`. A fresh `open -a FilmCraft --args --control 9876` opens the port (arguments reach only a fresh launch). Quitting the app discards its unsaved edits. The project's `filmcraft` MCP server appears once approved at session start.
- Commands: `filmcraft-cli --bridge 127.0.0.1:9876 …`. `render` is headless only: use MCP `render_frame {seconds}`. Use the MCP `ui_*` tools only for actions with no command.
- `--save` or `file.save` on an app project with no path opens a macOS save dialog, and every request then times out after 60 s with no reason given. When such a project has to be saved, agree on the path with the user and send `file.saveAs {path}` instead. Already stuck: ask the user to click Cancel.
- The project file on disk can lag the app's unsaved edits.
- A project open in the app holds the user's unsaved, half-made edits: saving it over the bridge commits them to their file, and the version they last saved does not come back. The `ui_*` tools move the visible window, so what they send while the user types mixes with the user's input.

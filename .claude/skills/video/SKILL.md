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

- You edit together with the user, usually over many turns. Taste is theirs to decide and yours to offer: cut rhythm, transitions, how much pause or filler to keep, caption and title design, graphics, the look, how music ends, shot order. Say in a line what you chose and why. When they choose otherwise do theirs, and what they tell you about how they work outranks this skill; when a choice collides with a platform requirement or a fact below, say so once with the consequence.
- With no idea behind the order, shots end up cycling through the sources in file order, which gives the user nothing to judge: choose shots by what is in them and say the idea.
- `${CLAUDE_SKILL_DIR}/data/`, when it exists, is the user's own record of work: each earlier piece there (its project, the pages and compositions in its `graphics/`, the exported video) is what they chose. When you propose something taste decides and an earlier piece resembles this one, read their taste from it; it informs your proposal and does not bind it. Unless the user names another folder, a new piece goes in `data/<piece>/`, so it becomes the record for the next one.
- Cheap to change (a trim, a transition, a caption style, a title's wording): make the call, show it, and move on.
- Costly to undo, or setting what the piece is (which segments a highlight or summary keeps, the overall look, a long export, a model download, overwriting a project you were handed, since `--save` has no undo across calls): show candidates and your reasons, and ask first.

## Before you hand something over

- A rendered deliverable passes `qc` for its target.
- Read the final cut's words (`transcript.inspect`) for a sentence cut off or a splice that changes what someone said; `timeline --project` on the saved `.fcproj` matches what you report.
- A page or a composition can look right in its own frame and different over the edit, and one that moves differs entering, at its fullest and leaving: when FilmCraft composites it, `frames --project` shows it there. `fallback` fonts and `blocked` requests in `graphic`'s output, and a font EffectCraft substituted, change the picture.
- Say what changed, the calls you made that the user did not, and what you could not verify. You cannot hear the cut, so how its audio flows is always unverified.
- What the user can open and change again is the edit as its `.fcproj`, a composition as its `.ecproj` and a graphic as its page. A change ffmpeg makes to picture or sound leaves a file but is recorded in no project, so the user cannot open it to adjust it; the lossless remux `qc` names changes no picture or sound.

## Before the first command

- `doctor` says what blocks the tools on this machine and gives the commands that fix it. A CLI whose version differs from its app gives no warning when it saves; the user meets it when the app refuses a project saved with a newer schema. An optional item, EffectCraft among them, matters only when the task needs it.
- FilmCraft changes often; where this skill, `describe` and what happens disagree, trust what happens and say so.

## Headless or the running app

- Work headless by default (`filmcraft-cli --project P.fcproj --save …`); there is no autosave, so saving is yours.
- `--project` opens a file that exists; start one with `filmcraft-cli --save-as P.fcproj import <media>`.
- A project open in an app and changed on disk is overwritten by whichever saves later, losing the other's unsaved or later changes. An `.ecproj` open in EffectCraft is the same, and `effectcraft-cli`'s lock only keeps two CLI runs apart. Working headless does not rule it out, since the user may have the project open.

## How filmcraft-cli fails quietly

- Every call is a fresh session: selection, track targeting and the Source monitor do not carry over, so pass ids (`clips`, `items`) wherever `describe` offers them, and use `timeline.*` rather than `trim.*` or `source.*` headless. A failing line stops a `run` before anything is saved.
- Unknown keys and unknown CLI options are ignored without an error. A float in `time` (ticks are integers; use `seconds`) or a misspelt key gives `cuts:0`; a misspelt `--bridge` or an unsplit `$OPTS` (zsh does not split) runs on an empty "Untitled" session and exits 0. Read every result for a no-op: `cuts:0`, `null`, an unchanged `durationFrames`, `path:null`.
- `timeline.place` puts a clip's sound on the targeted audio track (A1 by default), overwriting the speech there: pass `"audioTrack": "new"` or a free track. `graphics.newFromFile` leaves the sound out.
- `graphics.*` take `track` as a 0-based index, and a string like `"V2"` is silently ignored. `timecode` ignores the sequence's start timecode; Mark Out includes its frame.
- `clip.speedDuration` without `reverse` turns reverse playback off. Time-remapping keyframes do not render.
- Narration (`tts.*`) has English voices only; Korean text is refused with a message that does not say why.
- Text layers default to Inter, which has no Hangul: set an installed Korean family (`fonts.list`) and look at a render.
- A HEIC still is refused with a container error that does not name the format.
- Lumetri and FilmCraft-only effects do not travel in a handoff; say which. Importing an FCP7 XML merges it into the open project and makes its sequence the active one.

## Seeing and hearing the edit

- You cannot play anything. Picture: `frames`; one frame of a composition, `effectcraft-cli render-frame` (comp time, `--transparent` for alpha). Sound: `waveform`, which draws the audio with word boxes over it. The edit: `timeline`, not raw `inspect sequence`, whose output grows with every clip.
- Rendering 10-bit AV1/HEVC is slow per frame: ask `frames --project` only for the frames you need.

## What does not depend on taste

- When unsure of a name or term on screen, keep your best guess and list it for the user.
- Never splice speech into something the speaker did not mean: an answer shown without its question can read as answering something else, so keep the question when it does.
- Before showing anything check text collisions: captions over burned-in subtitles or broadcast supers, text and faces inside the target platform's UI (`frames --overlay <platform>`). How to resolve one is a choice to offer.
- A sequence takes the delivery's size and, unless the user wants otherwise, the source's frame rate: converting 60p to 30p throws motion away.

## Speech as material

- Transcribe with `transcribe`. Unless told `--engine local`, it sends the audio to OpenRouter and costs money; its `--help` compares the engines and covers correcting and applying the result.
- A transcript's times are a claim about the audio, and no check in `transcribe` proves them. When timing decides something and you have a reason to doubt it (a word start from the local engine, a `compressed` range, two transcripts that disagree, a model or language you have not checked), look with `waveform`.
- `transcript.removeFillers` removes English fillers only unless given a list, and still reports success: pass Korean ones (음, 어, 아, 뭐; discourse markers such as 그러니까, 이제, 약간 only if the user wants them gone). A list removes every match whatever follows it, so 그 and 저 would turn 그 사람은 into 사람은: cut those by word after reading them. A filler the engine left out of the transcript cannot be removed this way. Remove fillers before pauses; the other order leaves a gap where each filler was.
- `transcript.removePauses` keeps `keepSeconds` on both sides of each pause, so set it to half the gap you want.
- Speaker labels are the engine's clustering and nothing here checks them. A wrong attribution puts words in someone's mouth, so list what you attributed for the user before captions name or colour a speaker.
- Captions come from `captions`, then its `next` commands: not `transcript.createCaptions` (it runs a short sentence into the next and does not measure width) and not `captions.add`/`setTimes` (they refuse overlaps; import is lenient).
- `captions` breaks lines by length and cannot tell a phrase, so a break can part a modifier from its noun: read its lines and correct them in the SubRip; `--cues` keeps the lines and cues that fit.

## Where a picture is made

When: a title, lower third, callout, number or chart, how an inserted image is shown, an intro, an effect on the footage itself, or a motion graphic on its own.

Where it is made changes what is left for the user to change, what can see the footage, and what the trip between the apps costs.

- What is left, and where it changes: FilmCraft's native text and shapes stay editable element by element in FilmCraft and are dropped from an FCP7 XML handoff. A page rendered with `graphic` (read its `--help` before the first page) changes only by editing its code and rendering again. An EffectCraft composition stays an `.ecproj` the user can open and change in EffectCraft. Inside FilmCraft a page or a composition is a rendered clip, so only its place, length and Motion change there.
- Whether it needs the footage's pixels: FilmCraft works on a clip's own pixels, with its effects, a blur or mosaic in a mask that follows a subject (`masks.track`), keying and stabilising. EffectCraft also moves one layer by a point tracked in another (a label that follows a subject) and separates a subject from its picture with a matte (text behind a person). A page never sees the footage: pushing in on the person speaking is FilmCraft's Motion, while pushing in on one spot of an image shown on screen is movement inside the graphic.
- Layout: a page lays itself out around its text. A composition places by coordinates, and a box that follows its text's length is an expression (`sourceRectAtTime`), which works headless. Keyframing FilmCraft's native graphics takes repeated test renders.
- FilmCraft to EffectCraft: FCP7 XML (`file.exportInterchange`, then `file.importTimeline`) carries each clip's place, length, trim, Motion and a constant speed change, with its sound as layers of their own. Effects are dropped with a warning from EffectCraft only, FilmCraft's graphics with one from both, and captions with none. There is no live link: a later change to the edit is not in the comp.
- EffectCraft back to FilmCraft: what the render holds decides how it goes back. An overlay with alpha (ProRes 4444, the footage's picture off) goes on a track above the clip; a render that remakes the whole picture takes the clip's place, since on top its picture hides the original and its sound overwrites A1. A comp that came through interchange holds the edit's sound and `render` includes it unless `--audio off`, so a placed overlay replaces the speech on A1. A whole-comp render placed at the sequence start lines up frame for frame; a range render (`--start` to `--end`, end excluded) carries no timecode, so where it goes is a number you carry. FilmCraft keeps a placed clip's length, so a shorter render written to the same path holds its last frame to the old end without a warning. HLG footage comes back in other colours: FilmCraft tone-maps it into a Rec. 709 sequence, and a default EffectCraft project does not.
- Partial transparency: FilmCraft blends in linear light and a default EffectCraft project blends its layers in gamma (`file.projectSettings {"blendLinear": true}` changes that), so a partly transparent layer placed in FilmCraft looks different over the picture than in EffectCraft's own frame, a browser or an ffmpeg composite: a dark layer weaker and a light one stronger. The render of whatever composites it shows it; `frames --project` when FilmCraft does.

## How effectcraft-cli fails quietly

When: driving `effectcraft-cli`. Unknown options and unknown top-level parameter keys are refused, unlike in filmcraft-cli; these are not.

- A call with no project, or whose project after the subcommand does not end in `.ecproj`, runs on the built-in demo project and exits 0; `--project` opens the path as given. `--save-as` without `--empty` saves the demo's compositions along with the new work. `--save` writes only after a command that can change the project (`exec`, `run`, `set`, `script`) and is ignored without a word by `render`, `render-frame`, `info`, `props` and `get`.
- Every call is a fresh session: layer and key selection, the matte model chosen with `roto.model.select`, and `prefs.set` do not carry over.
- `set --time` and the keyframe commands take layer time unless a command accepts `timeBase: "comp"` (`set` does not), and layer time 0 is the layer's `start`, not its In point; a trimmed clip that came through interchange has a `start` other than 0. `render-frame` and `get` take comp time, and a key's `compTime` in the result shows where it landed.
- A font that is not installed draws in Inter without an error; `file.findMissing {"what":"fonts"}` names a layer's missing font but not one set on a range of characters (`text.fonts` lists what is installed). Colour emoji draw as empty space.
- Footage the built-in decoder cannot read (H.264 4:2:2, for one) imports without an error, is not marked missing and renders black with exit 0; only a line on stderr says why.
- The built-in templates carry a full-frame "Preview Background" layer, so an alpha render of one is opaque until that layer is removed.
- Mattes: on a subject told apart by shape rather than colour, the built-in engine's Object Matte reports every frame computed and gives a matte the size of the clicked point, and its Roto Brush a partial one. A learned model (MobileSAM, SAM 2) is a download that stays in the user's EffectCraft data folder, outside the piece, and runs on the CPU. An Object Matte or Roto Brush matte is kept in the project only when frozen (`objectMatte.freeze`, `roto.freeze`) in the call that computed it; otherwise the call that renders it computes it again with its own engine, the built-in one, without an error. Outside its tracked span (`before`/`after` frames) the layer is transparent everywhere. These commands report success whatever the matte looks like; `render-frame --transparent` shows it.

## Delivery

- Every export: `range: "entire"` (the default is In to Out when marks are set), `burnCaptions` and `captionSidecar` as intended (a render shows captions an export drops), loudness at the `qc` target.
- Fix offline media with `media.findMissing`; `--allow-offline` is for previews, not deliverables.
- YouTube chapters go in the description as timestamps, not into the MP4.
- An MP4 rendered by EffectCraft puts `moov` at the end, and EffectCraft has no command that sets loudness: a piece with sound gets its delivery loudness from a FilmCraft export.

## Working files

- Every piece has the same shape, so a later session can find its way in: the project and its deliverables at the piece's root; `assets/` for material brought in, copied in with `cp -c` from wherever it came, so the piece's folder alone opens the project; `graphics/` for pages, compositions (`.ecproj`) and their renders, kept because the projects play them; `etc/` for the rest (tool outputs, transcripts and caption drafts worth keeping), with throwaway files such as frame sheets removed at the end. Write nothing outside the user's folders: a file in `/tmp` may be unreadable to you in a restricted session.
- No global installs beyond what `doctor` asks for; tools otherwise run through `uv run` and `uvx`.
- FilmCraft keeps `FilmCraft Previews/`, its render cache, next to every saved project with a sequence. It is not an output; say so rather than leaving the user to wonder.

## Working in the running app

When: the user wants to watch or work along, or the project is open in the app.

- Connect: `nc -z 127.0.0.1 9876`. If the app is not running, `open -a FilmCraft --args --control 9876` (arguments reach only a fresh launch). If it runs without the port, ask the user to save and quit it; never quit it yourself. The project's `filmcraft` MCP server appears once approved at session start.
- Commands: `filmcraft-cli --bridge 127.0.0.1:9876 …`. `render` is headless only: use MCP `render_frame {seconds}`. Use the MCP `ui_*` tools only for actions with no command.
- `--save` or `file.save` on an app project with no path opens a macOS save dialog, and every request then times out after 60 s with no reason given. When such a project has to be saved, agree on the path with the user and send `file.saveAs {path}` instead. Already stuck: ask the user to click Cancel.
- The project file on disk can lag the app's unsaved edits.
- Do not drive the UI while the user is typing, and leave saving the open project to them. Leave the app open when done.

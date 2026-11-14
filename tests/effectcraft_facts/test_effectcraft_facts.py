"""EffectCraft behaviour the skill's prose relies on, checked against the installed effectcraft-cli (and filmcraft-cli where the two meet). EffectCraft ships often; when one of these fails after an update, the SKILL.md sentence named in its docstring is the one to rewrite (or delete), not the test to loosen.

Every expectation comes from the synthetic input's own parameters or a value worked by hand, and every test holds its own control: the case the sentence warns about next to the case it does not. The matte tests use this Mac's installed MobileSAM model through a private data dir and never download it; without the model they are skipped, visibly.

Run after an update: `uv run --with pytest --with pillow pytest tests/effectcraft_facts`."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from video import ffmpeg as ff, mp4
from support import EFFECTCRAFT, TICKS, ec, ec_json, ec_run, fc, fc_json, fc_run, ffmpeg, needs_effectcraft, needs_ffmpeg, needs_filmcraft, needs_mobilesam

pytestmark = [needs_effectcraft, needs_ffmpeg]

NTSC = 30000 / 1001


def new_project(d: Path, name: str, steps: list[tuple[str, dict]]) -> Path:
    """An empty project with `steps` run in it, saved as `<name>.ecproj`."""
    p = d / f"{name}.ecproj"
    args = [a for c, prm in steps for a in (c, json.dumps(prm, ensure_ascii=False))]
    ec("--empty", "--save-as", str(p), "--json", "run", *args, cwd=d)
    return p


def summary_names(p: Path, d: Path) -> set[str]:
    return {i["name"] for i in ec_json("--project", str(p), "exec", "project.summary", cwd=d)["items"]}


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rgba(png: Path) -> Image.Image:
    return Image.open(png).convert("RGBA")


def lin(v: float) -> float:
    c = v / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def srgb(l: float) -> float:
    c = 12.92 * l if l <= 0.0031308 else 1.055 * l ** (1 / 2.4) - 0.055
    return c * 255


# -- How effectcraft-cli fails quietly: which project a call works on ------------------------------------------------------------

def test_00_unknown_options_and_parameter_keys_are_refused(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: unlike filmcraft-cli, an unknown option exits 2 and an unknown top-level parameter key is an error naming the keys accepted; the control call with the right spelling succeeds."""
    assert ec("info", "--jsno", cwd=tmp_path, check=False).returncode == 2
    bad = ec("--empty", "exec", "comp.new", "--params", '{"nmae": "x"}', cwd=tmp_path, check=False)
    assert bad.returncode != 0 and "nmae" in bad.stderr and "accepted: name" in bad.stderr
    assert ec("--empty", "exec", "comp.new", "--params", '{"name": "x"}', cwd=tmp_path).returncode == 0


def test_01_a_positional_project_needs_the_ecproj_extension_or_the_demo_runs(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: a positional project whose name does not end in `.ecproj` is ignored and the call runs on the built-in demo project with exit 0, as does a call with no project; `--project` opens the path it is given."""
    p = new_project(tmp_path, "mine", [("comp.new", {"name": "Mine", "width": 320, "height": 180, "duration": 1})])
    typo = tmp_path / "mine.ecprj"
    typo.write_bytes(p.read_bytes())
    demo = ec("info", str(typo), cwd=tmp_path)
    assert demo.returncode == 0 and "Lower Third" in demo.stdout and "Mine" not in demo.stdout
    assert "Lower Third" in ec("info", cwd=tmp_path).stdout
    # controls: the right extension, and --project with the wrong one, open the file
    assert "Mine" in ec("info", str(p), cwd=tmp_path).stdout
    opened = ec("--project", str(typo), "info", cwd=tmp_path).stdout
    assert "Mine" in opened and "Lower Third" not in opened
    # a missing path ending in .ecproj is an error, not the demo
    assert ec("info", str(tmp_path / "none.ecproj"), cwd=tmp_path, check=False).returncode != 0


def test_02_save_as_without_empty_saves_the_demo_with_the_new_work(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: `--save-as` without `--empty` starts from the demo, so the saved project holds the demo's compositions next to what the call made; with `--empty` it holds only the new work."""
    step = ["exec", "comp.new", "--params", json.dumps({"name": "Mine", "duration": 1})]
    ec("--save-as", str(tmp_path / "demo.ecproj"), *step, cwd=tmp_path)
    ec("--empty", "--save-as", str(tmp_path / "empty.ecproj"), *step, cwd=tmp_path)
    with_demo, alone = summary_names(tmp_path / "demo.ecproj", tmp_path), summary_names(tmp_path / "empty.ecproj", tmp_path)
    assert {"Mine", "Lower Third", "EffectCraft Intro"} <= with_demo
    assert alone == {"Mine"}


def test_03_save_is_ignored_by_commands_that_only_read_or_render(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: `--save` writes only after a command that can change the project (`exec`, `run`, `set`, `script`); with `info`, `props`, `get`, `render-frame` and `render` the file is not written and nothing says so. Written is told by the file's modification time, since a save of an unchanged project writes the same bytes."""
    p = new_project(tmp_path, "p", [("comp.new", {"name": "C", "width": 160, "height": 90, "duration": 0.5}), ("layer.newText", {"text": "x"})])

    def written(*args) -> tuple[bool, str]:
        os.utime(p, ns=(1_000_000_000, 1_000_000_000))
        r = ec("--project", str(p), "--save", *args, "--json", cwd=tmp_path)
        return p.stat().st_mtime_ns != 1_000_000_000, r.stdout

    for args in (["info"], ["props", "C", "#1"], ["get", "C", "#1", "transform/position"], ["render-frame", "--comp", "C", "--out", "f.png"], ["render", "--comp", "C", "--out", "r.mov", "--format", "prores"]):
        saved, out = written(*args)
        assert not saved and '"saved"' not in out, args
    # control: a command that changes nothing is still saved when it may change the project
    saved, out = written("exec", "project.summary")
    assert saved and '"saved"' in out


def test_04a_each_call_is_a_new_session_and_forgets_selection_and_settings(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: every call is a new session; a layer selected and a setting changed with `prefs.set` hold within that call and are gone in the next, even with `--save`."""
    p = tmp_path / "s.ecproj"
    out = ec_json("--empty", "--save-as", str(p), "run", "comp.new", '{"name": "C", "duration": 1}', "layer.newText", '{"text": "a"}', "layer.newText", '{"text": "b"}',
                  "layer.select", '{"layers": ["#2"]}', "project.summary", "{}", "prefs.set", '{"key": "general.undoLevels", "value": 99}', "prefs.get", '{"key": "general.undoLevels"}', cwd=tmp_path)
    rows = [r["result"] for r in out["result"]]
    assert len(rows[4]["selectedLayers"]) == 1 and rows[6] == 99                      # control: same call
    assert ec_json("--project", str(p), "exec", "project.summary", cwd=tmp_path)["selectedLayers"] == []
    assert ec_json("exec", "prefs.get", "--params", '{"key": "general.undoLevels"}', cwd=tmp_path) != 99


@needs_mobilesam
def test_04_each_call_is_a_new_session_and_forgets_the_chosen_model(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: every call is a new session; the matte model chosen with `roto.model.select` holds within that call only, and the next call is back on the built-in engine."""
    def selected(rows):
        return next(m["id"] for m in rows["models"] if m["selected"])

    out = ec_json("run", "roto.model.select", json.dumps({"id": "mobilesam", "wait": True}), "roto.models", "{}", cwd=tmp_path)
    assert selected(out[1]["result"]) == "mobilesam"                       # control: same call
    ec("exec", "roto.model.select", "--params", json.dumps({"id": "mobilesam", "wait": True}), cwd=tmp_path)
    assert selected(ec_json("exec", "roto.models", cwd=tmp_path)) == "classical"     # next call


# -- How effectcraft-cli fails quietly: time ------------------------------------------------------------------------------------

def test_05_set_time_is_layer_time_counted_from_the_layer_start(roundtrip):
    """SKILL.md › How effectcraft-cli fails quietly: `set --time` is layer time and `set` takes no time base; layer time 0 is the layer's `start`, not its In point, and a trimmed clip that came through interchange has a `start` other than 0. `prop.addKey` with `timeBase: comp` puts the key at the comp time given, `get --time` reads comp time, and the result's `compTime` shows where a key landed. Expected: the clip shows source frame 20 at sequence frame 30, so its start is (30 - 20) frames = 10 x 1001/30000 s."""
    d, e, layer = roundtrip["dir"], roundtrip["ecproj"], roundtrip["layer"]
    work = d / "t05.ecproj"
    work.write_bytes(e.read_bytes())
    info = next(l for l in ec_json("--project", str(work), "exec", "comp.info", cwd=d)["layers"] if l["id"] == layer)
    assert info["start"] == pytest.approx(10 / NTSC, abs=1e-3) and info["in"] == pytest.approx(30 / NTSC, abs=1e-3)
    frame = 1 / NTSC   # keys land on the comp's frames
    [key] = ec_json("--project", str(work), "--save", "set", "-", str(layer), "transform/opacity", "40", "--time", "1", cwd=d)["result"]["keys"]
    assert key["compTime"] == pytest.approx(10 / NTSC + 1, abs=frame)                 # from the start, 0.33 s before the In point
    assert abs(key["compTime"] - (30 / NTSC + 1)) > 0.5                              # not from the In point
    [comp_key] = ec_run(work, [("prop.addKey", {"layer": layer, "path": "transform/opacity", "time": 2, "timeBase": "comp", "value": 70})], cwd=d)
    assert comp_key["compTime"] == pytest.approx(2, abs=frame)
    # `get --time` is comp time: at the first key's comp time it reads that key's value; read as layer time it would land between the keys
    at_first = ec_json("--project", str(work), "get", "-", str(layer), "transform/opacity", "--time", f"{key['compTime']:.6f}", cwd=d)["value"]
    assert at_first == pytest.approx(40, abs=0.5)


# -- How effectcraft-cli fails quietly: fonts ------------------------------------------------------------------------------------

def test_06_a_missing_font_falls_back_to_inter_and_only_a_layer_font_is_reported(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: a font name that is not installed draws in Inter with no error; `file.findMissing {"what":"fonts"}` names a layer's missing font but not one set on a range of characters."""
    comp = {"width": 400, "height": 120, "duration": 0.5, "background": "#000000"}
    text = {"text": "Hello", "size": 60, "fill": "#ffffff"}
    p = new_project(tmp_path, "f", [("comp.new", {"name": "Missing", **comp}), ("layer.newText", {**text, "font": "NoSuchFontXYZ"}),
                                    ("comp.new", {"name": "Inter", **comp}), ("layer.newText", {**text, "font": "Inter"}),
                                    ("comp.new", {"name": "Georgia", **comp}), ("layer.newText", {**text, "font": "Georgia"}),
                                    ("comp.new", {"name": "Range", **comp}), ("layer.newText", {**text, "text": "abc def", "font": "Inter"}),
                                    ("comp.new", {"name": "RangeOk", **comp}), ("layer.newText", {**text, "text": "abc def", "font": "Inter"}),
                                    ("comp.new", {"name": "Plain", **comp}), ("layer.newText", {**text, "text": "abc def", "font": "Inter"})])

    def only_layer(comp_name):
        return ec_json("--project", str(p), "exec", "comp.info", "--params", json.dumps({"comp": comp_name}), cwd=tmp_path)["layers"][0]["id"]

    ec_run(p, [("comp.open", {"comp": "Range"}), ("layer.setText", {"layer": only_layer("Range"), "range": [4, 7], "font": "NoSuchFontXYZ"}),
               ("comp.open", {"comp": "RangeOk"}), ("layer.setText", {"layer": only_layer("RangeOk"), "range": [4, 7], "font": "Georgia"})], cwd=tmp_path)
    for c in ("Missing", "Inter", "Georgia", "Range", "RangeOk", "Plain"):
        ec("--project", str(p), "render-frame", "--comp", c, "--out", f"{c}.png", cwd=tmp_path)

    def same(a, b):
        return rgba(tmp_path / f"{a}.png").tobytes() == rgba(tmp_path / f"{b}.png").tobytes()

    assert same("Missing", "Inter") and not same("Georgia", "Inter")    # control: an installed font draws differently
    assert same("Range", "Plain") and not same("RangeOk", "Plain")      # control: a range font is applied when installed
    missing = ec_json("--project", str(p), "exec", "file.findMissing", "--params", '{"what":"fonts"}', cwd=tmp_path)["fonts"]
    assert [m["font"] for m in missing] == ["NoSuchFontXYZ"] and len(missing) == 1   # the layer font, not the range one


def test_07_colour_emoji_draw_as_nothing(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: a colour emoji in a text layer draws as empty space without an error, in the default font and in Apple Color Emoji alike; a monochrome symbol such as ★ draws."""
    comp = {"width": 200, "height": 200, "duration": 0.5, "background": "#000000"}
    p = new_project(tmp_path, "e", [("comp.new", {"name": "Emoji", **comp}), ("layer.newText", {"text": "😀", "size": 120, "fill": "#ffffff"}),
                                    ("comp.new", {"name": "EmojiFont", **comp}), ("layer.newText", {"text": "😀", "size": 120, "fill": "#ffffff", "font": "Apple Color Emoji"}),
                                    ("comp.new", {"name": "Star", **comp}), ("layer.newText", {"text": "★", "size": 120, "fill": "#ffffff"})])
    lit = {}
    for c in ("Emoji", "EmojiFont", "Star"):
        ec("--project", str(p), "render-frame", "--comp", c, "--out", f"{c}.png", cwd=tmp_path)
        lit[c] = sum(1 for px in Image.open(tmp_path / f"{c}.png").convert("L").get_flattened_data() if px > 40)
    assert lit["Emoji"] == 0 and lit["EmojiFont"] == 0
    assert lit["Star"] > 500


# -- How effectcraft-cli fails quietly: footage --------------------------------------------------------------------------------

def test_08_footage_the_decoder_cannot_read_renders_black_with_success(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: footage the built-in decoder cannot read (here H.264 4:2:2 10-bit) imports without an error or warning, is not marked missing, and renders as black with exit 0; only a line on stderr says why. The same picture as 4:2:0 renders."""
    for name, profile, pix in (("h422", "high422", "yuv422p10le"), ("h420", "high", "yuv420p")):
        ffmpeg("-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=1", "-c:v", "libx264", "-profile:v", profile, "-pix_fmt", pix, str(tmp_path / f"{name}.mp4"))
    seen = {}
    for name in ("h422", "h420"):
        p = tmp_path / f"{name}.ecproj"
        out = ec_json("--empty", "--save-as", str(p), "run", "file.import", json.dumps({"paths": [str(tmp_path / f"{name}.mp4")], "newComp": True}), cwd=tmp_path)
        imported = out["result"][0]["result"]
        assert imported["errors"] == [] and imported["warnings"] == []
        assert not any(i["missing"] for i in ec_json("--project", str(p), "exec", "project.summary", cwd=tmp_path)["items"])
        r = ec("--project", str(p), "render-frame", "--time", "0.5", "--out", f"{name}.png", cwd=tmp_path)
        assert r.returncode == 0
        seen[name] = (max(Image.open(tmp_path / f"{name}.png").convert("L").get_flattened_data()), r.stderr)
    assert seen["h422"][0] == 0 and seen["h420"][0] > 100
    assert "4:2:0" in seen["h422"][1] and "4:2:0" not in seen["h420"][1]    # the reason, on stderr only


def test_09_most_builtin_templates_render_opaque_with_transparent(tmp_path):
    """SKILL.md › How effectcraft-cli fails quietly: most built-in templates fill the frame with layers of their own, so a `--transparent` render comes out opaque without a warning, until those layers are removed. Controls: the 3D text template renders transparent, and the lower third without its "Preview Background" layer does too."""
    opaque = {}
    for tid in [t["id"] for t in ec_json("exec", "templates.list", cwd=tmp_path)]:
        q = tmp_path / f"{tid}.ecproj"
        ec("--empty", "exec", "templates.create", "--params", json.dumps({"id": tid, "projectPath": str(q)}), cwd=tmp_path)
        r = ec("--project", str(q), "render-frame", "--time", "1.5", "--max-side", "320", "--transparent", "--out", f"{tid}.png", cwd=tmp_path)
        assert r.returncode == 0 and "warn" not in r.stderr.lower()
        opaque[tid] = min(rgba(tmp_path / f"{tid}.png").getchannel("A").get_flattened_data()) == 255
    assert sum(opaque.values()) > len(opaque) / 2 and opaque["lower-third"], opaque
    assert opaque["text-orbit-3d"] is False
    p = tmp_path / "lower-third.ecproj"
    layers = ec_json("--project", str(p), "exec", "comp.info", cwd=tmp_path)["layers"]
    [bg] = [l["id"] for l in layers if l["name"].startswith("Preview Background")]
    ec_run(p, [("edit.clear", {"layers": [bg]})], cwd=tmp_path)
    ec("--project", str(p), "render-frame", "--time", "2", "--max-side", "480", "--transparent", "--out", "without.png", cwd=tmp_path)
    assert min(rgba(tmp_path / "without.png").getchannel("A").get_flattened_data()) == 0


# -- How effectcraft-cli fails quietly: mattes ---------------------------------------------------------------------------------

RING = dict(cx0=100, speed=90, cy=120, r=45)  # a disc moving right at 90 px/s, outlined by a black ring, over noise of the same colours


def ring_clip(path: Path) -> Path:
    """320x240, 30 fps, 1 s: random colours everywhere, the disc told apart only by a 3 px black ring, so colour statistics cannot separate it."""
    dist = f"hypot(X-({RING['cx0']}+T*{RING['speed']})\\,Y-{RING['cy']})"
    expr = {c: f"if(lt(abs({dist}-{RING['r']})\\,3)\\,0\\,255*random({i}))" for i, c in enumerate("rgb", 1)}
    ffmpeg("-f", "lavfi", "-i", f"color=c=black:s=320x240:r=30:d=1,format=rgb24,geq=r='{expr['r']}':g='{expr['g']}':b='{expr['b']}'", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", str(path))
    return path


def disc_alpha(png: Path, t: float) -> tuple[float, float]:
    """Mean alpha (0–1) inside the disc and outside it at time t, 4 px clear of the ring."""
    a = rgba(png).getchannel("A")
    cx = RING["cx0"] + RING["speed"] * t
    inside, outside = [], []
    for y in range(0, 240, 2):
        for x in range(0, 320, 2):
            dd = math.hypot(x - cx, y - RING["cy"])
            (inside if dd < RING["r"] - 4 else outside if dd > RING["r"] + 4 else []).append(a.getpixel((x, y)) / 255)
    return sum(inside) / len(inside), sum(outside) / len(outside)


@pytest.fixture(scope="module")
def ring(tmp_path_factory):
    d = tmp_path_factory.mktemp("ring")
    return d, ring_clip(d / "ring.mp4")


def matte_project(d: Path, name: str, clip: Path, steps: list[tuple[str, dict]]) -> Path:
    p = d / f"{name}.ecproj"
    ec("--empty", "--save-as", str(p), "run", "file.import", json.dumps({"paths": [str(clip)], "newComp": True}), cwd=d)
    if steps:
        ec_run(p, steps, cwd=d)
    return p


def alpha_at(p: Path, d: Path, t: float) -> tuple[float, float]:
    out = d / f"{p.stem}_{t}.png"
    ec("--project", str(p), "render-frame", "--time", str(t), "--transparent", "--out", str(out), cwd=d)
    return disc_alpha(out, t)


POINT, BOX = [100, 120], [50, 70, 150, 170]


@pytest.mark.slow
@needs_mobilesam
def test_10_the_builtin_object_matte_reports_success_with_an_empty_matte(ring):
    """SKILL.md › How effectcraft-cli fails quietly: on a picture whose subject is told apart by shape rather than colour, the built-in engine's Object Matte reports every frame computed and gives a matte the size of the clicked point; MobileSAM, frozen, separates the whole disc."""
    d, clip = ring
    p = matte_project(d, "builtin", clip, [])
    rows = ec_run(p, [("objectMatte.apply", {"layer": 1, "point": POINT, "box": BOX, "frame": 0}), ("objectMatte.propagate", {"layer": 1, "wait": True})], cwd=d)
    assert len(rows[1]["status"]["computed"]) >= 30
    assert alpha_at(p, d, 0)[0] < 0.05 and alpha_at(p, d, 0.5)[0] < 0.05
    q = matte_project(d, "sam_frozen", clip, [("roto.model.select", {"id": "mobilesam", "wait": True}), ("objectMatte.apply", {"layer": 1, "point": POINT, "box": BOX, "frame": 0}),
                                               ("objectMatte.propagate", {"layer": 1, "wait": True}), ("objectMatte.freeze", {"layer": 1, "wait": True})])
    for t in (0, 0.5):
        inside, outside = alpha_at(q, d, t)
        assert inside > 0.95 and outside < 0.05, (t, inside, outside)


@pytest.mark.slow
@needs_mobilesam
@pytest.mark.parametrize("effect", ["objectMatte", "roto"])
def test_11_an_unfrozen_matte_is_recomputed_by_the_next_call_with_the_builtin_engine(ring, effect):
    """SKILL.md › How effectcraft-cli fails quietly: an Object Matte or Roto Brush matte that is not frozen is not stored in the project; the call that renders it computes it again with that call's engine, which is the built-in one, so a MobileSAM matte saved unfrozen renders like the built-in engine's, without an error. Frozen in the call that made it, it renders as MobileSAM made it. Compared at the reference frame, where the built-in result is not empty (Object Matte's point, Roto Brush's partial matte) and the unfrozen render matches it pixel for pixel, so an unfrozen matte that merely blanked the layer would fail."""
    d, clip = ring
    if effect == "objectMatte":
        make = [("objectMatte.apply", {"layer": 1, "point": POINT, "box": BOX, "frame": 0}), ("objectMatte.propagate", {"layer": 1, "wait": True})]
    else:
        make = [("roto.stroke", {"layer": 1, "kind": "fg", "points": [[85, 120], [115, 120], [100, 105], [100, 135]], "frame": 0, "radius": 8}),
                ("roto.stroke", {"layer": 1, "kind": "bg", "points": [[20, 20], [300, 20], [300, 220], [20, 220], [250, 120]], "frame": 0, "radius": 8}),
                ("roto.propagate", {"layer": 1, "direction": "forward", "wait": True})]
    sam = [("roto.model.select", {"id": "mobilesam", "wait": True})]
    builtin = matte_project(d, f"{effect}_builtin", clip, make)
    unfrozen = matte_project(d, f"{effect}_unfrozen", clip, sam + make)
    frozen = matte_project(d, f"{effect}_frozen", clip, sam + make + [(f"{effect}.freeze", {"layer": 1, "wait": True})])
    for t in (0, 0.5):
        assert alpha_at(unfrozen, d, t)[0] == pytest.approx(alpha_at(builtin, d, t)[0], abs=0.02), t
        assert alpha_at(frozen, d, t)[0] > 0.95, t
    # at the reference frame the built-in matte is not empty (Object Matte: the clicked point; Roto Brush: a partial matte), and the unfrozen one matches it pixel for pixel, so a blanked layer fails
    assert alpha_at(builtin, d, 0)[0] > 0.001
    assert rgba(d / f"{unfrozen.stem}_0.png").getchannel("A").tobytes() == rgba(d / f"{builtin.stem}_0.png").getchannel("A").tobytes()
    if effect == "roto":
        assert 0.1 < alpha_at(builtin, d, 0)[0] < 0.6          # the built-in Roto Brush: a partial matte


@pytest.mark.slow
@needs_mobilesam
def test_12_outside_the_tracked_span_the_whole_layer_is_transparent(ring):
    """SKILL.md › How effectcraft-cli fails quietly: an Object Matte follows its subject only over its span (`before`/`after` frames around the reference frame); past it the layer is transparent everywhere, subject and background alike."""
    d, clip = ring
    p = matte_project(d, "span", clip, [("roto.model.select", {"id": "mobilesam", "wait": True}), ("objectMatte.apply", {"layer": 1, "point": POINT, "box": BOX, "frame": 0, "after": 10}),
                                        ("objectMatte.propagate", {"layer": 1, "wait": True}), ("objectMatte.freeze", {"layer": 1, "wait": True})])
    inside, outside = alpha_at(p, d, 6 / 30)      # frame 6: in the span
    assert inside > 0.95 and outside < 0.05
    inside, outside = alpha_at(p, d, 20 / 30)     # frame 20: past it
    assert inside == 0 and outside == 0


# -- Where a picture is made: the round trip FilmCraft -> EffectCraft -> FilmCraft ------------------------------------------------

def marker_clip(path: Path, seconds: float = 4) -> Path:
    """29.97 fps 640x360 grey frames with a white 8 px square at x = 8 + 4n in frame n, so a frame's index is read from the picture, and a 1 kHz tone."""
    inside = "between(X\\,8+4*N\\,15+4*N)*between(Y\\,100\\,107)"
    v = f"if({inside}\\,255\\,128)"
    ffmpeg("-f", "lavfi", "-i", f"color=c=gray:s=640x360:r=30000/1001:d={seconds},format=rgb24,geq=r='{v}':g='{v}':b='{v}'",
           "-f", "lavfi", "-i", f"sine=frequency=1000:sample_rate=48000:duration={seconds}", "-c:v", "libx264", "-crf", "4", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path))
    return path


def frame_index(png: Path) -> int | None:
    im = Image.open(png).convert("RGB")
    xs = [x for x in range(im.width) if im.getpixel((x, 103))[0] > 200]
    return round((xs[0] - 8) / 4) if xs else None


def fc_tracks(p: Path, d: Path) -> dict:
    s = fc_json("inspect", "sequence", project=p, cwd=d)
    return {f"{k[0].upper()}{i + 1}": [(c["name"], c["startFrame"], c["endFrame"]) for c in t["items"]] for k in ("video", "audio") for i, t in enumerate(s[k])}


@pytest.fixture(scope="module")
def roundtrip(tmp_path_factory):
    """A FilmCraft sequence S (29.97, 640x360, 3 s) holding the marker clip trimmed to start at source frame 20, placed at sequence frame 30 for 60 frames on V1/A1, exported as FCP7 XML and opened in EffectCraft; `layer` is the comp's picture layer."""
    if subprocess.run(["which", "filmcraft-cli"], capture_output=True).returncode != 0 and not (Path.home() / ".local/bin/filmcraft-cli").exists():
        pytest.skip("filmcraft-cli is not installed")
    d = tmp_path_factory.mktemp("roundtrip")
    marker_clip(d / "src.mp4")
    p = d / "edit.fcproj"
    fc("--save-as", str(p), "import", str(d / "src.mp4"), cwd=d)
    rows = fc_run([{"id": "file.newSequence", "params": {"name": "S", "width": 640, "height": 360, "fps": 29.97, "video": 3, "audio": 2}},
                   {"id": "timeline.place", "params": {"item": 1, "track": "V1", "audioTrack": "A1", "frame": 30, "sourceIn": {"frame": 20}, "duration": {"frame": 60}}}], p, cwd=d)
    assert all(r["ok"] for r in rows), rows
    xml = d / "edit.xml"
    fc("exec", "file.exportInterchange", json.dumps({"format": "xml", "path": str(xml)}), project=p, cwd=d)
    e = d / "edit.ecproj"
    imported = ec_json("--empty", "--save-as", str(e), "exec", "file.importTimeline", "--params", json.dumps({"path": str(xml)}), cwd=d)["result"]
    comp = ec_json("--project", str(e), "exec", "comp.info", cwd=d)
    [layer] = [l["id"] for l in comp["layers"] if l["switches"]["video"]]
    return {"dir": d, "fcproj": p, "ecproj": e, "import": imported, "comp": comp, "layer": layer}


def overlay_project(rt: dict, name: str) -> Path:
    """The round-trip comp with a soft-edged (Gaussian Blur 20), 60 % white box over the footage, and the footage's picture switched off: the overlay to render."""
    d = rt["dir"]
    e = d / f"{name}.ecproj"
    e.write_bytes(rt["ecproj"].read_bytes())
    [box, _] = ec_run(e, [("layer.newSolid", {"color": "#ffffff", "width": 300, "height": 150, "name": "box"}), ("effect.apply", {"effect": "Gaussian Blur"})], cwd=d)
    ec("--project", str(e), "--save", "set", "-", str(box["layer"]), "effects/#1/blurriness", "20", cwd=d)
    ec("--project", str(e), "--save", "set", "-", str(box["layer"]), "transform/opacity", "60", cwd=d)
    ec_run(e, [("layer.setSwitch", {"layers": [rt["layer"]], "switch": "video", "value": False})], cwd=d)
    return e


def place_copy(rt: dict, name: str, media: Path, params: dict) -> Path:
    """A copy of the FilmCraft edit with `media` imported and placed with `params`."""
    d = rt["dir"]
    q = d / f"{name}.fcproj"
    q.write_bytes(rt["fcproj"].read_bytes())
    item = fc_json("--save", "exec", "file.import", json.dumps({"paths": [str(media)]}), project=q, cwd=d)["items"][0]
    rows = fc_run([{"id": "timeline.place", "params": {"item": item, **params}}], q, cwd=d)
    assert rows[0]["ok"], rows
    return q


@needs_filmcraft
def test_13_interchange_keeps_timing_and_motion_and_drops_the_rest_unequally_reported(tmp_path):
    """SKILL.md › Where a picture is made: FCP7 XML from `file.exportInterchange` into `file.importTimeline` keeps each clip's place, length, trim, Motion and a constant speed change, with its sound as separate layers; effects are dropped with a warning from EffectCraft only, FilmCraft's own graphics with a word from both sides, and captions with a word from neither."""
    d = tmp_path
    marker_clip(d / "src.mp4")
    p = d / "m.fcproj"
    fc("--save-as", str(p), "import", str(d / "src.mp4"), cwd=d)
    fc_run([{"id": "file.newSequence", "params": {"name": "S", "width": 640, "height": 360, "fps": 29.97, "video": 3, "audio": 2}},
            {"id": "timeline.place", "params": {"item": 1, "track": "V1", "audioTrack": "A1", "frame": 30, "sourceIn": {"frame": 20}, "duration": {"frame": 30}}},
            {"id": "timeline.place", "params": {"item": 1, "track": "V1", "audioTrack": "A1", "frame": 60, "sourceIn": {"frame": 0}, "duration": {"frame": 30}}}], p, cwd=d)
    v1 = fc_json("inspect", "sequence", project=p, cwd=d)["video"][0]["items"]
    c1, c2 = v1[0]["clip"], v1[1]["clip"]
    rows = fc_run([{"id": "effects.setParam", "params": {"clip": c1, "effect": "motion", "param": "scale", "value": 150}},
                   {"id": "effects.apply", "params": {"clips": [c1], "effect": "gaussian_blur"}},
                   {"id": "clip.speedDuration", "params": {"clips": [c2], "speed": 200}},
                   {"id": "graphics.newText", "params": {"text": "TITLE", "track": 1, "time": TICKS, "seconds": 1}},
                   {"id": "captions.add", "params": {"text": "a caption", "seconds": 1.2, "durationSeconds": 1}}], p, cwd=d)
    assert all(r["ok"] for r in rows), rows
    xml = d / "m.xml"
    report = fc_json("exec", "file.exportInterchange", json.dumps({"format": "xml", "path": str(xml)}), project=p, cwd=d)["report"]
    e = d / "m.ecproj"
    warnings = ec_json("--empty", "--save-as", str(e), "exec", "file.importTimeline", "--params", json.dumps({"path": str(xml)}), cwd=d)["result"]["warnings"]
    layers = ec_json("--project", str(e), "exec", "comp.info", cwd=d)["layers"]
    pictures = sorted((l for l in layers if l["switches"]["video"]), key=lambda l: l["in"])
    sounds = [l for l in layers if l["switches"]["audio"] and not l["switches"]["video"]]
    assert len(pictures) == 2 and len(sounds) == 2
    trimmed, fast = pictures
    assert trimmed["in"] == pytest.approx(30 / NTSC, abs=1e-3) and trimmed["start"] == pytest.approx(10 / NTSC, abs=1e-3) and trimmed["out"] == pytest.approx(60 / NTSC, abs=1e-3)
    assert fast["stretch"] == 50.0 and fast["out"] - fast["in"] == pytest.approx(15 / NTSC, abs=1e-3)
    assert ec_json("--project", str(e), "get", "-", str(trimmed["id"]), "transform/scale", cwd=d)["value"][:2] == [150.0, 150.0]
    assert any("Gaussian Blur" in w for w in warnings) and not any("blur" in r.lower() or "effect" in r.lower() for r in report)
    assert any("TITLE" in w for w in warnings) and any("TITLE" in r for r in report)
    assert "caption" not in xml.read_text().lower()
    assert not any("caption" in m.lower() for m in warnings + report)


@needs_filmcraft
def test_14_an_overlay_render_carries_the_edits_sound_unless_audio_is_off(roundtrip):
    """SKILL.md › Where a picture is made: a comp that came through interchange holds the edit's sound, and `render` puts it in the file by default, so placing that render over the edit (`timeline.place` on a new track) overwrites the speech on A1; rendered with `--audio off` it carries no sound and A1 stays."""
    rt, d = roundtrip, roundtrip["dir"]
    e = overlay_project(rt, "t14")
    for name, extra in (("with_sound", []), ("silent", ["--audio", "off"])):
        ec("--project", str(e), "render", "--out", f"{name}.mov", "--format", "prores", "--prores", "4444", "--channels", "rgba", *extra, cwd=d)
    loud_file, silent_file = ff.probe(d / "with_sound.mov"), ff.probe(d / "silent.mov")
    assert len(loud_file.video) == 1 and len(loud_file.audio) == 1
    assert len(silent_file.video) == 1 and silent_file.audio == []
    loud = place_copy(rt, "t14_loud", d / "with_sound.mov", {"track": "new", "frame": 0})
    assert fc_tracks(loud, d)["A1"] == [("with_sound.mov", 0, 90)]
    quiet = place_copy(rt, "t14_quiet", d / "silent.mov", {"track": "new", "frame": 0})
    assert fc_tracks(quiet, d)["A1"] == [("src.mp4", 30, 90)]


@needs_filmcraft
def test_15_a_comp_render_lines_up_frame_for_frame_with_the_edit(roundtrip):
    """SKILL.md › Where a picture is made: a comp from interchange keeps the sequence's rate (30000/1001) and length, so its render placed at the sequence start, over the edit or in place of the clip, shows the same source frame at each sequence frame. Expected: sequence frame 45 is source frame 20 + (45 - 30) = 35."""
    rt, d = roundtrip, roundtrip["dir"]
    assert rt["comp"]["frameRate"] == pytest.approx(NTSC, abs=1e-6) and rt["comp"]["duration"] == pytest.approx(90 / NTSC, abs=1e-3)
    ec("--project", str(rt["ecproj"]), "render", "--out", "full.mov", "--format", "prores", cwd=d)
    t45 = f"{45 / NTSC:.6f}"
    for name, params in (("over", {"track": "new", "audioTrack": "new", "frame": 0}), ("instead", {"track": "V1", "audioTrack": "A1", "frame": 0})):
        q = place_copy(rt, f"t15_{name}", d / "full.mov", params)
        fc("render", "--seconds", t45, "--out", str(d / f"t15_{name}.png"), project=q, cwd=d)
        assert frame_index(d / f"t15_{name}.png") == 35, name
    assert fc_tracks(d / "t15_instead.fcproj", d)["V1"] == [("full.mov", 0, 90)]
    assert fc_tracks(d / "t15_over.fcproj", d)["V1"] == [("src.mp4", 30, 90)]   # over: the original is still under it


@needs_filmcraft
def test_16_a_soft_alpha_edge_composites_in_linear_light_without_a_fringe(roundtrip):
    """SKILL.md › Where a picture is made: a straight-alpha ProRes 4444 from EffectCraft placed in FilmCraft composites its soft, partly transparent edge exactly as linear light predicts from the file's own alpha and colour over the background FilmCraft drew, with no fringe; a gamma (browser or ffmpeg) blend of the same pixels would be darker by up to about 14 levels."""
    rt, d = roundtrip, roundtrip["dir"]
    e = overlay_project(rt, "t16")
    ec("--project", str(e), "render", "--out", "edge.mov", "--format", "prores", "--prores", "4444", "--channels", "rgba", "--audio", "off", cwd=d)
    t45 = f"{45 / NTSC:.6f}"
    fc("render", "--seconds", t45, "--out", str(d / "t16_base.png"), project=rt["fcproj"], cwd=d)
    q = place_copy(rt, "t16", d / "edge.mov", {"track": "new", "frame": 0})
    fc("render", "--seconds", t45, "--out", str(d / "t16_got.png"), project=q, cwd=d)
    ffmpeg("-i", str(d / "edge.mov"), "-vf", "select=eq(n\\,45)", "-frames:v", "1", "-pix_fmt", "rgba", str(d / "t16_ov.png"))
    ov, base, got = rgba(d / "t16_ov.png"), Image.open(d / "t16_base.png").convert("RGB"), Image.open(d / "t16_got.png").convert("RGB")
    worst_linear = worst_gamma = 0.0
    partial = 0
    for x in range(140, 200):   # across the box's left edge on its middle row
        r, _, _, a8 = ov.getpixel((x, 180))
        a, b = a8 / 255, base.getpixel((x, 180))[0]
        partial += 0 < a8 < 255
        g = got.getpixel((x, 180))[0]
        worst_linear = max(worst_linear, abs(g - srgb(a * lin(r) + (1 - a) * lin(b))))
        worst_gamma = max(worst_gamma, abs(g - (a * r + (1 - a) * b)))
    assert partial > 30
    assert worst_linear <= 2 and worst_gamma > 8, (worst_linear, worst_gamma)


def test_17_effectcraft_blends_layers_in_gamma_by_default(tmp_path):
    """SKILL.md › Where a picture is made: with a project's default settings EffectCraft blends a partly transparent layer over the layers below in gamma, so 50 % black and 50 % white over a grey 128 layer are 64 and 192 in its own frame, where FilmCraft's linear-light blend gives 92 and 205 (worked by hand: sRGB(0.5 x lin(128)) and sRGB(0.5 x lin(128) + 0.5)); `file.projectSettings {"blendLinear": true}` makes EffectCraft's layers agree with FilmCraft."""
    steps = [("comp.new", {"name": "C", "width": 200, "height": 100, "duration": 0.5}), ("layer.newSolid", {"color": "#808080", "width": 200, "height": 100}),
             ("layer.newSolid", {"color": "#000000", "width": 100, "height": 100}), ("layer.setTransform", {"prop": "position", "value": [50, 50]}), ("layer.setTransform", {"prop": "opacity", "value": 50}),
             ("layer.newSolid", {"color": "#ffffff", "width": 100, "height": 100}), ("layer.setTransform", {"prop": "position", "value": [150, 50]}), ("layer.setTransform", {"prop": "opacity", "value": 50})]
    gamma = new_project(tmp_path, "gamma", steps)
    linear = new_project(tmp_path, "linear", [("file.projectSettings", {"blendLinear": True}), *steps])
    for p in (gamma, linear):
        ec("--project", str(p), "render-frame", "--out", f"{p.stem}.png", cwd=tmp_path)
    g, l = Image.open(tmp_path / "gamma.png").convert("L"), Image.open(tmp_path / "linear.png").convert("L")
    assert g.getpixel((50, 50)) == pytest.approx(64, abs=2) and g.getpixel((150, 50)) == pytest.approx(192, abs=2)
    assert l.getpixel((50, 50)) == pytest.approx(92, abs=2) and l.getpixel((150, 50)) == pytest.approx(205, abs=2)


@needs_filmcraft
def test_18_hdr_footage_through_effectcraft_comes_back_in_other_colours(tmp_path):
    """SKILL.md › Where a picture is made: FilmCraft tone-maps HLG footage into its Rec. 709 sequence, while a default EffectCraft project shows the HLG code values as they are, so the same clip rendered by EffectCraft and put back in FilmCraft changes colour, without a warning. Control: an SDR clip with the same code values looks the same in both."""
    patch = "color=c=0x808080:size=160x90:rate=30:duration=1[a];color=c=0xC04020:size=160x90:rate=30:duration=1[b];[a][b]hstack"
    ffmpeg("-f", "lavfi", "-i", patch, "-c:v", "libx265", "-x265-params", "log-level=error:colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1", str(tmp_path / "hlg.mp4"))
    ffmpeg("-f", "lavfi", "-i", patch, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(tmp_path / "sdr.mp4"))

    def fc_frame(media: Path, name: str) -> tuple:
        p = tmp_path / f"{name}.fcproj"
        fc("--save-as", str(p), "import", str(media), cwd=tmp_path)
        fc("--save", "exec", "file.newSequenceFromClip", "items=[1]", project=p, cwd=tmp_path)
        fc("render", "--seconds", "0.5", "--out", str(tmp_path / f"{name}.png"), project=p, cwd=tmp_path)
        im = Image.open(tmp_path / f"{name}.png").convert("RGB")
        return im.getpixel((im.width // 4, im.height // 2)) + im.getpixel((3 * im.width // 4, im.height // 2))

    def far(a, b):
        return max(abs(x - y) for x, y in zip(a, b))

    for clip in ("hlg", "sdr"):
        e = tmp_path / f"{clip}.ecproj"
        ec("--empty", "--save-as", str(e), "run", "file.import", json.dumps({"paths": [str(tmp_path / f"{clip}.mp4")], "newComp": True}), cwd=tmp_path)
        ec("--project", str(e), "render", "--out", f"{clip}_ec.mov", "--format", "prores", cwd=tmp_path)
    assert far(fc_frame(tmp_path / "sdr.mp4", "sdr_orig"), fc_frame(tmp_path / "sdr_ec.mov", "sdr_back")) <= 4
    assert far(fc_frame(tmp_path / "hlg.mp4", "hlg_orig"), fc_frame(tmp_path / "hlg_ec.mov", "hlg_back")) >= 8


# -- Delivery ------------------------------------------------------------------------------------------------------------------

def test_19_a_direct_mp4_has_moov_at_the_end_and_effectcraft_cannot_set_loudness(tmp_path):
    """SKILL.md › Delivery: an H.264 MP4 rendered by EffectCraft puts `moov` after `mdat` (no fast start), and EffectCraft has no command that sets loudness, so a piece with sound gets its delivery loudness from a FilmCraft export."""
    p = new_project(tmp_path, "p", [("comp.new", {"name": "C", "width": 320, "height": 180, "duration": 1})])
    ec("--project", str(p), "render", "--comp", "C", "--out", "c.mp4", "--format", "h264", cwd=tmp_path)
    assert mp4.layout(tmp_path / "c.mp4").moov_first is False
    for word in ("loud", "lufs", "normaliz"):
        assert ec("commands", "--filter", word, cwd=tmp_path).stdout.strip() == "", word

"""SKILL.md names commands and flags that live elsewhere, and the FilmCraft facts name sentences that live here. Text cannot say when it went stale, so what it points at is checked: a sentence's meaning is not, only that what it names exists. Every check is a function of a text, so each is also run against a text built to break it."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

from support import CLI, FILMCRAFT, needs_filmcraft

REPO = Path(__file__).resolve().parents[2]
SKILL = (REPO / ".claude/skills/video/SKILL.md").read_text()
FACTS = REPO / "tests/filmcraft_facts/test_facts.py"
# File names and things that are not FilmCraft command ids but look like `word.word`.
NOT_COMMANDS = re.compile(r"\.(fcproj|jsonl|srt|mov|png|mp4|json|html|py|md)$|^(P|X|Y)\.")


def code_spans(text: str) -> list[str]:
    return re.findall(r"`([^`\n]+)`", text)


def help_of(*args: str) -> str:
    return subprocess.run([sys.executable, str(CLI), *args, "--help"], capture_output=True, text=True, timeout=60).stdout


def tools() -> set[str]:
    return set(re.findall(r"^    (\w+) {2,}", help_of(), flags=re.M))


def check_tool_flags(text: str, known: set[str], help_for) -> list[str]:
    """A span that starts with one of our tools names only flags that tool has."""
    out = []
    for span in code_spans(text):
        words = span.split()
        if words and words[0] in known:
            out += [f"`{span}`: {w} is not in {words[0]} --help" for w in words[1:] if w.startswith("--") and w != "--help" and not re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", help_for(words[0]))]
    return out


def check_tools_named_in_prose(text: str, known: set[str]) -> list[str]:
    """`<word> --help` points at a command, so the word has to be one."""
    return [f"`{w} --help` is not a command" for w in re.findall(r"`(\w+) --help`", text) if w not in known and w != "filmcraft-cli"]


def command_ids(text: str) -> set[str]:
    """Spans holding a dotted id such as `transcript.inspect`, with parameters or a wildcard family such as `timeline.*` left out."""
    ids = set()
    for span in code_spans(text):
        for token in re.findall(r"\b[a-zA-Z]+\.[a-zA-Z][a-zA-Z]*\b", span):
            if not NOT_COMMANDS.search(token) and not span.startswith(("/", "$", "cp ")):
                ids.add(token)
    return ids


def check_command_ids(ids: set[str], exists) -> list[str]:
    return [f"`{i}` is not a FilmCraft command" for i in sorted(ids) if not exists(i)]


def fact_sections(path: Path) -> list[tuple[str, str]]:
    """(test name, section) for every test whose docstring points at a SKILL.md section."""
    out = []
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            doc = ast.get_docstring(node) or ""
            out += [(node.name, m) for m in re.findall(r"SKILL\.md › ([^:,]+?)(?:[:,]| and `)", doc)]
    return out


def fact_helps(path: Path) -> list[tuple[str, str]]:
    out = []
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            out += [(node.name, m) for m in re.findall(r"`(\w+) --help`", ast.get_docstring(node) or "")]
    return out


def sections(text: str) -> set[str]:
    return set(re.findall(r"^## (.+)$", text, flags=re.M))


# -- the real text ----------------------------------------------------------------------------------------------------------

def test_every_tool_and_flag_the_skill_names_exists():
    known = tools()
    assert {"transcribe", "captions", "waveform", "doctor", "frames", "qc", "timeline", "graphic"} <= known
    assert check_tool_flags(SKILL, known, lambda t: help_of(t)) == []
    assert check_tools_named_in_prose(SKILL, known) == []


@needs_filmcraft
def test_every_filmcraft_command_the_skill_names_exists():
    def exists(i):
        return subprocess.run([FILMCRAFT, "describe", i], capture_output=True, text=True, timeout=60).returncode == 0
    ids = command_ids(SKILL)
    assert {"timeline.place", "transcript.removeFillers", "transcript.createCaptions"} <= ids
    assert check_command_ids(ids, exists) == []


def test_every_section_a_fact_names_is_in_the_skill():
    named = fact_sections(FACTS)
    assert len(named) >= 15
    assert [f"{t}: {s}" for t, s in named if s not in sections(SKILL)] == []


def test_every_help_a_fact_names_is_a_command():
    named = fact_helps(FACTS)
    assert len(named) >= 5
    known = tools()
    assert [f"{t}: {h}" for t, h in named if h not in known] == []


def test_the_skill_body_points_at_tools_rather_than_copying_their_values():
    """What a tool owns stays out: the provider's defaults and this skill's own numbers are in each --help."""
    for copied in ("elevenlabs/scribe-v2", "nvidia/nemotron", "--max-shift", "OPENROUTER_API_KEY", "42 characters", "16 units"):
        assert copied not in SKILL, copied


def test_the_skill_has_no_references_folder():
    assert not (REPO / ".claude/skills/video/references").exists()


def test_the_key_file_is_ignored_by_git():
    r = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", ".claude/skills/video/scripts/video/openrouter/.env"])
    assert r.returncode == 0


# -- each check against a text built to break it --------------------------------------------------------------------------------

def test_a_flag_a_tool_does_not_have_is_caught():
    found = check_tool_flags("use `waveform --no-such-flag X`", {"waveform"}, lambda t: "--at A-B --words FILE --out")
    assert found and "--no-such-flag" in found[0]


def test_a_flag_that_is_only_a_prefix_of_a_real_one_is_caught():
    assert check_tool_flags("`waveform --wor`", {"waveform"}, lambda t: "--words FILE")


def test_a_real_flag_passes():
    assert check_tool_flags("`waveform --words`", {"waveform"}, lambda t: "--at --words --out") == []


def test_a_help_for_a_missing_command_is_caught():
    assert check_tools_named_in_prose("read `nosuch --help` first", {"waveform"})


def test_a_command_id_that_does_not_exist_is_caught():
    ids = command_ids("then `transcript.nosuch` and `P.fcproj` and `timeline.*`")
    assert ids == {"transcript.nosuch"}
    assert check_command_ids(ids, lambda i: False) == ["`transcript.nosuch` is not a FilmCraft command"]


def test_a_fact_pointing_at_a_missing_section_is_caught(tmp_path):
    f = tmp_path / "t.py"
    f.write_text('def test_x():\n    """SKILL.md › No Such Section: a claim."""\n')
    assert fact_sections(f) == [("test_x", "No Such Section")]
    assert "No Such Section" not in sections(SKILL)

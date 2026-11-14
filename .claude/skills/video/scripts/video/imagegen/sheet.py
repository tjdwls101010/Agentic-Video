"""The contact sheet: one fixed-layout HTML page per folder, redrawn from the ledger after every write.

The layout is fixed so every folder reads the same way: the folder's path, then one section per name (its tries that came out, the user's notes on it), one row per request (its label and time, then its tries), each try with its caption, Claude's assessment and the user's notes, and the request's prompt, references and failures folded away. Clicking a picture enlarges it; ← and → step through every picture on the sheet, Esc closes. The page cannot fetch the ledger over file://, so every redraw also writes `.sheet-stamp.js`; an open tab loads that script every two seconds and reloads itself when the stamp changes, keeping its scroll position and waiting while a picture is enlarged. Pictures are linked by relative path, never inlined.
"""

from __future__ import annotations

import fcntl
import hashlib
import html
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote

from video import imageledger

SHEET = "contact-sheet.html"
STAMP = ".sheet-stamp.js"
LOCK = ".sheet.lock"

CSS = """
:root { color-scheme: light dark; --bg:#f7f6f3; --fg:#1d1b18; --muted:#6f685f; --line:#dedad3; --card:#fff; --accent:#a24a1c; --ok:#2e6b42; --warn:#986a10; --bad:#a1322b; }
@media (prefers-color-scheme: dark) { :root { --bg:#151412; --fg:#ebe7e1; --muted:#9c958b; --line:#33302b; --card:#1f1d1a; --accent:#e58a51; --ok:#80c49a; --warn:#d9ae5d; --bad:#e07d73; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 -apple-system, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif; }
.top { position:sticky; top:0; z-index:5; background:color-mix(in srgb, var(--bg) 94%, transparent); backdrop-filter:blur(6px); border-bottom:1px solid var(--line); padding:.6rem 1.25rem; }
.top h1 { font-size:1.05rem; margin:0; }
main { max-width:96rem; margin:0 auto; padding:1rem 1.25rem 5rem; }
.path { font-family:ui-monospace, Menlo, monospace; font-size:.72rem; color:var(--muted); word-break:break-all; }
.name { border-top:2px solid var(--line); padding:1.2rem 0 .4rem; }
.nhead { display:flex; flex-wrap:wrap; gap:.3rem .8rem; align-items:baseline; }
.nname { font-weight:700; font-size:1.2rem; } .nmeta { color:var(--muted); font-size:.82rem; }
.notes { font-size:.85rem; margin:.4rem 0 .6rem; padding-left:1.1rem; }
.at { color:var(--muted); font-size:.72rem; margin-left:.4rem; }
.request { padding:.9rem 0; border-top:1px dashed var(--line); }
.rhead { display:flex; flex-wrap:wrap; gap:.3rem .8rem; align-items:baseline; margin-bottom:.6rem; }
.rlabel { color:var(--accent); font-weight:600; } .rmeta { color:var(--muted); font-size:.82rem; }
.row { display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); gap:.8rem; }
figure { margin:0; background:var(--card); border:1px solid var(--line); border-radius:8px; overflow:hidden; }
figure.chosen { border-color:var(--accent); box-shadow:0 0 0 3px color-mix(in srgb, var(--accent) 45%, transparent); }
figure.unusable img { opacity:.6; }
figure img { display:block; width:100%; height:auto; cursor:zoom-in; background:repeating-conic-gradient(#ccc 0 25%, #fff 0 50%) 0 0/16px 16px; }
figure.pending { display:flex; align-items:center; justify-content:center; min-height:160px; color:var(--muted); font-size:.85rem; border-style:dashed; }
figcaption { padding:.4rem .55rem; font-size:.74rem; color:var(--muted); display:flex; flex-wrap:wrap; gap:.25rem .45rem; align-items:center; }
.judged { padding:0 .55rem .5rem; font-size:.8rem; }
.crit { margin:.2rem 0; padding:.4rem .6rem; border-left:3px solid var(--accent); background:color-mix(in srgb, var(--accent) 6%, transparent); white-space:pre-wrap; }
.judged ul { margin:.2rem 0; padding-left:1rem; }
.tag { border-radius:4px; padding:0 .3rem; background:var(--line); color:var(--fg); }
.tag.ok { background:color-mix(in srgb, var(--ok) 22%, transparent); color:var(--ok); }
.tag.warn { background:color-mix(in srgb, var(--warn) 22%, transparent); color:var(--warn); }
.tag.bad { background:color-mix(in srgb, var(--bad) 22%, transparent); color:var(--bad); }
details { margin-top:.5rem; } summary { cursor:pointer; color:var(--muted); font-size:.82rem; }
pre { white-space:pre-wrap; word-break:break-word; background:var(--card); border:1px solid var(--line); border-radius:6px; padding:.6rem .7rem; font-size:.8rem; }
.refs { grid-template-columns:repeat(auto-fill, minmax(130px, 170px)); margin-top:.4rem; }
.fails li { font-size:.8rem; color:var(--muted); margin:.2rem 0; }
.empty { color:var(--muted); }
dialog { border:none; padding:0; background:transparent; max-width:98vw; max-height:98vh; }
dialog::backdrop { background:rgba(0,0,0,.85); }
dialog img { max-width:98vw; max-height:92vh; cursor:zoom-out; display:block; margin:0 auto; background:repeating-conic-gradient(#888 0 25%, #bbb 0 50%) 0 0/24px 24px; }
dialog .cap { color:#eee; font:13px/1.4 ui-monospace, Menlo, monospace; text-align:center; padding:.4rem; }
dialog .nav { position:fixed; top:50%; transform:translateY(-50%); background:rgba(0,0,0,.4); color:#fff; border:none; font-size:2rem; padding:.4rem .8rem; cursor:pointer; border-radius:6px; }
dialog .prev { left:1vw; } dialog .next { right:1vw; }
"""

JS = """
const STAMP = "%(stamp)s", KEY = "imagegen-sheet:" + location.pathname;
const dlg = document.getElementById("zoom"), big = dlg.querySelector("img"), cap = dlg.querySelector(".cap");
const shots = Array.from(document.querySelectorAll("img[data-zoom]"));
let at = -1;
function show(i) { at = (i + shots.length) %% shots.length; big.src = shots[at].src; cap.textContent = (shots[at].dataset.name || shots[at].alt) + "  (" + (at + 1) + "/" + shots.length + ")"; }
shots.forEach((img, i) => img.addEventListener("click", () => { show(i); dlg.showModal(); }));
big.addEventListener("click", () => dlg.close());
dlg.querySelector(".prev").addEventListener("click", e => { e.stopPropagation(); show(at - 1); });
dlg.querySelector(".next").addEventListener("click", e => { e.stopPropagation(); show(at + 1); });
document.addEventListener("keydown", e => {
  if (!dlg.open) return;
  if (e.key === "ArrowRight") { e.preventDefault(); show(at + 1); }
  else if (e.key === "ArrowLeft") { e.preventDefault(); show(at - 1); }
});
function remember() { try { localStorage.setItem(KEY, String(window.scrollY)); } catch (e) {} }
function restore() { try { const y = localStorage.getItem(KEY); if (y !== null) window.scrollTo(0, Number(y)); } catch (e) {} }
restore(); window.addEventListener("load", restore);
window.addEventListener("scroll", () => { clearTimeout(window.__t); window.__t = setTimeout(remember, 150); });
window.addEventListener("beforeunload", remember);
let pending = false;
function poll() {
  const s = document.createElement("script");
  s.src = "%(stamp_file)s?" + Date.now();
  s.onload = () => { s.remove(); if (window.__sheetStamp && window.__sheetStamp !== STAMP) pending = true; maybeReload(); };
  s.onerror = () => s.remove();
  document.head.appendChild(s);
}
function maybeReload() { if (pending && !dlg.open) { remember(); location.reload(); } }
dlg.addEventListener("close", maybeReload);
setInterval(poll, 2000);
"""

UNUSABLE = {"prompt_altered": "Codex가 프롬프트를 바꿈", "interrupted": "중단됨 · 출처 미확인"}


def _e(value) -> str:
    return html.escape("" if value is None else str(value))


def _src(folder: Path, stored: str) -> str:
    return _e(quote(os.path.relpath(os.path.normpath(folder / stored), folder)))


def _img(folder: Path, stored: str, name: str, size: tuple | None = None, zoom: bool = True) -> str:
    # A known pixel size reserves the picture's space before it loads, so a restored scroll position lands where it was.
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    return f'<img src="{_src(folder, stored)}" alt="{_e(name)}" data-name="{_e(name)}"{dims} loading="lazy"{" data-zoom" if zoom else ""}>'


def _notes(notes: list[dict]) -> str:
    return "".join(f'<li>{_e(n["text"])}<span class="at">{_e(n["at"][:16].replace("T", " "))}</span></li>' for n in notes)


def _attempt(folder: Path, a: dict) -> str:
    if a["status"] == "running":
        return f'<figure class="pending"><span>{_e(a["id"])} · 생성 중</span></figure>'
    if not a.get("file"):
        return ""
    classes = ["chosen"] if a.get("chosen") else ["unusable"] if a["status"] != "ok" else []
    tags = [f'<span class="path">{_e(a["id"])}</span>']
    if a.get("chosen"):
        tags.append('<span class="tag ok">선택</span>')
    if a.get("w") and a.get("h"):
        tags.append(f'<span class="tag">{a["w"]}×{a["h"]}</span>')
    alpha = a.get("alpha")
    if alpha:
        tags.append(f'<span class="tag ok">투명 {alpha["transparent_share"]:.0%}</span>' if alpha["has_alpha"] else '<span class="tag bad">알파 없음</span>')
    verbatim = a.get("verbatim")
    if verbatim and verbatim != "exact":
        tags.append(f'<span class="tag warn">verbatim {_e(verbatim)}</span>')
    if a["status"] != "ok":
        tags.append(f'<span class="tag bad">{_e(a["status"])} · {_e(UNUSABLE.get(a["status"], ""))} · 고를 수 없음</span>')
    size = (a["w"], a["h"]) if a.get("w") and a.get("h") else None
    judged = ""
    if a.get("critique") or a.get("notes"):
        crit = f'<div class="crit">{_e(a["critique"])}</div>' if a.get("critique") else ""
        notes = f'<ul>{_notes(a["notes"])}</ul>' if a.get("notes") else ""
        judged = f'<div class="judged">{crit}{notes}</div>'
    return f'<figure class="{" ".join(classes)}">{_img(folder, a["file"], a["id"], size)}<figcaption>{"".join(tags)}</figcaption>{judged}</figure>'


def _request(folder: Path, req: dict) -> str:
    shown = [x for x in (_attempt(folder, a) for a in req["attempts"]) if x]
    failed = [a for a in req["attempts"] if a["status"] not in ("ok", "running") and not a.get("file")]
    label = f'<span class="rlabel">{_e(req["label"])}</span>' if req.get("label") else f'<span class="rlabel">요청 {req["r"]}</span>'
    meta = [_e(req["created"][:16].replace("T", " ")), f'{len(req["attempts"])}회 시도']
    if req["transparent"]:
        meta.append("투명 배경 요청")
    parts = [f'<div class="request" id="r-{_e(req["r"])}"><div class="rhead">{label}<span class="rmeta">{" · ".join(meta)}</span></div>']
    parts.append(f'<div class="row">{"".join(shown)}</div>' if shown else '<div class="empty">보여 줄 그림 없음</div>')
    parts.append(f'<details><summary>프롬프트 ({len(req["prompt"])}자)</summary><pre>{_e(req["prompt"])}</pre></details>')
    if req["refs"]:
        thumbs = "".join(f'<figure>{_img(folder, r["path"], Path(r["path"]).name, zoom=False)}<figcaption><span class="path">{_e(r["path"])}</span></figcaption></figure>' for r in req["refs"])
        parts.append(f'<details><summary>참조 {len(req["refs"])}장</summary><div class="row refs">{thumbs}</div></details>')
    if failed:
        items = []
        for a in failed:
            d = a.get("detail") or {}
            said = [str(x) for x in (d.get("code"), f"stage={d['stage']}" if d.get("stage") else None, ",".join(d.get("categories") or []) or None, d.get("message") or d.get("note")) if x]
            items.append(f'<li><span class="tag bad">{_e(a["status"])}</span> {_e(a["id"])} {_e(" · ".join(said))}</li>')
        parts.append(f'<details><summary>실패 {len(failed)}건</summary><ul class="fails">{"".join(items)}</ul></details>')
    parts.append("</div>")
    return "".join(parts)


def _name(folder: Path, entry: dict) -> str:
    attempts = [a for r in entry["requests"] for a in r["attempts"]]
    ok = sum(a["status"] == "ok" for a in attempts)
    chosen = [a["id"] for a in attempts if a.get("chosen")]
    meta = f"성공 {ok} / 시도 {len(attempts)}" + (f" · 선택 {', '.join(chosen)}" if chosen else "")
    notes = f'<ul class="notes">{_notes(entry["notes"])}</ul>' if entry["notes"] else ""
    body = "".join(_request(folder, r) for r in reversed(entry["requests"]))
    return f'<section class="name" id="n-{_e(entry["name"])}"><div class="nhead"><span class="nname">{_e(entry["name"])}</span><span class="nmeta">{_e(meta)}</span></div>{notes}{body}</section>'


def render(doc: dict, folder: Path, stamp: str) -> str:
    sections = "".join(_name(folder, e) for e in doc["names"]) or '<p class="empty">아직 만든 그림이 없다</p>'
    script = JS % {"stamp": stamp, "stamp_file": STAMP}
    return ("<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f'<title>{_e(folder.parent.name + "/" + folder.name)} · 생성 그림</title><style>{CSS}</style></head><body>'
            f'<header class="top"><h1>생성 그림 · {_e(folder.name)}</h1><div class="path">{_e(folder)}/</div></header><main>{sections}</main>'
            f'<dialog id="zoom"><button class="nav prev" aria-label="이전">‹</button><img alt=""><div class="cap"></div><button class="nav next" aria-label="다음">›</button></dialog><script>{script}</script></body></html>')


def _atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def publish(folder: Path) -> Path:
    """Redraw the sheet from the ledger as it is now. The ledger is read after the sheet's lock is taken, so a redraw from an older ledger never lands after a newer one; the ledger's own lock is taken and released inside, never held around the drawing."""
    out = folder / SHEET
    with open(folder / LOCK, "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            doc = imageledger.read(folder)
            stamp = hashlib.sha1(render(doc, folder, "").encode()).hexdigest()[:12]
            _atomic(out, render(doc, folder, stamp))
            _atomic(folder / STAMP, f'window.__sheetStamp = "{stamp}";\n')
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return out


def open_once(folder: Path, path: Path) -> None:
    """Open the sheet in the browser if this folder's sheet never was, and record that only when `open` succeeded, so a session that cannot open it (a sandbox) leaves the next one to try."""
    if "sheet_opened" in imageledger.read(folder):
        return
    try:
        r = subprocess.run(["open", str(path)], capture_output=True, text=True, timeout=20)
        ok, why = r.returncode == 0, (r.stderr or "").strip() or f"exit {r.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        ok, why = False, str(exc)
    if ok:
        imageledger.mark_opened(folder)
    else:
        print(f"the contact sheet could not be opened ({why}); it is at {path}", file=sys.stderr, flush=True)

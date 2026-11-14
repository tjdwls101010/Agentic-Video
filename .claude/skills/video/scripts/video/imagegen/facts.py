"""What a placed picture is (its size, and its alpha when transparency was asked for or came anyway), and placing a file under a name that must not exist yet."""

from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from pathlib import Path


def measure(path: Path, transparent: bool) -> dict:
    from PIL import Image

    with Image.open(path) as im:
        w, h = im.size
        out: dict = {"w": w, "h": h}
        has_alpha = "A" in im.getbands() or "transparency" in im.info
        # A transparent request is answered either way; an opaque one is reported only when alpha came anyway (a prompt or a reference can bring it).
        if transparent or has_alpha:
            share = 0.0
            if has_alpha:
                hist = im.convert("RGBA").getchannel("A").histogram()
                share = round(hist[0] / (w * h), 3)
            out["alpha"] = {"has_alpha": has_alpha, "transparent_share": share}
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Taken(Exception):
    """The destination already exists; it was left alone."""


def place_new(src: Path, dest: Path) -> None:
    """Copy `src` to `dest`, which must not exist yet: written beside it under a hidden temporary name, then given its real name by a hard link, so `dest` never holds a half-written file and a file already there is never replaced. On a volume without hard links an exclusive-create copy stands in, and a partial copy is removed."""
    tmp = dest.with_name(f".{dest.stem}.{uuid.uuid4().hex[:8]}{dest.suffix}")
    try:
        shutil.copyfile(src, tmp)
        try:
            os.link(tmp, dest)
        except FileExistsError:
            raise Taken(str(dest)) from None
        except OSError:
            try:
                with open(dest, "xb") as out, open(tmp, "rb") as data:
                    try:
                        shutil.copyfileobj(data, out)
                    except BaseException:
                        out.close()
                        dest.unlink(missing_ok=True)
                        raise
            except FileExistsError:
                raise Taken(str(dest)) from None
    finally:
        tmp.unlink(missing_ok=True)

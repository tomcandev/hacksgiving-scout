"""Build the demo video from real artefacts: a terminal transcript and screenshots.

    python3 tools/make_demo.py evidence/run.log evidence/issue-*.png -o evidence/demo.mp4

Frames are drawn with Pillow and stitched with ffmpeg. No screen recording, so
nothing else on the desktop ends up in the video.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 720, 30
BG, FG, DIM, ACC = (17, 17, 27), (230, 230, 240), (140, 140, 160), (167, 139, 250)
MONO = "/System/Library/Fonts/Menlo.ttc"
SANS = "/System/Library/Fonts/HelveticaNeue.ttc"


def font(path, size):
    return ImageFont.truetype(path, size)


class Reel:
    def __init__(self, tmp: Path):
        self.tmp, self.n = tmp, 0

    def hold(self, img: Image.Image, seconds: float):
        p = self.tmp / f"still{self.n:05d}.png"
        img.save(p)
        for _ in range(int(seconds * FPS)):
            (self.tmp / f"f{self.n:06d}.png").symlink_to(p)
            self.n += 1


def card(title: str, sub: str = "", foot: str = "") -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((W // 2, H // 2 - 40), title, font=font(SANS, 54), fill=FG, anchor="mm")
    if sub:
        d.text((W // 2, H // 2 + 30), sub, font=font(SANS, 28), fill=ACC, anchor="mm")
    if foot:
        d.text((W // 2, H - 60), foot, font=font(SANS, 22), fill=DIM, anchor="mm")
    return img


def terminal(lines: list[str], caption: str) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((30, 30, W - 30, H - 70), 14, fill=(28, 28, 40))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((52 + i * 24, 48, 66 + i * 24, 62), fill=c)
    f = font(MONO, 17)
    y = 84
    for ln in lines[-28:]:
        color = ACC if ln.startswith("$") else FG
        d.text((54, y), ln[:118], font=f, fill=color)
        y += 21
    d.text((W // 2, H - 36), caption, font=font(SANS, 24), fill=DIM, anchor="mm")
    return img


def screenshot_pages(path: Path, caption: str) -> list[Image.Image]:
    shot = Image.open(path).convert("RGB")
    scale = min((W - 80) / shot.width, (H - 110) / shot.height)
    shot = shot.resize((W - 80, int(shot.height * scale)))
    view_h = H - 110
    pages = []
    top = 0
    while True:
        img = Image.new("RGB", (W, H), BG)
        img.paste(shot.crop((0, top, shot.width, min(top + view_h, shot.height))), ((W - shot.width) // 2, 30))
        ImageDraw.Draw(img).text((W // 2, H - 36), caption, font=font(SANS, 24), fill=DIM, anchor="mm")
        pages.append(img)
        if top + view_h >= shot.height:
            return pages
        top += int(view_h * 0.8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("shots", nargs="*")
    ap.add_argument("-o", "--out", default="evidence/demo.mp4")
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp())
    reel = Reel(tmp)
    reel.hold(card("hacksgiving-scout",
                   "A personal hackathon + startup-program scout on a Fly.io Sprite",
                   "Fly.io Hacksgiving 2026 · github.com/tomcandev/hacksgiving-scout"), 5)

    blocks = Path(a.log).read_text().split("\n## ")
    for block in blocks:
        head, _, body = block.partition("\n")
        caption, lines = head.lstrip("# ").strip(), body.rstrip().splitlines()
        shown: list[str] = []
        step = max(1, len(lines) // 24)
        for i in range(0, len(lines), step):
            shown = lines[: i + step]
            reel.hold(terminal(shown, caption), 0.45)
        reel.hold(terminal(lines, caption), 6)

    for s in a.shots:
        name = Path(s).stem.split("-", 2)[-1].replace("-", " ").capitalize()
        pages = screenshot_pages(Path(s), name)
        for pg in pages:
            reel.hold(pg, 5 if len(pages) > 1 else 9)

    reel.hold(card("Runs every morning at 8:00 Perth",
                   "Devpost + rules pages · startup programs · GitHub connector · Weird Uncle",
                   "github.com/tomcandev/hacksgiving-scout"), 4)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%06d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", a.out], check=True)
    shutil.rmtree(tmp)
    print(f"{a.out}: {reel.n / FPS:.0f}s")


if __name__ == "__main__":
    main()

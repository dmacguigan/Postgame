"""Draws the PG scoreboard tile and writes icon.svg, Postgame.ico, Postgame.icns."""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "..", "sleeper_recap", "static")
FIELD = "#061229"
AMBER = "#ffb000"
DIM = "#1b2f55"

# seven segment layout on a 100x100 tile: letters are 22 wide, 46 tall
SEG = {
    "a": (0, 0, 22, 5), "b": (17, 0, 22, 25), "c": (17, 21, 22, 46),
    "d": (0, 41, 22, 46), "e": (0, 21, 5, 46), "f": (0, 0, 5, 25), "g": (0, 21, 22, 25),
}
LETTERS = {"P": "abefg", "G": "acdef"}
ORIGINS = {"P": (22, 27), "G": (56, 27)}


def rects():
    out = []
    for letter, (ox, oy) in ORIGINS.items():
        for seg, (x0, y0, x1, y1) in SEG.items():
            out.append((ox + x0, oy + y0, ox + x1, oy + y1, seg in LETTERS[letter]))
    return out


def svg():
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">',
        f'<rect width="100" height="100" rx="18" fill="{FIELD}"/>',
        f'<rect x="6" y="6" width="88" height="88" rx="13" fill="none" stroke="{AMBER}" stroke-width="3"/>',
    ]
    for x0, y0, x1, y1, on in rects():
        parts.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="{AMBER if on else DIM}"/>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def png(size):
    scale = size / 100
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(18 * scale)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=FIELD)
    d.rounded_rectangle((6 * scale, 6 * scale, 94 * scale, 94 * scale), radius=int(13 * scale), outline=AMBER, width=max(1, int(3 * scale)))
    for x0, y0, x1, y1, on in rects():
        d.rectangle((x0 * scale, y0 * scale, x1 * scale - 1, y1 * scale - 1), fill=AMBER if on else DIM)
    return img


if __name__ == "__main__":
    with open(os.path.join(STATIC, "icon.svg"), "w", encoding="utf-8") as f:
        f.write(svg())
    base = png(1024)
    base.save(os.path.join(HERE, "Postgame.png"))
    base.save(os.path.join(HERE, "Postgame.ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    base.save(os.path.join(HERE, "Postgame.icns"))
    print("wrote icon.svg, Postgame.png, Postgame.ico, Postgame.icns")

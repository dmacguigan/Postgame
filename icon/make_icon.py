"""Writes the Postgame speech bubble icon: icon.svg, Postgame.png, Postgame.ico.
Needs: pip install cairosvg pillow"""
import io
import os

import cairosvg
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "..", "sleeper_recap", "static")

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" rx="18" fill="#061229"/>
<path d="M22 22h56a8 8 0 0 1 8 8v34a8 8 0 0 1-8 8H46l-14 14v-14h-10a8 8 0 0 1-8-8V30a8 8 0 0 1 8-8z" fill="#f4f6fb"/>
<g transform="translate(50 46) scale(0.72) translate(-50 -50) rotate(-35 50 50)">
<ellipse cx="50" cy="50" rx="33" ry="19" fill="#ffb000"/>
<line x1="36" y1="50" x2="64" y2="50" stroke="#061229" stroke-width="3.5" stroke-linecap="round"/>
<line x1="42" y1="45" x2="42" y2="55" stroke="#061229" stroke-width="3.5" stroke-linecap="round"/>
<line x1="50" y1="45" x2="50" y2="55" stroke="#061229" stroke-width="3.5" stroke-linecap="round"/>
<line x1="58" y1="45" x2="58" y2="55" stroke="#061229" stroke-width="3.5" stroke-linecap="round"/>
</g>
</svg>
"""

if __name__ == "__main__":
    with open(os.path.join(STATIC, "icon.svg"), "w", encoding="utf-8") as f:
        f.write(SVG)
    png = cairosvg.svg2png(bytestring=SVG.encode(), output_width=1024, output_height=1024)
    base = Image.open(io.BytesIO(png)).convert("RGBA")
    base.save(os.path.join(HERE, "Postgame.png"))
    base.save(os.path.join(HERE, "Postgame.ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote icon.svg, Postgame.png, Postgame.ico")

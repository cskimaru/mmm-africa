#!/usr/bin/env python3
"""Paint the soft watercolour backgrounds for each colour scheme: a savanna wash with acacia trees,
distant hills and small gold stars ("We have seen his star", Matthew 2:2).

Writes one SVG per scheme. Render each to services/web/app/static/art/<key>.webp at 1800x1200 so
visitors' phones never compute the watercolour filters:

    python3 scripts/paint_backgrounds.py <out_dir>
    (then open each SVG in a browser at 1800x1200, screenshot, save as WebP quality 80;
     scripts/render_backgrounds.cjs does this with Playwright)
"""

import math
import random
import sys
from pathlib import Path

W, H = 1800, 1200

# key: paper, wash colours (top-left, top-right, bottom), hill colour, tree colour, star colour
SCHEMES = {
    "sunrise": ("#fdf8f2", ["#f9d9b8", "#f6c7b0", "#d9ece6"], "#e9cfae", "#b98c62", "#e2a93b"),
    "coast": ("#f7fbfb", ["#cdeef0", "#f6e3c8", "#d4e8f6"], "#cfe3dc", "#7fa39a", "#d9a441"),
    "highlands": ("#f8fbf4", ["#dcefd2", "#f4e7b8", "#cfe8e0"], "#c9ddb9", "#7d9a6a", "#d8a636"),
    "evening": ("#fbf8fc", ["#e3d8f4", "#f7d6cf", "#d6e0f5"], "#ddd0e8", "#9d86ad", "#dcaa48"),
}

FILTERS = """
<defs>
  <filter id="wash" x="-30%" y="-30%" width="160%" height="160%">
    <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="3" seed="11" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="90"/>
    <feGaussianBlur stdDeviation="38"/>
  </filter>
  <filter id="wc" x="-20%" y="-20%" width="140%" height="140%">
    <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="4" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="7"/>
    <feGaussianBlur stdDeviation="1.1"/>
  </filter>
  <filter id="soft"><feGaussianBlur stdDeviation="6"/></filter>
</defs>
"""


def star(cx: float, cy: float, r: float) -> str:
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return " ".join(pts)


def acacia(x: float, base: float, h: float, colour: str, rnd: random.Random, flip: bool = False) -> str:
    """A flat-topped acacia: a forked trunk and a wide, layered umbrella canopy."""
    s = -1 if flip else 1
    top = base - h
    trunk = (
        f'<path d="M{x:.0f},{base:.0f} C{x + s * 6:.0f},{base - h * 0.4:.0f} {x - s * 4:.0f},{base - h * 0.62:.0f} '
        f'{x + s * h * 0.18:.0f},{top + h * 0.12:.0f}" stroke="{colour}" stroke-width="{h * 0.045:.1f}" '
        f'fill="none" stroke-linecap="round"/>'
        f'<path d="M{x + s * 2:.0f},{base - h * 0.45:.0f} C{x - s * h * 0.1:.0f},{base - h * 0.62:.0f} '
        f'{x - s * h * 0.22:.0f},{top + h * 0.2:.0f} {x - s * h * 0.3:.0f},{top + h * 0.14:.0f}" stroke="{colour}" '
        f'stroke-width="{h * 0.03:.1f}" fill="none" stroke-linecap="round"/>'
    )
    canopy = []
    for layer in range(3):
        w = h * (1.05 - layer * 0.18)
        cy = top + h * (0.1 - layer * 0.07)
        for _ in range(7):
            cx = x + s * h * 0.02 + rnd.uniform(-w / 2, w / 2)
            rx = rnd.uniform(w * 0.14, w * 0.24)
            ry = rnd.uniform(h * 0.05, h * 0.08)
            canopy.append(
                f'<ellipse cx="{cx:.0f}" cy="{cy + rnd.uniform(-h * 0.03, h * 0.03):.0f}" rx="{rx:.0f}" '
                f'ry="{ry:.0f}" fill="{colour}" opacity="{0.35 + layer * 0.12:.2f}"/>'
            )
    return f'<g filter="url(#wc)">{trunk}{"".join(canopy)}</g>'


def grass(x0: float, x1: float, base: float, colour: str, rnd: random.Random) -> str:
    blades = []
    x = x0
    while x < x1:
        h = rnd.uniform(14, 40)
        lean = rnd.uniform(-10, 10)
        blades.append(
            f'<path d="M{x:.0f},{base:.0f} q{lean / 2:.0f},{-h / 2:.0f} {lean:.0f},{-h:.0f}" stroke="{colour}" '
            f'stroke-width="2" fill="none" opacity="{rnd.uniform(0.25, 0.5):.2f}" stroke-linecap="round"/>'
        )
        x += rnd.uniform(5, 14)
    return f'<g filter="url(#wc)">{"".join(blades)}</g>'


def paint(key: str) -> str:
    paper, washes, hill, tree, gold = SCHEMES[key]
    rnd = random.Random(key)  # noqa: S311 - artwork, not security
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FILTERS]
    parts.append(f'<rect width="{W}" height="{H}" fill="{paper}"/>')
    # Broad watercolour washes
    parts.append('<g filter="url(#wash)" opacity="0.8">')
    parts.append(f'<ellipse cx="260" cy="230" rx="560" ry="380" fill="{washes[0]}"/>')
    parts.append(f'<ellipse cx="1560" cy="260" rx="520" ry="360" fill="{washes[1]}"/>')
    parts.append(f'<ellipse cx="900" cy="1180" rx="900" ry="320" fill="{washes[2]}"/>')
    parts.append(f'<ellipse cx="1650" cy="980" rx="380" ry="260" fill="{washes[0]}"/>')
    parts.append("</g>")
    # A low sun behind the right-hand trees
    parts.append(f'<circle cx="1490" cy="300" r="120" fill="{gold}" opacity="0.16" filter="url(#soft)"/>')
    # Distant hills along the bottom
    parts.append(
        f'<path filter="url(#wc)" d="M0,1030 C250,960 420,1000 640,975 C860,950 1000,1010 1240,985 '
        f'C1460,962 1620,995 1800,970 L1800,1200 L0,1200 Z" fill="{hill}" opacity="0.55"/>'
    )
    parts.append(
        f'<path filter="url(#wc)" d="M0,1090 C300,1060 520,1100 820,1078 C1120,1056 1400,1096 1800,1070 '
        f'L1800,1200 L0,1200 Z" fill="{hill}" opacity="0.7"/>'
    )
    # Acacias: a pair bottom-left, one bottom-right, a small far one
    parts.append(acacia(170, 1095, 250, tree, rnd))
    parts.append(acacia(330, 1088, 160, tree, rnd, flip=True))
    parts.append(acacia(1610, 1080, 230, tree, rnd, flip=True))
    parts.append(acacia(1100, 1060, 70, tree, rnd))
    parts.append(grass(0, 520, 1110, tree, rnd))
    parts.append(grass(1400, 1800, 1100, tree, rnd))
    # Small gold stars across the sky, one brighter
    for _ in range(14):
        cx, cy = rnd.uniform(500, 1350), rnd.uniform(60, 520)
        parts.append(f'<polygon points="{star(cx, cy, rnd.uniform(4, 9))}" fill="{gold}" opacity="0.45"/>')
    parts.append(f'<circle cx="1180" cy="150" r="34" fill="{gold}" opacity="0.18" filter="url(#soft)"/>')
    parts.append(f'<polygon points="{star(1180, 150, 22)}" fill="{gold}" opacity="0.75"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "art-svg")
    out.mkdir(parents=True, exist_ok=True)
    for key in SCHEMES:
        (out / f"{key}.svg").write_text(paint(key))
        print(f"wrote {out / key}.svg")


if __name__ == "__main__":
    main()

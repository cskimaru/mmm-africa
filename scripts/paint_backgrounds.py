#!/usr/bin/env python3
"""Paint the soft watercolour backgrounds for each colour scheme: an East African savanna with umbrella thorn
acacias, golden grass, distant hills and small gold stars ("We have seen his star", Matthew 2:2).

Writes one SVG per scheme. Render each to services/web/app/static/art/<key>.webp at 1800x1200 so
visitors' phones never compute the watercolour filters:

    python3 scripts/paint_backgrounds.py <out_dir>
    node scripts/render_backgrounds.cjs <out_dir>     (then convert the PNGs to WebP, quality 80)
"""

import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

W, H = 1800, 1200


@dataclass(frozen=True)
class Scheme:
    paper: str
    washes: tuple[str, str, str]  # top-left, top-right, bottom
    hill: str
    far_hill: str
    canopy: tuple[str, str, str]  # shade, leaf, sunlit leaf
    bark: str
    grass: tuple[str, str, str]  # dry, darker, sunlit
    haze: str  # distant trees
    gold: str


SCHEMES = {
    "sunrise": Scheme(
        "#fdf8f2",
        ("#f9d9b8", "#f6c7b0", "#e3eedf"),
        "#e2c99f",
        "#ecd9bd",
        ("#3f4a22", "#5f6d2e", "#8e9a48"),
        "#4a3424",
        ("#c99a4e", "#a87c3a", "#e2bd78"),
        "#b9a98a",
        "#e2a93b",
    ),
    "coast": Scheme(
        "#f7fbfb",
        ("#cdeef0", "#f6e3c8", "#dcebe4"),
        "#d6d2ad",
        "#e3e6d4",
        ("#2c4a38", "#436b4c", "#6e9a64"),
        "#3e352b",
        ("#c8b27a", "#a8935e", "#e0cc94"),
        "#9fb3a6",
        "#d9a441",
    ),
    "highlands": Scheme(
        "#f8fbf4",
        ("#dcefd2", "#f4e7b8", "#d6eadb"),
        "#c5d6a6",
        "#dde6cc",
        ("#29452a", "#3f6a35", "#6f9a4c"),
        "#40342a",
        ("#a9b765", "#879a4c", "#cbd58a"),
        "#9fb092",
        "#d8a636",
    ),
    "evening": Scheme(
        "#fbf8fc",
        ("#e3d8f4", "#f7d6cf", "#e2dcef"),
        "#d6c4d8",
        "#e6dbe9",
        ("#352c46", "#4a3f5e", "#665a7d"),
        "#2b2436",
        ("#a68aa2", "#8a7189", "#c4a9b9"),
        "#b3a5c0",
        "#dcaa48",
    ),
}

FILTERS = """
<defs>
  <filter id="wash" x="-30%" y="-30%" width="160%" height="160%">
    <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="3" seed="11" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="90"/>
    <feGaussianBlur stdDeviation="38"/>
  </filter>
  <filter id="leaf" x="-10%" y="-30%" width="120%" height="160%">
    <feTurbulence type="fractalNoise" baseFrequency="0.08" numOctaves="2" seed="3" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="5"/>
    <feGaussianBlur stdDeviation="0.6"/>
  </filter>
  <filter id="bark" x="-20%" y="-5%" width="140%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="2" seed="8" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="2.5"/>
  </filter>
  <filter id="hill" x="-5%" y="-20%" width="110%" height="140%">
    <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" seed="5" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="10"/>
    <feGaussianBlur stdDeviation="1.5"/>
  </filter>
  <filter id="haze"><feGaussianBlur stdDeviation="1.2"/></filter>
  <filter id="soft"><feGaussianBlur stdDeviation="6"/></filter>
  <filter id="shadow"><feGaussianBlur stdDeviation="9"/></filter>
</defs>
"""


def star(cx: float, cy: float, r: float) -> str:
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return " ".join(pts)


def limb(x0: float, y0: float, x1: float, y1: float, w0: float, w1: float, bend: float) -> str:
    """A tapering branch from (x0, y0) to (x1, y1), as a filled shape so it narrows naturally."""
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1
    nx, ny = -dy / length, dx / length
    cx, cy = (x0 + x1) / 2 + nx * bend, (y0 + y1) / 2 + ny * bend
    return (
        f"M{x0 + nx * w0 / 2:.1f},{y0 + ny * w0 / 2:.1f} "
        f"Q{cx + nx * (w0 + w1) / 4:.1f},{cy + ny * (w0 + w1) / 4:.1f} {x1 + nx * w1 / 2:.1f},{y1 + ny * w1 / 2:.1f} "
        f"L{x1 - nx * w1 / 2:.1f},{y1 - ny * w1 / 2:.1f} "
        f"Q{cx - nx * (w0 + w1) / 4:.1f},{cy - ny * (w0 + w1) / 4:.1f} {x0 - nx * w0 / 2:.1f},{y0 - ny * w0 / 2:.1f} Z"
    )


def acacia(x: float, base: float, h: float, s: Scheme, rnd: random.Random, lean: float = 0.0) -> str:
    """An umbrella thorn acacia (Vachellia tortilis): a short trunk that forks into several limbs fanning out to a
    wide, thin, flat-topped crown made of layered leaf pads, dark underneath and lit on top."""
    width = h * rnd.uniform(1.7, 2.1)
    crown_y = base - h  # top of the crown
    crown_th = h * rnd.uniform(0.16, 0.22)  # crown thickness
    under = crown_y + crown_th * 0.85  # where limbs meet the crown
    cx = x + lean * h
    trunk_w = max(3.0, h * 0.065)
    fork_y = base - h * rnd.uniform(0.32, 0.42)
    fork_x = x + lean * h * 0.35
    out: list[str] = []

    # Soft shadow on the ground
    out.append(
        f'<ellipse cx="{cx:.0f}" cy="{base + 4:.0f}" rx="{width * 0.42:.0f}" ry="{h * 0.045:.0f}" '
        f'fill="{s.canopy[0]}" opacity="0.22" filter="url(#shadow)"/>'
    )

    # Trunk and limbs
    wood = [limb(x, base + 2, fork_x, fork_y, trunk_w * 1.15, trunk_w * 0.9, rnd.uniform(-6, 6))]
    n_limbs = rnd.randint(4, 6)
    tips = []
    for i in range(n_limbs):
        t = (i + 0.5) / n_limbs
        tx = cx - width * 0.42 + width * 0.84 * t + rnd.uniform(-width * 0.04, width * 0.04)
        ty = under + rnd.uniform(-crown_th * 0.15, crown_th * 0.1)
        w0 = trunk_w * rnd.uniform(0.42, 0.6)
        wood.append(limb(fork_x, fork_y, tx, ty, w0, max(1.2, w0 * 0.35), rnd.uniform(-h * 0.08, h * 0.08)))
        tips.append((tx, ty))
        # A smaller side branch from part-way along each limb
        mx, my = fork_x + (tx - fork_x) * 0.55, fork_y + (ty - fork_y) * 0.55
        sx = mx + (tx - fork_x) * rnd.uniform(0.25, 0.5) + rnd.uniform(-width * 0.06, width * 0.06)
        sy = under + rnd.uniform(-crown_th * 0.1, crown_th * 0.15)
        wood.append(limb(mx, my, sx, sy, w0 * 0.45, 1.0, rnd.uniform(-h * 0.04, h * 0.04)))
        tips.append((sx, sy))
    out.append(f'<g filter="url(#bark)" fill="{s.bark}">' + "".join(f'<path d="{d}"/>' for d in wood) + "</g>")

    # Crown: several overlapping pads, each a flattened cloud of small leaf clusters
    # Each pad sits at its own height, so the crown reads as uneven tiers with sky showing between them.
    pads = []
    for tx, _ty in tips:
        pads.append(
            (
                tx + rnd.uniform(-width * 0.05, width * 0.05),
                rnd.uniform(width * 0.09, width * 0.16),
                rnd.uniform(-crown_th * 0.35, crown_th * 0.3),
            )
        )
    pads.append((cx, width * 0.2, -crown_th * 0.15))
    pads.append((cx + rnd.uniform(-width * 0.15, width * 0.15), width * 0.12, -crown_th * 0.45))

    def crown_layer(
        colour: str, dy: float, height: float, size: tuple[float, float], density: float, alpha: str
    ) -> str:
        dots = []
        for px, half, pad_dy in pads:
            n = int(half * density)
            for _ in range(n):
                u = rnd.uniform(-1, 1)
                # Flat top, ragged thinning ends and a soft underside
                edge = 1 - u * u
                if rnd.random() > 0.35 + 0.65 * edge:
                    continue
                local_h = height * math.sqrt(max(0.0, edge)) ** 0.6
                dx = px + u * half
                dy_ = (
                    crown_y
                    + pad_dy
                    + dy
                    + rnd.uniform(0, local_h)
                    - (rnd.uniform(0, height * 0.5) if rnd.random() < 0.08 else 0)
                )
                r = rnd.uniform(*size)
                dots.append(f'<ellipse cx="{dx:.1f}" cy="{dy_:.1f}" rx="{r * 1.5:.1f}" ry="{r:.1f}"/>')
        return f'<g filter="url(#leaf)" fill="{colour}" opacity="{alpha}">{"".join(dots)}</g>'

    k = h / 250
    out.append(crown_layer(s.canopy[0], crown_th * 0.35, crown_th * 0.65, (4 * k + 1, 9 * k + 1.5), 0.9, "0.92"))
    out.append(crown_layer(s.canopy[1], crown_th * 0.12, crown_th * 0.55, (3.5 * k + 1, 8 * k + 1.5), 0.85, "0.9"))
    out.append(crown_layer(s.canopy[2], 0, crown_th * 0.28, (2.5 * k + 0.8, 5.5 * k + 1), 0.6, "0.75"))
    return "<g>" + "".join(out) + "</g>"


def far_tree(x: float, base: float, h: float, colour: str, rnd: random.Random) -> str:
    """A distant acacia: a simple silhouette softened by the haze."""
    width = h * rnd.uniform(1.6, 2.0)
    top = base - h
    trunk = limb(x, base, x + rnd.uniform(-2, 2), top + h * 0.2, max(1.2, h * 0.07), 0.8, rnd.uniform(-2, 2))
    crown = (
        f"M{x - width / 2:.1f},{top + h * 0.18:.1f} "
        f"Q{x - width * 0.3:.1f},{top - h * 0.02:.1f} {x:.1f},{top:.1f} "
        f"Q{x + width * 0.3:.1f},{top - h * 0.02:.1f} {x + width / 2:.1f},{top + h * 0.18:.1f} "
        f"Q{x:.1f},{top + h * 0.3:.1f} {x - width / 2:.1f},{top + h * 0.18:.1f} Z"
    )
    return f'<g fill="{colour}" opacity="0.7" filter="url(#haze)"><path d="{trunk}"/><path d="{crown}"/></g>'


def grass(x0: float, x1: float, base: float, s: Scheme, rnd: random.Random, tall: float = 1.0) -> str:
    """Dry savanna grass: dense tufts of thin, curving blades in two or three tones."""
    blades = []
    x = x0
    while x < x1:
        tuft = rnd.randint(4, 9)
        for _ in range(tuft):
            h = rnd.uniform(12, 46) * tall
            lean = rnd.uniform(-14, 14)
            colour = rnd.choice(s.grass)
            bx = x + rnd.uniform(-5, 5)
            by = base + rnd.uniform(-3, 6)
            blades.append(
                f'<path d="M{bx:.1f},{by:.1f} q{lean * 0.3:.1f},{-h * 0.6:.1f} {lean:.1f},{-h:.1f}" stroke="{colour}" '
                f'stroke-width="{rnd.uniform(1.1, 2.2):.1f}" fill="none" opacity="{rnd.uniform(0.45, 0.85):.2f}" '
                f'stroke-linecap="round"/>'
            )
        x += rnd.uniform(9, 22)
    return f'<g filter="url(#leaf)">{"".join(blades)}</g>'


def paint(key: str) -> str:
    s = SCHEMES[key]
    rnd = random.Random(key)  # noqa: S311 - artwork, not security
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FILTERS]
    parts.append(f'<rect width="{W}" height="{H}" fill="{s.paper}"/>')
    # Broad watercolour washes in the sky
    parts.append('<g filter="url(#wash)" opacity="0.8">')
    parts.append(f'<ellipse cx="260" cy="230" rx="560" ry="380" fill="{s.washes[0]}"/>')
    parts.append(f'<ellipse cx="1560" cy="260" rx="520" ry="360" fill="{s.washes[1]}"/>')
    parts.append(f'<ellipse cx="900" cy="1180" rx="900" ry="320" fill="{s.washes[2]}"/>')
    parts.append(f'<ellipse cx="1650" cy="980" rx="380" ry="260" fill="{s.washes[0]}"/>')
    parts.append("</g>")
    # A low sun behind the right-hand trees
    parts.append(f'<circle cx="1490" cy="330" r="150" fill="{s.gold}" opacity="0.12" filter="url(#shadow)"/>')
    parts.append(f'<circle cx="1490" cy="330" r="85" fill="{s.gold}" opacity="0.10" filter="url(#soft)"/>')
    # Far hills, then the plain
    parts.append(
        f'<path filter="url(#hill)" d="M0,1005 C180,965 330,985 520,968 C700,952 860,990 1060,972 '
        f'C1260,955 1450,985 1620,962 C1700,952 1760,958 1800,955 L1800,1200 L0,1200 Z" fill="{s.far_hill}" opacity="0.85"/>'
    )
    # Distant acacias on the horizon
    for fx, fh in ((640, 26), (700, 18), (930, 30), (1200, 22), (1265, 15), (1450, 24)):
        parts.append(far_tree(fx, 1000 + rnd.uniform(-6, 4), fh, s.haze, rnd))
    parts.append(
        f'<path filter="url(#hill)" d="M0,1050 C260,1030 520,1062 820,1045 C1120,1028 1420,1058 1800,1038 '
        f'L1800,1200 L0,1200 Z" fill="{s.hill}" opacity="0.9"/>'
    )
    parts.append(grass(560, 1300, 1050, s, rnd, tall=0.45))
    # Foreground acacias: a pair bottom-left, a lone tree bottom-right, a smaller one in the middle distance
    parts.append(acacia(1110, 1046, 82, s, rnd, lean=0.05))
    parts.append(acacia(330, 1100, 165, s, rnd, lean=0.12))
    parts.append(acacia(165, 1112, 255, s, rnd, lean=-0.06))
    parts.append(acacia(1615, 1102, 235, s, rnd, lean=0.08))
    parts.append(grass(0, 560, 1112, s, rnd))
    parts.append(grass(1380, 1800, 1104, s, rnd))
    # Small gold stars across the sky, one brighter
    for _ in range(14):
        cx, cy = rnd.uniform(500, 1350), rnd.uniform(60, 520)
        parts.append(f'<polygon points="{star(cx, cy, rnd.uniform(4, 9))}" fill="{s.gold}" opacity="0.45"/>')
    parts.append(f'<circle cx="1180" cy="150" r="34" fill="{s.gold}" opacity="0.18" filter="url(#soft)"/>')
    parts.append(f'<polygon points="{star(1180, 150, 22)}" fill="{s.gold}" opacity="0.75"/>')
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

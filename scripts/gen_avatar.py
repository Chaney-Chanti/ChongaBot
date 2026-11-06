# ruff: noqa  (SVG-drawing scripts: long path strings are clearer unwrapped)
"""Generate assets/avatar.svg: a knight of Chonga standing in the snow.

Run: python3 scripts/gen_avatar.py
Render: uv run --no-project --with cairosvg python -c "import cairosvg; cairosvg.svg2png(
    url='assets/avatar.svg', write_to='assets/avatar.png', output_width=1024, output_height=1024)"
"""

import random
from pathlib import Path

random.seed(11)
out: list[str] = []
w = out.append

w("""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <radialGradient id="bg" cx="38%" cy="35%" r="80%">
      <stop offset="0" stop-color="#4f7472"/>
      <stop offset="0.5" stop-color="#2a4344"/>
      <stop offset="1" stop-color="#0d1718"/>
    </radialGradient>
    <radialGradient id="fog">
      <stop offset="0" stop-color="#9cc2bd" stop-opacity="0.35"/>
      <stop offset="1" stop-color="#9cc2bd" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vignette" cx="50%" cy="45%" r="62%">
      <stop offset="0.6" stop-color="#000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.75"/>
    </radialGradient>
    <radialGradient id="flake">
      <stop offset="0" stop-color="#eaf7f5" stop-opacity="1"/>
      <stop offset="0.5" stop-color="#eaf7f5" stop-opacity="0.6"/>
      <stop offset="1" stop-color="#eaf7f5" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="steel" x1="0" y1="0" x2="1" y2="0.3">
      <stop offset="0" stop-color="#8fa6a3"/>
      <stop offset="0.35" stop-color="#4f6463"/>
      <stop offset="0.7" stop-color="#2a3837"/>
      <stop offset="1" stop-color="#151e1e"/>
    </linearGradient>
    <linearGradient id="steelDark" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#5d7372"/>
      <stop offset="1" stop-color="#121a1a"/>
    </linearGradient>
    <linearGradient id="cloak" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1d2a2b"/>
      <stop offset="1" stop-color="#0a1011"/>
    </linearGradient>
    <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#d6ece8" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#d6ece8" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#d6ece8" stop-opacity="0"/>
    </linearGradient>
    <pattern id="mail" width="14" height="12" patternUnits="userSpaceOnUse">
      <rect width="14" height="12" fill="#1b2525"/>
      <circle cx="7" cy="6" r="4.5" fill="none" stroke="#61797770" stroke-width="2.2"/>
      <circle cx="0" cy="0" r="4.5" fill="none" stroke="#61797770" stroke-width="2.2"/>
      <circle cx="14" cy="0" r="4.5" fill="none" stroke="#61797770" stroke-width="2.2"/>
      <circle cx="0" cy="12" r="4.5" fill="none" stroke="#61797770" stroke-width="2.2"/>
      <circle cx="14" cy="12" r="4.5" fill="none" stroke="#61797770" stroke-width="2.2"/>
    </pattern>
  </defs>
  <rect width="1024" height="1024" fill="url(#bg)"/>
""")

# drifting fog
for x, y, rx, ry in [
    (250, 300, 380, 260),
    (820, 200, 300, 220),
    (150, 800, 320, 200),
    (900, 750, 260, 240),
    (520, 120, 420, 160),
]:
    w(f'  <ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="url(#fog)"/>')


def snow(count: int, rmin: float, rmax: float, omin: float, omax: float) -> None:
    for _ in range(count):
        x, y = random.uniform(0, 1024), random.uniform(0, 1024)
        r = random.uniform(rmin, rmax)
        rot = random.uniform(-40, 40)
        w(
            f'  <ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.1f}" ry="{r * random.uniform(0.5, 1):.1f}" '
            f'transform="rotate({rot:.0f} {x:.0f} {y:.0f})" fill="url(#flake)" opacity="{random.uniform(omin, omax):.2f}"/>'
        )


# far snow, behind the knight
snow(320, 2, 5, 0.3, 0.7)

# cloak, falling behind and around the shoulders
w("""  <path d="M330 560 Q170 600 120 760 Q90 900 110 1024 L914 1024 Q940 880 900 760 Q850 610 700 560 Z" fill="url(#cloak)"/>
  <path d="M330 560 Q220 610 190 760 Q170 880 200 1024" fill="none" stroke="#3f5757" stroke-width="5" opacity="0.6"/>
  <path d="M260 700 Q230 850 260 1024" fill="none" stroke="#000" stroke-width="10" opacity="0.35"/>
  <path d="M820 700 Q860 850 830 1024" fill="none" stroke="#000" stroke-width="10" opacity="0.35"/>""")

# sword hilt over the right shoulder
w("""  <g>
    <path d="M708 640 L782 420" stroke="#1a1410" stroke-width="30" stroke-linecap="round"/>
    <path d="M708 640 L782 420" stroke="#4a3a2c" stroke-width="20" stroke-linecap="round"/>
    <path d="M715 590 L740 520 M728 560 L752 488 M742 520 L766 452" stroke="#2a201a" stroke-width="5"/>
    <path d="M640 600 L790 670" stroke="url(#steelDark)" stroke-width="22" stroke-linecap="round"/>
    <circle cx="792" cy="392" r="34" fill="url(#steel)" stroke="#0d1414" stroke-width="5"/>
    <circle cx="782" cy="382" r="11" fill="#c8dcd9" opacity="0.5"/>
  </g>""")

# chainmail neck and body under the plate
w("""  <path d="M400 540 L624 540 L680 680 L344 680 Z" fill="url(#mail)"/>
  <path d="M400 540 L624 540 L680 680 L344 680 Z" fill="url(#steelDark)" opacity="0.35"/>""")

# breastplate
w("""  <path d="M330 690 Q512 640 694 690 L720 1024 L304 1024 Z" fill="url(#steel)" stroke="#0d1414" stroke-width="6"/>
  <path d="M512 660 L512 1024" stroke="#0d1414" stroke-width="5" opacity="0.7"/>
  <path d="M505 662 L505 1024" stroke="#c7dcd8" stroke-width="3" opacity="0.4"/>
  <path d="M340 760 Q512 720 684 760" fill="none" stroke="#0d1414" stroke-width="5" opacity="0.6"/>
  <path d="M340 755 Q512 715 684 755" fill="none" stroke="#c7dcd8" stroke-width="2" opacity="0.3"/>
  <path d="M440 820 Q512 790 584 820 Q575 900 512 940 Q449 900 440 820 Z" fill="none" stroke="#0d1414" stroke-width="4" opacity="0.5"/>""")
# rivets
for x, y in [(350, 712), (380, 704), (644, 704), (674, 712), (350, 790), (674, 790)]:
    w(f'  <circle cx="{x}" cy="{y}" r="6" fill="#9ab1ae" stroke="#0d1414" stroke-width="2"/>')

# pauldrons: layered plates on each shoulder
for side in (-1, 1):
    cx = 512 + side * 215
    for i, (dy, rx, ry) in enumerate([(70, 175, 120), (30, 165, 115), (-10, 150, 105)]):
        y = 650 + dy
        w(
            f'  <path d="M{cx - rx} {y + 20} Q{cx - rx * 0.9} {y - ry} {cx} {y - ry} '
            f'Q{cx + rx * 0.9} {y - ry} {cx + rx} {y + 20} Q{cx} {y - ry * 0.25} {cx - rx} {y + 20} Z" '
            f'fill="url(#{"steel" if side < 0 else "steelDark"})" stroke="#0d1414" stroke-width="6"/>'
        )
        w(
            f'  <path d="M{cx - rx * 0.7} {y - ry * 0.55} Q{cx} {y - ry * 1.02} {cx + rx * 0.5} {y - ry * 0.75}" '
            f'fill="none" stroke="#d6ece8" stroke-width="3" opacity="{0.45 if side < 0 else 0.2}"/>'
        )
    for k in (-1, 0, 1):
        w(
            f'  <circle cx="{cx + k * 55}" cy="{560 + abs(k) * 18}" r="6" fill="#9ab1ae" stroke="#0d1414" stroke-width="2"/>'
        )

# great helm
helm = "M512 140 C600 190 655 290 652 420 L640 565 Q512 615 384 565 L372 420 C369 290 424 190 512 140 Z"
w(f'  <path d="{helm}" fill="url(#steel)" stroke="#0a1010" stroke-width="7"/>')
# shading on the right half
w(
    '  <path d="M512 140 C600 190 655 290 652 420 L640 565 Q580 590 512 595 Z" fill="#000" opacity="0.28"/>'
)
# central ridge
w('  <path d="M512 145 L512 595" stroke="#0a1010" stroke-width="6"/>')
w('  <path d="M505 150 L505 590" stroke="#d6ece8" stroke-width="4" opacity="0.5"/>')
# visor plate
w(
    '  <path d="M382 400 Q512 360 642 400 L636 560 Q512 608 388 560 Z" fill="url(#steel)" stroke="#0a1010" stroke-width="6"/>'
)
w('  <path d="M512 370 L512 600 L636 560 L642 400 Q580 378 512 370 Z" fill="#000" opacity="0.3"/>')
w('  <path d="M512 370 L512 600" stroke="#0a1010" stroke-width="6"/>')
w('  <path d="M506 375 L506 596" stroke="#d6ece8" stroke-width="3" opacity="0.5"/>')
# eye slits, angled into a frown
w('  <path d="M400 432 L494 450 L494 474 L404 458 Z" fill="#050808"/>')
w('  <path d="M624 432 L530 450 L530 474 L620 458 Z" fill="#050808"/>')
# a faint cold glow in the eyes
w('  <ellipse cx="455" cy="456" rx="16" ry="5" fill="#9fe8e0" opacity="0.35"/>')
w('  <ellipse cx="569" cy="456" rx="16" ry="5" fill="#9fe8e0" opacity="0.35"/>')
# breathing holes
for row in range(3):
    for col in range(3):
        x, y = 555 + col * 22, 510 + row * 18
        w(f'  <circle cx="{x}" cy="{y}" r="4.5" fill="#050808"/>')
# rim light on the left edge of the helm
w(
    '  <path d="M505 150 C430 195 378 285 378 420 L388 560" fill="none" stroke="#d6ece8" stroke-width="5" opacity="0.4"/>'
)
# scratches and wear
for _ in range(14):
    x, y = random.uniform(410, 620), random.uniform(220, 560)
    dx, dy = random.uniform(-26, 26), random.uniform(-10, 10)
    w(
        f'  <path d="M{x:.0f} {y:.0f} l{dx:.0f} {dy:.0f}" stroke="#d6ece8" stroke-width="1.5" opacity="0.3"/>'
    )
# snow settled on the shoulders and helm
w('  <path d="M440 210 Q512 160 584 210 Q512 195 440 210 Z" fill="#e6f4f2" opacity="0.6"/>')
w('  <path d="M270 545 Q330 520 400 552 Q330 540 270 560 Z" fill="#e6f4f2" opacity="0.55"/>')
w(
    '  <path d="M624 552 Q700 520 760 545 L760 560 Q700 540 624 552 Z" fill="#e6f4f2" opacity="0.4"/>'
)

# near snow, in front of the knight: bigger, softer flakes
snow(110, 3.5, 9, 0.5, 0.95)
snow(18, 12, 22, 0.25, 0.5)

w('  <rect width="1024" height="1024" fill="url(#vignette)"/>')
w("</svg>")
Path("assets/avatar.svg").write_text("\n".join(out) + "\n")

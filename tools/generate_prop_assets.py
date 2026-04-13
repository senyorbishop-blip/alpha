#!/usr/bin/env python3
"""
tools/generate_prop_assets.py
=============================
Generates the built-in SVG prop and marker assets for the fantasy_props and
world_markers packs, then writes/updates client/static/assets/manifest.json.

Usage:
    python tools/generate_prop_assets.py [--output-dir client/static/assets]

The script is idempotent: re-running it regenerates only the SVG files and
rebuilds the manifest sections for the two managed packs; user-uploaded entries
are untouched because they live in the separate user_manifest.json.

Design rules applied to every SVG
----------------------------------
- 128 × 128 viewBox, transparent background
- Top-down / isometric-hint perspective
- Warm parchment / amber palette (matches the app's --gold / --parchment CSS vars)
- Strong readable silhouette at 32 px (thumbnail size)
- No more than 3 flat fill colours + 1 stroke colour per icon
- Drop shadow via a subtle <filter> to lift props off the floor
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Canvas / palette constants
# ---------------------------------------------------------------------------

W = H = 128  # SVG viewBox dimension

# Colour palette (warm fantasy)
C_BG       = "none"            # transparent
C_STROKE   = "#2a1f0e"         # deep walnut outline
C_WOOD     = "#8b5c2a"         # warm oak
C_WOOD_LT  = "#c28a4e"         # light oak highlight
C_WOOD_DK  = "#5a3614"         # dark oak shadow
C_STONE    = "#7a7060"         # weathered stone
C_STONE_LT = "#b0a898"         # stone highlight
C_IRON     = "#4a4a55"         # dark iron
C_IRON_LT  = "#8888a0"         # iron highlight
C_GOLD     = "#cfa14a"         # gold / treasure
C_GOLD_LT  = "#ffe08a"         # bright gold
C_LEATHER  = "#9b6644"         # worn leather
C_ROPE     = "#c8a060"         # rope / twine
C_RED      = "#c0392b"         # blood / danger
C_FIRE     = "#f08030"         # torch / flame
C_FIRE_LT  = "#ffe05a"         # bright flame
C_GREEN    = "#3a7a3a"         # foliage / plants
C_TEAL     = "#2a6a6a"         # water / magic
C_MAGIC    = "#8060c0"         # arcane / purple
C_MAGIC_LT = "#c0a0f0"         # arcane highlight
C_PARCHMT  = "#e8d8b0"         # paper / scroll
C_BONE     = "#d4c89e"         # bone / ivory
SW         = 2                 # default stroke-width

SHADOW_FILTER = """\
  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="1" dy="2" stdDeviation="2" flood-color="#0d0900" flood-opacity="0.5"/>
    </filter>
  </defs>"""


def _svg(body: str, extra_defs: str = "") -> str:
    defs_block = SHADOW_FILTER if not extra_defs else SHADOW_FILTER + "\n" + extra_defs
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}">\n'
        f'{defs_block}\n'
        f'<g filter="url(#shadow)">\n{body}\n</g>\n</svg>\n'
    )


def _rect(x, y, w, h, fill, rx=0, stroke=C_STROKE, sw=SW) -> str:
    r = f' rx="{rx}"' if rx else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{r}/>'


def _circle(cx, cy, r, fill, stroke=C_STROKE, sw=SW) -> str:
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def _poly(points: list[tuple], fill, stroke=C_STROKE, sw=SW) -> str:
    pts = " ".join(f"{x},{y}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def _path(d: str, fill="none", stroke=C_STROKE, sw=SW) -> str:
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def _line(x1, y1, x2, y2, stroke=C_STROKE, sw=SW) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"/>'


# ---------------------------------------------------------------------------
# Individual prop drawers
# ---------------------------------------------------------------------------

def _barrel() -> str:
    body = [
        # body
        _rect(28, 30, 72, 68, C_WOOD, rx=12),
        # hoops
        _rect(22, 48, 84, 10, C_IRON, rx=3),
        _rect(22, 70, 84, 10, C_IRON, rx=3),
        # lid
        _rect(28, 24, 72, 18, C_WOOD_LT, rx=5),
        # highlight
        _rect(36, 30, 14, 50, C_WOOD_LT, rx=4, stroke="none"),
    ]
    return _svg("\n".join(body))


def _crate() -> str:
    body = [
        _rect(22, 22, 84, 84, C_WOOD, rx=4),
        # cross braces
        _line(22, 64, 106, 64, C_WOOD_DK, 3),
        _line(64, 22, 64, 106, C_WOOD_DK, 3),
        # corner reinforcements
        _rect(22, 22, 18, 18, C_IRON, rx=2),
        _rect(88, 22, 18, 18, C_IRON, rx=2),
        _rect(22, 88, 18, 18, C_IRON, rx=2),
        _rect(88, 88, 18, 18, C_IRON, rx=2),
        # lid highlight
        _rect(30, 30, 68, 24, C_WOOD_LT, rx=3, stroke="none"),
    ]
    return _svg("\n".join(body))


def _chest() -> str:
    body = [
        # lid (top)
        _rect(18, 14, 92, 36, C_WOOD, rx=8),
        # lid arch highlight
        _rect(26, 16, 76, 20, C_WOOD_LT, rx=6, stroke="none"),
        # body
        _rect(18, 48, 92, 54, C_WOOD, rx=4),
        # hinge strip
        _rect(18, 46, 92, 8, C_IRON, rx=2),
        # clasp
        _rect(52, 50, 24, 18, C_GOLD, rx=3),
        _circle(64, 59, 5, C_GOLD_LT),
    ]
    return _svg("\n".join(body))


def _table() -> str:
    body = [
        # tabletop (isometric hint - wide trapezoid)
        _poly([(18, 38), (110, 38), (106, 62), (22, 62)], C_WOOD_LT),
        _rect(18, 38, 92, 4, C_WOOD_LT, stroke="none"),
        # frame edge
        _poly([(18, 38), (110, 38), (110, 45), (18, 45)], C_WOOD),
        # legs
        _rect(24, 60, 10, 42, C_WOOD_DK, rx=2),
        _rect(94, 60, 10, 42, C_WOOD_DK, rx=2),
    ]
    return _svg("\n".join(body))


def _chair() -> str:
    body = [
        # backrest
        _rect(30, 16, 68, 42, C_WOOD, rx=6),
        _rect(38, 20, 52, 28, C_WOOD_LT, rx=4, stroke="none"),
        # seat
        _rect(24, 54, 80, 18, C_WOOD, rx=4),
        _rect(30, 56, 68, 10, C_WOOD_LT, rx=3, stroke="none"),
        # legs
        _rect(28, 72, 10, 38, C_WOOD_DK, rx=2),
        _rect(90, 72, 10, 38, C_WOOD_DK, rx=2),
    ]
    return _svg("\n".join(body))


def _bookshelf() -> str:
    body = [
        # frame
        _rect(16, 12, 96, 104, C_WOOD_DK, rx=3),
        # shelves
        _rect(20, 12, 88, 8, C_WOOD, rx=2),
        _rect(20, 44, 88, 8, C_WOOD, rx=2),
        _rect(20, 76, 88, 8, C_WOOD, rx=2),
        _rect(20, 108, 88, 8, C_WOOD, rx=2),
        # books (row 1)
        _rect(22, 18, 12, 24, "#7b3f3f"),
        _rect(36, 20, 10, 22, C_GOLD),
        _rect(48, 16, 14, 26, "#3f5a7b"),
        _rect(64, 18, 10, 24, "#3a7a3a"),
        _rect(76, 20, 12, 22, C_LEATHER),
        _rect(90, 17, 14, 25, "#6a3a7a"),
        # books (row 2)
        _rect(22, 50, 10, 24, "#3a7a3a"),
        _rect(34, 52, 14, 22, C_WOOD_LT),
        _rect(50, 50, 10, 24, C_RED),
        _rect(62, 52, 12, 22, "#3f5a7b"),
        _rect(76, 50, 10, 24, C_GOLD),
        _rect(88, 50, 18, 24, C_LEATHER),
    ]
    return _svg("\n".join(body))


def _altar() -> str:
    body = [
        # base plinth
        _rect(20, 76, 88, 36, C_STONE, rx=4),
        _rect(24, 72, 80, 12, C_STONE_LT, rx=3),
        # altar top
        _rect(16, 52, 96, 28, C_STONE_LT, rx=5),
        # carved front panel
        _rect(30, 56, 68, 20, C_STONE, rx=3),
        # symbol on front
        _circle(64, 66, 7, C_GOLD_LT, stroke=C_GOLD),
        # candles
        _rect(26, 42, 6, 16, C_PARCHMT, rx=2),
        _rect(96, 42, 6, 16, C_PARCHMT, rx=2),
        # flames
        _poly([(26, 42), (32, 42), (29, 34)], C_FIRE_LT, stroke="none"),
        _poly([(96, 42), (102, 42), (99, 34)], C_FIRE_LT, stroke="none"),
    ]
    return _svg("\n".join(body))


def _ritual_circle() -> str:
    extra_defs = """\
  <radialGradient id="rg" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#8060c0" stop-opacity="0.4"/>
    <stop offset="100%" stop-color="#8060c0" stop-opacity="0"/>
  </radialGradient>"""
    body = [
        _circle(64, 64, 54, "url(#rg)", stroke="none"),
        _circle(64, 64, 52, "none", stroke=C_MAGIC, sw=2),
        _circle(64, 64, 38, "none", stroke=C_MAGIC_LT, sw=1),
        # pentagram
        _path("M64 20 L76 54 L110 54 L83 75 L93 110 L64 89 L35 110 L45 75 L18 54 L52 54 Z",
              fill=C_MAGIC, stroke=C_MAGIC_LT, sw=1),
        # central rune
        _circle(64, 64, 10, C_MAGIC, stroke=C_MAGIC_LT, sw=2),
    ]
    return _svg("\n".join(body), extra_defs)


def _torch() -> str:
    body = [
        # handle
        _rect(58, 52, 12, 56, C_WOOD, rx=3),
        # flame wrap
        _rect(52, 40, 24, 20, C_LEATHER, rx=3),
        # flame layers
        _poly([(64, 10), (76, 42), (64, 36), (52, 42)], C_FIRE, stroke="none"),
        _poly([(64, 10), (72, 38), (64, 32)], C_FIRE_LT, stroke="none"),
        # glow ring
        _circle(64, 32, 18, "none", stroke=C_FIRE, sw=1),
    ]
    return _svg("\n".join(body))


def _brazier() -> str:
    body = [
        # bowl base
        _poly([(34, 84), (94, 84), (84, 100), (44, 100)], C_IRON),
        # bowl
        _poly([(26, 54), (102, 54), (94, 84), (34, 84)], C_IRON_LT),
        # flame
        _poly([(64, 20), (80, 56), (64, 46), (48, 56)], C_FIRE, stroke="none"),
        _poly([(64, 20), (74, 50), (64, 42)], C_FIRE_LT, stroke="none"),
        # coals glow
        _rect(34, 74, 60, 10, "#d05020", rx=3, stroke="none"),
        # tripod legs
        _line(34, 84, 20, 112, C_IRON_LT, 3),
        _line(94, 84, 108, 112, C_IRON_LT, 3),
        _line(64, 84, 64, 112, C_IRON_LT, 3),
    ]
    return _svg("\n".join(body))


def _door() -> str:
    body = [
        # door frame (stone)
        _rect(18, 14, 92, 100, C_STONE, rx=4),
        # door panel
        _rect(26, 18, 76, 92, C_WOOD, rx=3),
        # upper panel
        _rect(32, 24, 64, 34, C_WOOD_LT, rx=3),
        # lower panel
        _rect(32, 64, 64, 38, C_WOOD_LT, rx=3),
        # knob
        _circle(82, 82, 6, C_GOLD, stroke=C_STROKE),
        # arch keystone
        _poly([(64, 10), (74, 18), (54, 18)], C_STONE_LT),
    ]
    return _svg("\n".join(body))


def _campfire() -> str:
    body = [
        # log circle
        _poly([(40, 88), (88, 88), (96, 100), (32, 100)], C_WOOD_DK),
        _poly([(36, 76), (92, 76), (88, 88), (40, 88)], C_WOOD),
        # crossed logs
        _rect(34, 70, 60, 12, C_WOOD, rx=4),
        _poly([(44, 60), (84, 60), (88, 74), (40, 74)], C_WOOD_DK),
        # flames
        _poly([(64, 16), (82, 58), (64, 50), (46, 58)], C_FIRE, stroke="none"),
        _poly([(64, 16), (76, 52), (64, 44)], C_FIRE_LT, stroke="none"),
        _poly([(56, 26), (68, 60), (56, 54)], C_FIRE_LT, stroke="none"),
    ]
    return _svg("\n".join(body))


def _well() -> str:
    body = [
        # stone ring
        _circle(64, 72, 40, C_STONE_LT, stroke=C_STROKE, sw=SW),
        _circle(64, 72, 28, C_TEAL, stroke=C_STONE, sw=SW),
        # posts
        _rect(28, 28, 8, 44, C_WOOD_DK, rx=2),
        _rect(92, 28, 8, 44, C_WOOD_DK, rx=2),
        # crossbar
        _rect(22, 26, 84, 10, C_WOOD, rx=3),
        # bucket rope
        _line(64, 36, 64, 60, C_ROPE, 2),
        _rect(56, 60, 16, 14, C_WOOD_LT, rx=2),
    ]
    return _svg("\n".join(body))


def _fountain() -> str:
    extra_defs = """\
  <radialGradient id="water" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#6abcdc" stop-opacity="0.9"/>
    <stop offset="100%" stop-color="#2a6a9a" stop-opacity="1"/>
  </radialGradient>"""
    body = [
        # outer basin rim
        _circle(64, 82, 44, C_STONE_LT),
        _circle(64, 82, 38, "url(#water)", stroke="none"),
        # water ripples
        _circle(64, 82, 24, "none", stroke="#8ad4f0", sw=1),
        _circle(64, 82, 14, "none", stroke="#8ad4f0", sw=1),
        # centre spout pillar
        _rect(58, 40, 12, 48, C_STONE, rx=3),
        # top basin
        _circle(64, 44, 20, C_STONE_LT),
        _circle(64, 44, 14, "url(#water)", stroke="none"),
        # water arc
        _path("M64 40 Q88 20 90 60", fill="none", stroke="#8ad4f0", sw=2),
        _path("M64 40 Q40 20 38 60", fill="none", stroke="#8ad4f0", sw=2),
    ]
    return _svg("\n".join(body), extra_defs)


def _shrine() -> str:
    body = [
        # base
        _rect(28, 80, 72, 32, C_STONE, rx=4),
        # body
        _rect(36, 44, 56, 40, C_STONE_LT, rx=4),
        # arch top
        _path("M36 64 L36 52 Q64 30 92 52 L92 64 Z", fill=C_STONE, stroke=C_STROKE, sw=SW),
        # idol / rune
        _circle(64, 64, 12, C_GOLD, stroke=C_GOLD_LT, sw=2),
        _circle(64, 64, 5, C_GOLD_LT, stroke="none"),
        # incense smoke
        _path("M52 42 Q48 30 52 20", fill="none", stroke="#c0c0e0", sw=1),
        _path("M76 42 Q80 30 76 20", fill="none", stroke="#c0c0e0", sw=1),
    ]
    return _svg("\n".join(body))


def _bones() -> str:
    body = [
        # scattered skull
        _circle(46, 52, 18, C_BONE),
        # eye sockets
        _circle(40, 50, 5, C_STONE),
        _circle(52, 50, 5, C_STONE),
        # jaw
        _rect(38, 62, 16, 6, C_BONE, rx=2),
        # long bone 1
        _rect(64, 38, 10, 52, C_BONE, rx=4),
        _circle(69, 36, 8, C_BONE),
        _circle(69, 92, 8, C_BONE),
        # long bone 2
        _path("M 86 36 L 100 86", fill="none", stroke=C_BONE, sw=8),
        _circle(93, 36, 8, C_BONE),
        _circle(93, 88, 8, C_BONE),
    ]
    return _svg("\n".join(body))


def _rubble() -> str:
    body = [
        # rock pile
        _poly([(20, 90), (50, 60), (80, 66), (110, 88), (100, 108), (30, 108)], C_STONE),
        _poly([(30, 80), (58, 54), (74, 62), (80, 78)], C_STONE_LT),
        _poly([(66, 72), (90, 56), (108, 68), (104, 82)], C_STONE),
        _poly([(68, 58), (90, 44), (106, 56)], C_STONE_LT),
        # small stones
        _circle(36, 96, 8, C_STONE_LT),
        _circle(90, 98, 6, C_STONE),
        _circle(60, 100, 5, C_STONE_LT),
    ]
    return _svg("\n".join(body))


def _lantern() -> str:
    body = [
        # chain / hook
        _line(64, 8, 64, 22, C_IRON, 3),
        _circle(64, 10, 5, C_IRON),
        # hanging ring
        _circle(64, 22, 7, C_IRON, sw=3),
        # top cap (hexagonal taper)
        _poly([(46, 26), (82, 26), (88, 36), (40, 36)], C_IRON),
        # glass body - bright amber/yellow to suggest light
        _poly([(40, 36), (88, 36), (92, 88), (36, 88)], C_FIRE_LT),
        # left glass panel frame
        _line(40, 36, 36, 88, C_IRON, 2),
        # right glass panel frame
        _line(88, 36, 92, 88, C_IRON, 2),
        # center vertical divider
        _line(64, 36, 64, 88, C_IRON, 2),
        # horizontal divider
        _line(38, 62, 90, 62, C_IRON, 2),
        # bottom cap
        _poly([(36, 88), (92, 88), (86, 100), (42, 100)], C_IRON),
        # ventilation holes at bottom cap
        _circle(54, 94, 3, C_WOOD_DK, stroke="none"),
        _circle(64, 94, 3, C_WOOD_DK, stroke="none"),
        _circle(74, 94, 3, C_WOOD_DK, stroke="none"),
        # candle flame (bigger, more visible)
        _poly([(64, 40), (74, 68), (64, 60), (54, 68)], C_FIRE, stroke="none"),
        _poly([(64, 40), (71, 62), (64, 55)], C_FIRE_LT, stroke="none"),
        # glow highlight on glass
        _poly([(42, 38), (60, 38), (58, 60), (40, 60)], "rgba(255,240,100,0.18)", stroke="none"),
    ]
    return _svg("\n".join(body))


def _spike_trap() -> str:
    parts = []
    for i in range(6):
        x = 22 + i * 16
        parts.append(_poly([(x, 76), (x + 10, 76), (x + 5, 30)], C_IRON))
        parts.append(_poly([(x + 2, 76), (x + 7, 76), (x + 5, 40)], C_IRON_LT, stroke="none"))
    parts.append(_rect(14, 76, 100, 22, C_IRON, rx=3))
    parts.append(_rect(20, 80, 88, 14, C_IRON_LT, rx=2))
    return _svg("\n".join(parts))


def _pressure_plate() -> str:
    body = [
        # floor surround
        _rect(14, 52, 100, 54, C_STONE, rx=4),
        _rect(20, 58, 88, 42, C_STONE_LT, rx=3),
        # plate
        _rect(30, 62, 68, 30, C_IRON, rx=3),
        _rect(36, 66, 56, 22, C_IRON_LT, rx=2),
        # hinge
        _rect(56, 86, 16, 8, C_IRON, rx=2),
        # warning runes
        _path("M64 70 L68 82 L60 82 Z", fill=C_RED, stroke="none"),
    ]
    return _svg("\n".join(body))


def _sack() -> str:
    body = [
        # sack body
        _path("M34 46 Q28 86 40 106 Q64 118 88 106 Q100 86 94 46 Q78 30 50 30 Z",
              fill=C_LEATHER),
        # tie rope
        _path("M46 36 Q64 28 82 36", fill="none", stroke=C_ROPE, sw=4),
        # shading
        _path("M38 50 Q34 80 44 104", fill="none", stroke=C_WOOD_DK, sw=2),
        # bulge highlight
        _path("M70 38 Q90 50 90 80 Q90 100 80 110", fill="none", stroke=C_WOOD_LT, sw=2),
    ]
    return _svg("\n".join(body))


def _lockbox() -> str:
    body = [
        # body
        _rect(18, 40, 92, 72, C_IRON, rx=4),
        _rect(24, 46, 80, 58, C_IRON_LT, rx=3),
        # lock plate
        _rect(46, 54, 36, 36, C_GOLD, rx=3),
        # keyhole
        _circle(64, 68, 8, C_IRON),
        _rect(60, 72, 8, 12, C_IRON, rx=2),
        # rivets
        _circle(26, 50, 4, C_IRON),
        _circle(102, 50, 4, C_IRON),
        _circle(26, 104, 4, C_IRON),
        _circle(102, 104, 4, C_IRON),
    ]
    return _svg("\n".join(body))


def _bedroll() -> str:
    body = [
        # mat
        _rect(16, 36, 96, 68, C_LEATHER, rx=8),
        _rect(22, 42, 84, 56, C_WOOD_LT, rx=6),
        # stripes
        _line(22, 62, 106, 62, C_LEATHER, 2),
        _line(22, 72, 106, 72, C_LEATHER, 2),
        # pillow
        _rect(22, 44, 34, 28, C_PARCHMT, rx=5),
        # roll at the end
        _rect(90, 40, 14, 54, C_LEATHER, rx=6),
        _rect(92, 42, 10, 50, C_WOOD_LT, rx=5, stroke="none"),
    ]
    return _svg("\n".join(body))


def _cooking_pot() -> str:
    body = [
        # tripod legs
        _line(38, 84, 20, 114, C_IRON, 4),
        _line(90, 84, 108, 114, C_IRON, 4),
        _line(64, 86, 64, 114, C_IRON, 4),
        # pot body
        _poly([(28, 54), (100, 54), (94, 90), (34, 90)], C_IRON),
        _poly([(32, 58), (96, 58), (92, 86), (36, 86)], C_IRON_LT),
        # rim
        _rect(24, 48, 80, 12, C_IRON, rx=3),
        # handle bar
        _path("M24 54 Q64 34 104 54", fill="none", stroke=C_IRON_LT, sw=4),
        # steam
        _path("M50 48 Q46 36 50 24", fill="none", stroke="#e0e0ff", sw=2),
        _path("M78 48 Q82 36 78 24", fill="none", stroke="#e0e0ff", sw=2),
    ]
    return _svg("\n".join(body))


def _tent() -> str:
    body = [
        # tent body
        _poly([(10, 104), (64, 18), (118, 104)], C_LEATHER),
        # door opening
        _poly([(50, 104), (64, 62), (78, 104)], C_WOOD_DK),
        # fabric seam lines
        _line(64, 18, 64, 104, C_LEATHER, 2),
        _line(10, 104, 64, 18, C_WOOD_LT, 1),
        _line(118, 104, 64, 18, C_WOOD_LT, 1),
        # centre pole
        _line(64, 24, 64, 14, C_WOOD, 3),
        _circle(64, 12, 4, C_GOLD),
        # guide ropes
        _line(10, 104, 30, 84, C_ROPE, 1),
        _line(118, 104, 98, 84, C_ROPE, 1),
        # ground pegs
        _circle(10, 108, 4, C_IRON),
        _circle(118, 108, 4, C_IRON),
    ]
    return _svg("\n".join(body))


def _market_stall() -> str:
    body = [
        # awning
        _rect(12, 14, 104, 38, C_RED, rx=3),
        _rect(12, 46, 104, 8, C_WOOD_DK, rx=1),
        # scalloped hem
        _path("M12 52 Q24 62 36 52 Q48 62 60 52 Q72 62 84 52 Q96 62 108 52 L116 52 L116 58 L12 58 Z",
              fill=C_RED, stroke=C_STROKE, sw=1),
        # counter top
        _rect(14, 56, 100, 30, C_WOOD, rx=3),
        _rect(20, 58, 88, 18, C_WOOD_LT, rx=2),
        # goods
        _circle(36, 66, 8, C_GREEN),
        _circle(54, 66, 8, C_GOLD),
        _circle(72, 66, 8, C_RED),
        _circle(90, 66, 8, C_WOOD_LT),
        # posts
        _rect(14, 56, 8, 56, C_WOOD_DK, rx=2),
        _rect(106, 56, 8, 56, C_WOOD_DK, rx=2),
    ]
    return _svg("\n".join(body))


def _signpost() -> str:
    body = [
        # post
        _rect(58, 30, 12, 90, C_WOOD, rx=3),
        # signs
        _rect(14, 34, 64, 22, C_WOOD_LT, rx=3),
        _rect(50, 62, 64, 20, C_WOOD_LT, rx=3),
        # text lines (implied by lines)
        _line(22, 42, 68, 42, C_WOOD_DK, 2),
        _line(22, 48, 60, 48, C_WOOD_DK, 2),
        _line(58, 70, 104, 70, C_WOOD_DK, 2),
        _line(58, 76, 96, 76, C_WOOD_DK, 2),
        # arrow tips
        _poly([(14, 45), (22, 34), (22, 56)], C_WOOD, stroke="none"),
        _poly([(114, 72), (106, 62), (106, 82)], C_WOOD, stroke="none"),
    ]
    return _svg("\n".join(body))


def _poison_vent() -> str:
    body = [
        # floor grate
        _rect(16, 70, 96, 30, C_STONE, rx=3),
        _rect(20, 74, 88, 22, C_IRON, rx=2),
        # grate bars
        _line(38, 74, 38, 96, C_STONE, 3),
        _line(56, 74, 56, 96, C_STONE, 3),
        _line(74, 74, 74, 96, C_STONE, 3),
        _line(92, 74, 92, 96, C_STONE, 3),
        # gas cloud
        _circle(46, 46, 26, C_GREEN, stroke="none"),
        _circle(74, 38, 22, "#2a9a2a", stroke="none"),
        _circle(62, 56, 20, "#1a7a1a", stroke="none"),
        # gas highlights
        _circle(42, 40, 10, "#5acc5a", stroke="none"),
        _circle(70, 34, 8, "#5acc5a", stroke="none"),
    ]
    return _svg("\n".join(body))


def _loot_pile() -> str:
    body = [
        # coins base
        _circle(64, 88, 32, C_GOLD),
        _circle(64, 88, 24, C_GOLD_LT, stroke="none"),
        # gem
        _poly([(54, 56), (74, 56), (80, 72), (64, 80), (48, 72)], C_TEAL),
        _poly([(54, 56), (64, 62), (74, 56)], "#80f0e0", stroke="none"),
        # small items
        _circle(42, 80, 8, C_GOLD_LT),
        _circle(86, 76, 6, C_GOLD_LT),
        # scroll
        _rect(78, 58, 20, 24, C_PARCHMT, rx=3),
        _line(80, 66, 96, 66, C_STONE, 1),
        _line(80, 70, 96, 70, C_STONE, 1),
        _line(80, 74, 92, 74, C_STONE, 1),
        # coin glint
        _circle(64, 88, 5, "#fff8d0", stroke="none"),
    ]
    return _svg("\n".join(body))


def _shop_front() -> str:
    """Top-down shop building prop with awning and door."""
    body = [
        # building footprint
        _rect(10, 30, 108, 88, C_WOOD_LT, rx=3),
        # awning
        _rect(8, 24, 112, 22, C_RED, rx=3),
        # awning scallop hem
        _path("M8 44 Q20 54 32 44 Q44 54 56 44 Q68 54 80 44 Q92 54 104 44 Q116 54 120 44 L120 48 L8 48 Z",
              fill=C_RED, stroke=C_STROKE, sw=1),
        # shop windows
        _rect(14, 52, 36, 32, "#5a9090", rx=3),
        _rect(78, 52, 36, 32, "#5a9090", rx=3),
        # window highlights
        _line(20, 58, 44, 58, "#8ac8c8", sw=2),
        _line(84, 58, 108, 58, "#8ac8c8", sw=2),
        # door
        _rect(50, 78, 28, 40, C_WOOD, rx=4),
        _circle(58, 98, 4, C_GOLD),
        # door panel lines
        _line(54, 86, 74, 86, C_WOOD_DK, 1),
    ]
    return _svg("\n".join(body))



def _magic_portal() -> str:
    extra_defs = """\
  <radialGradient id="portal_glow" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#c0a0f0" stop-opacity="0.9"/>
    <stop offset="70%" stop-color="#8060c0" stop-opacity="0.7"/>
    <stop offset="100%" stop-color="#4020a0" stop-opacity="0"/>
  </radialGradient>"""
    body = [
        _circle(64, 64, 52, "url(#portal_glow)", stroke="none"),
        _circle(64, 64, 50, "none", stroke=C_MAGIC_LT, sw=3),
        _circle(64, 64, 42, "none", stroke=C_MAGIC, sw=2),
        # inner swirl
        _path("M64 22 Q96 64 64 106 Q32 64 64 22", fill=C_MAGIC, stroke=C_MAGIC_LT, sw=1),
        _circle(64, 64, 14, C_MAGIC_LT, stroke="none"),
        _circle(64, 64, 7, "#ffffff", stroke="none"),
        # rune ring
        _path("M64 16 L68 26 L64 22 L60 26 Z", fill=C_MAGIC_LT, stroke="none"),
        _path("M64 112 L68 102 L64 106 L60 102 Z", fill=C_MAGIC_LT, stroke="none"),
    ]
    return _svg("\n".join(body), extra_defs)


# ---------------------------------------------------------------------------
# Marker / world map icons
# ---------------------------------------------------------------------------

def _marker_city() -> str:
    body = [
        # outer wall ring
        _circle(64, 74, 44, C_STONE_LT),
        _circle(64, 74, 36, C_STONE, stroke="none"),
        # towers
        _rect(24, 36, 20, 46, C_STONE_LT, rx=2),
        _rect(84, 36, 20, 46, C_STONE_LT, rx=2),
        _rect(50, 14, 28, 66, C_STONE_LT, rx=2),
        # roofs
        _poly([(24, 36), (34, 18), (44, 36)], C_RED),
        _poly([(84, 36), (94, 18), (104, 36)], C_RED),
        _poly([(50, 14), (64, -2), (78, 14)], C_RED),
        # gates
        _rect(52, 78, 24, 36, C_WOOD_DK, rx=2),
    ]
    return _svg("\n".join(body))


def _marker_town() -> str:
    body = [
        # houses
        _rect(12, 58, 38, 40, C_WOOD, rx=2),
        _poly([(12, 58), (31, 38), (50, 58)], C_RED),
        _rect(74, 58, 38, 40, C_WOOD, rx=2),
        _poly([(74, 58), (93, 38), (112, 58)], C_RED),
        _rect(40, 66, 48, 32, C_WOOD_LT, rx=2),
        _poly([(40, 66), (64, 44), (88, 66)], C_WOOD_DK),
        # road
        _rect(20, 96, 88, 12, C_STONE, rx=2),
    ]
    return _svg("\n".join(body))


def _marker_ruin() -> str:
    body = [
        # crumbled walls
        _rect(14, 68, 22, 40, C_STONE, rx=2),
        _rect(20, 58, 10, 14, C_STONE_LT, rx=1),
        _rect(90, 72, 24, 36, C_STONE, rx=2),
        _rect(94, 58, 14, 18, C_STONE_LT, rx=1),
        # fallen block
        _poly([(40, 80), (74, 72), (80, 88), (44, 96)], C_STONE),
        # rubble
        _circle(58, 100, 10, C_STONE_LT),
        _circle(76, 96, 8, C_STONE),
        _circle(42, 94, 6, C_STONE_LT),
    ]
    return _svg("\n".join(body))


def _marker_castle() -> str:
    body = [
        # tower
        _rect(38, 28, 52, 80, C_STONE_LT, rx=2),
        # battlements
        _rect(36, 18, 12, 14, C_STONE_LT, rx=1),
        _rect(54, 18, 12, 14, C_STONE_LT, rx=1),
        _rect(72, 18, 12, 14, C_STONE_LT, rx=1),
        _rect(36, 22, 56, 8, C_STONE, rx=1),
        # arrow slits
        _rect(52, 46, 6, 18, C_WOOD_DK, rx=1),
        _rect(70, 46, 6, 18, C_WOOD_DK, rx=1),
        # gate
        _rect(54, 82, 20, 26, C_WOOD_DK, rx=2),
        _path("M54 94 Q64 80 74 94", fill=C_WOOD_DK, stroke=C_STROKE, sw=1),
    ]
    return _svg("\n".join(body))


def _marker_forest() -> str:
    body = [
        # trees
        _poly([(64, 10), (98, 68), (30, 68)], C_GREEN),
        _poly([(64, 22), (92, 68), (36, 68)], "#2a9a2a", stroke="none"),
        # second tree
        _poly([(96, 30), (120, 78), (72, 78)], "#2a7a2a"),
        # third tree
        _poly([(32, 30), (56, 78), (8, 78)], "#2a7a2a"),
        # trunks
        _rect(60, 66, 8, 32, C_WOOD_DK, rx=2),
        _rect(92, 76, 6, 28, C_WOOD_DK, rx=1),
        _rect(28, 76, 6, 28, C_WOOD_DK, rx=1),
    ]
    return _svg("\n".join(body))


def _marker_mountain() -> str:
    body = [
        # distant peak
        _poly([(64, 8), (110, 90), (18, 90)], C_STONE),
        _poly([(64, 8), (90, 90), (38, 90)], C_STONE_LT),
        # snow caps
        _poly([(64, 8), (82, 50), (46, 50)], "#e8eef8"),
        _poly([(64, 8), (76, 46), (52, 46)], "#ffffff", stroke="none"),
        # base shadow
        _rect(18, 88, 92, 18, C_STONE, rx=2, stroke="none"),
    ]
    return _svg("\n".join(body))


def _marker_harbor() -> str:
    body = [
        # water
        _rect(12, 72, 104, 40, C_TEAL, rx=4),
        _path("M12 82 Q34 72 56 82 Q78 92 100 82 Q110 78 116 82 L116 112 L12 112 Z",
              fill="#2a8aaa", stroke="none"),
        # pier
        _rect(50, 52, 28, 52, C_WOOD_DK, rx=2),
        # ship
        _poly([(28, 66), (100, 66), (106, 80), (22, 80)], C_WOOD),
        # mast
        _line(64, 40, 64, 66, C_WOOD_DK, 3),
        # sail
        _poly([(66, 42), (94, 52), (94, 64), (66, 64)], C_PARCHMT),
    ]
    return _svg("\n".join(body))


def _marker_tavern() -> str:
    body = [
        # building
        _rect(18, 40, 92, 72, C_WOOD, rx=3),
        _poly([(12, 40), (64, 10), (116, 40)], C_WOOD_DK),
        # windows
        _rect(26, 50, 22, 20, C_FIRE_LT, rx=2),
        _rect(80, 50, 22, 20, C_FIRE_LT, rx=2),
        # door
        _rect(52, 80, 24, 32, C_WOOD_DK, rx=3),
        _path("M52 90 Q64 78 76 90", fill=C_WOOD_DK, stroke=C_STROKE, sw=1),
        # sign
        _rect(44, 26, 40, 16, C_WOOD_LT, rx=3),
        _line(48, 30, 80, 30, C_WOOD_DK, 2),
        _line(48, 36, 76, 36, C_WOOD_DK, 2),
    ]
    return _svg("\n".join(body))


def _marker_shop() -> str:
    body = [
        # building
        _rect(18, 44, 92, 68, C_WOOD_LT, rx=3),
        # awning
        _rect(12, 36, 104, 16, C_RED, rx=2),
        # windows / display
        _rect(22, 52, 36, 30, C_TEAL, rx=2),
        _rect(70, 52, 36, 30, C_TEAL, rx=2),
        # items in window
        _circle(36, 64, 7, C_GOLD),
        _circle(84, 64, 7, C_MAGIC),
        _circle(36, 74, 5, C_IRON),
        _circle(84, 74, 5, C_RED),
        # door
        _rect(52, 80, 24, 32, C_WOOD, rx=3),
    ]
    return _svg("\n".join(body))


def _marker_camp() -> str:
    body = [
        # tents
        _poly([(10, 90), (38, 50), (66, 90)], C_LEATHER),
        _poly([(62, 90), (90, 50), (118, 90)], C_LEATHER),
        # campfire
        _poly([(64, 56), (72, 80), (64, 74), (56, 80)], C_FIRE, stroke="none"),
        _poly([(64, 56), (70, 76), (64, 70)], C_FIRE_LT, stroke="none"),
        _circle(64, 84, 8, C_IRON_LT),
        # rope line between tents
        _line(36, 58, 92, 58, C_ROPE, 1),
    ]
    return _svg("\n".join(body))


def _marker_blacksmith() -> str:
    body = [
        # anvil
        _rect(28, 66, 72, 30, C_IRON, rx=3),
        _rect(34, 56, 60, 16, C_IRON_LT, rx=2),
        _rect(48, 46, 32, 14, C_IRON, rx=2),
        # hammer
        _rect(72, 22, 16, 36, C_WOOD, rx=3),
        _rect(66, 22, 28, 14, C_IRON, rx=2),
        # sparks
        _circle(56, 62, 4, C_FIRE_LT, stroke="none"),
        _circle(68, 56, 3, C_FIRE, stroke="none"),
        _circle(44, 58, 3, C_FIRE_LT, stroke="none"),
    ]
    return _svg("\n".join(body))


def _marker_landmark() -> str:
    body = [
        # obelisk
        _poly([(54, 12), (74, 12), (80, 100), (48, 100)], C_STONE_LT),
        _poly([(60, 14), (68, 14), (64, 8)], C_STONE),
        # carvings
        _line(54, 40, 74, 40, C_STONE, 1),
        _circle(64, 56, 8, C_GOLD_LT, stroke=C_GOLD),
        _line(54, 70, 74, 70, C_STONE, 1),
        # base
        _rect(40, 98, 48, 14, C_STONE, rx=2),
        _rect(30, 108, 68, 8, C_STONE_LT, rx=2),
    ]
    return _svg("\n".join(body))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PROP_REGISTRY: dict[str, tuple] = {
    # id: (display_name, drawer_fn, subtype, tags)
    "barrel":         ("Barrel",         _barrel,         "container",  ["barrel", "dungeon", "storage", "clutter"]),
    "crate":          ("Crate",           _crate,          "container",  ["crate", "dungeon", "storage", "clutter"]),
    "chest":          ("Chest",           _chest,          "container",  ["chest", "treasure", "storage", "loot"]),
    "sack":           ("Sack",            _sack,           "container",  ["sack", "bag", "storage", "loot"]),
    "lockbox":        ("Lockbox",         _lockbox,        "container",  ["lockbox", "chest", "storage", "treasure"]),
    "table":          ("Table",           _table,          "furniture",  ["table", "furniture", "dungeon", "tavern"]),
    "chair":          ("Chair",           _chair,          "furniture",  ["chair", "furniture", "dungeon", "tavern"]),
    "bookshelf":      ("Bookshelf",       _bookshelf,      "furniture",  ["bookshelf", "books", "library", "furniture"]),
    "altar":          ("Altar",           _altar,          "religious",  ["altar", "shrine", "church", "ritual"]),
    "ritual_circle":  ("Ritual Circle",   _ritual_circle,  "ritual",     ["ritual", "circle", "magic", "arcane"]),
    "shrine":         ("Shrine",          _shrine,         "religious",  ["shrine", "temple", "ritual", "religious"]),
    "torch":          ("Torch",           _torch,          "lighting",   ["torch", "light", "fire", "dungeon"]),
    "brazier":        ("Brazier",         _brazier,        "lighting",   ["brazier", "fire", "light", "dungeon"]),
    "lantern":        ("Lantern",         _lantern,        "lighting",   ["lantern", "light", "fire", "tavern"]),
    "campfire":       ("Campfire",        _campfire,       "lighting",   ["campfire", "fire", "camp", "outdoor"]),
    "door":           ("Door",            _door,           "structure",  ["door", "entrance", "dungeon", "structure"]),
    "bones":          ("Bones",           _bones,          "clutter",    ["bones", "skull", "dead", "dungeon", "clutter"]),
    "rubble":         ("Rubble",          _rubble,         "clutter",    ["rubble", "rocks", "ruins", "clutter"]),
    "spike_trap":     ("Spike Trap",      _spike_trap,     "hazard",     ["trap", "spikes", "hazard", "dungeon"]),
    "pressure_plate": ("Pressure Plate",  _pressure_plate, "hazard",     ["trap", "pressure", "hazard", "dungeon"]),
    "poison_vent":    ("Poison Vent",     _poison_vent,    "hazard",     ["poison", "gas", "hazard", "trap", "dungeon"]),
    "bedroll":        ("Bedroll",         _bedroll,        "camp",       ["bedroll", "camp", "rest", "sleep"]),
    "cooking_pot":    ("Cooking Pot",     _cooking_pot,    "camp",       ["pot", "cooking", "camp", "food"]),
    "tent":           ("Tent",            _tent,           "camp",       ["tent", "camp", "outdoor", "shelter"]),
    "loot_pile":      ("Loot Pile",       _loot_pile,      "treasure",   ["loot", "gold", "treasure", "gems"]),
    "magic_portal":   ("Magic Portal",    _magic_portal,   "arcane",     ["portal", "magic", "arcane", "teleport"]),
    "well":           ("Well",            _well,           "structure",  ["well", "water", "village", "outdoor"]),
    "fountain":       ("Fountain",        _fountain,       "structure",  ["fountain", "water", "plaza", "decorative"]),
    "market_stall":   ("Market Stall",    _market_stall,   "furniture",  ["stall", "market", "shop", "vendor", "counter"]),
    "shop_front":     ("Shop Front",      _shop_front,     "structure",  ["shop", "store", "building", "merchant", "front"]),
    "signpost":       ("Signpost",        _signpost,       "structure",  ["sign", "post", "direction", "road"]),
}

MARKER_REGISTRY: dict[str, tuple] = {
    "marker_city":        ("City",        _marker_city,       "settlement", ["city", "urban", "capital", "large"]),
    "marker_town":        ("Town",        _marker_town,       "settlement", ["town", "village", "small", "buildings"]),
    "marker_tavern":      ("Tavern",      _marker_tavern,     "building",   ["tavern", "inn", "building", "rest"]),
    "marker_shop":        ("Shop",        _marker_shop,       "building",   ["shop", "store", "market", "building"]),
    "marker_ruin":        ("Ruin",        _marker_ruin,       "ruin",       ["ruin", "old", "crumbled", "ancient"]),
    "marker_castle":      ("Castle",      _marker_castle,     "fortified",  ["castle", "keep", "fortress", "fortified"]),
    "marker_forest":      ("Forest",      _marker_forest,     "biome",      ["forest", "trees", "wood", "nature"]),
    "marker_mountain":    ("Mountain",    _marker_mountain,   "terrain",    ["mountain", "peak", "high", "elevation"]),
    "marker_harbor":      ("Harbor",      _marker_harbor,     "settlement", ["harbor", "port", "dock", "water", "ship"]),
    "marker_blacksmith":  ("Blacksmith",  _marker_blacksmith, "building",   ["blacksmith", "forge", "smith", "crafting"]),
    "marker_camp":        ("Camp",        _marker_camp,       "camp",       ["camp", "rest", "outdoor", "tent"]),
    "marker_landmark":    ("Landmark",    _marker_landmark,   "monument",   ["landmark", "monument", "obelisk", "stone"]),
}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _asset_entry(
    asset_id: str,
    name: str,
    subtype: str,
    tags: list,
    category: str,
    style_pack: str,
    file_url: str,
    thumb_url: str | None = None,
) -> dict:
    return {
        "id": asset_id,
        "name": name,
        "category": category,
        "subtype": subtype,
        "tags": tags,
        "style_pack": style_pack,
        "file": file_url,
        "thumbnail": thumb_url or file_url,
        "license": "internal",
        "animated": False,
        "tileable": False,
        "scale": 1.0,
        "anchor": "center",
        "footprint": 1.0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate fantasy prop SVG assets and update manifest.json")
    parser.add_argument("--output-dir", default=str(Path(__file__).parent.parent / "client" / "static" / "assets"))
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing files")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    props_dir = output_dir / "props"
    markers_dir = output_dir / "markers"
    manifest_path = output_dir / "manifest.json"

    if not args.dry_run:
        props_dir.mkdir(parents=True, exist_ok=True)
        markers_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Generate prop SVGs
    # -----------------------------------------------------------------------
    new_prop_entries = []
    for asset_id, (name, fn, subtype, tags) in PROP_REGISTRY.items():
        svg_path = props_dir / f"{asset_id}.svg"
        url = f"/static/assets/props/{asset_id}.svg"
        if not args.dry_run:
            svg_path.write_text(fn(), encoding="utf-8")
            print(f"  [prop] {svg_path.name}")
        else:
            print(f"  [dry-run] would write {svg_path}")
        new_prop_entries.append(_asset_entry(
            asset_id=f"prop_{asset_id}",
            name=name,
            subtype=subtype,
            tags=tags,
            category="props",
            style_pack="fantasy_props",
            file_url=url,
        ))

    # -----------------------------------------------------------------------
    # Generate marker SVGs
    # -----------------------------------------------------------------------
    new_marker_entries = []
    for asset_id, (name, fn, subtype, tags) in MARKER_REGISTRY.items():
        svg_path = markers_dir / f"{asset_id}.svg"
        url = f"/static/assets/markers/{asset_id}.svg"
        if not args.dry_run:
            svg_path.write_text(fn(), encoding="utf-8")
            print(f"  [marker] {svg_path.name}")
        else:
            print(f"  [dry-run] would write {svg_path}")
        new_marker_entries.append(_asset_entry(
            asset_id=asset_id,
            name=name,
            subtype=subtype,
            tags=tags,
            category="markers",
            style_pack="world_markers",
            file_url=url,
        ))

    # -----------------------------------------------------------------------
    # Update manifest.json
    # -----------------------------------------------------------------------
    try:
        existing = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    except Exception:
        existing = {}

    managed_packs = {"fantasy_props", "world_markers"}
    managed_ids = (
        {f"prop_{k}" for k in PROP_REGISTRY}
        | {k for k in MARKER_REGISTRY}
    )

    # Keep existing packs and assets that are NOT in our managed sets
    kept_packs = [p for p in existing.get("packs", []) if p.get("id") not in managed_packs]
    kept_assets = [a for a in existing.get("assets", []) if a.get("id") not in managed_ids]

    new_packs = [
        {"id": "fantasy_props", "name": "Fantasy Props", "description": "Built-in top-down fantasy prop icons for dungeon, camp, and world scenes."},
        {"id": "world_markers", "name": "World Markers", "description": "Built-in world-map location markers for cities, ruins, terrain features, and more."},
    ]

    manifest = {
        "version": existing.get("version", 1),
        "packs": kept_packs + new_packs,
        "assets": kept_assets + new_prop_entries + new_marker_entries,
    }

    if not args.dry_run:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        total = len(new_prop_entries) + len(new_marker_entries)
        print(f"\n✓ manifest.json updated — {total} new entries ({len(new_prop_entries)} props, {len(new_marker_entries)} markers)")
    else:
        print(f"\n[dry-run] Would write {len(new_prop_entries)} props + {len(new_marker_entries)} markers to manifest.json")


if __name__ == "__main__":
    main()

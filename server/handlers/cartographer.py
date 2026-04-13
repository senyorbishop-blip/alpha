"""
server/handlers/cartographer.py — AI Cartographer pipeline.

Architecture:
  Layer 1 – STRUCTURE (Claude):  map planner, layout designer, prompt composer
  Layer 2 – IMAGE (provider):    swappable image-generation backend
  Layer 3 – EDITOR INTEGRATION: returns editor-importable result

Claude is NEVER asked to produce final image bytes.
It acts as cartography director and structured layout/prompt generator.

Environment variables (see .env.example in project root):
  IMAGE_PROVIDER      — Force a specific provider: openai | stability | replicate | stub
  OPENAI_API_KEY      — OpenAI API key (uses gpt-image-1 model)
  STABILITY_API_KEY   — Stability AI key (DEPRECATED — see StabilityImageProvider note)
  REPLICATE_API_TOKEN — Replicate API token
  REPLICATE_MODEL     — Override Replicate model (default: black-forest-labs/flux-1.1-pro)
  ANTHROPIC_API_KEY   — Claude API key for the structure/planning layer
"""
from __future__ import annotations

import base64
import json
import logging
import os
import uuid
from pathlib import Path

import httpx

# Load .env file when python-dotenv is available (optional dev convenience).
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(override=False)     # don't overwrite already-set env vars
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────
# Grid dimension defaults
# ────────────────────────────────────────────────

GRID_DEFAULTS: dict[str, dict[str, tuple[int, int]]] = {
    "interior": {
        "tiny":  (16, 16),
        "small": (24, 24),
        "medium": (36, 36),
        "large": (48, 48),
        "huge": (64, 64),
    },
    "dungeon": {
        "small": (30, 30),
        "medium": (45, 45),
        "large": (60, 60),
        "huge": (80, 80),
    },
    "house": {
        "tiny":  (12, 12),
        "small": (18, 18),
        "medium": (24, 24),
        "large": (32, 32),
    },
    "castle": {
        "small": (36, 36),
        "medium": (48, 48),
        "large": (64, 64),
        "huge": (80, 80),
    },
    "region": {
        "small": (40, 40),
        "medium": (60, 60),
        "large": (80, 80),
        "huge": (120, 120),
    },
}

# Map interior_type -> grid_defaults key
INTERIOR_TYPE_CLASS: dict[str, str] = {
    "cave": "dungeon",
    "dungeon": "dungeon",
    "crypt": "dungeon",
    "mine": "dungeon",
    "sewer": "dungeon",
    "tavern": "house",
    "house": "house",
    "manor": "house",
    "blacksmith": "house",
    "shop": "house",
    "temple": "house",
    "shrine": "house",
    "tower": "house",
    "prison": "dungeon",
    "bandit_hideout": "dungeon",
    "cult_lair": "dungeon",
    "castle": "castle",
    "castle_keep": "castle",
    "fort": "castle",
    "world": "region",
    "region": "region",
    "local_area": "interior",
    "settlement": "interior",
    "interior": "interior",
}

# ────────────────────────────────────────────────
# Built-in prompt library
# ────────────────────────────────────────────────

TERRAIN_PRESETS: dict[str, dict] = {
    "coastal_kingdom": {
        "title": "Coastal Kingdom",
        "terrain_keywords": ["ocean coast", "sandy shores", "sea cliffs", "harbors", "tidal flats"],
        "mood_keywords": ["maritime", "windswept", "prosperous", "naval"],
        "composition_rules": "coastline along one edge, inland elevation rising away from shore",
    },
    "deep_forest_frontier": {
        "title": "Deep Forest Frontier",
        "terrain_keywords": ["ancient forest", "dense canopy", "forest trails", "clearings", "wilderness"],
        "mood_keywords": ["wild", "mysterious", "overgrown", "primeval"],
        "composition_rules": "thick forest covering most of map, clearings mark settlements and POIs",
    },
    "mountain_realm": {
        "title": "Mountain Realm",
        "terrain_keywords": ["mountain peaks", "alpine passes", "rocky ridges", "snowline", "valleys"],
        "mood_keywords": ["rugged", "majestic", "cold", "fortified"],
        "composition_rules": "mountain range as dominant feature, passes as travel routes",
    },
    "volcanic_wasteland": {
        "title": "Volcanic Wasteland",
        "terrain_keywords": ["volcanic rock", "lava flows", "ash fields", "caldera", "obsidian"],
        "mood_keywords": ["hostile", "scorched", "dangerous", "infernal"],
        "composition_rules": "active volcano as centerpiece, radial terrain zones around it",
    },
    "swamp_marches": {
        "title": "Swamp Marches",
        "terrain_keywords": ["murky swamp", "brackish water", "twisted trees", "bogs", "reed beds"],
        "mood_keywords": ["oppressive", "fetid", "hidden", "corrupted"],
        "composition_rules": "water channels winding through boggy terrain, dry hummocks mark safe paths",
    },
    "high_desert": {
        "title": "High Desert Expanse",
        "terrain_keywords": ["arid desert", "sand dunes", "mesa formations", "dry riverbeds", "oases"],
        "mood_keywords": ["harsh", "sun-baked", "ancient", "sparse"],
        "composition_rules": "open sand sea with rocky outcrops, oases and ruins as key landmarks",
    },
    "frozen_north": {
        "title": "Frozen North",
        "terrain_keywords": ["tundra", "permafrost", "frozen lakes", "ice shelf", "blizzard plains"],
        "mood_keywords": ["desolate", "brutal", "frozen", "elemental"],
        "composition_rules": "flat frozen plains broken by glacial features and storm-carved ridges",
    },
    "riverlands": {
        "title": "Riverlands",
        "terrain_keywords": ["river delta", "fertile floodplain", "oxbow lakes", "wetlands", "bridges"],
        "mood_keywords": ["prosperous", "navigable", "agricultural", "contested"],
        "composition_rules": "major river as spine of map, tributaries branching, settlements along banks",
    },
    "underdark": {
        "title": "Underdark Cavern Region",
        "terrain_keywords": ["vast caverns", "underground lakes", "stalactite forests", "fungal growths", "deep tunnels"],
        "mood_keywords": ["lightless", "alien", "dangerous", "subterranean"],
        "composition_rules": "interconnected cave systems with major voids as encounter hubs",
    },
    "rolling_farmland": {
        "title": "Rolling Farmland Realm",
        "terrain_keywords": ["crop fields", "rolling hills", "farm roads", "orchards", "pastures"],
        "mood_keywords": ["pastoral", "peaceful", "civilized", "vulnerable"],
        "composition_rules": "patchwork fields with roads connecting villages, manor visible from distance",
    },
}

BUILD_PRESETS: dict[str, dict] = {
    "ancient_castle": {
        "title": "Ancient Castle Region",
        "architecture_keywords": ["ancient castle", "crumbling battlements", "moat", "towers", "curtain wall"],
        "poi_rules": "castle as dominant structure, surrounding village, approach road, outer defenses",
    },
    "trade_road": {
        "title": "Trade Road Network",
        "architecture_keywords": ["cobbled road", "waypost", "caravanserai", "toll bridge", "road shrine"],
        "poi_rules": "major road as spine, inns and checkpoints every few miles, bandit or monster threats along route",
    },
    "frontier_villages": {
        "title": "Frontier Villages",
        "architecture_keywords": ["wooden palisade", "longhouse", "watchtower", "stockade", "simple homes"],
        "poi_rules": "2-4 small villages scattered, wilderness between them, local threats nearby",
    },
    "dungeon_rich_wilderness": {
        "title": "Dungeon-Rich Wilderness",
        "architecture_keywords": ["dungeon entrance", "ruins", "ancient arch", "buried vault", "tomb mouth"],
        "poi_rules": "multiple dungeon entrances scattered across wilderness, rumors and trails leading between",
    },
    "tavern_crossroads": {
        "title": "Tavern Crossroads",
        "architecture_keywords": ["large inn", "stable", "well", "signpost", "merchant stall"],
        "poi_rules": "prominent tavern at road junction, travelers, merchants, potential intrigue",
    },
    "ruined_empire": {
        "title": "Ruined Empire Zone",
        "architecture_keywords": ["broken colossus", "crumbled forum", "overgrown road", "collapsed aqueduct", "mosaic floors"],
        "poi_rules": "extensive ruins across map, wilderness reclaiming civilization, danger in every structure",
    },
    "war_torn": {
        "title": "War-Torn Province",
        "architecture_keywords": ["burned village", "siege works", "mass grave", "broken wall", "military camp"],
        "poi_rules": "multiple factions visible, destruction and fortification side by side",
    },
    "pirate_coast": {
        "title": "Pirate Coast",
        "architecture_keywords": ["hidden cove", "sea cave", "signal tower", "smuggler's den", "wrecked ship"],
        "poi_rules": "rocky coastline with hidden anchorages, pirate stronghold, naval threats",
    },
}

INTERIOR_PRESETS: dict[str, dict] = {
    "cave": {
        "title": "Cave",
        "long_prompt": (
            "A natural cave interior with layered stone chambers and believable tunnel branching. "
            "Include underground pools, dripping water, mineral deposits, and optional crystals, fungi, "
            "or nests. Natural bottlenecks and wider encounter chambers. Verticality implied through ledges, "
            "pits, and drop shafts. Strong rock mass silhouettes and readable traversal paths. "
            "Hidden alcoves and optional beast den, shrine, or smuggler cache."
        ),
        "grid_rules": (
            "Tunnels preserve minimum 2-cell playable width. Chambers support token movement with "
            "at least 6x6 clear cells. Hazards occupy defined cells. No micro-gaps or broken wall alignment."
        ),
        "room_rules": "natural chambers of varying size, no right angles, organic wall shapes",
        "negative_prompt": "grid-perfect walls, rectangular rooms, sterile corridors, unusable cramped passages",
        "type_class": "dungeon",
    },
    "dungeon": {
        "title": "Dungeon",
        "long_prompt": (
            "A stone dungeon with meaningful room network: loops, chokepoints, secrets, and a memorable "
            "central chamber. Include armory, prison, barracks, crypt, ritual room, boss room, or treasury "
            "depending on theme. Architecturally coherent wall layout with strong faction/theme identity. "
            "Encounter spaces and exploration spaces balanced."
        ),
        "grid_rules": (
            "All rooms and corridors align to grid. Doors and walls snap cleanly. "
            "Reserve tactical combat space in key rooms. No broken corridor widths. Navigation readable."
        ),
        "room_rules": "rectangular and irregular rooms, corridors 2-3 cells wide, main chamber 10x10+",
        "negative_prompt": "open field layout, no walls, no doors, inaccessible rooms, dead-end-only corridors",
        "type_class": "dungeon",
    },
    "crypt": {
        "title": "Crypt",
        "long_prompt": (
            "An ancient stone crypt with burial niches, sarcophagi, and ritual spaces. "
            "Include catacomb passages, funerary chambers, a central burial vault, and optional undead lore "
            "elements such as bone piles, candles, and altar. Oppressive atmosphere, tight corridors opening "
            "into wider ceremonial spaces."
        ),
        "grid_rules": "corridors 2-cell wide, burial alcoves 1x2 cells, main vault 8x8+",
        "room_rules": "linear main axis with branching burial wings, ceremonial chamber at center or end",
        "negative_prompt": "bright cheerful decor, living quarters, kitchens, tavern elements",
        "type_class": "dungeon",
    },
    "tavern": {
        "title": "Tavern Interior",
        "long_prompt": (
            "A fantasy tavern interior with a strong hearth focal point, common room with spaced tables, "
            "bar counter, kitchen and service route, and optional cellar. Table spacing allows token movement. "
            "Mood variants: roadside cozy, dockside rough, noble establishment, shady backstreet."
        ),
        "grid_rules": (
            "Tables occupy 2x2 cells. Bar counter along one wall. Fireplace 2x2. Stairs 2x3. "
            "Maintain clear 2-cell movement lanes between tables. All doors align to walls."
        ),
        "room_rules": "common room as main space, bar visible from entrance, kitchen accessible from bar, optional stairs to rooms",
        "negative_prompt": "dungeon elements, no exits, cramped unusable layout, no seating areas",
        "type_class": "house",
    },
    "house": {
        "title": "Village House",
        "long_prompt": (
            "A modest village house interior with believable room adjacency: entry hall, kitchen, bedroom, "
            "sitting room, optional storage. Poor cottage to prosperous merchant variants. "
            "Furniture snapped to usable cells. Doorway spacing supports movement."
        ),
        "grid_rules": "rooms minimum 4x4 cells, corridors 2 cells wide, furniture doesn't block doorways",
        "room_rules": "2-5 rooms depending on size, practical layout, no wasted space",
        "negative_prompt": "dungeon feel, no windows, maze-like corridors, oversized empty rooms",
        "type_class": "house",
    },
    "manor": {
        "title": "Manor House",
        "long_prompt": (
            "A noble manor interior with entry hall, great hall, dining room, study, master bedroom, "
            "servant quarters, kitchen, pantry, and optional secret passages. Wealth reflected in room sizes "
            "and furnishings. Distinct service and noble wings."
        ),
        "grid_rules": "great hall 10x8+, bedrooms 6x6+, corridors 2-3 cells wide",
        "room_rules": "formal rooms face front, service areas at rear, symmetry in noble areas",
        "negative_prompt": "dungeon layout, single large room, no room differentiation",
        "type_class": "house",
    },
    "blacksmith": {
        "title": "Blacksmith",
        "long_prompt": (
            "A fantasy blacksmith workshop with forge station as centerpiece, anvil, quench barrel, "
            "tool racks, coal/fuel storage, finished goods display, and optional back storage room. "
            "Heat and soot atmosphere. Clear working space around forge."
        ),
        "grid_rules": "forge occupies 2x3 cells, anvil 1x2, quench barrel 1x1, work lanes 2 cells clear",
        "room_rules": "main forge room with side storage, optional attached house living quarters",
        "negative_prompt": "clean sterile interior, no forge, residential-only layout",
        "type_class": "house",
    },
    "temple": {
        "title": "Temple",
        "long_prompt": (
            "A divine temple interior with nave, altar dais, side chapels, vestry, and optional underground "
            "vault or catacombs. Sacred geometry, columns, and devotional spaces. Deity theme reflected in "
            "symbols, materials, and ceremonial layout."
        ),
        "grid_rules": "nave 8 cells wide, altar dais 4x4+, columns in pairs flanking nave",
        "room_rules": "axial layout with altar at far end, side rooms branching off nave",
        "negative_prompt": "commercial interior, tavern feel, dungeon without religious elements",
        "type_class": "house",
    },
    "tower": {
        "title": "Tower",
        "long_prompt": (
            "A wizard or guard tower with multiple floors shown as separate rooms: ground level storage/guard, "
            "main study/workshop, upper sleeping quarters, roof battlements. Spiral staircase connecting floors. "
            "Arcane or military theme."
        ),
        "grid_rules": "tower footprint 8x8 to 12x12, staircase 2x3, each floor distinct use",
        "room_rules": "circular or square tower cross-section, central stair, rooms ring the stair",
        "negative_prompt": "single floor, no vertical element, sprawling footprint",
        "type_class": "house",
    },
    "mine": {
        "title": "Mine",
        "long_prompt": (
            "An active or abandoned mine with main shaft, ore veins, support beam tunnels, "
            "minecart tracks, storage and equipment areas, optional collapse zones, and underground "
            "cavern breakthrough. Functional layout with extraction logic."
        ),
        "grid_rules": "main shaft 3 cells wide, branching tunnels 2 cells, cavern chambers 8x8+",
        "room_rules": "linear main tunnel with branching ore veins, wide collection chambers at intersections",
        "negative_prompt": "random cave without logic, no equipment, no shafts",
        "type_class": "dungeon",
    },
    "castle_keep": {
        "title": "Castle Keep",
        "long_prompt": (
            "A castle keep interior with great hall, throne/audience chamber, garrison quarters, "
            "armory, chapel, kitchens, and dungeon cells. Defensive architecture with thick walls, "
            "murder holes, portcullis, and great tower. Active or ruined variants."
        ),
        "grid_rules": "great hall 12x8+, throne room 10x10+, walls 2 cells thick, courtyard 8x8+",
        "room_rules": "defensive outer ring with inner keep, service areas in corners, great hall central",
        "negative_prompt": "residential home scale, no defensive features, modern layout",
        "type_class": "castle",
    },
    "bandit_hideout": {
        "title": "Bandit Hideout",
        "long_prompt": (
            "A bandit or criminal hideout repurposed from cave, ruin, or abandoned building. "
            "Guard posts, sleeping areas, loot storage, interrogation space, captain's quarters. "
            "Signs of habitation, makeshift fortification, escape routes."
        ),
        "grid_rules": "guard post at entrance, storage in back, main hall central",
        "room_rules": "organic layout adapted from existing structure, improvised barricades",
        "negative_prompt": "clean professional architecture, no defensive positions, single room",
        "type_class": "dungeon",
    },
    "cult_lair": {
        "title": "Cult Lair",
        "long_prompt": (
            "A secret cult lair with ritual chamber as centerpiece, initiate dormitories, "
            "preparation rooms, sacrificial altar, forbidden library, and hidden underground vault. "
            "Dark symbols, candles, and ritual geometry throughout. Multiple layers of access control."
        ),
        "grid_rules": "ritual chamber 12x12+, altar platform raised, corridors narrow and twisting",
        "room_rules": "concentric access levels: public facade, inner sanctuary, secret vault",
        "negative_prompt": "bright open layout, no ritual elements, domestic feel",
        "type_class": "dungeon",
    },
    "prison": {
        "title": "Prison",
        "long_prompt": (
            "A dungeon prison with guard post, cell block, interrogation room, guard barracks, "
            "armory, and warden's office. Cells line corridors with locked doors. Signs of both "
            "long-term confinement and recent activity."
        ),
        "grid_rules": "cells 2x3 each, cell corridor 3 wide, guard post covers cell block entrance",
        "room_rules": "linear cell blocks off central guard corridor, administrative area near entrance",
        "negative_prompt": "open prison without cells, no guard infrastructure",
        "type_class": "dungeon",
    },
    "sewer": {
        "title": "Sewer",
        "long_prompt": (
            "An urban sewer network beneath a city with main channels, maintenance walkways, "
            "junction chambers, grate access points, overflow chambers, and hidden criminal spaces. "
            "Flowing water channels with narrow walkways beside them."
        ),
        "grid_rules": "water channels 2 cells wide, walkways 1-2 cells beside channels, junction chambers 6x6+",
        "room_rules": "grid-like main network with organic flood overflow areas",
        "negative_prompt": "dry dungeon without water channels, residential interior",
        "type_class": "dungeon",
    },
}

# ────────────────────────────────────────────────
# Image provider abstraction
# ────────────────────────────────────────────────

class ImageProviderBase:
    """Base class for image generation providers."""

    async def generate(self, prompt: str, negative_prompt: str, width: int, height: int,
                       style: str = "", **kwargs) -> dict:
        raise NotImplementedError


class StubImageProvider(ImageProviderBase):
    """
    Stub provider — generates a colored grid placeholder so the cartographer
    flow produces a visible result even without a real image-generation API.
    Replace with a real provider (Stability AI, DALL·E, Replicate, etc.).
    Set IMAGE_PROVIDER env var to configure.
    """

    async def generate(self, prompt: str, negative_prompt: str, width: int, height: int,
                       style: str = "", **kwargs) -> dict:
        logger.info("[Cartographer:Stub] Generating placeholder %dx%d image. Prompt: %.120s…", width, height, prompt)
        note = (
            "No image provider configured. "
            "Set STABILITY_API_KEY, OPENAI_API_KEY (for dall-e-3), or REPLICATE_API_TOKEN "
            "to enable real image generation."
        )
        data_url = _make_stub_placeholder(width, height, style)
        return {
            "url": None,
            "stub": True,
            "width": width,
            "height": height,
            "provider": "stub",
            "note": note,
            "preview_data_url": data_url,
        }


def _make_stub_placeholder(width: int, height: int, style: str = "") -> str | None:
    """
    Generate a colored, grid-lined placeholder image using Pillow and return
    it as a ``data:image/jpeg;base64,…`` string.  Returns None if Pillow is
    not available.
    """
    try:
        # Pillow is an optional dependency — import lazily so the module loads
        # even in environments where it is not installed.
        import io as _io
        from PIL import Image, ImageDraw  # type: ignore

        # Scale down to a reasonable preview size
        scale = min(1.0, 512 / max(width, height, 1))
        pw = max(64, int(width * scale))
        ph = max(64, int(height * scale))

        # Background colour varies by style so different maps look distinct
        style_colors: dict[str, tuple[int, int, int]] = {
            "fantasy-art": (38, 28, 48),
            "tile-texture": (35, 38, 42),
            "dark":         (22, 18, 28),
            "atlas":        (42, 36, 28),
            "painterly":    (36, 42, 30),
        }
        r, g, b = style_colors.get(style, (32, 30, 42))

        img = Image.new("RGB", (pw, ph), (r, g, b))
        draw = ImageDraw.Draw(img)

        # Draw a subtle grid
        cell = max(16, pw // 16)
        grid_col = (min(r + 35, 255), min(g + 35, 255), min(b + 35, 255))
        for x in range(0, pw, cell):
            draw.line([(x, 0), (x, ph)], fill=grid_col, width=1)
        for y in range(0, ph, cell):
            draw.line([(0, y), (pw, y)], fill=grid_col, width=1)

        # Centered label
        label = "Map placeholder\nConfigure an AI provider for real art"
        label_col = (min(r + 130, 255), min(g + 110, 255), min(b + 70, 255))
        draw.multiline_text((pw // 2, ph // 2), label, fill=label_col, anchor="mm", align="center")

        buf = _io.BytesIO()
        img.save(buf, "JPEG", quality=75)
        encoded = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{encoded}"
    except Exception as exc:
        logger.debug("[Cartographer:Stub] Could not generate placeholder image: %s", exc)
        return None


class StabilityImageProvider(ImageProviderBase):
    """
    Stability AI image generation provider.
    Requires STABILITY_API_KEY environment variable.

    DEPRECATED: The Stability AI v1 REST endpoint used here
    (stable-diffusion-xl-1024-v1-0) is a legacy API path. Stability AI has
    migrated to the Stability AI Platform API v2beta. This provider will
    continue to work while the v1 endpoint remains live, but new deployments
    should prefer OpenAI (gpt-image-1) or Replicate instead.
    See: https://platform.stability.ai/docs/api-reference
    """

    BASE_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(self, prompt: str, negative_prompt: str, width: int, height: int,
                       style: str = "", **kwargs) -> dict:
        # Clamp to Stability-accepted sizes (multiples of 64, min 512)
        w = max(512, min(1536, (width // 64) * 64))
        h = max(512, min(1536, (height // 64) * 64))

        payload = {
            "text_prompts": [
                {"text": prompt, "weight": 1.0},
                {"text": negative_prompt, "weight": -1.0},
            ],
            "cfg_scale": 7,
            "width": w,
            "height": h,
            "samples": 1,
            "steps": 30,
        }
        if style:
            payload["style_preset"] = style

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(self.BASE_URL, json=payload, headers=headers)
            if r.status_code != 200:
                logger.error("[Cartographer:Stability] API error %d: %s", r.status_code, r.text[:300])
                return {"url": None, "error": f"Stability API error {r.status_code}"}

            data = r.json()
            artifacts = data.get("artifacts", [])
            if not artifacts:
                return {"url": None, "error": "No artifacts returned"}

            import base64
            img_b64 = artifacts[0].get("base64", "")
            if not img_b64:
                return {"url": None, "error": "No image data"}

            return {
                "url": f"data:image/png;base64,{img_b64}",
                "width": w,
                "height": h,
                "provider": "stability",
            }
        except Exception as exc:
            logger.error("[Cartographer:Stability] Error: %s", exc)
            return {"url": None, "error": str(exc)}


class OpenAIImageProvider(ImageProviderBase):
    """
    OpenAI image generation provider using gpt-image-1.
    Requires OPENAI_API_KEY environment variable.

    Uses the current gpt-image-1 model which supports richer prompt adherence
    and higher quality output than DALL·E 3 for fantasy map art.
    gpt-image-1 returns base64-encoded PNG; response_format is always b64_json.

    Supported sizes: 1024x1024, 1536x1024, 1024x1536, auto
    """

    BASE_URL = "https://api.openai.com/v1/images/generations"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(self, prompt: str, negative_prompt: str, width: int, height: int,
                       style: str = "", **kwargs) -> dict:
        # gpt-image-1 supports 1024x1024, 1536x1024 (landscape), 1024x1536 (portrait)
        if width > height:
            size = "1536x1024"
        elif height > width:
            size = "1024x1536"
        else:
            size = "1024x1024"

        payload = {
            "model": "gpt-image-1",
            "prompt": prompt[:32000],   # gpt-image-1 supports up to 32k char prompts
            "n": 1,
            "size": size,
            "quality": "high",
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                r = await client.post(self.BASE_URL, json=payload, headers=headers)
            if r.status_code != 200:
                logger.error("[Cartographer:OpenAI] API error %d: %s", r.status_code, r.text[:300])
                return {"url": None, "error": f"OpenAI API error {r.status_code}"}

            data = r.json()
            item = (data.get("data") or [{}])[0]
            # gpt-image-1 returns b64_json
            b64 = item.get("b64_json", "")
            if b64:
                return {
                    "url": f"data:image/png;base64,{b64}",
                    "width": int(size.split("x")[0]),
                    "height": int(size.split("x")[1]),
                    "provider": "openai",
                }
            # Fallback: some model variants still return a URL
            url = item.get("url", "")
            if url:
                return {
                    "url": url,
                    "width": int(size.split("x")[0]),
                    "height": int(size.split("x")[1]),
                    "provider": "openai",
                }
            return {"url": None, "error": "No image data in OpenAI response"}
        except Exception as exc:
            logger.error("[Cartographer:OpenAI] Error: %s", exc)
            return {"url": None, "error": str(exc)}


class ReplicateImageProvider(ImageProviderBase):
    """
    Replicate image generation provider.
    Requires REPLICATE_API_TOKEN environment variable.
    Default model: black-forest-labs/flux-1.1-pro (good for art/maps).
    Override with REPLICATE_MODEL env var.
    """

    API_URL = "https://api.replicate.com/v1/models/{model}/predictions"
    POLL_URL = "https://api.replicate.com/v1/predictions/{id}"
    DEFAULT_MODEL = "black-forest-labs/flux-1.1-pro"

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.model = os.environ.get("REPLICATE_MODEL", self.DEFAULT_MODEL)

    async def generate(self, prompt: str, negative_prompt: str, width: int, height: int,
                       style: str = "", **kwargs) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Prefer": "wait=60",
        }
        payload = {
            "input": {
                "prompt": prompt[:2000],
                "width": max(512, min(2048, width)),
                "height": max(512, min(2048, height)),
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
            }
        }
        if negative_prompt:
            payload["input"]["negative_prompt"] = negative_prompt

        url = self.API_URL.format(model=self.model)
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(url, json=payload, headers=headers)
                if r.status_code not in (200, 201):
                    logger.error("[Cartographer:Replicate] API error %d: %s", r.status_code, r.text[:300])
                    return {"url": None, "error": f"Replicate API error {r.status_code}"}
                data = r.json()

                # Poll if not complete
                for _ in range(30):
                    status = data.get("status")
                    if status == "succeeded":
                        break
                    if status in ("failed", "canceled"):
                        return {"url": None, "error": f"Replicate prediction {status}"}
                    pred_id = data.get("id")
                    if not pred_id:
                        break
                    import asyncio
                    await asyncio.sleep(3)
                    poll_r = await client.get(
                        self.POLL_URL.format(id=pred_id), headers=headers
                    )
                    data = poll_r.json()

            output = data.get("output")
            if isinstance(output, list) and output:
                output = output[0]
            if not output:
                return {"url": None, "error": "No output from Replicate"}

            return {
                "url": output,
                "width": width,
                "height": height,
                "provider": "replicate",
            }
        except Exception as exc:
            logger.error("[Cartographer:Replicate] Error: %s", exc)
            return {"url": None, "error": str(exc)}


def get_image_provider() -> ImageProviderBase:
    """
    Return the configured image provider.

    Auto-detection priority (when IMAGE_PROVIDER is not set):
      1. OPENAI_API_KEY      → gpt-image-1 (recommended)
      2. REPLICATE_API_TOKEN → Replicate / Flux (good alternative)
      3. STABILITY_API_KEY   → Stability AI SDXL (deprecated v1 API)
      4. stub               → no-op placeholder

    Override with IMAGE_PROVIDER env var: openai | replicate | stability | stub
    """
    forced = os.environ.get("IMAGE_PROVIDER", "").strip().lower()

    if forced == "openai" or (not forced and os.environ.get("OPENAI_API_KEY", "").strip()):
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if key:
            return OpenAIImageProvider(key)

    if forced == "replicate" or (not forced and os.environ.get("REPLICATE_API_TOKEN", "").strip()):
        token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
        if token:
            return ReplicateImageProvider(token)

    if forced == "stability" or (not forced and os.environ.get("STABILITY_API_KEY", "").strip()):
        key = os.environ.get("STABILITY_API_KEY", "").strip()
        if key:
            logger.warning(
                "[Cartographer] Using deprecated Stability AI v1 provider. "
                "Consider switching to OPENAI_API_KEY (gpt-image-1) or REPLICATE_API_TOKEN."
            )
            return StabilityImageProvider(key)

    return StubImageProvider()


# ────────────────────────────────────────────────
# Claude integration — structure layer
# ────────────────────────────────────────────────

_CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
_CLAUDE_MODEL = "claude-3-5-sonnet-20241022"


def _get_anthropic_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def _resolve_grid_dimensions(
    map_scope: str,
    output_mode: str,
    dimensions_preset: str,
    grid_width: int | None,
    grid_height: int | None,
    interior_type: str = "",
) -> tuple[int, int]:
    """Resolve grid width/height from preset + explicit overrides."""
    if grid_width and grid_height:
        return int(grid_width), int(grid_height)

    # Pick defaults class
    type_key = INTERIOR_TYPE_CLASS.get(interior_type or map_scope, "interior")
    defaults = GRID_DEFAULTS.get(type_key, GRID_DEFAULTS["interior"])

    preset_key = (dimensions_preset or "medium").lower()
    if preset_key in defaults:
        return defaults[preset_key]

    # Fallback
    return (36, 36)


def _build_style_guidance(image_style: str, output_mode: str) -> str:
    style_map = {
        "atlas": "premium hand-painted fantasy atlas art, rich color, clear cartographic labels",
        "painterly": "painterly fantasy illustration, brushstroke texture, warm tones",
        "inkwash": "detailed ink-wash line art with watercolor washes, classic fantasy cartography style",
        "tactical": "clean top-down tactical map, high contrast, readable grid cells",
        "realistic": "semi-realistic fantasy map with aerial perspective and atmospheric lighting",
        "dark": "dark fantasy map with deep shadows, muted palette, oppressive mood",
        "ancient": "aged parchment map, sepia tones, hand-drawn style, faded edges",
        "vibrant": "vibrant fantasy illustration, saturated colors, dramatic lighting, high detail",
    }
    base = style_map.get(image_style or "atlas", style_map["atlas"])
    if output_mode == "tactical_grid":
        base += ", functional top-down view, clean cell borders, readable props"
    elif output_mode == "hybrid":
        base += ", balanced artistic and tactical clarity, premium but playable"
    return base


async def call_claude_cartographer(request_data: dict) -> dict:
    """
    Call Claude to act as cartography director and produce structured map plan + image prompt.
    Claude NEVER generates images — it produces structured JSON.
    """
    api_key = _get_anthropic_key()
    if not api_key:
        logger.warning("[Cartographer] ANTHROPIC_API_KEY not set — using procedural fallback")
        return _procedural_fallback(request_data)

    map_scope = request_data.get("map_scope", "interior")
    output_mode = request_data.get("output_mode", "illustrated_overview")
    grid_type = request_data.get("grid_type", "square")
    grid_scale = request_data.get("grid_scale", "5ft")
    grid_width, grid_height = _resolve_grid_dimensions(
        map_scope=map_scope,
        output_mode=output_mode,
        dimensions_preset=request_data.get("dimensions_preset", "medium"),
        grid_width=request_data.get("grid_width"),
        grid_height=request_data.get("grid_height"),
        interior_type=request_data.get("interior_preset", ""),
    )
    image_style = request_data.get("image_style", "atlas")
    terrain_preset = request_data.get("terrain_preset", "")
    build_preset = request_data.get("build_preset", "")
    interior_preset = request_data.get("interior_preset", "")
    description = (request_data.get("description") or "").strip()[:800]
    pixel_size = request_data.get("pixel_export_size", 2048)
    detail_density = request_data.get("detail_density", "medium")
    poi_density = request_data.get("poi_density", "medium")

    # Assemble context from presets
    terrain_ctx = ""
    if terrain_preset and terrain_preset in TERRAIN_PRESETS:
        tp = TERRAIN_PRESETS[terrain_preset]
        terrain_ctx = (
            f"Terrain: {tp['title']}. "
            f"Keywords: {', '.join(tp['terrain_keywords'])}. "
            f"Mood: {', '.join(tp['mood_keywords'])}. "
            f"Composition: {tp['composition_rules']}."
        )

    build_ctx = ""
    if build_preset and build_preset in BUILD_PRESETS:
        bp = BUILD_PRESETS[build_preset]
        build_ctx = (
            f"Build/Location: {bp['title']}. "
            f"Architecture: {', '.join(bp['architecture_keywords'])}. "
            f"POI rules: {bp['poi_rules']}."
        )

    interior_ctx = ""
    if interior_preset and interior_preset in INTERIOR_PRESETS:
        ip = INTERIOR_PRESETS[interior_preset]
        interior_ctx = (
            f"Interior type: {ip['title']}. "
            f"Layout prompt: {ip['long_prompt']} "
            f"Grid rules: {ip['grid_rules']} "
            f"Room rules: {ip['room_rules']}."
        )

    style_guidance = _build_style_guidance(image_style, output_mode)

    system_prompt = (
        "You are a master fantasy cartographer and DM tool architect. "
        "Your job is to design map layouts, compose image generation prompts, "
        "and output structured JSON for a D&D tabletop editor. "
        "You do NOT generate images yourself. You plan, design, and describe maps "
        "so that a separate image provider can render the final art. "
        "Always respond with valid JSON only — no markdown fences, no extra text."
    )

    user_prompt = f"""Design a fantasy map with these specifications:

MAP SCOPE: {map_scope}
OUTPUT MODE: {output_mode}
GRID TYPE: {grid_type}
GRID SCALE: {grid_scale} per cell
GRID DIMENSIONS: {grid_width}w x {grid_height}h cells
IMAGE STYLE: {image_style} — {style_guidance}
DETAIL DENSITY: {detail_density}
POI DENSITY: {poi_density}
TARGET PIXEL SIZE: {pixel_size}px
{f"DESCRIPTION: {description}" if description else ""}
{terrain_ctx}
{build_ctx}
{interior_ctx}

Generate a complete JSON map plan with exactly this structure:
{{
  "title": "map title",
  "summary": "2-sentence description of what this map depicts",
  "output_mode": "{output_mode}",
  "grid_type": "{grid_type}",
  "grid_scale": "{grid_scale}",
  "grid_width": {grid_width},
  "grid_height": {grid_height},
  "map_scope": "{map_scope}",
  "terrain_tags": ["tag1", "tag2"],
  "build_tags": ["tag1", "tag2"],
  "style_brief": "1-2 sentences describing visual style",
  "image_prompt": "The complete high-quality image generation prompt. Must be richly detailed, specific about style ({style_guidance}), include all terrain and structural elements, lighting, atmosphere, and composition. For tactical/hybrid modes ensure top-down perspective and grid-aware layout clarity.",
  "negative_prompt": "comma-separated negative terms to avoid in generation",
  "pois": [
    {{"name": "POI name", "type": "poi type", "x": 0.0, "y": 0.0, "description": "brief desc", "interior_type": "tavern|cave|dungeon|etc"}}
  ],
  "roads": [
    {{"kind": "road|river", "label": "name", "points": [[0.1, 0.2], [0.5, 0.6]]}}
  ],
  "labels": [
    {{"text": "label text", "x": 0.0, "y": 0.0, "size": "small|medium|large"}}
  ],
  "region_notes": "notes about this region for DM",
  "interior_candidates": ["list of POI names that could generate interiors"],
  "tactical_placement": {{
    "spawn_areas": ["description of player spawn zones"],
    "enemy_zones": ["description of enemy placement zones"],
    "key_terrain": ["description of significant tactical terrain"],
    "chokepoints": ["description of chokepoints and bottlenecks"]
  }},
  "room_list": [
    {{"id": "room1", "name": "room name", "purpose": "purpose", "width_cells": 6, "height_cells": 8, "notes": ""}}
  ],
  "wall_suggestions": ["description of wall placement"],
  "door_suggestions": ["description of door placement"],
  "prop_suggestions": ["item: cell footprint description"],
  "hazard_suggestions": ["hazard: location description"],
  "populate_suggestions": {{
    "monsters": [{{"name": "monster name", "count": 1, "placement": "placement hint"}}],
    "hazards": [{{"name": "hazard name", "radius_ft": 10, "effect": "effect description"}}],
    "props": [{{"kind": "prop kind", "note": "placement note"}}]
  }}
}}

Rules:
- POI x/y are 0.0-1.0 fractional positions on the map
- road/river points are 0.0-1.0 fractional coordinates
- room_list only needed for interior/tactical maps
- wall/door/prop/hazard suggestions only needed for tactical_grid and hybrid modes
- negative_prompt must be specific and useful for the image provider
- image_prompt must be comprehensive and evocative — this is what drives the final art quality
"""

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                _CLAUDE_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": _CLAUDE_MODEL,
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )

        if r.status_code != 200:
            logger.error("[Cartographer:Claude] API error %d: %s", r.status_code, r.text[:500])
            return _procedural_fallback(request_data)

        content = r.json().get("content", [])
        raw_text = ""
        for block in content:
            if block.get("type") == "text":
                raw_text += block.get("text", "")

        raw_text = raw_text.strip()
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].rstrip()

        plan = json.loads(raw_text)
        # Ensure resolved grid dimensions are present
        plan["grid_width"] = plan.get("grid_width") or grid_width
        plan["grid_height"] = plan.get("grid_height") or grid_height
        return plan

    except json.JSONDecodeError as exc:
        logger.error("[Cartographer:Claude] JSON parse error: %s. Raw: %.500s", exc, raw_text)
        return _procedural_fallback(request_data)
    except Exception as exc:
        logger.error("[Cartographer:Claude] Unexpected error: %s", exc)
        return _procedural_fallback(request_data)


def _procedural_fallback(request_data: dict) -> dict:
    """
    Fallback map plan when Claude is not available.
    Produces a reasonable minimal plan from the request inputs.
    """
    map_scope = request_data.get("map_scope", "interior")
    output_mode = request_data.get("output_mode", "illustrated_overview")
    terrain_preset = request_data.get("terrain_preset", "")
    build_preset = request_data.get("build_preset", "")
    interior_preset = request_data.get("interior_preset", "")
    image_style = request_data.get("image_style", "atlas")
    description = (request_data.get("description") or "").strip()

    grid_width, grid_height = _resolve_grid_dimensions(
        map_scope=map_scope,
        output_mode=output_mode,
        dimensions_preset=request_data.get("dimensions_preset", "medium"),
        grid_width=request_data.get("grid_width"),
        grid_height=request_data.get("grid_height"),
        interior_type=interior_preset,
    )

    terrain_name = TERRAIN_PRESETS.get(terrain_preset, {}).get("title", terrain_preset or "fantasy terrain")
    build_name = BUILD_PRESETS.get(build_preset, {}).get("title", build_preset or "")
    interior_name = INTERIOR_PRESETS.get(interior_preset, {}).get("title", interior_preset or map_scope)

    subject = interior_name if interior_preset else (
        f"{terrain_name} {build_name}".strip() if (terrain_preset or build_preset) else map_scope
    )

    style_guidance = _build_style_guidance(image_style, output_mode)

    if description:
        image_prompt = (
            f"{description}. {style_guidance}. Fantasy tabletop map, "
            f"top-down view, highly detailed, professional cartographic quality."
        )
    else:
        image_prompt = (
            f"Premium fantasy tabletop map of {subject}. "
            f"{style_guidance}. "
            f"Top-down view, richly detailed, professional cartographic quality, "
            f"clear landmarks and terrain features, dramatic lighting."
        )

    negative_prompt = (
        "blurry, low quality, modern elements, photorealistic photography, "
        "text errors, watermark, signature, ugly composition, muddy colors, "
        "unusable tactical spaces, broken wall alignment"
    )

    interior_ip = INTERIOR_PRESETS.get(interior_preset, {})
    if interior_ip.get("negative_prompt"):
        negative_prompt += ", " + interior_ip["negative_prompt"]

    return {
        "title": f"{subject.title()} Map",
        "summary": f"A {output_mode.replace('_', ' ')} map of {subject}.",
        "output_mode": output_mode,
        "grid_type": request_data.get("grid_type", "square"),
        "grid_scale": request_data.get("grid_scale", "5ft"),
        "grid_width": grid_width,
        "grid_height": grid_height,
        "map_scope": map_scope,
        "terrain_tags": [terrain_preset] if terrain_preset else [],
        "build_tags": [build_preset] if build_preset else [],
        "style_brief": style_guidance,
        "image_prompt": image_prompt,
        "negative_prompt": negative_prompt,
        "pois": [],
        "roads": [],
        "labels": [],
        "region_notes": "",
        "interior_candidates": [],
        "tactical_placement": {
            "spawn_areas": [],
            "enemy_zones": [],
            "key_terrain": [],
            "chokepoints": [],
        },
        "room_list": [],
        "wall_suggestions": [],
        "door_suggestions": [],
        "prop_suggestions": [],
        "hazard_suggestions": [],
        "populate_suggestions": {
            "monsters": [],
            "hazards": [],
            "props": [],
        },
    }


# ────────────────────────────────────────────────
# Main pipeline entry points
# ────────────────────────────────────────────────

def _persist_generated_image(url: str | None, result_id: str) -> str | None:
    """
    Save a generated image to the local maps directory and return a /static/ URL.

    Handles:
    - data:image/...;base64,<data> — decoded and saved to disk
    - Already a /static/ path — returned as-is
    - External http/https URLs — downloaded and saved
    - None / empty — returns None
    """
    if not url:
        return None

    from server.paths import MAPS_DIR  # avoid circular import at module level

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"gen_{result_id}.jpg"
    dest = MAPS_DIR / filename

    try:
        if url.startswith("/static/"):
            return url

        if url.startswith("data:"):
            # data:<mime>;base64,<data>
            header, _, raw = url.partition(",")
            img_bytes = base64.b64decode(raw)
            _write_image_bytes(img_bytes, dest)
            return f"/static/maps/{filename}"

        # External URL (e.g. OpenAI temporary URL)
        with httpx.Client(timeout=30) as client:
            resp = client.get(url)
            resp.raise_for_status()
            _write_image_bytes(resp.content, dest)
        return f"/static/maps/{filename}"

    except Exception as exc:
        logger.warning("[Cartographer] Could not persist generated image: %s", exc)
        return None


def _write_image_bytes(data: bytes, dest: Path) -> None:
    """Write image bytes to dest, compressing with PIL if available."""
    try:
        import io
        from PIL import Image  # type: ignore
        img = Image.open(io.BytesIO(data)).convert("RGB")
        if img.width > 4096 or img.height > 4096:
            img.thumbnail((4096, 4096), Image.LANCZOS)
        img.save(dest, "JPEG", quality=88, optimize=True)
    except Exception:
        dest.write_bytes(data)


async def generate_map(request_data: dict) -> dict:
    """
    Full cartography pipeline:
    1. Claude builds structured map plan + image prompt
    2. Image provider renders final art
    3. Returns editor-importable result
    """
    # Validate and sanitize inputs
    output_mode = str(request_data.get("output_mode", "illustrated_overview"))
    if output_mode not in ("illustrated_overview", "tactical_grid", "hybrid"):
        output_mode = "illustrated_overview"
    request_data["output_mode"] = output_mode

    grid_type = str(request_data.get("grid_type", "square"))
    if grid_type not in ("none", "square", "hex"):
        grid_type = "square"
    # Enforce grid type rules
    if output_mode == "tactical_grid" and grid_type == "none":
        grid_type = "square"
    request_data["grid_type"] = grid_type

    pixel_size = int(request_data.get("pixel_export_size", 2048))
    pixel_size = max(512, min(4096, pixel_size))

    # Resolve final pixel dimensions from grid aspect ratio
    grid_width, grid_height = _resolve_grid_dimensions(
        map_scope=request_data.get("map_scope", "interior"),
        output_mode=output_mode,
        dimensions_preset=request_data.get("dimensions_preset", "medium"),
        grid_width=request_data.get("grid_width"),
        grid_height=request_data.get("grid_height"),
        interior_type=request_data.get("interior_preset", ""),
    )
    request_data["grid_width"] = grid_width
    request_data["grid_height"] = grid_height

    if grid_height <= 0:
        raise ValueError(f"grid_height must be positive, got {grid_height}")
    aspect = grid_width / grid_height
    if aspect >= 1:
        img_w = pixel_size
        img_h = max(512, int(pixel_size / aspect))
    else:
        img_h = pixel_size
        img_w = max(512, int(pixel_size * aspect))

    # Step 1: Claude generates structured plan
    plan = await call_claude_cartographer(request_data)

    # Step 2: image provider generates artwork
    image_style = request_data.get("image_style", "atlas")
    stability_style = ""
    if image_style in ("painterly", "atlas", "ancient"):
        stability_style = "fantasy-art"
    elif image_style == "tactical":
        stability_style = "tile-texture"

    provider = get_image_provider()
    image_result = await provider.generate(
        prompt=plan.get("image_prompt", ""),
        negative_prompt=plan.get("negative_prompt", ""),
        width=img_w,
        height=img_h,
        style=stability_style,
    )

    # Step 3: persist generated image and assemble editor-importable result
    result_id = str(uuid.uuid4())[:8]
    static_url = _persist_generated_image(image_result.get("url"), result_id)
    if static_url:
        image_result = {**image_result, "url": static_url}
    return {
        "ok": True,
        "result_id": result_id,
        "plan": plan,
        "image": image_result,
        "editor_import": {
            "title": plan.get("title", "Generated Map"),
            "background_url": (
                static_url
                or image_result.get("url")
                or image_result.get("preview_data_url")
            ),
            "grid_type": plan.get("grid_type", grid_type),
            "grid_scale": plan.get("grid_scale", "5ft"),
            "grid_width": plan.get("grid_width", grid_width),
            "grid_height": plan.get("grid_height", grid_height),
            "pois": plan.get("pois", []),
            "roads": plan.get("roads", []),
            "labels": plan.get("labels", []),
            "metadata": {
                "output_mode": output_mode,
                "summary": plan.get("summary", ""),
                "terrain_tags": plan.get("terrain_tags", []),
                "build_tags": plan.get("build_tags", []),
                "interior_candidates": plan.get("interior_candidates", []),
                "tactical_placement": plan.get("tactical_placement", {}),
                "room_list": plan.get("room_list", []),
                "populate_suggestions": plan.get("populate_suggestions", {"monsters": [], "hazards": [], "props": []}),
            },
        },
    }


async def generate_interior(request_data: dict) -> dict:
    """
    Generate a linked interior map from a POI.
    Inherits parent map context and prefills from POI type.
    """
    poi_name = (request_data.get("poi_name") or "").strip()
    poi_type = (request_data.get("poi_type") or "").strip().lower()
    parent_context = request_data.get("parent_context") or {}

    # Auto-map POI type to interior preset
    poi_to_interior = {
        "cave": "cave",
        "dungeon": "dungeon",
        "crypt": "crypt",
        "tavern": "tavern",
        "inn": "tavern",
        "house": "house",
        "home": "house",
        "manor": "manor",
        "blacksmith": "blacksmith",
        "smithy": "blacksmith",
        "temple": "temple",
        "shrine": "temple",
        "church": "temple",
        "tower": "tower",
        "wizard": "tower",
        "mine": "mine",
        "castle": "castle_keep",
        "fort": "castle_keep",
        "keep": "castle_keep",
        "prison": "prison",
        "jail": "prison",
        "sewer": "sewer",
        "bandit": "bandit_hideout",
        "hideout": "bandit_hideout",
        "cult": "cult_lair",
        "ruins": "dungeon",
        "ruin": "dungeon",
    }

    interior_preset = poi_to_interior.get(poi_type, request_data.get("interior_preset", "dungeon"))

    # Build interior request
    interior_request = {
        "map_scope": "interior",
        "output_mode": request_data.get("output_mode", "tactical_grid"),
        "grid_type": request_data.get("grid_type", "square"),
        "grid_scale": request_data.get("grid_scale", parent_context.get("grid_scale", "5ft")),
        "dimensions_preset": request_data.get("dimensions_preset", "medium"),
        "grid_width": request_data.get("grid_width"),
        "grid_height": request_data.get("grid_height"),
        "interior_preset": interior_preset,
        "image_style": request_data.get("image_style", parent_context.get("image_style", "atlas")),
        "description": (
            f"{poi_name} interior" if poi_name else f"{interior_preset} interior"
        ) + (
            f". Located in {parent_context.get('title', 'the region')}" if parent_context.get("title") else ""
        ) + (
            f". {request_data.get('description', '')}" if request_data.get("description") else ""
        ),
        "terrain_preset": parent_context.get("terrain_preset", ""),
        "pixel_export_size": request_data.get("pixel_export_size", 2048),
        "detail_density": request_data.get("detail_density", "high"),
        "poi_density": request_data.get("poi_density", "medium"),
        "poi_name": poi_name,
        "parent_map_title": parent_context.get("title", ""),
        "parent_poi_id": request_data.get("poi_id"),
    }

    result = await generate_map(interior_request)

    # Tag the result as a linked interior
    if result.get("ok"):
        result["interior_link"] = {
            "poi_id": request_data.get("poi_id"),
            "poi_name": poi_name,
            "poi_type": poi_type,
            "interior_preset": interior_preset,
            "parent_map_title": parent_context.get("title", ""),
        }

    return result


def get_presets_manifest() -> dict:
    """Return all available presets for the editor UI."""
    return {
        "terrain_presets": [
            {"key": k, "title": v["title"]} for k, v in TERRAIN_PRESETS.items()
        ],
        "build_presets": [
            {"key": k, "title": v["title"]} for k, v in BUILD_PRESETS.items()
        ],
        "interior_presets": [
            {"key": k, "title": v["title"], "type_class": v.get("type_class", "interior")}
            for k, v in INTERIOR_PRESETS.items()
        ],
        "grid_defaults": GRID_DEFAULTS,
        "output_modes": [
            {"value": "illustrated_overview", "label": "Illustrated Overview"},
            {"value": "tactical_grid", "label": "Tactical Grid"},
            {"value": "hybrid", "label": "Hybrid"},
        ],
        "grid_types": [
            {"value": "none", "label": "None"},
            {"value": "square", "label": "Square"},
            {"value": "hex", "label": "Hex"},
        ],
        "grid_scales": [
            {"value": "5ft", "label": "5 ft / cell"},
            {"value": "10ft", "label": "10 ft / cell"},
            {"value": "25ft", "label": "25 ft / cell"},
            {"value": "50ft", "label": "50 ft / cell"},
            {"value": "custom", "label": "Custom"},
        ],
        "dimensions_presets": [
            {"value": "tiny", "label": "Tiny"},
            {"value": "small", "label": "Small"},
            {"value": "medium", "label": "Medium"},
            {"value": "large", "label": "Large"},
            {"value": "huge", "label": "Huge"},
            {"value": "custom", "label": "Custom"},
        ],
        "pixel_sizes": [
            {"value": 1024, "label": "1024 px"},
            {"value": 1536, "label": "1536 px"},
            {"value": 2048, "label": "2048 px"},
            {"value": 3072, "label": "3072 px"},
            {"value": "custom", "label": "Custom"},
        ],
        "image_styles": [
            {"value": "atlas", "label": "Fantasy Atlas"},
            {"value": "painterly", "label": "Painterly"},
            {"value": "inkwash", "label": "Ink & Wash"},
            {"value": "tactical", "label": "Tactical Clean"},
            {"value": "realistic", "label": "Realistic Aerial"},
            {"value": "dark", "label": "Dark Fantasy"},
            {"value": "ancient", "label": "Ancient Parchment"},
            {"value": "vibrant", "label": "Vibrant Illustrated"},
        ],
        "map_scopes": [
            {"value": "world", "label": "World"},
            {"value": "region", "label": "Region"},
            {"value": "local_area", "label": "Local Area"},
            {"value": "settlement", "label": "Settlement"},
            {"value": "interior", "label": "Interior"},
        ],
    }

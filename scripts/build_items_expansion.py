#!/usr/bin/env python3
"""
build_items_expansion.py — author + validate an item/crafting expansion pack.

Run from the repo root. It:
  1. Authors new magic items (spell-granting + attribute), crafting materials
     (including gap-fillers that existing recipes reference but lack records),
     and crafting recipes.
  2. Round-trips every item through server.item_schema.normalize_item_record so
     the output is guaranteed schema-correct (schema v2).
  3. Cross-checks: every granted spell_id exists in the rules spell list, and
     every recipe material name resolves to a real material record.
  4. Emits:  expanded_magic_items.json, expanded_crafting_materials.json,
             crafting_recipes_expansion.py,  VALIDATION_REPORT.md
"""
from __future__ import annotations
import json, glob, sys, pathlib

ROOT = pathlib.Path.cwd()
OUT = ROOT / "_expansion_out"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))

# --- load real vocab for validation -----------------------------------------
def _load_spell_ids() -> set[str]:
    ids = set()
    for f in glob.glob("server/data/rules/5e2024/**/*spell*.json", recursive=True):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        rows = d.get("spells", d.get("items", d)) if isinstance(d, dict) else d
        if isinstance(rows, list):
            for s in rows:
                if isinstance(s, dict) and (s.get("id") or s.get("slug")):
                    ids.add(s.get("id") or s.get("slug"))
    return ids

def _existing_material_names() -> set[str]:
    names = set()
    for f in glob.glob("server/data/rules/5e2024/items/*.json"):
        d = json.load(open(f, encoding="utf-8"))
        rows = d.get("items", d) if isinstance(d, dict) else d
        if isinstance(rows, list):
            for it in rows:
                if str(it.get("category", "")).lower() in ("material", "trade_goods_materials") or it.get("material_type"):
                    if it.get("name"):
                        names.add(it["name"])
    return names

SPELL_IDS = _load_spell_ids()

# ---------------------------------------------------------------------------
# helpers to author concise, schema-aligned records
# ---------------------------------------------------------------------------
def gspell(spell_id, name, charge_cost=1, cast_level=1):
    return {"id": spell_id, "name": name, "spell_id": spell_id,
            "charge_cost": charge_cost, "cast_level": cast_level,
            "uses_item_dc": True, "uses_item_attack_bonus": True}

def gaction(item_id, name, summary, charge_cost=1):
    # NOTE: real summary text — never the generic "Activate this item." filler.
    return {"id": f"{item_id}-action", "name": name,
            "action_type": "item_action", "charge_cost": charge_cost, "summary": summary}

def material(mid, name, mtype, prof_tags, recipe_tags, weight, price_gp=0, price_sp=0,
             stack=50, desc="", subtype=""):
    return {
        "id": mid, "name": name, "item_schema_version": 2,
        "category": "material", "subtype": subtype or mtype,
        "rarity": "common", "slug": mid, "material_type": mtype,
        "profession_tags": prof_tags, "recipe_tags": recipe_tags,
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": weight, "price_gp": price_gp, "price_sp": price_sp,
        "stack_limit": stack, "source": "expansion_pack",
        "description_summary": desc,
    }

# ===========================================================================
# 1) CRAFTING MATERIALS — gap-fillers (referenced by existing recipes but had
#    no item record) + a few new reagents for the new recipes below.
# ===========================================================================
MATERIALS = [
    # --- gap-fillers: existing recipes reference these by name ---
    material("mat_glass_vial", "Glass Vial", "container", ["alchemy"], ["vessel","potion"], 0.1, 0, 5, 100, "Clear blown-glass vial for potions and reagents."),
    material("mat_sunleaf_bunch", "Sunleaf Bunch", "herb", ["alchemy","herbalism"], ["healing","herb"], 0.2, 0, 8, 80, "Sun-warmed leaves prized for restorative tonics."),
    material("mat_cured_hide", "Cured Hide", "leather", ["leatherworking"], ["armor","repair"], 2.0, 1, 0, 40, "Tanned and cured animal hide ready for working."),
    material("mat_frostcap_mushroom", "Frostcap Mushroom", "herb", ["alchemy","herbalism"], ["cold","reagent"], 0.1, 0, 9, 60, "A pale fungus that stays cold to the touch."),
    material("mat_venom_sac", "Venom Sac", "monster_part", ["alchemy"], ["poison","reagent"], 0.2, 0, 12, 40, "Intact venom gland harvested from a serpent or spider."),
    material("mat_shadow_resin", "Shadow Resin", "reagent", ["enchanting","leatherworking"], ["stealth","reagent"], 0.3, 1, 0, 40, "Light-drinking sap used to dim cloth and leather."),
    material("mat_bat_wing_membrane", "Bat Wing Membrane", "monster_part", ["leatherworking","enchanting"], ["stealth","gliding"], 0.1, 0, 6, 50, "Thin, tough wing membrane from a giant bat."),
    material("mat_deepmoss_herb", "Deepmoss Herb", "herb", ["alchemy","herbalism"], ["healing","herb"], 0.1, 0, 7, 80, "Cave moss that glows faintly and soothes wounds."),
    material("mat_spider_silk_spool", "Spider Silk Spool", "thread", ["weaving","enchanting"], ["cloth","binding"], 0.2, 2, 0, 50, "A spool of remarkably strong giant-spider silk."),
    material("mat_darkwood_plank", "Darkwood Plank", "wood", ["woodworking"], ["weapon","haft"], 1.5, 3, 0, 40, "Lightweight, springy darkwood favored for shafts."),
    material("mat_hardwood_plank_bundle", "Hardwood Plank Bundle", "wood", ["woodworking","carpentry"], ["weapon","frame"], 6.0, 1, 0, 30, "A bound bundle of seasoned hardwood planks."),
    material("mat_sea_oak_plank", "Sea-Oak Plank", "wood", ["woodworking"], ["frame","waterproof"], 5.0, 1, 5, 30, "Salt-hardened oak that resists rot and water."),
    material("mat_tarred_rope_bundle", "Tarred Rope Bundle", "fiber", ["leatherworking","carpentry"], ["binding","rigging"], 3.0, 0, 8, 40, "Weatherproofed rope coil bound with pine tar."),
    material("mat_bone_shards", "Bone Shards", "monster_part", ["alchemy","enchanting"], ["reagent","focus"], 0.3, 0, 6, 60, "Splintered bone used as a grounding reagent."),
    material("mat_crystal_shard_cluster", "Crystal Shard Cluster", "crystal", ["enchanting","jeweling"], ["focus","arcane"], 0.4, 4, 0, 40, "A cluster of resonant quartz shards."),
    material("mat_coral_inlay_shards", "Coral Inlay Shards", "crystal", ["jeweling"], ["inlay","decor"], 0.2, 3, 0, 50, "Polished coral chips for decorative inlay."),
    material("mat_scaled_scraps", "Scaled Scraps", "monster_part", ["leatherworking"], ["armor","scale"], 1.0, 1, 0, 40, "Trimmed reptilian scales for scale armor work."),
    material("mat_copper_wire_spool", "Copper Wire Spool", "metal", ["tinkering","jeweling"], ["wiring","device"], 0.5, 2, 0, 50, "A spool of fine drawn copper wire."),
    material("mat_clockwork_spring_set", "Clockwork Spring Set", "component", ["tinkering"], ["device","mechanism"], 0.3, 5, 0, 40, "Matched coiled springs for clockwork mechanisms."),
    material("mat_precision_gear_pack", "Precision Gear Pack", "component", ["tinkering"], ["device","mechanism"], 0.4, 6, 0, 40, "A pack of finely machined brass gears."),
    material("mat_salvaged_brass_bundle", "Salvaged Brass Bundle", "metal", ["tinkering","blacksmithing"], ["device","scrap"], 2.0, 1, 0, 40, "Reclaimed brass fittings ready to be reworked."),
    material("mat_arc_battery_cell", "Arc Battery Cell", "component", ["tinkering","enchanting"], ["device","power"], 0.6, 8, 0, 30, "A sealed cell that holds a small electric charge."),
    material("mat_amberglass_vial", "Amberglass Vial", "container", ["alchemy","enchanting"], ["vessel","potion"], 0.1, 1, 5, 80, "Amber-tinted vial that shields contents from light."),
    material("mat_aether_dust", "Aether Dust", "reagent", ["enchanting"], ["arcane","reagent"], 0.05, 10, 0, 60, "Faintly glowing dust condensed from raw magic."),
    material("mat_bloomsteel_ingot", "Bloomsteel Ingot", "metal", ["blacksmithing","enchanting"], ["weapon","armor"], 3.0, 12, 0, 30, "Steel bloomed with arcane salts; takes enchantment well."),
    # --- brand-new reagents for the new recipes ---
    material("mat_emberbloom_petal", "Emberbloom Petal", "herb", ["alchemy","herbalism","enchanting"], ["fire","reagent"], 0.05, 5, 0, 60, "A petal that smolders without burning out."),
    material("mat_frost_lotus", "Frost Lotus", "herb", ["alchemy","enchanting"], ["cold","reagent"], 0.1, 6, 0, 50, "A bloom of living ice that never melts."),
    material("mat_wisp_essence", "Wisp Essence", "reagent", ["enchanting"], ["arcane","light"], 0.02, 14, 0, 40, "Captured glow of a will-o'-wisp in a stoppered bead."),
    material("mat_thunderscale_hide", "Thunderscale Hide", "monster_part", ["leatherworking","enchanting"], ["lightning","armor"], 2.5, 9, 0, 30, "Crackling hide from a storm-touched beast."),
    material("mat_living_ironwood", "Living Ironwood", "wood", ["woodworking","enchanting"], ["weapon","focus"], 2.0, 11, 0, 30, "Ironwood still faintly green, holding nature magic."),
    material("mat_quicksilver_dram", "Quicksilver Dram", "reagent", ["alchemy","tinkering"], ["reagent","device"], 0.1, 7, 0, 50, "A measured dram of restless quicksilver."),
]

# ===========================================================================
# 2) MAGIC ITEMS — spell-granting + attribute. Authored to avoid the known
#    data bugs: single attunement source, real action summaries, no recharge
#    on 0-charge items, authored weight, recognized passive_effect types.
# ===========================================================================
def magic_item(mid, name, category, rarity, *, attune=False, slot="", weight=1.0, price=0,
               charges=0, recharge_formula="", recharge_on_rest="", save_dc=0, atk_bonus=0,
               spells=None, actions=None, passives=None, ac_bonus=0, attack_bonus=0,
               damage_bonus=0, stat_minimums=None, stat_overrides=None, desc="", full=""):
    rec = {
        "id": mid, "name": name, "item_schema_version": 2,
        "category": category, "rarity": rarity, "slug": mid,
        "requires_attunement": bool(attune),
        "attunement": {"required": bool(attune), "supported": True},
        "equippable": bool(slot), "equip_slot": slot,
        "weight_lbs": weight, "price_gp": price,
        "charges_max": charges, "charges_current": charges,
        "recharge_type": "formula" if charges else "none",
        "recharge_formula": recharge_formula if charges else "",
        "recharge_on_rest": recharge_on_rest if charges else "",
        "item_spell_save_dc": save_dc, "item_spell_attack_bonus": atk_bonus,
        "granted_spells": spells or [], "granted_actions": actions or [],
        "passive_effects": passives or [], "bonuses": [],
        "ac_bonus": ac_bonus, "attack_bonus": attack_bonus, "damage_bonus": damage_bonus,
        "stat_minimums": stat_minimums or {}, "stat_overrides": stat_overrides or {},
        "source": "expansion_pack",
        "description_summary": desc, "full_description": full or desc,
    }
    return rec

MAGIC_ITEMS = [
    # ---- spell-granting (charges + granted_spells referencing real SRD spells) ----
    magic_item("wand-of-frost-lances", "Wand of Frost Lances", "wand", "uncommon",
        weight=1.0, price=900, charges=7, recharge_formula="1d6+1", recharge_on_rest="dawn", save_dc=15,
        spells=[gspell("ray-of-frost", "Ray of Frost", 1, 0), gspell("ice-knife", "Ice Knife", 2, 1)],
        actions=[gaction("wand-of-frost-lances", "Loose Frost Lance", "Spend a charge to hurl a lance of ice at a target you can see.")],
        desc="A rod of blue crystal that fires lances of biting frost."),
    magic_item("staff-of-emberbloom", "Staff of Emberbloom", "staff", "rare", attune=True,
        slot="held", weight=4.0, price=6000, charges=10, recharge_formula="1d8+2", recharge_on_rest="dawn", save_dc=16, atk_bonus=8,
        spells=[gspell("fire-bolt", "Fire Bolt", 0, 0), gspell("burning-hands", "Burning Hands", 1, 1), gspell("fireball", "Fireball", 3, 3)],
        actions=[gaction("staff-of-emberbloom", "Channel Emberbloom", "Expend charges to cast a fire spell stored in the staff.")],
        passives=[{"type": "resistance", "damage_type": "fire", "summary": "You have resistance to fire damage while attuned."}],
        desc="A blackwood staff crowned with an ever-smoldering bloom."),
    magic_item("ring-of-mistrecall", "Ring of Mistrecall", "ring", "rare", attune=True,
        slot="ring", weight=0.0, price=5000, charges=4, recharge_formula="1d4", recharge_on_rest="dawn", save_dc=15,
        spells=[gspell("misty-step", "Misty Step", 1, 2), gspell("dimension-door", "Dimension Door", 2, 4)],
        actions=[gaction("ring-of-mistrecall", "Step Through Mist", "Spend a charge to teleport in a swirl of grey mist.")],
        desc="A silver band that breaks into mist and reforms elsewhere."),
    magic_item("amulet-of-the-mending-tide", "Amulet of the Mending Tide", "amulet", "uncommon",
        slot="amulet", weight=0.5, price=1200, charges=5, recharge_formula="1d4+1", recharge_on_rest="dawn", save_dc=14,
        spells=[gspell("cure-wounds", "Cure Wounds", 1, 1), gspell("healing-word", "Healing Word", 1, 1)],
        actions=[gaction("amulet-of-the-mending-tide", "Call the Mending Tide", "Spend a charge to channel healing into a creature you touch or see.")],
        desc="A wave-carved pendant that pulses with cool, healing light."),
    magic_item("rod-of-the-thornwarden", "Rod of the Thornwarden", "rod", "rare", attune=True,
        slot="held", weight=2.0, price=4500, charges=6, recharge_formula="1d6", recharge_on_rest="dawn", save_dc=15,
        spells=[gspell("entangle", "Entangle", 1, 1), gspell("thorn-whip", "Thorn Whip", 1, 0)],
        actions=[gaction("rod-of-the-thornwarden", "Raise the Bramble", "Spend a charge to call grasping thorns from the ground.")],
        desc="A gnarled rod that sprouts living thorns at its wielder's will."),
    magic_item("circlet-of-whispered-sparks", "Circlet of Whispered Sparks", "wondrous", "uncommon",
        slot="head", weight=0.3, price=1000, charges=6, recharge_formula="1d6", recharge_on_rest="dawn", save_dc=14, atk_bonus=6,
        spells=[gspell("shocking-grasp", "Shocking Grasp", 0, 0), gspell("witch-bolt", "Witch Bolt", 1, 1)],
        actions=[gaction("circlet-of-whispered-sparks", "Whisper a Spark", "Spend a charge to lash out with arcing electricity.")],
        desc="A thin circlet that hums with restless static."),
    magic_item("orb-of-veiled-sight", "Orb of Veiled Sight", "wondrous", "rare", attune=True,
        slot="held", weight=1.5, price=4000, charges=5, recharge_formula="1d4+1", recharge_on_rest="dawn", save_dc=15,
        spells=[gspell("detect-magic", "Detect Magic", 1, 1), gspell("see-invisibility", "See Invisibility", 1, 2), gspell("clairvoyance", "Clairvoyance", 3, 3)],
        actions=[gaction("orb-of-veiled-sight", "Peer Through the Veil", "Spend a charge to reveal hidden magic or unseen things.")],
        passives=[{"type": "sense_bonus", "sense": "see_magic_aura", "value": 1, "summary": "Faint magical auras shimmer at the edge of your vision."}],
        desc="A smoky glass orb in which distant and hidden things surface."),
    magic_item("wand-of-binding-vines", "Wand of Binding Vines", "wand", "uncommon",
        weight=1.0, price=850, charges=7, recharge_formula="1d6+1", recharge_on_rest="dawn", save_dc=14,
        spells=[gspell("ensnaring-strike", "Ensnaring Strike", 1, 1), gspell("web", "Web", 2, 2)],
        actions=[gaction("wand-of-binding-vines", "Cast Binding Vines", "Spend a charge to entangle a target in conjured vines.")],
        desc="A green-veined wand that weeps sap and sprouts tendrils."),

    # ---- attribute / passive items (recognized passive_effect + stat fields) ----
    magic_item("bracers-of-the-iron-stag", "Bracers of the Iron Stag", "wondrous", "rare", attune=True,
        slot="arms", weight=1.0, price=3500, stat_minimums={"con": 19},
        passives=[{"type": "ability_floor", "ability": "con", "value": 19, "summary": "Your Constitution score can't be lower than 19 while worn."}],
        desc="Heavy bracers that lend the endurance of a great stag."),
    magic_item("headband-of-the-keen-mind", "Headband of the Keen Mind", "wondrous", "uncommon", attune=True,
        slot="head", weight=0.2, price=2000, stat_overrides={"int": 19},
        passives=[{"type": "ability_set", "ability": "int", "value": 19, "summary": "Your Intelligence becomes 19 while worn."}],
        desc="A plain band that sharpens the wearer's intellect."),
    magic_item("goggles-of-the-deepdark", "Goggles of the Deepdark", "wondrous", "common",
        slot="eyes", weight=0.2, price=200,
        passives=[{"type": "sense_bonus", "sense": "darkvision", "value": 60, "summary": "You gain darkvision out to 60 ft (or +60 ft if you already have it)."}],
        desc="Smoked-lens goggles that drink in the dark."),
    magic_item("boots-of-the-fleetfoot", "Boots of the Fleetfoot", "wondrous", "uncommon",
        slot="feet", weight=1.0, price=1500,
        passives=[{"type": "speed_bonus", "value": 10, "summary": "Your walking speed increases by 10 feet."}],
        desc="Light boots that quicken every stride."),
    magic_item("cloak-of-the-gale", "Cloak of the Gale", "wondrous", "rare", attune=True,
        slot="back", weight=1.0, price=4000, ac_bonus=1,
        passives=[{"type": "resistance", "damage_type": "lightning", "summary": "You have resistance to lightning damage."},
                  {"type": "ac_bonus", "value": 1, "summary": "+1 bonus to Armor Class while attuned."}],
        desc="A storm-grey cloak that snaps with wind and crackles faintly."),
    magic_item("gauntlets-of-the-quarry-breaker", "Gauntlets of the Quarry Breaker", "wondrous", "rare", attune=True,
        slot="hands", weight=2.0, price=3500, stat_minimums={"str": 19},
        passives=[{"type": "ability_floor", "ability": "str", "value": 19, "summary": "Your Strength score can't be lower than 19 while worn."}],
        desc="Stone-knuckled gauntlets that grant a giant's grip."),
    magic_item("pendant-of-emberward", "Pendant of Emberward", "amulet", "uncommon", attune=True,
        slot="amulet", weight=0.3, price=1200,
        passives=[{"type": "resistance", "damage_type": "fire", "summary": "You have resistance to fire damage."}],
        desc="A ruby teardrop that drinks in nearby heat."),
    magic_item("ring-of-warded-steps", "Ring of Warded Steps", "ring", "rare", attune=True,
        slot="ring", weight=0.0, price=3500, ac_bonus=1, attack_bonus=0,
        passives=[{"type": "ac_bonus", "value": 1, "summary": "+1 bonus to AC and saving throws while attuned."},
                  {"type": "save_bonus", "value": 1, "summary": "+1 bonus to all saving throws."}],
        desc="A worn band that turns aside blows and ill fortune."),
    magic_item("mantle-of-the-watchful-owl", "Mantle of the Watchful Owl", "wondrous", "uncommon",
        slot="shoulders", weight=1.0, price=900,
        passives=[{"type": "skill_advantage", "skill": "perception", "summary": "You have advantage on Wisdom (Perception) checks that rely on sight."},
                  {"type": "sense_bonus", "sense": "darkvision", "value": 30, "summary": "You gain 30 ft of darkvision (or +30 ft)."}],
        desc="A feathered mantle that keeps watch when you cannot."),
    magic_item("vest-of-the-tideheart", "Vest of the Tideheart", "wondrous", "rare", attune=True,
        slot="chest", weight=2.0, price=4000,
        passives=[{"type": "resistance", "damage_type": "cold", "summary": "You have resistance to cold damage."},
                  {"type": "swim_speed", "value": 30, "summary": "You gain a swimming speed of 30 feet and can breathe underwater."}],
        desc="A scaled vest that beats with the rhythm of the tide."),
]

# ===========================================================================
# 3) CRAFTING RECIPES (seed format for db._seed_crafting_recipes)
# ===========================================================================
def recipe(rid, name, result, professions, materials, fee, duration, stations, tags, rarity="common"):
    return {
        "id": rid, "name": name,
        "result_item_json": json.dumps(result),
        "requires_professions_json": json.dumps(professions),
        "requires_materials_json": json.dumps(materials),
        "fee_units": fee, "duration_seconds": duration,
        "station_shop_types_json": json.dumps(stations),
        "tags_json": json.dumps(tags), "rarity": rarity,
    }

RECIPES = [
    recipe("rec_emberward_pendant", "Pendant of Emberward",
        {k: MAGIC_ITEMS[15][k] for k in ("id","name","category","rarity")} | {"item_type": "amulet"},
        ["enchanting","jeweling"],
        [{"name": "Emberbloom Petal", "qty": 3}, {"name": "Crystal Shard Cluster", "qty": 1}, {"name": "Aether Dust", "qty": 1}],
        420, 600, ["magic","jeweler"], ["amulet","fire","enchanting"], "uncommon"),
    recipe("rec_frost_lance_wand", "Wand of Frost Lances",
        {"id":"wand-of-frost-lances","name":"Wand of Frost Lances","category":"wand","rarity":"uncommon","item_type":"wand"},
        ["enchanting","woodworking"],
        [{"name": "Living Ironwood", "qty": 1}, {"name": "Frost Lotus", "qty": 2}, {"name": "Aether Dust", "qty": 2}],
        480, 720, ["magic"], ["wand","cold","enchanting"], "uncommon"),
    recipe("rec_goggles_deepdark", "Goggles of the Deepdark",
        {"id":"goggles-of-the-deepdark","name":"Goggles of the Deepdark","category":"wondrous","rarity":"common","item_type":"wondrous"},
        ["tinkering","jeweling"],
        [{"name": "Amberglass Vial", "qty": 2}, {"name": "Copper Wire Spool", "qty": 1}, {"name": "Shadow Resin", "qty": 1}],
        220, 480, ["general","magic"], ["wondrous","vision","starter"], "common"),
    recipe("rec_mending_tide_amulet", "Amulet of the Mending Tide",
        {"id":"amulet-of-the-mending-tide","name":"Amulet of the Mending Tide","category":"amulet","rarity":"uncommon","item_type":"amulet"},
        ["enchanting","herbalism"],
        [{"name": "Deepmoss Herb", "qty": 3}, {"name": "Coral Inlay Shards", "qty": 2}, {"name": "Wisp Essence", "qty": 1}],
        400, 660, ["magic","jeweler"], ["amulet","healing","enchanting"], "uncommon"),
    recipe("rec_storm_cloak", "Cloak of the Gale",
        {"id":"cloak-of-the-gale","name":"Cloak of the Gale","category":"wondrous","rarity":"rare","item_type":"wondrous"},
        ["leatherworking","enchanting"],
        [{"name": "Thunderscale Hide", "qty": 2}, {"name": "Spider Silk Spool", "qty": 2}, {"name": "Aether Dust", "qty": 2}],
        900, 1200, ["magic","leatherworker"], ["cloak","lightning","enchanting"], "rare"),
    recipe("rec_thornwarden_rod", "Rod of the Thornwarden",
        {"id":"rod-of-the-thornwarden","name":"Rod of the Thornwarden","category":"rod","rarity":"rare","item_type":"rod"},
        ["woodworking","enchanting"],
        [{"name": "Living Ironwood", "qty": 2}, {"name": "Deepmoss Herb", "qty": 2}, {"name": "Crystal Shard Cluster", "qty": 1}],
        880, 1200, ["magic"], ["rod","nature","enchanting"], "rare"),
    recipe("rec_sparks_circlet", "Circlet of Whispered Sparks",
        {"id":"circlet-of-whispered-sparks","name":"Circlet of Whispered Sparks","category":"wondrous","rarity":"uncommon","item_type":"wondrous"},
        ["tinkering","enchanting"],
        [{"name": "Arc Battery Cell", "qty": 1}, {"name": "Copper Wire Spool", "qty": 2}, {"name": "Quicksilver Dram", "qty": 1}],
        460, 720, ["magic","general"], ["circlet","lightning","enchanting"], "uncommon"),
    recipe("rec_binding_vines_wand", "Wand of Binding Vines",
        {"id":"wand-of-binding-vines","name":"Wand of Binding Vines","category":"wand","rarity":"uncommon","item_type":"wand"},
        ["enchanting","herbalism"],
        [{"name": "Living Ironwood", "qty": 1}, {"name": "Spider Silk Spool", "qty": 2}, {"name": "Sunleaf Bunch", "qty": 1}],
        460, 700, ["magic"], ["wand","nature","enchanting"], "uncommon"),
    recipe("rec_antivenom_draught", "Antivenom Draught",
        {"id":"crafted_antivenom_draught","name":"Antivenom Draught","category":"Consumable","item_type":"potion","rarity":"common"},
        ["alchemy"],
        [{"name": "Glass Vial", "qty": 1}, {"name": "Venom Sac", "qty": 1}, {"name": "Deepmoss Herb", "qty": 1}],
        120, 180, ["alchemist","magic"], ["potion","cure","starter"], "common"),
    recipe("rec_frostfire_oil", "Frostfire Coating Oil",
        {"id":"crafted_frostfire_oil","name":"Frostfire Coating Oil","category":"Consumable","item_type":"oil","rarity":"uncommon"},
        ["alchemy"],
        [{"name": "Amberglass Vial", "qty": 1}, {"name": "Emberbloom Petal", "qty": 1}, {"name": "Frost Lotus", "qty": 1}],
        260, 300, ["alchemist","magic"], ["oil","weapon","elemental"], "uncommon"),
    recipe("rec_scaled_brigandine", "Scaled Brigandine",
        {"id":"crafted_scaled_brigandine","name":"Scaled Brigandine","category":"Armor","item_type":"armor","rarity":"uncommon"},
        ["leatherworking","blacksmithing"],
        [{"name": "Scaled Scraps", "qty": 4}, {"name": "Cured Hide", "qty": 2}, {"name": "Steel Ingot", "qty": 1}],
        520, 900, ["blacksmith","leatherworker"], ["armor","medium"], "uncommon"),
    recipe("rec_bloomsteel_blade", "Bloomsteel Blade",
        {"id":"crafted_bloomsteel_blade","name":"Bloomsteel Blade","category":"Weapon","item_type":"weapon","rarity":"rare"},
        ["blacksmithing","enchanting"],
        [{"name": "Bloomsteel Ingot", "qty": 2}, {"name": "Darkwood Plank", "qty": 1}, {"name": "Aether Dust", "qty": 1}],
        950, 1500, ["blacksmith","magic"], ["weapon","sword","enchanting"], "rare"),
    recipe("rec_tideheart_vest", "Vest of the Tideheart",
        {"id":"vest-of-the-tideheart","name":"Vest of the Tideheart","category":"wondrous","rarity":"rare","item_type":"wondrous"},
        ["leatherworking","enchanting"],
        [{"name": "Scaled Scraps", "qty": 3}, {"name": "Coral Inlay Shards", "qty": 2}, {"name": "Wisp Essence", "qty": 1}],
        880, 1200, ["magic","leatherworker"], ["armor","cold","enchanting"], "rare"),
    recipe("rec_fleetfoot_boots", "Boots of the Fleetfoot",
        {"id":"boots-of-the-fleetfoot","name":"Boots of the Fleetfoot","category":"wondrous","rarity":"uncommon","item_type":"wondrous"},
        ["leatherworking","enchanting"],
        [{"name": "Cured Hide", "qty": 2}, {"name": "Bat Wing Membrane", "qty": 2}, {"name": "Aether Dust", "qty": 1}],
        420, 720, ["magic","leatherworker"], ["boots","speed","enchanting"], "uncommon"),
]

# ===========================================================================
# VALIDATION — normalize through the real schema; cross-check spells/materials
# ===========================================================================
def main():
    from server.item_schema import normalize_item_record

    report = ["# Item & Crafting Expansion — Validation Report\n"]
    errors = []

    # normalize every item
    norm_items, norm_mats = [], []
    for it in MAGIC_ITEMS:
        c = normalize_item_record(it, source_type="magic_item", source_id=it["id"])
        assert c["identity"]["item_id"] == it["id"], it["id"]
        assert len(c["effects"]["granted_spells"]) == len(it.get("granted_spells",[])), it["id"]
        norm_items.append(it)
    for m in MATERIALS:
        normalize_item_record(m, source_type="srd_item", source_id=m["id"])
        norm_mats.append(m)

    # spell id cross-check
    bad_spells = []
    for it in MAGIC_ITEMS:
        for gs in it.get("granted_spells", []):
            if gs["spell_id"] not in SPELL_IDS:
                bad_spells.append((it["id"], gs["spell_id"]))

    # material resolution cross-check (existing + new)
    all_mats = _existing_material_names() | {m["name"] for m in MATERIALS}
    unresolved = []
    for r in RECIPES:
        for mat in json.loads(r["requires_materials_json"]):
            if mat["name"] not in all_mats:
                unresolved.append((r["id"], mat["name"]))

    # data-bug guard: ensure NONE of the new items reintroduce the old smells
    smells = {"generic_activate": 0, "recharge_no_charges": 0, "attune_mismatch": 0}
    for it in MAGIC_ITEMS:
        for a in it.get("granted_actions", []):
            if str(a.get("summary", "")).strip().lower() in {"activate this item.", "activate this item"}:
                smells["generic_activate"] += 1
        if (it.get("charges_max", 0) == 0) and str(it.get("recharge_formula", "")).strip():
            smells["recharge_no_charges"] += 1
        if bool(it.get("requires_attunement")) != bool(it.get("attunement", {}).get("required")):
            smells["attune_mismatch"] += 1

    report.append(f"- Magic items authored & normalized: **{len(MAGIC_ITEMS)}**")
    report.append(f"- Crafting materials authored & normalized: **{len(MATERIALS)}** "
                  f"(gap-fillers for existing recipes + new reagents)")
    report.append(f"- Crafting recipes authored: **{len(RECIPES)}**")
    report.append(f"- Spell library checked against: **{len(SPELL_IDS)}** spell ids")
    report.append(f"- Granted spells with no matching spell id: **{len(bad_spells)}** {bad_spells or ''}")
    report.append(f"- Recipe materials that don't resolve: **{len(unresolved)}** {unresolved or ''}")
    report.append(f"- Reintroduced data smells (must all be 0): {smells}")

    ok = not bad_spells and not unresolved and not any(smells.values())
    report.append(f"\n**RESULT: {'PASS ✅' if ok else 'FAIL ❌'}**")

    # emit files
    (OUT / "expanded_magic_items.json").write_text(json.dumps({
        "item_schema_version": 2, "rules_version": "5e2024", "category": "expansion_magic_items",
        "description": "Expansion pack — spell-granting and attribute magic items (original content; references SRD spell ids).",
        "items": MAGIC_ITEMS,
    }, indent=2) + "\n", encoding="utf-8")

    (OUT / "expanded_crafting_materials.json").write_text(json.dumps({
        "item_schema_version": 2, "rules_version": "5e2024", "category": "expansion_materials",
        "description": "Expansion pack — crafting materials, including gap-fillers referenced by existing recipes.",
        "items": MATERIALS,
    }, indent=2) + "\n", encoding="utf-8")

    # recipe seed module
    seed_src = ['"""Expansion crafting recipes — append into server.db._seed_crafting_recipes.',
                'Call EXPANSION_RECIPES from inside _seed_crafting_recipes (after the base list)',
                'and INSERT OR REPLACE each row, exactly like the existing seed rows."""',
                "import json", "", "EXPANSION_RECIPES = ["]
    for r in RECIPES:
        seed_src.append("    {")
        for k, v in r.items():
            seed_src.append(f"        {k!r}: {v!r},")
        seed_src.append("    },")
    seed_src.append("]")
    (OUT / "crafting_recipes_expansion.py").write_text("\n".join(seed_src) + "\n", encoding="utf-8")

    (OUT / "VALIDATION_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())

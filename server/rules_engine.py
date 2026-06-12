from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Tuple


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name or "").lower()).strip()


def _parse_modifier(value: Any) -> str:
    s = str(value or "").strip()
    return s if s else "—"


def _ability_mod(score: int) -> int:
    return (int(score or 10) - 10) // 2


def _character_level(character: dict) -> int:
    if not isinstance(character, dict):
        return 1
    if character.get("totalLevel"):
        try:
            return max(1, int(character.get("totalLevel")))
        except Exception:
            pass
    classes = character.get("classes") or []
    if isinstance(classes, list) and classes:
        total = 0
        for cls in classes:
            try:
                total += max(1, int((cls or {}).get("level") or 1))
            except Exception:
                total += 1
        if total:
            return total
    book = character.get("book") or {}
    try:
        return max(1, int(book.get("level") or character.get("level") or 1))
    except Exception:
        return 1


def _spellcasting_meta(character: dict) -> Dict[str, Any]:
    book = (character or {}).get("book") or {}
    meta = (character or {}).get("_spellMeta") or {}
    stats = (character or {}).get("stats") or []
    ability_scores = (book.get("abilityScores") or {}) if isinstance(book, dict) else {}
    ability = str(book.get("spellAbility") or meta.get("ability") or "").strip().upper()
    attack = str(book.get("spellAttack") or meta.get("attack") or "").strip()
    dc = str(book.get("spellSaveDc") or meta.get("saveDc") or "").strip()
    prof = int((character or {}).get("profBonus") or book.get("profBonus") or 0 or 0)

    if not ability and stats:
        classes = (character or {}).get("classes") or []
        first_class = str((classes[0] or {}).get("name") or "").lower()
        if first_class in {"cleric", "druid", "ranger"}:
            ability = "WIS"
        elif first_class in {"bard", "paladin", "sorcerer", "warlock"}:
            ability = "CHA"
        elif first_class in {"wizard", "artificer", "fighter", "rogue"}:
            ability = "INT"

    if ability and (not attack or not dc):
        ability_map = {
            "STR": 0, "DEX": 1, "CON": 2, "INT": 3, "WIS": 4, "CHA": 5,
            "STRENGTH": 0, "DEXTERITY": 1, "CONSTITUTION": 2, "INTELLIGENCE": 3, "WISDOM": 4, "CHARISMA": 5,
        }
        idx = ability_map.get(ability)
        mod = None
        if idx is not None and idx < len(stats):
            mod = _ability_mod(stats[idx])
        elif ability_scores:
            key_map = {"STR": "strength", "DEX": "dexterity", "CON": "constitution", "INT": "intelligence", "WIS": "wisdom", "CHA": "charisma"}
            full_key = key_map.get(ability[:3])
            if full_key:
                mod = _ability_mod(ability_scores.get(full_key) or 10)
        if mod is not None:
            if not attack:
                attack = f"{mod + prof:+d}"
            if not dc:
                dc = str(8 + prof + mod)
    return {"ability": ability or "—", "attack": attack or "—", "dc": dc or "—", "prof": prof}


def _extract_spell_names_from_text(text: str) -> List[str]:
    names: List[str] = []
    for raw_line in re.split(r"\n+", str(text or "")):
        line = raw_line.strip()
        if not line or len(line) > 120:
            continue
        name = re.split(r"\s+[—\-–]\s+", line, 1)[0].strip()
        if not name:
            continue
        if any(ch.isdigit() for ch in name) and len(name.split()) <= 2:
            continue
        if len(name.split()) > 6:
            continue
        if name.lower() in {"cantrips", "spells", "spell list"}:
            continue
        names.append(name)
    return names


def extract_imported_spell_names(character: dict) -> List[Dict[str, Any]]:
    seen = set()
    results: List[Dict[str, Any]] = []
    for entry in (character or {}).get("spellbookEntries") or []:
        name = str((entry or {}).get("name") or "").strip()
        if not name:
            continue
        norm = normalize_name(name)
        if norm in seen:
            continue
        seen.add(norm)
        results.append({"name": name, "source_tag": "imported", "entry": entry})
    book = (character or {}).get("book") or {}
    for name in _extract_spell_names_from_text(book.get("spells") or ""):
        norm = normalize_name(name)
        if norm in seen:
            continue
        seen.add(norm)
        results.append({"name": name, "source_tag": "imported-text", "entry": None})
    return results


def _calc_cantrip(rule: dict, char_level: int) -> Tuple[str, str]:
    tiers = sorted(rule.get("scaling_data", {}).get("tiers", []), key=lambda t: int(t.get("level") or 1))
    formula = rule.get("base_damage_formula") or "—"
    chosen_level = 1
    for tier in tiers:
        if char_level >= int(tier.get("level") or 1):
            formula = tier.get("formula") or formula
            chosen_level = int(tier.get("level") or chosen_level)
    note = f"Cantrip scaling uses total character level {char_level}."
    return formula, note


def _formula_with_bonus(formula: str, slot_delta: int) -> str:
    if slot_delta <= 0:
        return formula
    return formula


def build_spell_calculation(rule: dict, character: dict, cast_level: int | None = None) -> Dict[str, Any]:
    char_level = _character_level(character)
    spell_level = int(rule.get("spell_level") or 0)
    cast_level = spell_level if cast_level is None else max(spell_level, int(cast_level))
    scaling_type = str(rule.get("scaling_type") or "none")
    scaling = rule.get("scaling_data") or {}
    formula = rule.get("base_damage_formula") or ""
    effect = rule.get("base_effect_text") or ""
    note = ""

    if spell_level == 0 and scaling_type == "cantrip_level":
        formula, note = _calc_cantrip(rule, char_level)
    elif scaling_type == "slot_damage":
        base_slot = int(scaling.get("base_slot") or spell_level or 1)
        base_formula = scaling.get("base_formula") or formula
        per_slot_formula = scaling.get("per_slot_formula") or ""
        delta = max(0, cast_level - base_slot)
        formula = base_formula if delta <= 0 else f"{base_formula} + {delta} × {per_slot_formula}"
        note = f"Cast at level {cast_level}." if delta else "Base slot calculation."
    elif scaling_type == "slot_healing":
        base_slot = int(scaling.get("base_slot") or spell_level or 1)
        base_formula = scaling.get("base_formula") or formula
        per_slot_formula = scaling.get("per_slot_formula") or ""
        delta = max(0, cast_level - base_slot)
        formula = base_formula if delta <= 0 else f"{base_formula} + {delta} × {per_slot_formula}"
        note = f"Healing scaled for slot {cast_level}." if delta else "Base healing."
    elif scaling_type == "extra_dart_per_slot":
        base_slot = int(scaling.get("base_slot") or spell_level or 1)
        darts = int(scaling.get("base_darts") or 3) + max(0, cast_level - base_slot) * int(scaling.get("per_slot") or 1)
        dart_formula = scaling.get("dart_formula") or "1d4+1"
        formula = f"{darts} darts × {dart_formula}"
        effect = f"Creates {darts} force darts."
        note = f"Cast at level {cast_level}."
    elif scaling_type == "extra_ray_per_slot":
        base_slot = int(scaling.get("base_slot") or spell_level or 2)
        rays = int(scaling.get("base_rays") or 3) + max(0, cast_level - base_slot) * int(scaling.get("per_slot") or 1)
        ray_formula = scaling.get("ray_formula") or "2d6"
        formula = f"{rays} rays × {ray_formula}"
        effect = f"Make {rays} ranged spell attacks."
        note = f"Cast at level {cast_level}."
    elif scaling_type == "extra_target_per_slot":
        base_slot = int(scaling.get("base_slot") or spell_level or 1)
        targets = int(scaling.get("base_targets") or 1) + max(0, cast_level - base_slot) * int(scaling.get("per_slot") or 1)
        formula = formula or "—"
        effect = f"Affects {targets} target{'s' if targets != 1 else ''}. {rule.get('base_effect_text') or ''}".strip()
        note = f"Cast at level {cast_level}."
    elif scaling_type == "text_only":
        formula = formula or "Rules text only"
        note = rule.get("higher_level_text") or ""

    levels = [0] if spell_level == 0 else list(range(spell_level, 10))
    return {
        "spell_level": spell_level,
        "cast_level": cast_level,
        "available_cast_levels": levels,
        "formula": formula or "—",
        "effect": effect or "—",
        "note": note,
    }


def build_spell_card(rule: dict, character: dict, imported_name: str, match_status: str, match_score: float, source_tag: str, imported_entry: dict | None = None) -> Dict[str, Any]:
    meta = _spellcasting_meta(character)
    card = {
        "id": rule.get("id"),
        "name": rule.get("name") or imported_name,
        "imported_name": imported_name,
        "normalized_name": rule.get("normalized_name") or normalize_name(rule.get("name") or imported_name),
        "source": rule.get("source") or "—",
        "source_page": rule.get("source_page") or "",
        "match_status": match_status,
        "match_score": round(float(match_score or 0), 3),
        "source_tag": source_tag,
        "level_school": ("Cantrip" if int(rule.get("spell_level") or 0) == 0 else f"Level {int(rule.get('spell_level') or 0)}") + f" • {rule.get('school') or 'Spell'}",
        "casting_time": rule.get("casting_time") or "—",
        "range": rule.get("range") or "—",
        "components": rule.get("components") or "—",
        "duration": rule.get("duration") or "—",
        "concentration": bool(rule.get("concentration")),
        "ritual": bool(rule.get("ritual")),
        "attack_bonus": meta["attack"] if rule.get("attack_type") else "—",
        "save_dc": meta["dc"] if rule.get("save_ability") else "—",
        "spell_ability": meta["ability"],
        "attack_type": rule.get("attack_type") or "",
        "save_ability": rule.get("save_ability") or "",
        "damage_type": rule.get("damage_type") or "",
        "healing_type": rule.get("healing_type") or "",
        "base_effect_text": rule.get("base_effect_text") or "",
        "higher_level_text": rule.get("higher_level_text") or "",
        "tags": list(rule.get("tags") or []),
        "class_lists": list(rule.get("class_lists") or []),
        "is_homebrew": bool(rule.get("is_homebrew")),
        "created_by_dm": bool(rule.get("created_by_dm")),
        "imported_entry": imported_entry or {},
    }
    calc_by_level = {}
    for level in build_spell_calculation(rule, character).get("available_cast_levels", [int(rule.get("spell_level") or 0)]):
        calc_by_level[str(level)] = build_spell_calculation(rule, character, level)
    default_cast = str(int(rule.get("spell_level") or 0))
    card["cast_options"] = calc_by_level
    card["default_cast_level"] = default_cast
    card["current"] = calc_by_level.get(default_cast) or next(iter(calc_by_level.values()), {"formula": "—", "effect": "—", "note": ""})
    return card


def match_spell_name(name: str, official_spells: List[dict], custom_spells: List[dict]) -> Tuple[str, float, dict | None, dict | None]:
    norm = normalize_name(name)
    if not norm:
        return "unmatched", 0.0, None, None
    all_rules = list(custom_spells or []) + list(official_spells or [])
    by_norm = {normalize_name(rule.get("name")): rule for rule in all_rules if rule.get("name")}
    if norm in by_norm:
        rule = by_norm[norm]
        return ("matched", 1.0, rule, None)
    best_rule = None
    best_score = 0.0
    for rule in all_rules:
        candidate = normalize_name(rule.get("name"))
        if not candidate:
            continue
        score = difflib.SequenceMatcher(None, norm, candidate).ratio()
        if score > best_score:
            best_score = score
            best_rule = rule
    if best_rule and best_score >= 0.9:
        return ("partial_match", best_score, best_rule, None)
    if best_rule and best_score >= 0.74:
        return ("review_required", best_score, None, best_rule)
    return ("unmatched", best_score, None, best_rule)


def enrich_spellbook(character: dict, official_spells: List[dict], custom_spells: List[dict]) -> Dict[str, Any]:
    imported_spells = extract_imported_spell_names(character)
    cards: List[dict] = []
    review: List[dict] = []
    unmatched: List[dict] = []
    for item in imported_spells:
        status, score, matched_rule, suggested = match_spell_name(item["name"], official_spells, custom_spells)
        if matched_rule:
            source_tag = "DM custom" if matched_rule.get("is_homebrew") else "database matched"
            card = build_spell_card(matched_rule, character, item["name"], status, score, source_tag, item.get("entry"))
            cards.append(card)
        else:
            review_item = {
                "name": item["name"],
                "normalized_name": normalize_name(item["name"]),
                "status": status,
                "match_score": round(float(score or 0), 3),
                "suggested_name": (suggested or {}).get("name") if suggested else "",
                "suggested_rule_id": (suggested or {}).get("id") if suggested else "",
                "source_tag": item.get("source_tag") or "imported",
                "imported_entry": item.get("entry") or {},
            }
            review.append(review_item)
            unmatched.append(review_item)
    cards.sort(key=lambda c: (int(c.get("current", {}).get("spell_level") or c.get("cast_options", {}).get(c.get("default_cast_level", "0"), {}).get("spell_level", 0)), c.get("name", "")))
    return {
        "spell_cards": cards,
        "review_queue": review,
        "unmatched": unmatched,
        "spellcasting": _spellcasting_meta(character),
        "total_level": _character_level(character),
    }

"""
server/utils/pdf_parser.py — Parse D&D Beyond character sheet PDFs.

Exposes a single public function:
    parse_character_pdf_data(data: bytes) -> dict

Returns a structured character dict, or raises ValueError / ImportError.
"""
import io
import re


def parse_character_pdf_data(data: bytes) -> dict:
    """Parse a D&D Beyond character PDF and return structured character data.

    Args:
        data: Raw bytes of the PDF file.

    Returns:
        A dict with all extracted character information.

    Raises:
        ImportError: If pypdf is not installed.
        ValueError: If the PDF could not be read.
    """
    try:
        import pypdf
    except ImportError:
        raise ImportError("pypdf not installed. Run: pip install pypdf")

    if not data:
        raise ValueError("Empty PDF data received.")

    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc

    fields = reader.get_form_text_fields() or {}
    all_fields: dict[str, str] = {}

    def _clean_pdf_value(raw_val) -> str:
        if raw_val is None:
            return ""
        sval = str(raw_val).strip()
        if sval in ("", "/Off", "Off", "None", "null"):
            return ""
        if sval in ("/Yes", "Yes", "/On", "On", "O"):
            return "true"
        return sval

    def _store_field(key, raw_val) -> None:
        if not key:
            return
        value = _clean_pdf_value(raw_val)
        if not value:
            return
        key = str(key).strip()
        current = str(all_fields.get(key, "") or "")
        # Keep the longer non-empty value when duplicate widgets exist across pages.
        if not current or len(value) > len(current):
            all_fields[key] = value

    try:
        raw_fields = reader.get_fields() or {}
        for key, value in raw_fields.items():
            raw_val = value.get("/V", "") if hasattr(value, "get") else ""
            _store_field(key, raw_val)
    except Exception:
        pass

    # D&D Beyond PDFs often expose values on page widget annotations even when
    # get_fields()/get_form_text_fields() is sparse or empty.
    try:
        for page in reader.pages:
            ann_ref = page.get("/Annots")
            annots = ann_ref.get_object() if ann_ref else []
            for annot_ref in annots or []:
                try:
                    annot = annot_ref.get_object()
                except Exception:
                    continue
                if str(annot.get("/Subtype")) != "/Widget":
                    continue
                key = annot.get("/T")
                if not key:
                    continue
                _store_field(key, annot.get("/V", ""))
    except Exception:
        pass

    for key, value in (fields or {}).items():
        _store_field(key, value)

    def normalize_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    normalized_items: list[tuple[str, str, str]] = []
    normalized_exact: dict[str, str] = {}
    for key, value in all_fields.items():
        val = str(value or "").strip()
        if not val:
            continue
        normalized = normalize_key(key)
        normalized_items.append((normalized, str(key), val))
        normalized_exact.setdefault(normalized, val)

    def clean_text(value, keep_newlines: bool = False) -> str:
        text_value = str(value or "").strip()
        if text_value in {"--", "—", "None", "null"}:
            return ""
        if keep_newlines:
            return re.sub(r"\n{3,}", "\n\n", text_value.replace("\r", "")).strip()
        return re.sub(r"\s+", " ", text_value).strip()

    def g(*patterns, default: str = "", keep_newlines: bool = False) -> str:
        for pattern in patterns:
            target = normalize_key(pattern)
            if target in normalized_exact:
                value = clean_text(normalized_exact[target], keep_newlines=keep_newlines)
                if value:
                    return value
            for norm_key, _orig_key, value in normalized_items:
                if target and (
                    target == norm_key or target in norm_key or norm_key in target
                ):
                    value = clean_text(value, keep_newlines=keep_newlines)
                    if value:
                        return value
        return default

    def gi(*patterns, default: int = 0) -> int:
        value = g(*patterns)
        if value == "":
            return default
        m = re.search(r"[-+]?\d[\d,]*", str(value))
        if not m:
            return default
        try:
            return int(m.group(0).replace(",", ""))
        except Exception:
            return default

    def format_bonus(value: int) -> str:
        return f"{value:+d}"

    # ── Identity ──────────────────────────────────────────────────────────────
    name = (
        g("CharacterName", "CharacterName2", "CharacterName3", "CharacterName4", "CHARACTER NAME")
        or "Unknown Hero"
    )
    player_name = g("PLAYER NAME", "PLAYER NAME2", "PLAYER NAME3")
    class_level = g("CLASS LEVEL", "CLASSLEVEL", "CLASS LEVEL2", "CLASS LEVEL3")
    race = g("RACE", "SPECIES", "RACE2", "RACE3")
    background = g("BACKGROUND", "BACKGROUND2", "BACKGROUND3")
    alignment = g("ALIGNMENT")
    experience = g("EXPERIENCE POINTS", "EXPERIENCE POINTS2", "EXPERIENCE POINTS3")
    faction = g("FACTION", "PARTY")
    personality = g("PersonalityTraits")

    # ── Classes ───────────────────────────────────────────────────────────────
    classes: list[dict] = []
    if class_level:
        for part in re.split(r"[/,]", class_level):
            part = part.strip()
            if not part:
                continue
            m = re.match(r"([A-Za-z][A-Za-z' \-]+?)\s*(\d+)$", part)
            if m:
                classes.append({"name": m.group(1).strip(), "level": int(m.group(2)), "subclass": None})
        if not classes:
            m = re.search(r"([A-Za-z][A-Za-z' \-]+?)\s*(\d+)", class_level)
            if m:
                classes.append({"name": m.group(1).strip(), "level": int(m.group(2)), "subclass": None})
    if not classes:
        classes = [{"name": class_level or "Adventurer", "level": 1, "subclass": None}]
    total_level = sum(max(1, int(c.get("level") or 1)) for c in classes)

    # ── Core stats ────────────────────────────────────────────────────────────
    stats = [
        gi("STR", default=10), gi("DEX", default=10), gi("CON", default=10),
        gi("INT", default=10), gi("WIS", default=10), gi("CHA", default=10),
    ]
    stat_mods = [(score - 10) // 2 for score in stats]

    ac = gi("AC", default=10)
    speed_raw = g("Speed", default="30")
    speed_match = re.search(r"(\d+)", speed_raw)
    speed = int(speed_match.group(1)) if speed_match else 30
    max_hp = gi("MaxHP", "HPMax", default=max(1, 8 + stat_mods[2] * max(1, total_level)))
    current_hp = gi("CurrentHP", "HPCurrent", default=max_hp)
    temp_hp = gi("TempHP", "HPTemp", default=0)
    initiative = gi("Init", "Initiative", default=0)
    prof_bonus = gi("ProfBonus", default=max(2, (max(total_level, 1) - 1) // 4 + 2))
    hit_dice = g("Total", "HitDice", "HIT DICE")
    passive_perception = gi("Passive1", "PassivePerception", default=10 + stat_mods[4])
    passive_insight = gi("Passive2", "PassiveInsight", default=10 + stat_mods[4])
    passive_investigation = gi("Passive3", "PassiveInvestigation", default=10 + stat_mods[3])

    save_map = {
        "Strength": g("ST Strength") or format_bonus(stat_mods[0]),
        "Dexterity": g("ST Dexterity") or format_bonus(stat_mods[1]),
        "Constitution": g("ST Constitution") or format_bonus(stat_mods[2]),
        "Intelligence": g("ST Intelligence") or format_bonus(stat_mods[3]),
        "Wisdom": g("ST Wisdom") or format_bonus(stat_mods[4]),
        "Charisma": g("ST Charisma") or format_bonus(stat_mods[5]),
    }

    # ── Skills ────────────────────────────────────────────────────────────────
    skill_fields = [
        ("Acrobatics", "Acrobatics"), ("Animal Handling", "Animal"),
        ("Arcana", "Arcana"), ("Athletics", "Athletics"),
        ("Deception", "Deception"), ("History", "History"),
        ("Insight", "Insight"), ("Intimidation", "Intimidation"),
        ("Investigation", "Investigation"), ("Medicine", "Medicine"),
        ("Nature", "Nature"), ("Perception", "Perception"),
        ("Performance", "Performance"), ("Persuasion", "Persuasion"),
        ("Religion", "Religion"), ("Sleight of Hand", "SleightofHand"),
        ("Stealth", "Stealth"), ("Survival", "Survival"),
    ]
    skills: dict[str, str] = {}
    prof_skills: list[str] = []
    half_skills: list[str] = []
    for label, field_key in skill_fields:
        value = g(field_key)
        if value:
            skills[label] = value
        prof_flag = g(f"{field_key}Prof")
        if prof_flag and prof_flag not in {"0", "false"}:
            prof_skills.append(label)

    proficiencies = g("ProficienciesLang", keep_newlines=True)
    senses = g("AdditionalSenses", keep_newlines=True)
    defenses = g("Defenses", keep_newlines=True)
    save_modifiers = g("SaveModifiers", keep_newlines=True)
    resistances = defenses
    campaign_notes = "\n\n".join(part for part in [save_modifiers, personality] if part)

    # ── Attacks ───────────────────────────────────────────────────────────────
    attacks: list[dict] = []
    attacks_text_lines: list[str] = []
    seen_attacks: set = set()
    seen_attack_names: set = set()
    for idx in range(0, 12):
        name_keys = [
            "Wpn Name" if idx == 0 else f"Wpn Name {idx+1}",
            f"WpnName{idx}", f"WeaponName{idx}",
        ]
        atk_keys = [f"Wpn{idx+1} AtkBonus", f"Wpn{idx+1}AtkBonus", f"Weapon{idx+1}AtkBonus"]
        dmg_keys = [f"Wpn{idx+1} Damage", f"Wpn{idx+1}Damage", f"Weapon{idx+1}Damage"]
        note_keys = [f"Wpn Notes {idx+1}", f"WpnNotes{idx+1}", f"WeaponNotes{idx+1}"]
        name_value = g(*name_keys)
        if not name_value:
            continue
        entry = {
            "name": name_value,
            "attack": g(*atk_keys),
            "damage": g(*dmg_keys),
            "notes": g(*note_keys, keep_newlines=True),
        }
        name_key = normalize_key(name_value)
        compact = (name_key, entry["attack"], entry["damage"], clean_text(entry["notes"], keep_newlines=True))
        if compact in seen_attacks:
            continue
        if name_key in seen_attack_names and not (entry["attack"] or entry["damage"] or entry["notes"]):
            continue
        seen_attacks.add(compact)
        seen_attack_names.add(name_key)
        attacks.append(entry)
        parts = [entry["name"]]
        if entry["attack"]:
            parts.append(f"Hit {entry['attack']}")
        if entry["damage"]:
            parts.append(entry["damage"])
        if entry["notes"]:
            parts.append(entry["notes"])
        attacks_text_lines.append(" — ".join(parts))

    # ── Actions / Features ────────────────────────────────────────────────────
    actions_blocks = [g(f"Actions{idx}", keep_newlines=True) for idx in range(1, 10)]
    actions_text = "\n\n".join(b for b in actions_blocks if b)

    features_blocks = [g(f"FeaturesTraits{idx}", keep_newlines=True) for idx in range(1, 8)]
    features_text = "\n\n".join(b for b in features_blocks if b)

    # ── Equipment ─────────────────────────────────────────────────────────────
    equipment: list[dict] = []
    seen_equipment: set = set()
    for idx in range(0, 160):
        item_name = g(f"Eq Name{idx}")
        if not item_name:
            continue
        qty = gi(f"Eq Qty{idx}", default=1)
        weight = g(f"Eq Weight{idx}")
        key_eq = (item_name.lower(), qty, weight)
        if key_eq in seen_equipment:
            continue
        seen_equipment.add(key_eq)
        equipment.append({"name": item_name, "qty": max(1, qty), "weight": weight})

    attuned: list[dict] = []
    for idx in range(1, 40):
        item_name = g(f"Attuned Name{idx}")
        if not item_name:
            continue
        attuned.append({
            "name": item_name,
            "qty": max(1, gi(f"Attuned Qty{idx}", default=1)),
            "weight": g(f"Attuned Weight{idx}"),
        })

    def format_equipment_line(item: dict) -> str:
        qty = max(1, int(item.get("qty") or 1))
        weight = item.get("weight") or ""
        parts = [f"{item.get('name')}"]
        if qty != 1:
            parts[0] += f" ×{qty}"
        if weight and weight not in {"--", "—"}:
            parts.append(weight)
        return " — ".join(parts)

    gear_text_parts = []
    if equipment:
        gear_text_parts.append("Equipment\n" + "\n".join(format_equipment_line(i) for i in equipment))
    if attuned:
        gear_text_parts.append("Attuned Magic Items\n" + "\n".join(format_equipment_line(i) for i in attuned))
    gear_text = "\n\n".join(gear_text_parts)

    # ── Currency ──────────────────────────────────────────────────────────────
    currency_map = {
        "pp": gi("PP", default=0), "gp": gi("GP", default=0),
        "ep": gi("EP", default=0), "sp": gi("SP", default=0),
        "cp": gi("CP", default=0),
    }
    currency_label = ", ".join(
        f"{amount} {coin}" for coin, amount in currency_map.items() if amount is not None
    )

    # ── Spells ────────────────────────────────────────────────────────────────
    spell_ability = g("spellCastingAbility0", "spellCastingAbility")
    spell_save_dc = g("spellSaveDC0", "spellSaveDC")
    spell_attack = g("spellAtkBonus0", "spellAttackBonus0", "spellAtkBonus")
    spell_class = g("spellCastingClass0", "spellCastingClass") or (classes[0]["name"] if classes else "")

    spell_slots: dict[str, int] = {}
    spell_slot_lines: list[str] = []
    spell_section_labels: dict[int, str] = {}
    for idx in range(0, 12):
        header = g(f"spellHeader{idx}")
        slot_header = g(f"spellSlotHeader{idx}")
        if header or slot_header:
            level_match = re.search(
                r"(cantrip|\d+(?:st|nd|rd|th)\s+level)",
                f"{header} {slot_header}", re.I,
            )
            level_label = level_match.group(1).title() if level_match else (header or f"Section {idx+1}")
            if slot_header:
                slots_match = re.search(r"(\d+)\s*Slots?\s*([Oo•]*)", slot_header, re.I)
                if slots_match:
                    spell_slots[str(idx)] = int(slots_match.group(1))
                spell_slot_lines.append(f"{level_label}: {slot_header}")
        label_bits = []
        if header:
            label_bits.append(re.sub(r"=+", "", header).strip())
        if slot_header and slot_header not in {"(At Will)", ""}:
            label_bits.append(slot_header.strip())
        spell_section_labels[idx] = " — ".join(bit for bit in label_bits if bit)

    spell_entries: list[dict] = []
    current_spell_section = ""
    for idx in range(0, 240):
        header_probe = g(f"spellHeader{idx}")
        if header_probe:
            cleaned = re.sub(r"=+", "", header_probe).strip()
            current_spell_section = cleaned or current_spell_section
        spell_name = g(f"spellName{idx}")
        if not spell_name:
            continue
        section_index = min(9, idx // 3)
        spell_entries.append({
            "name": spell_name,
            "section": current_spell_section or spell_section_labels.get(section_index, ""),
            "source": g(f"spellSource{idx}"),
            "saveHit": g(f"spellSaveHit{idx}"),
            "time": g(f"spellCastingTime{idx}"),
            "range": g(f"spellRange{idx}"),
            "components": g(f"spellComponents{idx}"),
            "duration": g(f"spellDuration{idx}"),
            "page": g(f"spellPage{idx}"),
            "notes": g(f"spellNotes{idx}", keep_newlines=True),
        })

    spell_lines: list[str] = []
    for entry in spell_entries:
        parts = [entry.get("name") or ""]
        meta = [
            v for v in [
                entry.get("source"), entry.get("saveHit"), entry.get("time"),
                entry.get("range"), entry.get("duration"), entry.get("notes"),
            ] if v
        ]
        if meta:
            parts.append(" — ".join(meta))
        spell_lines.append(" — ".join(parts))
    spells_text = "\n".join(spell_lines)

    # ── Assemble book / result ────────────────────────────────────────────────
    book = {
        "name": name,
        "className": " / ".join(c["name"] for c in classes if c.get("name")),
        "subclass": " / ".join(c.get("subclass") for c in classes if c.get("subclass")),
        "race": race,
        "background": background,
        "alignment": alignment,
        "level": total_level,
        "experience": experience,
        "faction": faction,
        "campaignNotes": campaign_notes,
        "currentHp": current_hp,
        "maxHp": max_hp,
        "tempHp": temp_hp,
        "initiative": initiative,
        "ac": ac,
        "speed": speed,
        "passivePerception": passive_perception,
        "profBonus": prof_bonus,
        "hitDice": hit_dice,
        "currency": currency_label,
        "attacks": "\n".join(attacks_text_lines),
        "actions": actions_text,
        "gear": gear_text,
        "proficiencies": proficiencies,
        "senses": "\n".join(
            part for part in [
                senses,
                f"Passive Perception {passive_perception}",
                f"Passive Insight {passive_insight}",
                f"Passive Investigation {passive_investigation}",
            ] if part
        ),
        "resistances": resistances,
        "vulnerabilities": "",
        "features": features_text,
        "feats": "",
        "spells": spells_text,
        "spellAbility": spell_ability,
        "spellSaveDc": spell_save_dc,
        "spellAttack": spell_attack,
        "spellSlots": "\n".join(spell_slot_lines),
        "abilityScores": {
            "strength": stats[0], "dexterity": stats[1], "constitution": stats[2],
            "intelligence": stats[3], "wisdom": stats[4], "charisma": stats[5],
        },
        "savingThrows": save_map,
        "skills": skills,
        "importedInventoryItems": [
            {
                "name": item["name"],
                "qty": item["qty"],
                "notes": (item.get("weight") or "").strip(),
                "price": "",
            }
            for item in equipment
        ],
        "importedCurrency": currency_map,
    }

    return {
        "name": name,
        "playerName": player_name,
        "race": race,
        "background": background,
        "alignment": alignment,
        "classes": classes,
        "totalLevel": total_level,
        "profBonus": prof_bonus,
        "stats": stats,
        "maxHp": max_hp,
        "currentHp": current_hp,
        "tempHp": temp_hp,
        "ac": ac,
        "speed": speed,
        "initiative": initiative,
        "passivePerception": passive_perception,
        "spellSlots": spell_slots,
        "profSkills": prof_skills,
        "halfSkills": half_skills,
        "skillMap": {
            "Acrobatics": 2, "Animal Handling": 5, "Arcana": 4, "Athletics": 1,
            "Deception": 6, "History": 4, "Insight": 5, "Intimidation": 6,
            "Investigation": 4, "Medicine": 5, "Nature": 4, "Perception": 5,
            "Performance": 6, "Persuasion": 6, "Religion": 4, "Sleight of Hand": 2,
            "Stealth": 2, "Survival": 5,
        },
        "currency": currency_label,
        "book": book,
        "spellbookEntries": spell_entries,
        "inventoryEntries": book["importedInventoryItems"],
        "currencyBreakdown": currency_map,
        "source": "pdf",
        "_rawFields": dict(all_fields),
        "_spellMeta": {
            "ability": spell_ability,
            "saveDc": spell_save_dc,
            "attack": spell_attack,
            "className": spell_class,
        },
    }

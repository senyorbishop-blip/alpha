"""Helpers for generating richer native class feature metadata and runtime slices.

Stage 1 goal:
- turn sparse progression tables into structured feature definitions
- expose useful runtime actions/passives/resources for native characters
- keep the implementation conservative and data-driven
"""
from __future__ import annotations

import copy
import re
from typing import Any

from server.character.feature_authored_data import build_feature_profile


def _safe_int(value: Any, fallback: int = 0, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = fallback
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _normalized_feature_name(name: Any) -> str:
    text = str(name or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s*\([^)]*\)", "", text).strip()
    return text


def _clean_player_text(value: Any) -> str:
    text = str(value or '').replace('\r', '').strip()
    if not text:
        return ''
    blocked_patterns = [
        r'\bthe sheet should\b',
        r'\bthe sheet should make\b',
        r'\bthe player should\b',
        r'\bpractical effect\b',
        r'\bthis shines most when\b',
        r'\bstart here\b',
        r'\bbest time to use it\b',
        r'\busually watch\b',
        r'\bimportant thing is\b',
        r'\bhidden unlock\b',
        r'\bin-app job\b',
        r'\bvisible in the sheet\b',
        r'\bin play, this should feel\b',
    ]
    paragraphs = [part.strip() for part in re.split(r'\n{2,}', text) if str(part or '').strip()]
    kept: list[str] = []
    for paragraph in paragraphs:
        lowered = paragraph.lower()
        if any(re.search(pattern, lowered) for pattern in blocked_patterns):
            continue
        cleaned = re.sub(r'\b[Ii]n play,?\s*', '', paragraph)
        cleaned = re.sub(r'\b[Tt]his matters because\b', 'It matters because', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'\s+([.,;:!?])', r'\1', cleaned)
        if cleaned:
            kept.append(cleaned)
    if not kept:
        return ''
    return '\n\n'.join(kept)


def _sanitize_feature_definition(defn: dict[str, Any], *, fallback_name: str, fallback_level: int, fallback_summary: str = '') -> dict[str, Any]:
    merged = copy.deepcopy(defn or {})
    summary = _clean_player_text(merged.get('summary') or fallback_summary)
    description = _clean_player_text(merged.get('description'))
    if not summary:
        summary = fallback_summary or (f'Level {fallback_level} {fallback_name} feature.' if fallback_level else f'{fallback_name} feature.')
    if not description:
        description = summary
    merged['summary'] = summary
    merged['description'] = description
    for key in ('effect', 'recovery', 'usage', 'trigger', 'save', 'range', 'duration'):
        if key in merged:
            merged[key] = _clean_player_text(merged.get(key))
    return merged


FEATURE_METADATA: dict[str, dict[str, Any]] = {
    "rage": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "resourceName": "Rage",
        "trackUses": True,
        "description": "Enter a Rage to gain offensive and defensive benefits. Uses are limited and recover on rest.",
        "tags": ["combat", "resource"],
    },
    "bardic inspiration": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "resourceName": "Bardic Inspiration",
        "trackUses": True,
        "description": "Grant an ally a Bardic Inspiration die they can add to a later roll.",
        "tags": ["support", "resource"],
    },
    "channel divinity": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Channel Divinity",
        "trackUses": True,
        "description": "Spend Channel Divinity to activate your divine options such as Divine Spark or Turn Undead.",
        "tags": ["divine", "resource"],
    },
    "wild shape": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Wild Shape",
        "trackUses": True,
        "description": "Transform into a beast form, replacing parts of your stat block with the chosen form.",
        "tags": ["shapechange", "resource"],
    },
    "second wind": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "resourceName": "Second Wind",
        "trackUses": True,
        "description": "Use a bonus action to regain hit points and steady yourself in combat.",
        "tags": ["healing", "resource"],
    },
    "action surge": {
        "section": "Class Features",
        "type": "special",
        "resourceName": "Action Surge",
        "trackUses": True,
        "description": "Push beyond your limits and gain an extra action on your turn.",
        "tags": ["combat", "resource"],
    },
    "monk's focus": {
        "section": "Class Features",
        "type": "passive",
        "resourceName": "Focus Points",
        "trackUses": True,
        "description": "Gain Focus Points used to fuel Monk techniques and special maneuvers.",
        "tags": ["resource"],
    },
    "ki / discipline points": {
        "section": "Class Features",
        "type": "passive",
        "resourceName": "Focus Points",
        "trackUses": True,
        "description": "Track your monk resource pool for techniques such as Flurry of Blows and Patient Defense.",
        "tags": ["resource"],
    },
    "lay on hands": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Lay on Hands",
        "trackUses": True,
        "description": "Spend points from your Lay on Hands pool to heal a creature or cure certain conditions.",
        "tags": ["healing", "resource"],
    },
    "sneak attack": {
        "section": "Class Features",
        "type": "passive",
        "description": "Once per turn, deal extra damage when you hit under the right conditions.",
        "tags": ["combat"],
    },
    "cunning action": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "description": "Take Dash, Disengage, or Hide as a bonus action.",
        "tags": ["mobility"],
    },
    "uncanny dodge": {
        "section": "Reactions",
        "type": "reaction",
        "description": "Use your reaction to reduce the damage of an attack that hits you.",
        "tags": ["defense"],
    },
    "evasion": {
        "section": "Class Features",
        "type": "passive",
        "description": "Avoid the full force of effects that allow Dexterity saves for half damage.",
        "tags": ["defense"],
    },
    "sorcery points": {
        "section": "Class Features",
        "type": "passive",
        "resourceName": "Sorcery Points",
        "trackUses": True,
        "description": "Track Sorcery Points used for Metamagic and spell-slot conversion.",
        "tags": ["resource", "spellcasting"],
    },
    "font of magic": {
        "section": "Class Features",
        "type": "special",
        "description": "Convert Sorcery Points into spell slots and spell slots into Sorcery Points.",
        "tags": ["spellcasting", "resource"],
    },
    "metamagic": {
        "section": "Class Features",
        "type": "special",
        "description": "Modify the way your spells work by spending Sorcery Points on Metamagic options.",
        "tags": ["spellcasting"],
    },
    "arcane recovery": {
        "section": "Class Features",
        "type": "special",
        "resourceName": "Arcane Recovery",
        "trackUses": True,
        "description": "Recover expended spell slots during a short rest, within your recovery limit.",
        "tags": ["spellcasting", "resource"],
    },
    "pact magic": {
        "section": "Class Features",
        "type": "passive",
        "description": "Your Pact Magic slots are few but refresh on a short or long rest.",
        "tags": ["spellcasting"],
    },
    "eldritch invocations": {
        "section": "Class Features",
        "type": "passive",
        "description": "Gain permanent magical customizations through Eldritch Invocations.",
        "tags": ["customization"],
    },
    "action surge": {
        "section": "Class Features",
        "type": "special",
        "resourceName": "Action Surge",
        "trackUses": True,
        "description": "Gain an extra action on your turn by spending an Action Surge use.",
        "tags": ["resource", "combat"],
    },
    "reckless attack": {
        "section": "Class Features",
        "type": "special",
        "description": "Choose to attack recklessly for advantage, while making yourself easier to hit.",
        "tags": ["combat"],
    },
    "danger sense": {
        "section": "Class Features",
        "type": "passive",
        "description": "Gain heightened awareness against visible dangers and traps.",
        "tags": ["defense"],
    },
    "martial arts": {
        "section": "Class Features",
        "type": "passive",
        "description": "Use your Martial Arts die for unarmed strikes and chain martial actions together.",
        "tags": ["combat"],
    },
    "stunning strike": {
        "section": "Class Features",
        "type": "special",
        "description": "On a hit, spend Focus to force a saving throw that can leave the target stunned.",
        "tags": ["control", "resource"],
    },
    "deflect attacks": {
        "section": "Reactions",
        "type": "reaction",
        "description": "Use your reaction to reduce or redirect incoming damage from attacks.",
        "tags": ["defense"],
    },
    "divine sense": {
        "section": "Actions",
        "type": "action",
        "description": "Sense strong celestial, fiendish, or undead presence around you.",
        "tags": ["utility"],
    },
    "divine smite": {
        "section": "Class Features",
        "type": "special",
        "description": "Spend a spell slot when you hit to add radiant burst damage to the attack.",
        "tags": ["combat", "spellcasting"],
    },
    "favored enemy": {
        "section": "Class Features",
        "type": "passive",
        "description": "Gain Hunter's Mark support and bonuses tied to your chosen prey.",
        "tags": ["combat", "spellcasting"],
    },
    "hunter's mark": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "description": "Mark a target to deal extra damage and improve tracking against it.",
        "tags": ["combat", "spellcasting"],
    },
    "divine intervention": {
        "section": "Actions",
        "type": "action",
        "description": "Call on your deity for direct aid when the moment truly matters.",
        "tags": ["divine"],
    },
    "extra attack": {
        "section": "Class Features",
        "type": "passive",
        "description": "Make additional attacks whenever you take the Attack action.",
        "tags": ["combat"],
    },
    "fighting style": {
        "section": "Class Features",
        "type": "passive",
        "description": "Gain a persistent combat specialty that shapes how you fight.",
        "tags": ["combat"],
    },
    "weapon mastery": {
        "section": "Class Features",
        "type": "passive",
        "description": "Unlock mastery properties for weapons you are trained to use effectively.",
        "tags": ["combat"],
    },
    "spellcasting": {
        "section": "Class Features",
        "type": "passive",
        "description": "Gain spell slots, a spellcasting ability, and access to magical options from your class list.",
        "tags": ["spellcasting"],
    },
}


RESOURCE_FIELD_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "rageUses": {"id": "rage_uses", "name": "Rage", "section": "Bonus Actions", "type": "bonus action", "trackUses": True},
    "disciplinePoints": {"id": "focus_points", "name": "Focus Points", "section": "Class Features", "type": "passive", "trackUses": True},
    "focusPoints": {"id": "focus_points", "name": "Focus Points", "section": "Class Features", "type": "passive", "trackUses": True},
    "bardicInspirationDie": {"id": "bardic_inspiration", "name": "Bardic Inspiration", "section": "Bonus Actions", "type": "bonus action", "trackUses": True},
    "channelDivinityUses": {"id": "channel_divinity", "name": "Channel Divinity", "section": "Actions", "type": "action", "trackUses": True},
    "wildShapeUses": {"id": "wild_shape", "name": "Wild Shape", "section": "Actions", "type": "action", "trackUses": True},
    "actionSurgeUses": {"id": "action_surge", "name": "Action Surge", "section": "Class Features", "type": "special", "trackUses": True},
    "indomitableUses": {"id": "indomitable", "name": "Indomitable", "section": "Class Features", "type": "special", "trackUses": True},
    "layOnHandsPool": {"id": "lay_on_hands", "name": "Lay on Hands", "section": "Actions", "type": "action", "trackUses": True},
    "sorceryPoints": {"id": "sorcery_points", "name": "Sorcery Points", "section": "Class Features", "type": "passive", "trackUses": True},
}


RESOURCE_RECOVERY_HINTS = {
    "rage_uses": "Short Rest: regain 1 use. Long Rest: regain all uses.",
    "focus_points": "Regain all expended Focus Points on a short or long rest.",
    "bardic_inspiration": "Long Rest recovery at low levels; upgrades to Short or Long Rest with Font of Inspiration.",
    "channel_divinity": "Short Rest: regain 1 use. Long Rest: regain all uses.",
    "wild_shape": "Short Rest: regain 1 use. Long Rest: regain all uses.",
    "action_surge": "Regain all uses on a short or long rest.",
    "indomitable": "Regain all uses on a long rest.",
    "lay_on_hands": "The pool refreshes on a long rest.",
    "sorcery_points": "Sorcery Points refresh on a long rest.",
}


def _feature_meta(feature_name: str) -> dict[str, Any]:
    normalized = _normalized_feature_name(feature_name).lower()
    return copy.deepcopy(FEATURE_METADATA.get(normalized) or {})


def _feature_definition_from_row(
    *,
    feature_id: str,
    feature_label: str,
    level: int,
    class_name: str = '',
    subclass_name: str = '',
    source_kind: str = 'class',
    raw_description: str = '',
) -> dict[str, Any]:
    meta = _feature_meta(feature_label)
    enriched = build_feature_profile(
        name=feature_label,
        level=level,
        description=raw_description,
        feature_id=feature_id,
        class_name=class_name,
        subclass_name=subclass_name,
        source_kind=source_kind,
        defaults=meta,
    )
    return {
        'id': feature_id,
        'displayName': enriched.get('displayName') or feature_label,
        'summary': str(enriched.get('summary') or '').strip(),
        'description': str(enriched.get('description') or '').strip(),
        'level': level,
        'section': str(enriched.get('section') or meta.get('section') or 'Class Features'),
        'type': str(enriched.get('type') or meta.get('type') or 'passive'),
        'resourceName': str(enriched.get('resourceName') or meta.get('resourceName') or ''),
        'trackUses': bool(enriched.get('trackUses') or meta.get('trackUses')),
        'tags': list(enriched.get('tags') or meta.get('tags') or []),
        'choices': [],
        'range': str(enriched.get('range') or ''),
        'duration': str(enriched.get('duration') or ''),
        'save': str(enriched.get('save') or ''),
        'trigger': str(enriched.get('trigger') or ''),
        'usage': str(enriched.get('usage') or ''),
        'recovery': str(enriched.get('recovery') or ''),
        'effect': str(enriched.get('effect') or ''),
        'dice': str(enriched.get('dice') or ''),
        'sourceKind': source_kind,
        'className': class_name,
        'subclassName': subclass_name,
    }


def build_class_feature_definitions(class_row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(class_row, dict):
        return {}
    existing = copy.deepcopy(class_row.get('featureDefinitions')) if isinstance(class_row.get('featureDefinitions'), dict) else {}

    class_id = str(class_row.get('id') or 'class').strip().lower() or 'class'
    class_name = str(class_row.get('displayName') or class_row.get('name') or class_id.title()).strip()
    rows = class_row.get('progressionTable') if isinstance(class_row.get('progressionTable'), list) else []
    definitions: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        level = _safe_int(row.get('level'), 0, minimum=0)
        unlock_ids = [str(v or '').strip() for v in (row.get('unlockIds') or []) if str(v or '').strip()]
        features = row.get('features') if isinstance(row.get('features'), list) else []
        for idx, feature_label in enumerate(features):
            label = str(feature_label or '').strip()
            if not label:
                continue
            feature_id = unlock_ids[idx] if idx < len(unlock_ids) else f'{class_id}-l{level}-{idx+1}'
            generated = _feature_definition_from_row(
                feature_id=feature_id,
                feature_label=label,
                level=level,
                class_name=class_name,
                source_kind='class',
            )
            existing_row = existing.get(feature_id) if isinstance(existing.get(feature_id), dict) else {}
            merged = {**generated, **copy.deepcopy(existing_row)}
            merged.setdefault('id', feature_id)
            merged.setdefault('displayName', generated.get('displayName') or label)
            merged.setdefault('level', level)
            definitions[feature_id] = _sanitize_feature_definition(
                merged,
                fallback_name=str(merged.get('displayName') or label),
                fallback_level=level,
                fallback_summary=str(generated.get('summary') or ''),
            )
    for key, value in existing.items():
        if key not in definitions:
            definitions[key] = copy.deepcopy(value)
    return definitions


def build_subclass_feature_definitions(subclass_row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(subclass_row, dict):
        return {}
    existing = copy.deepcopy(subclass_row.get('featureDefinitions')) if isinstance(subclass_row.get('featureDefinitions'), dict) else {}

    subclass_id = str(subclass_row.get('id') or 'subclass').strip().lower() or 'subclass'
    subclass_name = str(subclass_row.get('displayName') or subclass_id.title()).strip()
    class_name = str(subclass_row.get('classId') or '').strip()
    rows = subclass_row.get('features') if isinstance(subclass_row.get('features'), list) else []
    definitions: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        label = str(row.get('displayName') or row.get('name') or row.get('id') or '').strip()
        if not label:
            continue
        level = _safe_int(row.get('level'), 0, minimum=0)
        feature_id = str(row.get('id') or f'{subclass_id}-l{level}-{idx+1}').strip()
        generated = _feature_definition_from_row(
            feature_id=feature_id,
            feature_label=label,
            level=level,
            class_name=class_name,
            subclass_name=subclass_name,
            source_kind='subclass',
            raw_description=str(row.get('description') or '').strip(),
        )
        existing_row = existing.get(feature_id) if isinstance(existing.get(feature_id), dict) else {}
        merged = {**generated, **copy.deepcopy(existing_row)}
        merged.setdefault('id', feature_id)
        merged.setdefault('displayName', generated.get('displayName') or label)
        merged.setdefault('level', level)
        definitions[feature_id] = _sanitize_feature_definition(
            merged,
            fallback_name=str(merged.get('displayName') or label),
            fallback_level=level,
            fallback_summary=str(generated.get('summary') or ''),
        )
    for key, value in existing.items():
        if key not in definitions:
            definitions[key] = copy.deepcopy(value)
    return definitions


def build_features_by_level(class_row: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(class_row, dict):
        return []
    feature_defs = build_class_feature_definitions(class_row)
    rows = class_row.get('progressionTable') if isinstance(class_row.get('progressionTable'), list) else []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        level = _safe_int(row.get('level'), 0, minimum=0)
        features = row.get('features') if isinstance(row.get('features'), list) else []
        unlock_ids = [str(v or '').strip() for v in (row.get('unlockIds') or []) if str(v or '').strip()]
        items: list[dict[str, Any]] = []
        for idx, label in enumerate(features):
            feature_id = unlock_ids[idx] if idx < len(unlock_ids) else f"{class_row.get('id')}-l{level}-{idx+1}"
            details = copy.deepcopy(feature_defs.get(feature_id) or {})
            details.setdefault('id', feature_id)
            details.setdefault('displayName', str(label or '').strip())
            details.setdefault('level', level)
            items.append(details)
        out.append({'level': level, 'features': items})
    return out


def _resource_summary_from_mechanics(class_mechanics: dict[str, Any], *, ability_scores: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    ability_scores = ability_scores if isinstance(ability_scores, dict) else {}
    cha_score = _safe_int(ability_scores.get('cha'), 10, minimum=1)
    cha_mod = (cha_score - 10) // 2
    bardic_refresh_raw = str(class_mechanics.get('bardicInspirationRefresh') or '').strip().lower()
    bardic_refresh_text = ''
    if bardic_refresh_raw == 'longrest':
        bardic_refresh_text = 'Long Rest'
    elif bardic_refresh_raw == 'shortorlongrest':
        bardic_refresh_text = 'Short or Long Rest'
    for field, blueprint in RESOURCE_FIELD_BLUEPRINTS.items():
        if field not in class_mechanics:
            continue
        value = class_mechanics.get(field)
        if value in (None, 0, '0', ''):
            continue
        if field == 'bardicInspirationDie':
            die_text = str(value or '').strip().lower()
            if not die_text:
                continue
            uses = max(1, cha_mod)
            recovery = f"Refresh: {bardic_refresh_text}." if bardic_refresh_text else RESOURCE_RECOVERY_HINTS.get(str(blueprint['id']), '')
            resources.append(
                {
                    'id': str(blueprint['id']),
                    'name': str(blueprint['name']),
                    'current': uses,
                    'max': uses,
                    'summary': f'{die_text.upper()} • {uses}/{uses}',
                    'die': die_text.upper(),
                    'recovery': recovery,
                    'type': str(blueprint.get('type') or 'passive'),
                    'section': str(blueprint.get('section') or 'Class Features'),
                    'trackUses': bool(blueprint.get('trackUses')),
                }
            )
            continue
        is_unlimited = isinstance(value, str) and value.strip().lower() == 'unlimited'
        max_value = 999 if is_unlimited else _safe_int(value, 0, minimum=0)
        if not is_unlimited and max_value <= 0:
            continue
        resources.append(
            {
                'id': str(blueprint['id']),
                'name': str(blueprint['name']),
                'current': max_value,
                'max': max_value,
                'summary': 'Unlimited' if is_unlimited else f'{max_value}/{max_value}',
                'recovery': RESOURCE_RECOVERY_HINTS.get(str(blueprint['id']), ''),
                'type': str(blueprint.get('type') or 'passive'),
                'section': str(blueprint.get('section') or 'Class Features'),
                'trackUses': bool(blueprint.get('trackUses')),
            }
        )
    return resources


def _runtime_item_from_feature(feature: dict[str, Any], class_name: str, *, is_subclass: bool = False) -> dict[str, Any]:
    display_name = str(feature.get('displayName') or feature.get('name') or '').strip()
    feature_type = str(feature.get('type') or 'passive').strip().lower()
    summary = str(feature.get('summary') or '').strip()
    description = str(feature.get('description') or '').strip()
    return {
        'id': str(feature.get('id') or _slugify(display_name)),
        'name': display_name,
        'summary': summary,
        'description': summary if summary and not description else description,
        'text': description,
        'effect': str(feature.get('effect') or '').strip(),
        'type': feature_type,
        'range': str(feature.get('range') or '').strip(),
        'duration': str(feature.get('duration') or '').strip(),
        'save': str(feature.get('save') or '').strip(),
        'trigger': str(feature.get('trigger') or '').strip(),
        'usage': str(feature.get('usage') or '').strip(),
        'recovery': str(feature.get('recovery') or '').strip(),
        'resourceName': str(feature.get('resourceName') or '').strip(),
        'resourceSummary': str(feature.get('usage') or feature.get('recovery') or '').strip(),
        'typeLabel': feature_type,
        'tags': list(feature.get('tags') or []),
        'source': 'native',
        'details': {
            'source': class_name,
            'level': _safe_int(feature.get('level'), 0, minimum=0),
            'description': description,
            'summary': summary,
            'effect': str(feature.get('effect') or '').strip(),
            'range': str(feature.get('range') or '').strip(),
            'duration': str(feature.get('duration') or '').strip(),
            'save': str(feature.get('save') or '').strip(),
            'trigger': str(feature.get('trigger') or '').strip(),
            'usage': str(feature.get('usage') or '').strip(),
            'recovery': str(feature.get('recovery') or '').strip(),
            'subclass': bool(is_subclass),
        },
    }


def build_runtime_feature_payload(
    class_row: dict[str, Any] | None,
    *,
    class_name: str,
    level: int,
    subclass_row: dict[str, Any] | None = None,
    ability_scores: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(class_row, dict):
        return {'actions': [], 'bonusActions': [], 'reactions': [], 'passives': [], 'resources': [], 'classFeatures': []}

    defs = build_class_feature_definitions(class_row)
    by_level = build_features_by_level(class_row)
    unlocked_features: list[dict[str, Any]] = []
    for row in by_level:
        if _safe_int(row.get('level'), 0, minimum=0) > level:
            continue
        unlocked_features.extend(copy.deepcopy(row.get('features') or []))

    subclass_features: list[dict[str, Any]] = []
    subclass_name = ''
    if isinstance(subclass_row, dict):
        subclass_name = str(subclass_row.get('displayName') or subclass_row.get('id') or '').strip()
        sub_defs = build_subclass_feature_definitions(subclass_row)
        for feature in sub_defs.values():
            if _safe_int(feature.get('level'), 0, minimum=0) <= level:
                subclass_features.append(copy.deepcopy(feature))

    actions: list[dict[str, Any]] = []
    bonus_actions: list[dict[str, Any]] = []
    reactions: list[dict[str, Any]] = []
    passives: list[dict[str, Any]] = []
    class_features: list[dict[str, Any]] = []

    def ingest_feature(feature: dict[str, Any], *, is_subclass: bool = False) -> None:
        display_name = str(feature.get('displayName') or feature.get('name') or '').strip()
        if not display_name:
            return
        feature_type = str(feature.get('type') or 'passive').strip().lower()
        item = _runtime_item_from_feature(feature, class_name, is_subclass=is_subclass)
        class_features.append(
            {
                'id': item['id'],
                'name': display_name,
                'section': str(feature.get('section') or 'Class Features'),
                'type': feature_type,
                'className': class_name,
                'subclassName': subclass_name if is_subclass else '',
                'minLevel': _safe_int(feature.get('level'), 0, minimum=0),
                'resourceName': str(feature.get('resourceName') or '').strip(),
                'trackUses': bool(feature.get('trackUses')),
                'tags': list(feature.get('tags') or []),
                'summary': str(feature.get('summary') or '').strip(),
                'description': str(feature.get('description') or '').strip(),
                'range': str(feature.get('range') or '').strip(),
                'duration': str(feature.get('duration') or '').strip(),
                'save': str(feature.get('save') or '').strip(),
                'trigger': str(feature.get('trigger') or '').strip(),
                'usage': str(feature.get('usage') or '').strip(),
                'recovery': str(feature.get('recovery') or '').strip(),
                'effect': str(feature.get('effect') or '').strip(),
                'isSubclass': bool(is_subclass),
                'kind': 'class',
                'source': 'native',
            }
        )
        if feature_type == 'action':
            actions.append(item)
        elif feature_type == 'bonus action':
            bonus_actions.append(item)
        elif feature_type == 'reaction':
            reactions.append(item)
        else:
            passives.append(item)

    for feature in unlocked_features:
        ingest_feature(feature, is_subclass=False)
    for feature in subclass_features:
        ingest_feature(feature, is_subclass=True)

    progression_rows = class_row.get('progressionTable') if isinstance(class_row.get('progressionTable'), list) else []
    class_mechanics = next((row.get('classMechanics') for row in progression_rows if isinstance(row, dict) and _safe_int(row.get('level'), 0, minimum=0) == level and isinstance(row.get('classMechanics'), dict)), {})
    resources = _resource_summary_from_mechanics(
        class_mechanics if isinstance(class_mechanics, dict) else {},
        ability_scores=ability_scores,
    )

    resource_ids = {str(row.get('id') or '') for row in resources if isinstance(row, dict)}
    for feature in class_features:
        if not feature.get('trackUses'):
            continue
        resource_name = str(feature.get('resourceName') or feature.get('name') or '').strip()
        resource_id = _slugify(resource_name)
        if not resource_id or resource_id in resource_ids:
            continue
        resource_ids.add(resource_id)
        resources.append(
            {
                'id': resource_id,
                'name': resource_name,
                'current': 0,
                'max': 0,
                'summary': feature.get('usage') or 'Tracked in sheet text',
                'recovery': feature.get('recovery') or 'Manual tracking until a full automation rule is connected.',
                'type': feature.get('section', 'Class Features'),
                'section': feature.get('section', 'Class Features'),
                'trackUses': True,
            }
        )

    return {
        'actions': actions,
        'bonusActions': bonus_actions,
        'reactions': reactions,
        'passives': passives,
        'resources': resources,
        'classFeatures': class_features,
    }

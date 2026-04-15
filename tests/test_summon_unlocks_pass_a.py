from server.character.progression import apply_levelup
from server.character.resolver import resolve_character_runtime
from server.character.validation import validate_or_raise


def _summons(document: dict) -> dict:
    return (document.get("summons") or {}) if isinstance(document, dict) else {}


def test_warlock_pact_of_chain_levelup_unlocks_familiar_templates_without_duplicates():
    base = {
        "identity": {"name": "Nyx"},
        "classes": [{"classId": "warlock", "level": 2, "subclassId": "fiend-patron"}],
        "abilities": {"scores": {"cha": 16, "con": 14}},
    }

    applied_once = apply_levelup(
        base,
        choices={
            "featureChoices": {
                "warlock-pact-boon": "pact-of-the-chain",
                "warlock-eldritch-invocation-choice-l3": "agonizing-blast",
            }
        },
    )
    once_doc = applied_once["document"]
    once = _summons(once_doc)

    assert set(once.get("unlockedTemplates") or []) >= {
        "warlock-chain-imp",
        "warlock-chain-pseudodragon",
        "warlock-chain-quasit",
        "warlock-chain-sprite",
    }
    assert "warlock-pact-chain-familiar" in (once.get("unlockedGroups") or [])

    applied_twice = apply_levelup(
        once_doc,
        choices={"asiChoice": {"mode": "plus2", "ability": "cha"}},
    )
    twice = _summons(applied_twice["document"])

    assert len(twice.get("unlockedTemplates") or []) == len(set(twice.get("unlockedTemplates") or []))


def test_beast_master_subclass_choice_unlocks_primal_beasts_and_persists_variant_selection():
    applied = apply_levelup(
        {
            "identity": {"name": "Bran"},
            "classes": [{"classId": "ranger", "level": 2}],
            "abilities": {"scores": {"dex": 16, "wis": 14, "con": 14}},
        },
        choices={"subclassChoice": "beast-master"},
    )

    summons = _summons(applied["document"])
    assert set(summons.get("unlockedTemplates") or []) >= {
        "ranger-primal-beast-land",
        "ranger-primal-beast-sea",
        "ranger-primal-beast-sky",
    }
    assert summons.get("selectedVariants", {}).get("ranger-primal-beast") == "ranger-primal-beast-land"

    resolved = resolve_character_runtime(
        {
            "classes": [
                {
                    "classId": "ranger",
                    "level": 3,
                    "subclassId": "beast-master",
                    "selectedFeatures": [
                        {
                            "id": "beast-master-rangers-companion",
                            "selectedChoice": "ranger-primal-beast-sky",
                        }
                    ],
                }
            ],
            "abilities": {"scores": {"dex": 16, "wis": 14, "con": 14}},
        }
    )
    selected = _summons(resolved["document"]).get("selectedVariants", {})
    assert selected.get("ranger-primal-beast") == "ranger-primal-beast-sky"


def test_tinker_subclass_paths_unlock_companion_or_deployable_templates():
    mechanist = apply_levelup(
        {
            "classes": [{"classId": "tinker", "level": 2}],
            "abilities": {"scores": {"int": 16, "con": 14}},
        },
        choices={"subclassChoice": "mechanist"},
    )
    mech_templates = set(_summons(mechanist["document"]).get("unlockedTemplates") or [])
    assert "tinker-mechanist-companion-frame" in mech_templates

    artillerist = apply_levelup(
        {
            "classes": [{"classId": "tinker", "level": 2}],
            "abilities": {"scores": {"int": 16, "con": 14}},
        },
        choices={"subclassChoice": "artillerist"},
    )
    arti_templates = set(_summons(artillerist["document"]).get("unlockedTemplates") or [])
    assert "tinker-artillerist-arc-cannon" in arti_templates


def test_backward_compat_old_documents_without_summon_block_still_validate_and_non_summon_levelup_works():
    normalized = validate_or_raise(
        {
            "schema": "casual-dnd.character",
            "schemaVersion": 1,
            "rulesMode": "casual",
            "ruleset": "casual-dnd-5e-compatible",
            "sourceMode": "native",
            "identity": {"name": "Legacy"},
            "species": {},
            "background": {},
            "abilities": {"scores": {"str": 16, "dex": 12, "con": 14}},
            "classes": [{"classId": "fighter", "level": 2}],
            "feats": [],
            "talents": [],
            "awakening": {},
            "equipment": {},
            "spellState": {},
            "importMeta": {},
            "audit": {},
            "contentPackVersion": "",
        }
    )
    assert isinstance(normalized.get("summons"), dict)
    assert normalized["summons"].get("unlockedTemplates") == []

    applied = apply_levelup(
        {
            "classes": [{"classId": "fighter", "level": 2}],
            "abilities": {"scores": {"str": 16, "dex": 12, "con": 14}},
        },
        choices={"subclassChoice": "champion"},
    )
    assert applied["document"]["classes"][0]["level"] == 3
    assert _summons(applied["document"]).get("unlockedTemplates") == []

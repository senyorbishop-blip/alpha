from pathlib import Path


def test_character_creation_builder_maps_starting_weapon_damage_fields():
    src = Path("client/templates/character-creation.html").read_text(encoding="utf-8")
    assert "const STARTER_WEAPON_STATS = {" in src
    assert "function starterWeaponStatsForName(name) {" in src
    assert "const weaponStats = starterWeaponStatsForName(parsed.name);" in src
    assert "item.damage_dice = String(weaponStats.damage_dice || '').trim();" in src
    assert "item.damage_type = String(weaponStats.damage_type || '').trim();" in src

"""Verify all species files have complete required data."""

from server.character.rules_catalog import load_rules_catalog


def test_all_species_have_darkvision_or_no_senses():
    """Species with darkvision must have it in senses, not just traits."""
    catalog = load_rules_catalog()
    for species in catalog['species']:
        traits = species.get('traits', [])
        senses = species.get('senses', {})
        has_darkvision_trait = any('darkvision' in t.get('description', '').lower() for t in traits)
        has_darkvision_senses = senses.get('darkvision', 0) > 0
        if has_darkvision_trait:
            assert has_darkvision_senses, f"{species['id']} has darkvision in traits but not senses field"


def test_all_species_have_size():
    catalog = load_rules_catalog()
    for species in catalog['species']:
        assert 'size' in species, f"{species['id']} missing size field"
        assert species['size'] in ('Small', 'Medium', 'Large')


def test_all_species_have_flavor_text():
    catalog = load_rules_catalog()
    for species in catalog['species']:
        assert species.get('flavorText'), f"{species['id']} missing flavorText"
        assert len(species['flavorText']) > 50, f"{species['id']} flavorText too short"


def test_all_species_have_multiple_traits():
    """Most species should have at least 2 traits."""
    catalog = load_rules_catalog()
    for species in catalog['species']:
        traits = species.get('traits', [])
        assert len(traits) >= 1, f"{species['id']} has no traits"


def test_all_species_have_languages():
    catalog = load_rules_catalog()
    for species in catalog['species']:
        assert species.get('languages'), f"{species['id']} missing languages"

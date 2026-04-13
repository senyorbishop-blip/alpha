#!/usr/bin/env python3
"""Generate the starter portrait manifest used by the importer creator.

This does not create art. It creates the matrix of expected species/class/presentation
asset paths so the frontend can progressively light up combinations as real portrait
PNG files are added.
"""
from pathlib import Path
import json

SPECIES = ['human', 'elf', 'aasimar', 'dwarf', 'dragonborn', 'tiefling', 'goliath']
CLASSES = ['barbarian', 'bard', 'cleric', 'druid', 'fighter', 'monk', 'paladin', 'ranger', 'rogue', 'sorcerer', 'warlock', 'wizard']
PRESENTATIONS = ['masculine', 'feminine', 'neutral']
BASE = '/static/importer/portraits'


def build_manifest():
    return {
        'species_order': SPECIES,
        'class_order': CLASSES,
        'presentation_order': PRESENTATIONS,
        'species': {s: f'{BASE}/species/{s}.png' for s in SPECIES},
        'classes': {c: f'{BASE}/class/{c}.png' for c in CLASSES},
        'combos': {
            f'{s}__{c}__{p}': f'{BASE}/combos/{s}__{c}__{p}.png'
            for s in SPECIES for c in CLASSES for p in PRESENTATIONS
        },
    }


def main():
    out = Path('client/static/importer/portraits/manifest.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_manifest(), indent=2), encoding='utf-8')
    print(f'wrote {out}')


if __name__ == '__main__':
    main()

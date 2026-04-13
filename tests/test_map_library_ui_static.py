from pathlib import Path


def test_cartographer_ui_exposes_stage4_map_library_filters_and_labels():
    cartographer_js = Path(__file__).parent.parent / 'client' / 'static' / 'js' / 'cartographer.js'
    content = cartographer_js.read_text(encoding='utf-8')

    for needle in (
        'id="carto-build"',
        'id="carto-interior"',
        'id="carto-scale-label"',
        'id="carto-source-focus"',
        'id="cart-library-pack"',
        'id="cart-library-creator"',
        'id="cart-library-license"',
        'id="cart-library-asset-type"',
        'id="cart-library-origin"',
        'Premium Import',
        'Open / Free',
        'Quick Start:',
        'Using this map will apply it to the current scene context.',
    ):
        assert needle in content, f"Expected Stage 4 map-library UI marker missing: {needle}"

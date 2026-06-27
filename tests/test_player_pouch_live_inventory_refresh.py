"""Regression guard: looted/granted items must appear live in the map-first
player "Pouch" surface, not only in the legacy #inventory-list.

Players in the map-first UI see their carried gear through the player dashboard
shell ("Pouch > Items / Gold"), which is rendered by _renderPlayerMode →
_rpItemsList(). That surface reads the `playerInventory` array but is only
re-rendered when the player switches modes/tabs. The authoritative
`player_inventory_sync` handler (applyPlayerInventoryState) previously refreshed
only the legacy inventory panel, so chest loot / DM grants silently failed to
show in the Pouch until a manual tab switch. These assertions lock in the live
refresh.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _slice_function(src: str, signature: str) -> str:
    start = src.index(signature)
    depth = 0
    started = False
    for i in range(start, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                return src[start : i + 1]
    raise AssertionError(f"could not slice function for {signature!r}")


def test_inventory_sync_refreshes_player_pouch_surface():
    play = read("client/templates/play.html")

    # The Pouch surface the player actually looks at is rendered from playerInventory.
    assert "function _rpItemsList()" in play
    assert "function _rpRerender()" in play
    assert "window._rpRerender = _rpRerender;" in play

    body = _slice_function(play, "function applyPlayerInventoryState(")
    # The authoritative sync must re-render the live player dashboard (Pouch),
    # not just the legacy #inventory-list, when the viewer is a player.
    assert "renderInventoryPanel();" in body
    assert "_rpRerender" in body, (
        "applyPlayerInventoryState must refresh the map-first player Pouch surface "
        "so looted/granted items show live"
    )
    assert "ROLE === 'player'" in body


def test_optimistic_loot_paths_also_refresh_pouch_and_guard_empty_ids():
    play = read("client/templates/play.html")

    # Both optimistic loot paths refresh the Pouch in place.
    assert play.count("if (ROLE === 'player' && typeof _rpRerender === 'function') _rpRerender();") >= 1
    assert "if (ROLE === 'player' && typeof _rpRerender === 'function') _rpRerender();" in play

    # Inline onclick handlers resolve globals through window in some browsers,
    # so generated resource/economy controls must not call an unqualified
    # _rpRerender symbol.
    assert ";_rpRerender()" not in play
    assert "typeof window._rpRerender==='function'&&window._rpRerender()" in play

    # Empty/missing ids must not be matched as "existing" (would overwrite an
    # unrelated id-less item). Loot merge only matches by id when one is present.
    assert "item.id ? playerInventory.findIndex(it => it.id === item.id) : -1" in play

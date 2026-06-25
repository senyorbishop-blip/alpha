"""Character profile image-bloat regression tests."""

from __future__ import annotations

import base64
import copy
import json
from types import SimpleNamespace

from server.character import profile_assets
from server.character.profile_assets import char_profiles_bloat_diagnostics_from_serialized, json_size
from server.character.profile_sanitize import clean_oversized_profile
from server.handlers.content import upsert_char_profile_for_owner


def _data_image(size: int, *, mime: str = "image/png") -> str:
    raw = b"PNGTEST" + (b"x" * max(0, size - 7))
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def test_profile_save_relocates_large_inline_portrait_and_shrinks_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_assets, "USER_UPLOADS_DIR", tmp_path)
    large_portrait = _data_image(1024 * 1024)
    session = SimpleNamespace(char_profiles={})
    payload = {
        "id": "pdf-bishop",
        "name": "Bishop",
        "charSheet": {
            "portraitUrl": large_portrait,
            "abilities": {"str": 16, "dex": 14, "con": 13},
            "inventory": [{"name": "Quarterstaff", "qty": 1}],
            "spells": {"known": ["thunderwave"], "prepared": ["lightning-bolt"]},
        },
        "nativeRuntime": {"avatarUrl": large_portrait},
    }

    saved = upsert_char_profile_for_owner(session, "bishop", payload)

    portrait_url = saved["charSheet"]["portraitUrl"]
    runtime_url = saved["nativeRuntime"]["avatarUrl"]
    assert portrait_url.startswith("/static/user_uploads/char_profile_")
    assert runtime_url.startswith("/static/user_uploads/char_profile_")
    assert (tmp_path / portrait_url.rsplit("/", 1)[1]).exists()
    assert (tmp_path / runtime_url.rsplit("/", 1)[1]).exists()
    assert json_size(saved) < 100 * 1024


def test_real_character_fields_survive_image_relocation_byte_identical(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_assets, "USER_UPLOADS_DIR", tmp_path)
    real_fields = {
        "abilities": {"str": 16, "dex": 14, "con": 13, "int": 10, "wis": 12, "cha": 8},
        "inventory": [{"name": "Dagger", "qty": 2, "equipped": True}],
        "spells": {"known": ["mage-hand"], "prepared": ["shield", "thunderwave"]},
        "classFeatures": [{"id": "action-surge", "uses": 1}],
        "hp": {"current": 31, "max": 38, "temp": 0},
        "conditions": ["blessed"],
    }
    before = copy.deepcopy(real_fields)
    session = SimpleNamespace(char_profiles={})
    payload = {
        "id": "pdf-bishop",
        "name": "Bishop",
        "charSheet": {**copy.deepcopy(real_fields), "tokenImageUrl": _data_image(256 * 1024)},
    }

    saved = upsert_char_profile_for_owner(session, "bishop", payload)

    after = {key: saved["charSheet"][key] for key in before.keys()}
    assert json.dumps(after, sort_keys=True, separators=(",", ":")) == json.dumps(before, sort_keys=True, separators=(",", ":"))


def test_small_inline_icons_remain_inline(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_assets, "USER_UPLOADS_DIR", tmp_path)
    small_icon = _data_image(128)
    session = SimpleNamespace(char_profiles={})

    saved = upsert_char_profile_for_owner(session, "bishop", {
        "id": "small-icon-profile",
        "name": "Icon Keeper",
        "charSheet": {"smallIcon": small_icon, "abilities": {"str": 10}},
    })

    assert saved["charSheet"]["smallIcon"] == small_icon
    assert list(tmp_path.iterdir()) == []


def test_clean_oversized_profile_relocates_stored_data_image_on_restore(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_assets, "USER_UPLOADS_DIR", tmp_path)
    large_portrait = _data_image(512 * 1024)
    stored = {
        "id": "pdf-bishop",
        "name": "Bishop",
        "charSheet": {"portraitUrl": large_portrait, "abilities": {"str": 16}},
    }

    clean_oversized_profile(stored)

    url = stored["charSheet"]["portraitUrl"]
    assert url.startswith("/static/user_uploads/char_profile_")
    assert (tmp_path / url.rsplit("/", 1)[1]).exists()
    assert stored["charSheet"]["abilities"] == {"str": 16}


def test_large_profile_diagnostics_report_subkeys_and_data_url_paths():
    huge_image = _data_image(32 * 1024)
    profiles = {
        "bishop": [{
            "id": "pdf-bishop",
            "charSheet": {"portraitUrl": huge_image, "abilities": {"str": 16}, "inventory": [{"name": "Staff"}]},
            "nativeRuntime": {"avatarUrl": huge_image, "cache": {"x": 1}},
        }]
    }
    serialized = json.dumps(profiles, separators=(",", ":"), ensure_ascii=False)

    detail = char_profiles_bloat_diagnostics_from_serialized(serialized)

    assert "largest_profile=bishop/pdf-bishop" in detail
    assert "charSheet_subkeys[" in detail
    assert "nativeRuntime_subkeys[" in detail
    assert "data_urls[" in detail
    assert "charSheet.portraitUrl" in detail
    assert "nativeRuntime.avatarUrl" in detail


def test_db_large_field_breakdown_gets_profile_bloat_diagnostics():
    import server.db as db

    profile_assets.install_db_large_field_diagnostics()
    huge_image = _data_image(32 * 1024)
    profiles = {"bishop": [{"id": "pdf-bishop", "charSheet": {"portraitUrl": huge_image}, "nativeRuntime": {"avatarUrl": huge_image}}]}
    serialized = json.dumps(profiles, separators=(",", ":"), ensure_ascii=False)

    detail = db._char_profiles_size_breakdown(serialized)

    assert "largest_profile=bishop/pdf-bishop" in detail
    assert "charSheet_subkeys[" in detail
    assert "nativeRuntime_subkeys[" in detail
    assert "data_urls[" in detail

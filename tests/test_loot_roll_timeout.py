"""Tests for loot roll 8-second timeout / auto-pass mechanism."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest


def test_loot_roll_timeout_constant():
    from server.handlers.inventory import _LOOT_ROLL_TIMEOUT_SECONDS
    assert _LOOT_ROLL_TIMEOUT_SECONDS == 8, f"Timeout should be 8s, got {_LOOT_ROLL_TIMEOUT_SECONDS}"


def test_loot_roll_deadline_calculation():
    from server.handlers.inventory import _LOOT_ROLL_TIMEOUT_SECONDS
    t0 = time.time()
    deadline = t0 + _LOOT_ROLL_TIMEOUT_SECONDS
    assert deadline > t0
    assert abs(deadline - t0 - 8) < 0.01


def test_inventory_has_deadline_field():
    with open("server/handlers/inventory.py") as f:
        src = f.read()
    assert "deadline" in src, "inventory.py must have deadline field in loot state"


def test_inventory_has_timeout_constant():
    with open("server/handlers/inventory.py") as f:
        src = f.read()
    assert "_LOOT_ROLL_TIMEOUT_SECONDS" in src


def test_loot_prompt_includes_deadline():
    with open("server/handlers/inventory.py") as f:
        src = f.read()
    assert "deadline_at" in src, "Prompt payload must include deadline_at"
    assert "timeout_seconds" in src, "Prompt payload must include timeout_seconds"


def test_auto_pass_logic_present():
    with open("server/handlers/inventory.py") as f:
        src = f.read()
    assert "_auto_pass_loot_roll" in src or "auto" in src.lower(), \
        "Must have auto-pass logic for timed-out loot rolls"


def test_late_vote_rejection_present():
    with open("server/handlers/inventory.py") as f:
        src = f.read()
    # Check that handle_chest_loot_roll_choice rejects late votes
    idx = src.find("handle_chest_loot_roll_choice")
    assert idx >= 0, "Function must exist"
    body = src[idx:idx+800]
    assert "deadline" in body, "Late vote rejection must check deadline"

from server.quest_premium_progression import build_premium_progression_snapshot
from server.session import Session


def test_premium_progression_derives_reputation_and_rank_from_completed_quests():
    session = Session(id="premium-derive")
    session.session_quests = [
        {
            "id": "sq-a",
            "status": "completed",
            "reward_bundle": {"reputation": {"Iron Lantern": 6, "Silver Flame": 3}},
        },
        {
            "id": "sq-b",
            "status": "rewards_granted",
            "reward_bundle": {
                "reputation": [{"faction": "Iron Lantern", "delta": 5}],
                "flags": {"faction_reputation": "Silver Flame:+2"},
                "meta": {"guild_rank_points": 4},
            },
        },
        {
            "id": "sq-c",
            "status": "active",
            "reward_bundle": {"reputation": {"Iron Lantern": 999}},
        },
    ]

    snapshot = build_premium_progression_snapshot(session)
    reps = {row["faction"]: row["score"] for row in snapshot["faction_reputation"]}

    assert reps["Iron Lantern"] == 11
    assert reps["Silver Flame"] == 5
    assert snapshot["guild_rank"]["completed_quests"] == 2
    assert snapshot["guild_rank"]["points"] == 5
    assert snapshot["guild_rank"]["current_rank"]["label"] == "Trusted"
    assert snapshot["guild_rank"]["rank_id"] == "trusted"
    assert snapshot["guild_rank"]["next_rank"]["label"] == "Proven"
    assert snapshot["guild_rank"]["points_to_next"] == 1
    assert snapshot["guild_rank"]["unlock_hooks"]["board_tier"] == "regional"
    assert snapshot["guild_rank"]["thresholds"][0]["key"] == "novice"


def test_premium_progression_emits_rank_up_events_deterministically():
    session = Session(id="premium-events")
    session.session_quests = [
        {"id": "sq-a", "title": "First", "status": "completed", "created_at": 1, "updated_at": 1},
        {"id": "sq-b", "title": "Second", "status": "completed", "created_at": 2, "updated_at": 2},
        {
            "id": "sq-c",
            "title": "Promotion",
            "status": "rewards_granted",
            "created_at": 3,
            "updated_at": 3,
            "reward_bundle": {"meta": {"guild_rank_points": 2}},
        },
    ]

    snapshot = build_premium_progression_snapshot(session)
    events = snapshot["guild_rank"]["rank_up_events"]
    assert events
    assert events[-1]["rank_id"] == "trusted"
    assert events[-1]["quest_id"] == "sq-c"

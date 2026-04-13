from server.quest_progression import resolve_session_quest_progression
from server.quest_premium_progression import build_premium_progression_snapshot
from server.session import Session


def test_quest_chain_unlocks_follow_up_when_prereq_completes():
    session = Session(id="quest-chain")
    session.session_quests = [
        {
            "id": "sq-a",
            "title": "Quest A",
            "status": "completed",
            "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
            "unlocks_quest_ids": ["sq-b"],
        },
        {
            "id": "sq-b",
            "title": "Quest B",
            "status": "available",
            "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
            "prerequisite_quest_ids": ["sq-a"],
        },
    ]

    resolved = resolve_session_quest_progression(session)
    q2 = next(q for q in resolved if q["id"] == "sq-b")
    assert q2["availability_state"] == "unlocked"
    assert q2["visibility"]["mode"] == "party_public"


def test_hidden_until_unlocked_keeps_quest_hidden_for_players():
    session = Session(id="quest-hidden-chain")
    session.session_quests = [
        {
            "id": "sq-a",
            "title": "Quest A",
            "status": "active",
            "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        },
        {
            "id": "sq-secret",
            "title": "Secret Follow-up",
            "status": "available",
            "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
            "prerequisite_quest_ids": ["sq-a"],
            "hidden_until_unlocked": True,
        },
    ]
    session.session_quests = resolve_session_quest_progression(session)
    player_view = session.to_state_dict_for_role("player", "p1")["session_quests"]
    assert all(q["id"] != "sq-secret" for q in player_view)


def test_locked_quests_are_listed_but_redacted_for_players():
    session = Session(id="quest-locked")
    session.session_quests = [
        {
            "id": "sq-locked",
            "title": "Locked Board Contract",
            "status": "available",
            "description": "Hidden spoiler detail",
            "objective_list": [{"id": "obj-1", "title": "Secret", "status": "pending"}],
            "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
            "required_faction_tags": ["mages_guild"],
            "lock_visibility": "listed",
        }
    ]
    session.session_quests = resolve_session_quest_progression(session)
    player_view = session.to_state_dict_for_role("player", "p1")["session_quests"]
    assert len(player_view) == 1
    locked = player_view[0]
    assert locked["availability_state"] == "locked"
    assert locked["description"] == ""
    assert locked["objective_list"] == []


def test_required_guild_rank_blocks_until_threshold_met():
    session = Session(id="quest-rank-lock")
    session.session_quests = [
        {
            "id": "sq-complete",
            "title": "Starter",
            "status": "completed",
            "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        },
        {
            "id": "sq-elite",
            "title": "Elite Contract",
            "status": "available",
            "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
            "required_guild_rank_id": "trusted",
            "required_guild_rank_points": 3,
            "lock_visibility": "listed",
        },
    ]
    session.session_quests = resolve_session_quest_progression(session)
    locked = next(q for q in session.session_quests if q["id"] == "sq-elite")
    assert locked["availability_state"] == "locked"
    blockers = (locked.get("meta") or {}).get("unlock_blockers") or {}
    assert blockers.get("required_guild_rank_id") == "trusted"
    assert blockers.get("required_guild_rank_points") == 3

    session.session_quests[0]["status"] = "rewards_granted"
    session.session_quests.append({
        "id": "sq-boost",
        "title": "Boost",
        "status": "completed",
        "reward_bundle": {"meta": {"guild_rank_points": 2}},
        "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
    })
    session.session_quests = resolve_session_quest_progression(session)
    unlocked = next(q for q in session.session_quests if q["id"] == "sq-elite")
    assert unlocked["availability_state"] == "unlocked"


def test_completed_board_quest_refreshes_rank_and_unlocks_follow_up_listing():
    session = Session(id="quest-board-loop")
    session.session_quests = [
        {
            "id": "sq-contract-1",
            "title": "Town Contract",
            "status": "completed",
            "reward_bundle": {"meta": {"guild_rank_points": 3}},
            "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
            "unlocks_quest_ids": ["sq-contract-2"],
        },
        {
            "id": "sq-contract-2",
            "title": "Regional Contract",
            "status": "available",
            "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
            "lock_visibility": "listed",
            "prerequisite_quest_ids": ["sq-contract-1"],
        },
    ]
    session.session_quests = resolve_session_quest_progression(session)
    follow_up = next(q for q in session.session_quests if q["id"] == "sq-contract-2")
    assert follow_up["availability_state"] == "unlocked"
    assert follow_up["visibility"]["mode"] == "party_public"

    progression = build_premium_progression_snapshot(session)
    assert progression["guild_rank"]["rank_id"] == "trusted"
    assert progression["guild_rank"]["points"] == 3

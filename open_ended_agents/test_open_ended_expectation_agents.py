#!/usr/bin/env python3
import argparse
import tempfile
import threading
import zlib
from pathlib import Path

from ohol_open_ended_expectation_agents import (
    AgentSession,
    MapChunk,
    PrivateMind,
    ProtocolReader,
    grid_path,
    parse_food_change,
    parse_map_changes,
    parse_player_speech,
    parse_player_updates,
)


def pu_line(player_id: int, held: int, x: int, y: int) -> str:
    return (
        f"{player_id} 1 0 0 0 0 {held} 0 0 0 0 0 1 0 "
        f"{x} {y} 20 60 0 0;0;0;0;0;0 0 0 -1 0 1"
    )


def args(memory_dir: str) -> argparse.Namespace:
    return argparse.Namespace(
        memory_dir=memory_dir, language_radius=8.0, action_interval=0.0,
        search_radius=12, max_path_steps=8, teach_interval=12.0,
        curiosity_weight=1.0, novelty_weight=0.65,
        falsification_weight=0.8, social_weight=0.55, choice_noise=0.0,
        social_exploration_weight=0.45, social_radius=8.0,
        social_search_radius=24.0, no_progress_timeout=5.0,
        move_timeout=14.0, blocked_cooldown=30.0,
        dropped_object_cooldown=90.0,
        repetition_penalty=0.12, first_self_test_bonus=3.0,
        request_hunger=0.55, request_interval=20.0,
        request_ttl=45.0, cache_max_hunger=0.40,
        startup_group_wait=0.0, movement_drive_step=0.75,
        max_movement_drive=4.5, ordinary_speech_score=1.25,
        conversation_score=6.0, conversation_interval=8.0,
        speech_wait_log_interval=10.0,
        force_move_after=3, force_move_score=11.0,
    )


def main() -> None:
    updates = parse_player_updates(
        "PU\n" + pu_line(10, 34, 0, 0) + "\n" + pu_line(11, 0, 2, 1)
    )
    assert [(p.player_id, p.held_object, p.x, p.y) for p in updates] == [
        (10, 34, 0, 0), (11, 0, 2, 1)
    ]
    assert parse_player_speech("PS\n10/0 HFU\n11 BAK") == [(10, "HFU"), (11, "BAK")]
    assert parse_food_change("FX\n4 12 19 8 1.0 -1 0 0") == (4, 12)

    reader = ProtocolReader()
    assert reader.feed(b"PS\n10 HFU#") == ["PS\n10 HFU"]
    raw_map = b"1:0:0 1:0:34 1:0:0 1:0:0"
    compressed = zlib.compress(raw_map)
    header = f"MC\n2 2 -1 -1\n{len(raw_map)} {len(compressed)}#".encode()
    assert reader.feed(header) == []
    assert reader.feed(compressed) == [MapChunk(2, 2, -1, -1, [0, 34, 0, 0])]
    assert parse_map_changes("MX\n2 3 0 99 -1") == [(2, 3, 99)]
    world = {(0, 0): 0, (1, 0): 0, (2, 0): 0, (2, 1): 0}
    assert grid_path((0, 0), {(2, 1)}, world) == [
        (0, 0), (1, 0), (2, 0), (2, 1)
    ]

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "agent_2.json"
        mind = PrivateMind(2, path)

        # Language remains fallible and private.
        for _ in range(3):
            word = mind.hear_demonstration("HFU", 34, 10)
        assert word.status == "corroborated"
        assert mind.word_for_object(34) == ("HFU", False)
        for _ in range(6):
            mind.hear_demonstration("HFU", 99, 12)
        assert mind.hypotheses["HFU"][34].status == "falsified"

        mind.hear_food_testimony("BAK", 35, 11)
        assert mind.testimony_food_value(35) > 0
        assert "held:35|target:-1|action:SELF" not in mind.transitions

        # Learn an initially unknown two-step food chain:
        # empty + USE 34 -> hold 35; hold 35 + SELF -> food increases.
        for _ in range(3):
            mind.observe_action_result("USE", 34, 0, 35, 34, 34, 5, 5)
            mind.observe_action_result("SELF", -1, 35, 0, -1, -1, 5, 9)
        chain = mind.learned_chain_first_step(0)
        assert chain == ("USE", 34, 2), chain
        assert mind.best_food_action(35) == ("SELF", -1)
        assert mind.known_food_objects() == {35}

        # Repeated non-results lose uncertainty and become provisionally refuted.
        for _ in range(7):
            mind.observe_action_result("USE", 99, 0, 0, 99, 99, 5, 5)
        trials, value, uncertainty, status = mind.action_knowledge(0, 99, "USE")
        assert trials == 7 and value < 0 and uncertainty < 0.4
        assert status == "provisionally_refuted"

        # Proximity is learned from outcomes rather than imposed.
        for _ in range(4):
            mind.reinforce_social_context([11], 1.0)
        trials, value, uncertainty = mind.social_knowledge([11])
        assert trials >= 8 and value > 0 and uncertainty < 0.5

        # Candidate generation has generic USE, frontier MOVE, and learned scoring.
        session = AgentSession(
            2, args(directory), ("x@y", "ABC", "x"), threading.Event()
        )
        session.our_id = 10
        session.players = {10: updates[0], 11: updates[1]}
        session.world = {
            (-1, 0): 0, (0, 0): 0, (1, 0): 34,
            (0, 1): 0, (0, -1): 0,
        }
        session.mind = mind

        # A destination claimed by another runner is unavailable until its
        # short reservation expires.
        AgentSession.destination_reservations[(0, 1)] = (1, 200.0)
        assert not session.destination_available((0, 1), 100.0)
        assert session.destination_available((0, 1), 201.0)

        proposals = session.propose_actions(updates[0], 100.0)
        assert any(p.kind == "USE" and p.target_id == 34 for p in proposals)

        # Holding an object creates a durable teaching intention even when the
        # peer is outside speech range.  That intention then makes approaching
        # the peer competitive; M15 incorrectly required proximity before it
        # would create the utterance at all.
        session.players[11] = parse_player_updates(
            "PU\n" + pu_line(11, 0, 10, 0)
        )[0]
        session.world.update({(x, 0): 0 for x in range(1, 11)})
        session.pending_utterances.clear()
        session.last_spoken.clear()
        proposals = session.propose_actions(session.players[10], 100.1)
        held_token, _ = session.mind.word_for_object(34)
        assert held_token in session.pending_utterances
        assert not any(p.kind == "SAY" for p in proposals)
        assert any(
            p.kind == "APPROACH" and p.target_id == 11 for p in proposals
        )

        # Once the listener is reached, the queued name becomes an audible
        # conversation action.
        session.players[11] = parse_player_updates(
            "PU\n" + pu_line(11, 0, 2, 0)
        )[0]
        proposals = session.propose_actions(session.players[10], 100.2)
        assert any(
            p.kind == "SAY" and p.utterance == held_token and p.score == 6.0
            for p in proposals
        )
        session.pending_utterances.appendleft("HOME HERE")
        assert any(p.kind == "MOVE" for p in proposals)
        self_test = next(p for p in proposals if p.kind == "SELF")
        assert self_test.score >= 3.0

        # An unchanged, ineffective held item gets only one SELF attempt.
        mind.observe_action_result("SELF", -1, 34, 34, -1, -1, 5, 5)
        proposals = session.propose_actions(updates[0], 100.01)
        assert not any(p.kind == "SELF" for p in proposals)

        # The lowest visible player proposes a common meeting place.
        assert session.home_location == (0, 0)
        assert "HOME HERE" in session.pending_utterances

        # Grounded requests produce an actual delivery plan, then a high-value
        # drop when the holder reaches the requester.
        session.peer_requests[11] = (34, 4, 0, 100.0)
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 34, 0, 0)
        )[0]
        session.world.update({
            (1, 0): 0, (2, 0): 0, (3, 0): 0, (4, 0): 0
        })
        proposals = session.propose_actions(session.players[10], 100.1)
        assert any(p.kind == "DELIVER" for p in proposals)
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 34, 3, 0)
        )[0]
        proposals = session.propose_actions(session.players[10], 100.2)
        assert next(p for p in proposals if p.kind == "DROP").score >= 7.0

        # Agents sharing a spawn deliberately separate instead of all
        # competing for the same object.
        session.players[11] = parse_player_updates(
            "PU\n" + pu_line(11, 0, 0, 0)
        )[0]
        proposals = session.propose_actions(updates[0], 100.5)
        assert any(p.kind == "DISPERSE" for p in proposals)

        # Ordinary teaching receives a bounded conversation turn, while
        # NEED/HAVE coordination retains immediate priority.
        session.pending_utterances.clear()
        session.pending_utterances.append("FAPA")
        proposals = session.propose_actions(updates[0], 100.6)
        ordinary = next(
            p for p in proposals if p.kind == "SAY" and p.utterance == "FAPA"
        )
        assert ordinary.score == 6.0
        session.pending_utterances.clear()
        session.pending_utterances.append("NEED FAPA")
        proposals = session.propose_actions(updates[0], 100.7)
        urgent = next(
            p for p in proposals
            if p.kind == "SAY" and p.utterance == "NEED FAPA"
        )
        assert urgent.score == 10.0

        # Ordinary grounded teaching must beat routine USE scores when a
        # listener is present, then yield to other actions during cooldown.
        session.pending_utterances.clear()
        session.pending_utterances.append("HFU")
        session.last_conversation_at = -float("inf")
        proposals = session.propose_actions(updates[0], 100.71)
        teaching = next(
            p for p in proposals
            if p.kind == "SAY" and p.utterance == "HFU"
        )
        assert teaching.score == 6.0
        session.last_conversation_at = 100.71
        proposals = session.propose_actions(updates[0], 101.0)
        assert not any(
            p.kind == "SAY" and p.utterance == "HFU" for p in proposals
        )
        proposals = session.propose_actions(updates[0], 109.0)
        assert any(
            p.kind == "SAY" and p.utterance == "HFU" for p in proposals
        )

        # Recently spoken utterances are removed from a stale queue, but become
        # teachable again after the cooldown instead of being life-long silent.
        session.last_spoken["HFU"] = 100.75
        session.pending_utterances.append("HFU")
        session.propose_actions(updates[0], 100.8)
        assert "HFU" not in session.pending_utterances
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 34, 0, 0)
        )[0]
        proposals = session.propose_actions(session.players[10], 113.0)
        assert any(
            p.kind == "SAY" and p.utterance == "HFU" for p in proposals
        )

        # Stationary actions progressively make exploration competitive.
        session.stationary_action_streak = 6
        proposals = session.propose_actions(updates[0], 100.9)
        moving = next(p for p in proposals if p.kind == "MOVE")
        assert "movement_drive=4.50" in moving.reason
        forced = next(
            p for p in proposals
            if p.kind in {"ROAM", "WANDER"} and p.score == 11.0
        )
        assert "forced" in forced.reason

        # A completed SELF trial must be stored under the same semantic
        # target (-1) used by action selection, so it cannot receive the
        # one-time first-test bonus forever.
        mind.observe_action_result(
            "SELF", -1, 99, 99, -1, -1, 5, 5
        )
        trials, _, _, _ = mind.action_knowledge(99, -1, "SELF")
        assert trials == 1

        # A personally tested, non-beneficial held item should be released.
        for _ in range(2):
            mind.observe_action_result("SELF", -1, 99, 99, -1, -1, 5, 5)
        ineffective_holder = pu_line(10, 99, 0, 0)
        session.players[10] = parse_player_updates("PU\n" + ineffective_holder)[0]
        proposals = session.propose_actions(session.players[10], 101.0)
        drop = next(p for p in proposals if p.kind == "DROP")
        assert "release=2.25" in drop.reason
        assert not any(p.kind == "SELF" for p in proposals)

        # An unsent discovery makes reaching a listener the dominant social act.
        session.pending_utterances.append("HFU FOOD")
        session.players[11] = parse_player_updates(
            "PU\n" + pu_line(11, 0, 4, 0)
        )[0]
        session.world.update({
            (1, 0): 0, (2, 0): 0, (3, 0): 0, (4, 0): 0
        })
        proposals = session.propose_actions(session.players[10], 102.0)
        approach = next(p for p in proposals if p.kind == "APPROACH")
        assert approach.score >= 5.0

        # With no interactions or frontier left, the agent still roams.
        session.pending_utterances.clear()
        session.players = {10: parse_player_updates(
            "PU\n" + pu_line(10, 0, 0, 0)
        )[0]}
        session.world = {
            (x, y): (-1 if abs(x) == 2 or abs(y) == 2 else 0)
            for x in range(-2, 3) for y in range(-2, 3)
        }
        session.position_history.extend([(0, 0), (1, 0)])
        proposals = session.propose_actions(session.players[10], 103.0)
        assert any(p.kind == "ROAM" for p in proposals)

        # Even a one-cell initial map has a liveness action.
        session.world = {(0, 0): 0}
        proposals = session.propose_actions(session.players[10], 104.0)
        assert any(p.kind == "WANDER" for p in proposals)

        reloaded = PrivateMind(2, path)
        assert reloaded.transitions
        assert reloaded.learned_chain_first_step(0) == ("USE", 34, 2)

        session.begin_new_life()
        first_path = session.mind.path
        session.mind.hear_food_testimony("BAK", 35, 11)
        session.begin_new_life()
        assert session.mind.path != first_path
        assert not session.mind.transitions
        assert not session.mind.food_testimony

    print("All open-ended expectation-agent tests passed.")


if __name__ == "__main__":
    main()

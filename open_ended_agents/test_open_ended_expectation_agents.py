#!/usr/bin/env python3
import argparse
import tempfile
import threading
import zlib
from pathlib import Path

from hint_oracle import HintOracle

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
    life_stage,
    configure_id_shuffle,
    shuffled_id,
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
        verify_weight=1.5, cache_seek_weight=6.0,
        instrumental_weight=1.2, stuck_timeout=40.0,
        comfort_weight=0.8, home_patience=90.0,
        staple_weight=0.9, commitment_bonus=1.0, commitment_ttl=20.0,
        status_interval=30.0,
        decay_halflife=480.0, rehearse_interval=45.0, lead_weight=3.5,
        ask_interval=25.0, mode_dwell=20.0, threat_threshold=0.5,
        feed_hunger=0.55, urgency_dwell=8.0,
        event_log_dir=None, data_dir=None, prior_weight=2.0,
        generalization_weight=2.0, location_weight=1.5, care_weight=5.0,
        future_discount=0.6, planning_weight=0.8, dependant_weight=0.6,
        information_weight=0.4, effort_weight=0.5, risk_weight=1.5,
        switching_cost=0.25, duplication_penalty=0.4, follow_weight=3.0,
        no_communication=False, no_observation=False, no_properties=False,
        no_priors=False, id_shuffle_seed=0,
        goal_weight=4.0,
        hints="off", goal_commit_ttl=25.0,
        goal_retry_interval=90.0,
    )


def main() -> None:
    # Human-equivalent names preserve the complete hover label, and hints
    # include self-use plus both transition outputs.
    with tempfile.TemporaryDirectory() as data_directory:
        data = Path(data_directory)
        (data / "objects").mkdir()
        (data / "transitions").mkdir()
        for object_id, label in {
            34: "Sharp Stone", 35: "Stone Chips", 36: "Cut Plant",
        }.items():
            (data / "objects" / f"{object_id}.txt").write_text(
                f"id={object_id}\n{label}#variant\n", encoding="utf-8"
            )
        (data / "transitions" / "34_-1.txt").write_text(
            "35 36\n", encoding="utf-8"
        )
        oracle = HintOracle(data, "full")
        assert oracle.word_from_description(34) == "SHARP_STONE"
        assert oracle.hints_for(34) == [(34, -1, 35, 36)]

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

        # Testimony is trust-calibrated: an unknown speaker starts at the
        # neutral prior, and value is claim evidence times source trust.
        assert mind.trust_in(11) == 0.5
        assert mind.testimony_food_value(35) == (
            mind.testimony_claim_posterior(35) * 0.5
        )

        # A failed personal verification debits both the claim and every
        # affirming source; a successful one credits them.
        value_before = mind.testimony_food_value(35)
        mind.record_testimony_outcome(35, False)
        assert mind.trust_in(11) < 0.5
        assert int(mind.food_testimony[35]["contradictions"]) == 1
        assert mind.testimony_food_value(35) < value_before
        mind.record_testimony_outcome(35, True)
        mind.record_testimony_outcome(35, True)
        assert mind.trust_in(11) > 0.5

        # A heard "<TOKEN> BAD" correction weakens the claim as fallible
        # testimony without touching the listener's own trial history.
        contradictions_before = int(mind.food_testimony[35]["contradictions"])
        mind.hear_food_contradiction("BAK", 35, 12)
        assert int(mind.food_testimony[35]["contradictions"]) == (
            contradictions_before + 1
        )
        assert 12 in mind.food_testimony[35].get("deniers", [])
        assert 12 not in mind.food_testimony[35]["sources"]

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

        # Hovering learns the shared in-game name, while recipe access is an
        # explicit inspect/click action and is not injected passively.
        live_data = Path(directory) / "data"
        (live_data / "objects").mkdir(parents=True)
        (live_data / "transitions").mkdir()
        for object_id, label in {
            34: "Sharp Stone", 35: "Stone Chips", 36: "Cut Plant",
        }.items():
            (live_data / "objects" / f"{object_id}.txt").write_text(
                f"id={object_id}\n{label}\n", encoding="utf-8"
            )
        (live_data / "transitions" / "34_-1.txt").write_text(
            "35 36\n", encoding="utf-8"
        )
        session.hints = HintOracle(live_data, "full")
        session.consulted_hints.clear()
        proposals = session.propose_actions(updates[0], 99.9)
        assert session.mind.hint_words[34] == "SHARP_STONE"
        assert any(p.kind == "INSPECT" and p.target_id == 34 for p in proposals)
        assert 34 not in session.consulted_hints
        assert session.inspect_object_hints(34) == 1
        assert 34 in session.consulted_hints
        assert session.mind.hint_words[35] == "STONE_CHIPS"
        assert session.mind.hint_words[36] == "CUT_PLANT"
        assert "34|-1" in session.mind.rule_testimony


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

        # A personally unverified food claim from an unproven source makes
        # independent falsification a visible part of the SELF score.
        mind.hear_food_testimony("ZAVI", 77, 44)
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 77, 0, 0)
        )[0]
        proposals = session.propose_actions(session.players[10], 101.5)
        verify_test = next(p for p in proposals if p.kind == "SELF")
        assert "verify=0.50" in verify_test.reason, verify_test.reason

        # A heard "<TOKEN> BAD" correction flows through speech handling and
        # weakens the community food claim as fallible testimony.
        session.players[11] = parse_player_updates(
            "PU\n" + pu_line(11, 35, 2, 0)
        )[0]
        contradictions_before = int(
            session.mind.food_testimony[35]["contradictions"]
        )
        session.handle_ps("PS\n11 BAK BAD")
        assert int(session.mind.food_testimony[35]["contradictions"]) == (
            contradictions_before + 1
        )

        # A hungry, empty-handed agent travels back to the adopted HOME cache.
        session.food_store, session.food_capacity = 3, 20
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 0, 4, 0)
        )[0]
        proposals = session.propose_actions(session.players[10], 102.5)
        seek = next(p for p in proposals if p.kind == "SEEK_CACHE")
        assert (seek.target_x, seek.target_y) == session.home_location
        assert seek.score > 4.0
        session.food_store, session.food_capacity = 18, 20
        proposals = session.propose_actions(session.players[10], 102.6)
        assert not any(p.kind == "SEEK_CACHE" for p in proposals)
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 34, 0, 0)
        )[0]
        session.food_store = None
        session.food_capacity = None

        # M18: reward propagates backward through the learned causal graph,
        # so the empty-hand crafting step toward food carries derived value.
        values = session.mind.instrumental_values()
        assert values.get(35, 0.0) > values.get(0, 0.0) > 0.0
        session.world[(0, 2)] = 34
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 0, 0, 0)
        )[0]
        proposals = session.propose_actions(session.players[10], 103.0)
        use_craft = next(
            p for p in proposals if p.kind == "USE" and p.target_id == 34
        )
        assert "instr=" in use_craft.reason
        assert "instr=0.00" not in use_craft.reason, use_craft.reason

        # A taught causal rule is grounded through the listener's own
        # vocabulary and stored as fallible, verifiable testimony.
        session.handle_ps("PS\n11 HAND ON ZAVI MAKES BAK")
        assert session.mind.rule_testimony["0|77"]["result"] == 35
        session.world[(2, 1)] = 77
        proposals = session.propose_actions(session.players[10], 103.1)
        rule_probe = next(
            p for p in proposals if p.kind == "USE" and p.target_id == 77
        )
        assert "rule_verify=" in rule_probe.reason
        assert "rule_verify=0.00" not in rule_probe.reason, rule_probe.reason

        # Testing a testified rule settles its sources' reputations.
        trust_before = session.mind.trust_in(11)
        session.mind.record_rule_outcome("0|77", False)
        assert session.mind.trust_in(11) < trust_before
        assert int(session.mind.rule_testimony["0|77"]["contradictions"]) == 1

        # A spontaneous world change away from all agents is recorded as an
        # ambient expectation.
        session.world[(9, 9)] = 500
        session.handle_mx("MX\n9 9 0 501 -1")
        assert "ambient:500|action:TIME" in session.mind.transitions

        # The stuck watchdog clears stale avoidance state and probes an
        # adjacent tile with a dominant score.
        session.last_position = (0, 0)
        session.last_position_change_at = 10.0
        session.motions_since_progress = 5
        session.blocked_until[(6, 6)] = 999.0
        proposals = session.propose_actions(session.players[10], 103.2)
        watchdog = next(p for p in proposals if p.kind == "PROBE")
        assert watchdog.score == 13.0
        assert not session.blocked_until
        session.last_position_change_at = 0.0
        session.motions_since_progress = 0

        # M19: hunger-drain intervals teach place quality.  Objects present
        # during slow drain earn comfort; fast-drain company loses it.
        for _ in range(2):
            session.mind.observe_comfort({34}, 21.0)
            session.mind.observe_comfort({99}, 8.0)
        assert session.mind.comfort_value(34) > 0.15
        assert session.mind.comfort_value(99) < 0.0

        # A well-fed agent moves toward its learned-comfort place.
        session.food_store, session.food_capacity = 18, 20
        session.world[(0, 2)] = 0
        session.world[(0, 3)] = 0
        session.world[(0, 4)] = 34
        proposals = session.propose_actions(session.players[10], 103.3)
        warmth = next(p for p in proposals if p.kind == "APPROACH_WARMTH")
        assert warmth.target_id == 0 and (warmth.target_x, warmth.target_y) == (0, 4)
        session.food_store = None
        session.food_capacity = None

        # A fulfilled NEED request credits the giver's reputation through
        # the same trust ledger that gates claims and rules.
        session.last_need_object = 77
        session.last_need_at = __import__("time").monotonic()
        trust_before = session.mind.trust_in(11)
        session.handle_mx("MX\n1 0 0 77 -1")
        assert session.mind.trust_in(11) > trust_before
        assert session.last_need_object is None
        session.world[(1, 0)] = 0

        # An unsendable movement attempt still counts toward the watchdog.
        class _FakeSock:
            def sendall(self, _data: bytes) -> None:
                pass

        session.motions_since_progress = 0
        from ohol_open_ended_expectation_agents import ActionProposal
        unsendable = ActionProposal("MOVE", 1.0, "", 0, 0, path=[(0, 0)])
        assert session.begin_motion(_FakeSock(), unsendable, 103.4) is False
        assert session.motions_since_progress == 1
        session.motions_since_progress = 0

        # M20: exploration anneals with competence and hunger.  With a food
        # plan known, a starving agent stops sightseeing; a safe one keeps
        # exploring.  With no plan, exploration stays at full strength.
        session.world[(0, 4)] = 34
        session.food_store, session.food_capacity = 3, 20
        proposals = session.propose_actions(session.players[10], 103.5)
        hungry_use = next(p for p in proposals if p.kind == "USE")
        assert "explore=0.25" in hungry_use.reason, hungry_use.reason
        session.food_store, session.food_capacity = 18, 20
        proposals = session.propose_actions(session.players[10], 103.6)
        safe_use = next(p for p in proposals if p.kind == "USE")
        assert "explore=0.90" in safe_use.reason, safe_use.reason
        session.food_store = None
        session.food_capacity = None

        # Abundant, still-untested objects earn a staple bonus.
        for _ in range(30):
            session.mind.note_objects({88})
        session.world[(2, 1)] = 88
        proposals = session.propose_actions(session.players[10], 103.7)
        staple_use = next(
            p for p in proposals if p.kind == "USE" and p.target_id == 88
        )
        assert "staple=0.00" not in staple_use.reason, staple_use.reason

        # A committed goal earns hysteresis toward finishing it.
        session.committed_goal = ("USE", 0, 4, 103.7)
        proposals = session.propose_actions(session.players[10], 103.8)
        committed_use = next(
            p for p in proposals
            if p.kind == "USE" and (p.target_x, p.target_y) == (0, 4)
        )
        assert "commit=1.00" in committed_use.reason, committed_use.reason
        session.committed_goal = None

        # Two runner threads can never claim the same world identity.
        first = AgentSession(
            5, args(directory), ("x@y", "ABC", "x"), threading.Event()
        )
        second = AgentSession(
            6, args(directory), ("x@y", "ABC", "x"), threading.Event()
        )
        shared_pu = (
            "PU\n" + pu_line(21, 0, 0, 0) + "\n" + pu_line(22, 0, 1, 0)
        )
        first.handle_pu(shared_pu)
        second.handle_pu(shared_pu)
        assert first.our_id == 22
        assert second.our_id == 21
        first._release_identity()
        second._release_identity()

        # ===== M21: the Lexical Workspace (fully Gregorian reasoning) =====

        # Thought in token form: a rule whose tokens cannot be grounded is
        # kept, chained over, and valued -- words for things never perceived.
        session.handle_ps("PS\n11 QQQ ON RRR MAKES BAK")
        assert "QQQ|RRR" in session.mind.token_rules
        assert "0|" + "QQQ" not in session.mind.rule_testimony
        import time as _time
        token_worth = session.mind.token_values(_time.time(), 480.0)
        assert token_worth.get("QQQ", 0.0) > 0.0

        # WHERE is answered with egocentric WAY testimony about space.
        session.world[(6, 0)] = 35
        session.handle_ps("PS\n11 WHERE BAK")
        assert "BAK WAY E NEAR" in session.pending_utterances

        # A heard WAY answer becomes a journey toward an absent referent.
        session.handle_ps("PS\n11 BAK WAY N FAR")
        assert "BAK" in session.spatial_leads
        session.food_store, session.food_capacity = 3, 20
        proposals = session.propose_actions(session.players[10], 104.0)
        assert any(p.kind == "SEEK_LEAD" for p in proposals)
        session.spatial_leads.clear()
        session.food_store = None
        session.food_capacity = None

        # A taught warning installs a graded veto on an act never tried.
        session.handle_ps("PS\n11 ZAVI HURTS")
        assert session.mind.danger_value(77) > 0.0
        session.world[(3, 1)] = 77
        proposals = session.propose_actions(session.players[10], 104.1)
        wary_use = next(
            p for p in proposals if p.kind == "USE" and p.target_id == 77
        )
        assert "danger=" in wary_use.reason
        assert "danger=0.00" not in wary_use.reason, wary_use.reason

        # A taught recipe assembles from TEACH plus ordered rules, and its
        # matching step guides action.
        session.handle_ps("PS\n11 TEACH ZAVI")
        session.handle_ps("PS\n11 HAND ON HFU MAKES ZAVI")
        assert session.mind.recipes.get("ZAVI", {}).get("steps")
        proposals = session.propose_actions(session.players[10], 104.2)
        recipe_use = next(
            p for p in proposals if p.kind == "USE" and p.target_id == 34
        )
        assert "recipe=0.00" not in recipe_use.reason, recipe_use.reason

        # Unrehearsed chains decay; contemplation rehearses and restores.
        session.mind.token_rules["QQQ|RRR"]["fresh"] = _time.time() - 100000
        faded = session.mind.token_values(_time.time(), 480.0).get("QQQ", 0.0)
        session.mind.rehearse(_time.time(), 480.0)
        restored = session.mind.token_values(
            _time.time(), 480.0
        ).get("QQQ", 0.0)
        assert restored > faded

        # Observation: a peer's hand changing beside a lone candidate object
        # is witnessed causal evidence, no words needed.
        session.world[(30, 30)] = 301
        session.handle_pu("PU\n" + pu_line(12, 0, 30, 30))
        session.handle_pu("PU\n" + pu_line(12, 302, 30, 30))
        assert session.mind.rule_testimony.get("0|301", {}).get("result") == 302

        # A witnessed death leaves weak danger evidence on the final context.
        session.handle_pu("PU\n12 X X")
        assert 12 not in session.players
        assert session.mind.danger.get(301) is not None

        # Habits of mind are meta-conjectures: repeated failure falsifies a
        # way of thinking, and its behavior disappears.
        for _ in range(5):
            session.mind.credit_habits(("VERIFY",), False)
        session.mind.rehearse(_time.time(), 480.0)
        assert session.mind.habit_factor("VERIFY") == 0.0
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 77, 0, 0)
        )[0]
        proposals = session.propose_actions(session.players[10], 104.3)
        unverified = next(p for p in proposals if p.kind == "SELF")
        assert "verify=0.00" in unverified.reason, unverified.reason
        # ...and a trusted cultural endorsement re-adopts the habit.
        session.mind.source_trust[13] = {"helpful": 8, "failed": 0}
        session.players[13] = parse_player_updates(
            "PU\n" + pu_line(13, 0, 1, 1)
        )[0]
        session.handle_ps("PS\n13 WAY VERIFY GOOD")
        session.handle_ps("PS\n13 WAY VERIFY GOOD")
        session.mind.rehearse(_time.time(), 480.0)
        assert session.mind.habit_factor("VERIFY") == 1.0

        # Second-order language: introductions bind names to speakers, and
        # reputation is taught through the shared trust ledger.
        session.handle_ps("PS\n11 I AM KODA")
        assert session.mind.person_names.get("KODA") == 11
        reputation_before = session.mind.trust_in(11)
        session.handle_ps("PS\n13 KODA BAD")
        assert session.mind.trust_in(11) < reputation_before

        # A confessed mistake weakens the community's token rule.
        contradictions_before = int(
            session.mind.token_rules["QQQ|RRR"].get("contradictions", 0)
        )
        session.handle_ps("PS\n11 MISTAKE QQQ ON RRR")
        assert int(
            session.mind.token_rules["QQQ|RRR"]["contradictions"]
        ) == contradictions_before + 1

        # A trusted correction reopens my own settled test.
        session.mind.source_trust[19] = {"helpful": 9, "failed": 0}
        session.players[19] = parse_player_updates(
            "PU\n" + pu_line(19, 0, 1, 0)
        )[0]
        session.handle_ps("PS\n19 BAK BAD")
        self_key = "held:35|target:-1|action:SELF"
        assert all(
            e.status != "corroborated"
            for e in session.mind.transitions[self_key].values()
        )
        assert "35|-1" in session.mind.retest_pairs
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 35, 0, 0)
        )[0]
        proposals = session.propose_actions(session.players[10], 104.4)
        retested = next(p for p in proposals if p.kind == "SELF")
        assert "retest=1.50" in retested.reason, retested.reason

        # Meta-credit bookkeeping.
        session.mind.credit_habits(("TRUST",), True)
        assert int(session.mind.habits["TRUST"]["helpful"]) >= 1

        # ===== M23: reflective priorities (drive modes) =====

        # Urgent hunger without a threat adopts FEED, and FEED reweights:
        # exploration is suppressed relative to LEARN.
        session.food_store, session.food_capacity = 3, 20
        session.mind.danger["77"] = None  # guard: no accidental key type
        del session.mind.danger["77"]
        saved_danger = dict(session.mind.danger)
        session.mind.danger.clear()
        session.appraise_priority(session.players[10], 200.0, 0.85)
        assert session.current_mode == "FEED", session.current_mode
        proposals = session.propose_actions(session.players[10], 200.1)
        feed_use = next(p for p in proposals if p.kind == "USE")
        assert "explore=" in feed_use.reason

        # A strong nearby danger preempts everything: SAFE.
        session.mind.danger.update(saved_danger)
        session.mind.note_danger_own(77, 4.0)
        session.appraise_priority(session.players[10], 200.2, 0.85)
        assert session.current_mode == "SAFE", session.current_mode
        # ...and the SAFE profile doubles the graded veto.
        proposals = session.propose_actions(session.players[10], 200.3)
        safe_use = next(
            p for p in proposals if p.kind == "USE" and p.target_id == 77
        )
        assert "danger=" in safe_use.reason
        assert "danger=0.00" not in safe_use.reason

        # Reflection: leaving FEED after hunger dropped credits FEED.
        feed_before = int(session.mind.modes["FEED"].get("helpful", 0))
        session.mode_snapshot = session._priority_snapshot(0.85)
        session.current_mode = "FEED"
        session.food_store = 15
        session._settle_mode(0.25)
        assert int(session.mind.modes["FEED"]["helpful"]) == feed_before + 1

        # Discretionary selection follows learned mode weights once fed
        # and out of dwell: a strongly credited CRAFT wins.
        session.mind.danger.clear()
        session.food_store = 18
        for _ in range(6):
            session.mind.credit_mode("CRAFT", True)
        for _ in range(4):
            session.mind.credit_mode("LEARN", False)
            session.mind.credit_mode("NEST", False)
        session.current_mode = "LEARN"
        session.mode_started_at = 0.0
        session.appraise_priority(session.players[10], 300.0, 0.1)
        assert session.current_mode == "CRAFT", session.current_mode

        # Culture reaches priorities: a trusted endorsement raises a
        # mode's selection weight through the same trust ledger.
        nest_weight_before = session.mind.mode_weight("NEST")
        session.handle_ps("PS\n13 WAY NEST GOOD")
        assert session.mind.mode_weight("NEST") > nest_weight_before

        # Contemplation teaches priorities that earned their keep.
        endorsements = session.mind.rehearse(_time.time(), 480.0)
        assert "WAY CRAFT GOOD" in endorsements, endorsements

        session.mind.danger.update(saved_danger)
        session.current_mode = "LEARN"
        session.mode_started_at = 10.0 ** 9
        session.food_store = None
        session.food_capacity = None

        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 34, 0, 0)
        )[0]
        session.players.pop(13, None)
        session.players.pop(19, None)

        # ===== M24: fear must be falsifiable; urgency must not thrash =====

        class _AbsorbSock:
            def sendall(self, *_args, **_kwargs) -> None:
                return None

        # Surviving contact unharmed weakens danger a step at a time.
        session.mind.danger[77]["own"] = 0.6
        danger_before = session.mind.danger_value(77)
        assert danger_before > 0.0
        session.mind.weaken_danger(77)
        assert session.mind.danger_value(77) < danger_before

        # A held change right after my own action is my action's echo, not
        # harm: within the settling window no wound is recorded.
        narratives_before = len(session.mind.narratives)
        session.last_own_held = 34
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 601, 0, 0)
        )[0]
        session.pending_trial = None
        session.motion = None
        session.last_action_at = 498.0
        session.autonomy_step(_AbsorbSock(), 500.0)
        assert 601 not in session.mind.danger
        # ...but the same change well after any action is felt harm.
        session.last_own_held = 34
        session.pending_trial = None
        session.motion = None
        session.queued_action = None
        session.last_action_at = 490.0
        session.autonomy_step(_AbsorbSock(), 500.5)
        assert 601 in session.mind.danger
        assert any(
            n.get("kind") == "afflicted" and n.get("wound") == 601
            for n in session.mind.narratives[narratives_before:]
        )
        # ...and a thing my own trials proved good is never a wound.
        session.pending_trial = None
        session.motion = None
        session.last_own_held = 601
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 35, 0, 0)
        )[0]
        session.last_action_at = 495.0
        session.autonomy_step(_AbsorbSock(), 506.0)
        assert 35 not in session.mind.danger

        # Hysteresis: SAFE holds through its urgency dwell even after the
        # threat clears, then yields to hunger -- no fear/hunger thrash.
        session.pending_trial = None
        session.motion = None
        session.queued_action = None
        saved_danger_24 = dict(session.mind.danger)
        session.mind.danger.clear()
        session.current_mode = "SAFE"
        session.mode_started_at = 600.0
        session.appraise_priority(session.players[10], 602.0, 0.9)
        assert session.current_mode == "SAFE"
        session.appraise_priority(session.players[10], 609.0, 0.9)
        assert session.current_mode == "FEED", session.current_mode

        # SAFE is not paralysis: with a feared object in view, retreat is
        # proposed as a positive act.
        session.mind.danger.update(saved_danger_24)
        session.blocked_until.clear()
        session.current_mode = "SAFE"
        proposals = session.propose_actions(session.players[10], 610.0)
        assert any(p.kind == "RETREAT" for p in proposals), [
            p.kind for p in proposals
        ]

        # FEED reflection is judged by food actually gained, even when
        # drain returns hunger to where it started.
        session.current_mode = "FEED"
        session.mode_snapshot = session._priority_snapshot(0.9)
        session.note_food_change((5, 20), 700.0)
        session.note_food_change((8, 20), 701.0)
        feed_helpful_before = int(session.mind.modes["FEED"]["helpful"])
        session._settle_mode(0.9)
        assert int(
            session.mind.modes["FEED"]["helpful"]
        ) == feed_helpful_before + 1

        session.current_mode = "LEARN"
        session.mode_started_at = 10.0 ** 9
        session.pending_trial = None
        session.motion = None
        session.queued_action = None
        session.food_store = None
        session.food_capacity = None
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 34, 0, 0)
        )[0]

        # ===== M25: perception, generalization, stages, places, roles =====
        import json as _json
        import tempfile as _tempfile
        from visual_properties import VisualPerception as _VP

        # Property-level generalization (Module 4): an outcome teaches the
        # agent about how things *look*, transferring to unseen objects.
        signature_sharp = ("elongated", "pointed")
        signature_fibre = ("fibrous",)
        confidence, evidence = session.mind.property_confidence(
            signature_sharp, signature_fibre, "transform"
        )
        assert evidence == 0
        for _ in range(4):
            session.mind.note_property_outcome(
                signature_sharp, signature_fibre, "transform", True
            )
        confidence, evidence = session.mind.property_confidence(
            signature_sharp, signature_fibre, "transform"
        )
        assert evidence == 4 and confidence > 0.7, (confidence, evidence)
        session.mind.note_property_outcome(
            signature_sharp, signature_fibre, "transform", False
        )
        lowered, _ = session.mind.property_confidence(
            signature_sharp, signature_fibre, "transform"
        )
        assert lowered < confidence

        # Location value (Module 6): places accrue worth from outcomes.
        assert session.mind.location_worth(100, 100) == 0.0
        session.mind.note_location_outcome(100, 100, "food", 1.0)
        session.mind.note_location_outcome(101, 101, "comfort", 0.5)
        assert session.mind.location_worth(100, 100) > 0.0
        session.mind.note_location_outcome(200, 200, "danger", 2.0)
        assert session.mind.location_worth(200, 200) < 0.0

        # Competence and emergent roles (Module 13): repetition builds
        # competence, from which a dominant task appears with no label.
        assert session.mind.task_competence("forage") == 0.0
        for _ in range(12):
            session.mind.note_task_outcome("forage", True)
        for _ in range(6):
            session.mind.note_task_outcome("craft", False)
        assert session.mind.task_competence("forage") > 0.7
        assert session.mind.task_competence("craft") == 0.0
        dominant, strength = session.mind.dominant_task()
        assert dominant == "forage" and strength > 0.7

        # Developmental stages (Module 8) come from age alone.
        assert life_stage(1.0) == "infant"
        assert life_stage(8.0) == "child"
        assert life_stage(25.0) == "adult"
        assert life_stage(52.0) == "elder"

        # Dependant care (Module 14): an adult holding something its own
        # trials proved nourishing offers it to a nearby infant.
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 35, 0, 0)
        )[0]
        session.players[10].age = 25.0
        session.players[44] = parse_player_updates(
            "PU\n" + pu_line(44, 0, 1, 0)
        )[0]
        session.players[44].age = 1.5
        session.dependents = {44: 1.5}
        session.stage = "adult"
        proposals = session.propose_actions(session.players[10], 800.0)
        assert any(
            p.kind == "CARE" and p.target_id == 44 for p in proposals
        ), [p.kind for p in proposals]
        session.dependents.clear()
        session.players.pop(44, None)

        # Structured event logging (Phase 1): JSONL, one object a line.
        with _tempfile.TemporaryDirectory() as tmpdir:
            session.args.event_log_dir = tmpdir
            session.life_index = 7
            session.open_event_log()
            session.record_event("unit_test", detail="hello")
            assert session.event_log_path is not None
            lines = session.event_log_path.read_text().strip().splitlines()
            assert len(lines) == 2
            first = _json.loads(lines[0])
            last = _json.loads(lines[-1])
            assert first["kind"] == "life_start"
            assert last["kind"] == "unit_test"
            assert last["detail"] == "hello"
            for field in ("t", "agent", "life", "stage", "mode", "peers"):
                assert field in last, field
            session.args.event_log_dir = None
            session.event_log_path = None

        # ===== M26: planning, roles, society, controls =====

        # Module 11: a full social model, not just testimony accuracy.
        session.mind.note_kinship(44, 0.5)
        session.mind.note_caregiving(44, 2.0)
        session.mind.note_cooperation(44, 1.0)
        session.mind.note_familiarity(44, 0.4)
        belief = session.mind.belief_about(44)
        assert belief["kinship"] == 0.5 and belief["caregiving"] == 2.0
        assert session.mind.social_regard(44) > 0.0
        assert session.mind.social_regard(9999) == 0.0

        # Commitments feed the same trust ledger as claims (Module 11/13).
        trust_before = session.mind.trust_in(45)
        session.mind.note_commitment_outcome(45, True)
        assert session.mind.trust_in(45) > trust_before
        session.mind.note_commitment_outcome(45, False)
        session.mind.note_danger_caused(45, 1.0)
        assert int(session.mind.belief_about(45)["commitments_broken"]) == 1

        # Module 5: delayed effects accrue to the act that preceded them.
        assert session.mind.delayed_value("use:1|2") == 0.0
        session.mind.note_delayed_effect("use:1|2", "comfort", 2.0)
        assert session.mind.delayed_value("use:1|2") > 0.0
        session.mind.note_delayed_effect("use:1|2", "danger", 8.0)
        assert session.mind.delayed_value("use:1|2") < 0.0

        # Module 7: an act with no immediate pay-off can still be worth
        # doing once its delayed effects have been felt.
        barren, _ = session.expected_value(
            "invest", immediate=0.0, effort=0.5, risk=0.0, context="fresh"
        )
        session.mind.note_delayed_effect("proven", "comfort", 6.0)
        proven, reason = session.expected_value(
            "invest", immediate=0.0, effort=0.5, risk=0.0, context="proven"
        )
        assert proven > barren, (proven, barren)
        assert "future=" in reason
        # ...and dependants and information both raise it.
        with_dep, _ = session.expected_value(
            "invest", immediate=0.0, effort=0.5, risk=0.0,
            context="proven", dependant_effect=1.0,
        )
        assert with_dep > proven

        # Module 13: competence feeds back into task scoring, closing the
        # specialization loop, and commitments prevent duplication.
        session.current_task = ""
        plain = session.task_suitability("novel_task", 1.0, 1.0, 900.0)
        for _ in range(12):
            session.mind.note_task_outcome("hunt", True)
        skilled = session.task_suitability("hunt", 1.0, 1.0, 900.0)
        assert skilled > plain, (skilled, plain)
        session.mind.note_commitment_heard(46, "hunt", _time.time())
        taken = session.task_suitability("hunt", 1.0, 1.0, 900.0)
        assert taken < skilled
        assert session.mind.task_is_taken("hunt", _time.time())
        assert not session.mind.task_is_taken("hunt", _time.time() + 500.0)

        # Module 13: local needs are estimated from the agent's own view.
        session.food_store, session.food_capacity = 2, 20
        needs = session.local_needs(session.players[10], 0.9)
        assert needs["forage"] > 0.8 and set(needs) >= {
            "forage", "care", "safety", "craft", "explore"
        }
        session.food_store = None
        session.food_capacity = None

        # Module 10: the remaining message types all land.
        session.players[47] = parse_player_updates(
            "PU\n" + pu_line(47, 0, 1, 1)
        )[0]
        session.handle_ps("PS\n47 COMMIT FORAGE")
        assert session.mind.task_is_taken("forage", _time.time())
        session.mind.source_trust[47] = {"helpful": 6, "failed": 0}
        session.handle_ps("PS\n47 HELP CRAFT")
        assert "craft" in session.help_requests
        session.mind.person_names[str(session.self_name or "ZZTOP")] = (
            session.our_id
        )
        session.self_name = session.self_name or "ZZTOP"
        session.handle_ps(f"PS\n47 FOLLOW {session.self_name}")
        assert session.follow_target is not None
        session.handle_ps("PS\n47 AVOID ZAVI")
        assert session.mind.danger_value(77) > 0.0
        session.handle_ps("PS\n47 BRING ZAVI")
        assert 77 in session.requests_heard

        # Module 14: care is weighted by regard, not blind altruism.
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 35, 0, 0)
        )[0]
        session.players[10].age = 30.0
        session.players[48] = parse_player_updates(
            "PU\n" + pu_line(48, 0, 1, 0)
        )[0]
        session.players[48].age = 1.0
        session.dependents = {48: 1.0}
        session.stage = "adult"
        stranger_care = next(
            p for p in session.propose_actions(session.players[10], 910.0)
            if p.kind == "CARE"
        )
        session.mind.note_kinship(48, 1.0)
        session.mind.note_caregiving(48, 3.0)
        kin_care = next(
            p for p in session.propose_actions(session.players[10], 911.0)
            if p.kind == "CARE"
        )
        assert kin_care.score > stranger_care.score
        session.dependents.clear()
        session.players.pop(48, None)

        # Control 2: id remapping leaves appearances untouched.
        configure_id_shuffle(0)
        assert shuffled_id(34) == 34
        configure_id_shuffle(7)
        remapped = shuffled_id(34)
        assert remapped != 34 and shuffled_id(34) == remapped
        assert shuffled_id(34) != shuffled_id(51)
        configure_id_shuffle(0)
        assert shuffled_id(34) == 34

        # Control 5: with communication disabled nothing is ever said.
        session.args.no_communication = True
        session.pending_utterances.clear()
        session.pending_utterances.append("HELLO")
        session.pending_trial = None
        session.motion = None
        session.queued_action = None
        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 34, 0, 0)
        )[0]
        spoken_before = dict(session.last_spoken)
        for tick in range(6):
            session.autonomy_step(_AbsorbSock(), 920.0 + tick)
        # Nothing may ever be uttered while the control is engaged.
        assert session.last_spoken == spoken_before, (
            set(session.last_spoken) - set(spoken_before)
        )
        session.args.no_communication = False

        # Ablation: observation can be switched off for the transmission
        # comparisons the roadmap calls for.
        session.args.no_observation = True
        session.world[(31, 31)] = 401
        session.handle_pu("PU\n" + pu_line(49, 0, 31, 31))
        session.handle_pu("PU\n" + pu_line(49, 402, 31, 31))
        assert "0|401" not in session.mind.rule_testimony
        session.args.no_observation = False
        session.players.pop(49, None)
        session.players.pop(47, None)

        # An explicit path that holds no game data means blind, with no
        # silent fallback: the property ablation must really be blind.
        blind = _VP("/definitely/not/a/data/dir")
        assert blind.available is False, (
            "explicit bad path must not fall back to auto-detection"
        )
        assert blind.properties(34) == {}
        assert blind.descriptor(34) == ()
        assert blind.similarity(34, 51) == 0.0

        session.players[10] = parse_player_updates(
            "PU\n" + pu_line(10, 34, 0, 0)
        )[0]

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

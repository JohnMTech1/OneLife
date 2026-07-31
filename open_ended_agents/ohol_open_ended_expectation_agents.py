#!/usr/bin/env python3
"""Open-ended OneLife agents with private expectations and grounded cooperation.

Milestone 7:
* every biological life owns a separate JSON mind;
* discoveries can be transmitted only through visible in-game speech;
* listeners ground the token in the speaker's visible held object;
* repeated evidence corroborates a Popperian conjecture;
* conflicting evidence weakens/falsifies it;
* the same observations reinforce Skinnerian associations.

Milestone 5 removes the scripted task loop.  The only innate knowledge is the
agent's action repertoire and drives.  Object affordances, useful action
sequences, transition expectations, and word meanings are learned privately.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import random
import re
import select
import signal
import socket
import sys
import threading
import time
import zlib
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def read_setting(settings: Path, name: str, default: str = "") -> str:
    try:
        return (settings / f"{name}.ini").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return default


def hmac_sha1(key: str, challenge: str) -> str:
    return hmac.new(key.encode(), challenge.encode(), hashlib.sha1).hexdigest().upper()


def pure_account_key(value: str) -> str:
    return value.upper().replace("-", "")


def agent_email(base_email: str, index: int) -> str:
    if "@" in base_email:
        local, domain = base_email.rsplit("@", 1)
        return f"{local}+headless-{index}@{domain}"
    return f"headless-agent-{index}@local.invalid"


@dataclass
class PendingBinary:
    kind: str
    compressed_size: int
    header: str = ""


@dataclass
class MapChunk:
    size_x: int
    size_y: int
    x: int
    y: int
    cells: list[int]


class ProtocolReader:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.pending: PendingBinary | None = None

    def feed(self, data: bytes) -> list[str | MapChunk]:
        self.buffer.extend(data)
        messages: list[str | MapChunk] = []
        while True:
            if self.pending is not None:
                if len(self.buffer) < self.pending.compressed_size:
                    break
                payload = bytes(self.buffer[: self.pending.compressed_size])
                del self.buffer[: self.pending.compressed_size]
                pending = self.pending
                self.pending = None
                if pending.kind == "CM":
                    messages.append(zlib.decompress(payload).decode("utf-8", "replace"))
                elif pending.kind == "MC":
                    raw = zlib.decompress(payload).decode("utf-8", "replace")
                    numbers = [int(v) for v in re.findall(r"-?\d+", pending.header)]
                    if len(numbers) >= 6:
                        sx, sy, x, y = numbers[:4]
                        tokens = raw.split()
                        cells = []
                        for token in tokens[: sx * sy]:
                            try:
                                # biome:floor:object[,contained...]
                                cells.append(int(token.split(",", 1)[0].split(":")[2]))
                            except (ValueError, IndexError):
                                cells.append(-1)
                        if len(cells) == sx * sy:
                            messages.append(MapChunk(sx, sy, x, y, cells))
                continue
            try:
                end = self.buffer.index(ord("#"))
            except ValueError:
                break
            message = bytes(self.buffer[:end]).decode("utf-8", "replace")
            del self.buffer[: end + 1]
            if message.startswith("CM\n"):
                match = re.match(r"CM\n(\d+) (\d+)\n?", message)
                if not match:
                    raise RuntimeError(f"Malformed CM header: {message!r}")
                self.pending = PendingBinary("CM", int(match.group(2)), message)
            elif message.startswith("MC\n"):
                numbers = [int(v) for v in re.findall(r"-?\d+", message)]
                if len(numbers) < 6:
                    raise RuntimeError(f"Malformed MC header: {message!r}")
                self.pending = PendingBinary("MC", numbers[5], message)
            else:
                messages.append(message)
        return messages


def message_kind(message: str) -> str:
    return message.split("\n", 1)[0].split(" ", 1)[0]


def build_login(challenge_message: str, email: str, account_key: str,
                server_password: str, client_tag: str, tutorial: int) -> str:
    lines = challenge_message.splitlines()
    if len(lines) < 3:
        raise RuntimeError(f"Malformed SN message: {challenge_message!r}")
    challenge = lines[2].strip()
    return (
        f"LOGIN {client_tag} {email or 'blank_email'} "
        f"{hmac_sha1(server_password, challenge)} "
        f"{hmac_sha1(pure_account_key(account_key), challenge)} {tutorial}#"
    )


@dataclass
class PlayerView:
    player_id: int
    x: int
    y: int
    held_object: int
    age: float
    updated_at: float


@dataclass
class ActionProposal:
    kind: str
    score: float
    reason: str
    target_x: int = 0
    target_y: int = 0
    target_id: int = 0
    path: list[tuple[int, int]] = field(default_factory=list)
    utterance: str = ""


@dataclass
class WordHypothesis:
    token: str
    referent_id: int
    confirmations: int = 0
    contradictions: int = 0
    confidence: float = 0.5
    status: str = "tentative"
    sources: list[int] = field(default_factory=list)

    def observe(self, shown_id: int, source: int) -> float:
        reward = 1.0 if shown_id == self.referent_id else -1.0
        if reward > 0:
            self.confirmations += 1
        else:
            self.contradictions += 1
        if source not in self.sources:
            self.sources.append(source)
        # Beta(1,1) posterior mean: explicit, bounded, and easy to inspect.
        self.confidence = (self.confirmations + 1) / (
            self.confirmations + self.contradictions + 2
        )
        if self.contradictions >= 2 and self.confidence < 0.4:
            self.status = "falsified"
        elif self.confirmations >= 3 and self.confidence >= 0.7:
            self.status = "corroborated"
        else:
            self.status = "tentative"
        return reward


@dataclass
class SkinnerianExpectation:
    context: str
    action: str
    outcome: str
    trials: int = 0
    total_reward: float = 0.0
    value: float = 0.0

    def reinforce(self, reward: float, learning_rate: float = 0.25) -> None:
        self.trials += 1
        self.total_reward += reward
        self.value += learning_rate * (reward - self.value)


@dataclass
class ActionTrial:
    action: str
    target_id: int
    x: int
    y: int
    held_before: int
    target_before: int
    food_before: int | None
    started_at: float


@dataclass
class MotionIntent:
    proposal: ActionProposal
    started_at: float
    start: tuple[int, int]
    last_progress_at: float
    last_position: tuple[int, int]
    commanded_goal: tuple[int, int]


@dataclass
class TransitionExpectation:
    context: str
    action: str
    predicted_outcome: str
    trials: int = 0
    confirmations: int = 0
    contradictions: int = 0
    mean_reward: float = 0.0
    confidence: float = 0.5
    status: str = "tentative"

    def observe(self, outcome: str, reward: float) -> None:
        self.trials += 1
        if outcome == self.predicted_outcome:
            self.confirmations += 1
        else:
            self.contradictions += 1
        self.mean_reward += (reward - self.mean_reward) / self.trials
        self.confidence = (self.confirmations + 1) / (
            self.confirmations + self.contradictions + 2
        )
        if self.contradictions >= 2 and self.confidence < 0.4:
            self.status = "falsified"
        elif self.confirmations >= 3 and self.confidence >= 0.7:
            self.status = "corroborated"
        else:
            self.status = "tentative"


class PrivateMind:
    SYLLABLES = (
        "BA", "BE", "BO", "DA", "DE", "DO", "FA", "FI", "FU", "GA", "GI",
        "HA", "HE", "HU", "KA", "KI", "KO", "LA", "LE", "LU", "MA", "MI",
        "MO", "NA", "NE", "NO", "PA", "PI", "RA", "RE", "RO", "SA", "SI",
        "TA", "TE", "TO", "VA", "VI", "ZA",
    )

    def __init__(self, agent_index: int, path: Path) -> None:
        self.agent_index = agent_index
        self.path = path
        self.object_words: dict[int, str] = {}
        self.hypotheses: dict[str, dict[int, WordHypothesis]] = {}
        self.skinnerian: dict[str, SkinnerianExpectation] = {}
        self.transitions: dict[str, dict[str, TransitionExpectation]] = {}
        self.encounter_counts: dict[int, int] = {}
        self.action_counts: dict[str, int] = {}
        self.social_values: dict[str, SkinnerianExpectation] = {}
        self.food_testimony: dict[int, dict[str, Any]] = {}
        self.episodes: list[dict[str, Any]] = []
        self.rng = random.Random(agent_index * 1_000_003)
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.object_words = {int(k): v for k, v in data.get("object_words", {}).items()}
        for token, candidates in data.get("popperian_hypotheses", {}).items():
            self.hypotheses[token] = {
                int(k): WordHypothesis(**v) for k, v in candidates.items()
            }
        self.skinnerian = {
            k: SkinnerianExpectation(**v)
            for k, v in data.get("skinnerian_expectations", {}).items()
        }
        self.transitions = {
            context_action: {
                outcome: TransitionExpectation(**expectation)
                for outcome, expectation in outcomes.items()
            }
            for context_action, outcomes in data.get(
                "transition_expectations", {}
            ).items()
        }
        self.encounter_counts = {
            int(k): int(v) for k, v in data.get("encounter_counts", {}).items()
        }
        self.action_counts = {
            str(k): int(v) for k, v in data.get("action_counts", {}).items()
        }
        self.social_values = {
            k: SkinnerianExpectation(**v)
            for k, v in data.get("social_expectations", {}).items()
        }
        self.food_testimony = {
            int(k): dict(v) for k, v in data.get("food_testimony", {}).items()
        }
        self.episodes = list(data.get("episodes", []))[-500:]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "agent_index": self.agent_index,
            "object_words": {str(k): v for k, v in self.object_words.items()},
            "popperian_hypotheses": {
                token: {str(k): asdict(v) for k, v in candidates.items()}
                for token, candidates in self.hypotheses.items()
            },
            "skinnerian_expectations": {
                k: asdict(v) for k, v in self.skinnerian.items()
            },
            "transition_expectations": {
                key: {outcome: asdict(value) for outcome, value in outcomes.items()}
                for key, outcomes in self.transitions.items()
            },
            "encounter_counts": {
                str(k): v for k, v in self.encounter_counts.items()
            },
            "action_counts": self.action_counts,
            "social_expectations": {
                k: asdict(v) for k, v in self.social_values.items()
            },
            "food_testimony": {
                str(k): v for k, v in self.food_testimony.items()
            },
            "episodes": self.episodes[-500:],
        }
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

    def _used_tokens(self) -> set[str]:
        return set(self.object_words.values()) | set(self.hypotheses)

    def word_for_object(self, object_id: int) -> tuple[str, bool]:
        if object_id in self.object_words:
            return self.object_words[object_id], False
        # Language learned from another agent must be available for production,
        # not merely stored as a passive hypothesis.  Prefer the strongest
        # non-falsified heard label before inventing a private synonym.
        heard = [
            candidate
            for candidates in self.hypotheses.values()
            for candidate in candidates.values()
            if candidate.referent_id == object_id
            and candidate.status != "falsified"
        ]
        if heard:
            candidate = max(
                heard,
                key=lambda item: (
                    item.confidence, item.confirmations, -item.contradictions,
                    item.token,
                ),
            )
            self.object_words[object_id] = candidate.token
            self._record(
                "adopt_word", token=candidate.token, object_id=object_id,
                confidence=candidate.confidence,
            )
            self.save()
            return candidate.token, False
        used = self._used_tokens()
        for _ in range(500):
            token = self.rng.choice(self.SYLLABLES) + self.rng.choice(self.SYLLABLES)
            if token not in used:
                self.object_words[object_id] = token
                self._record("invent_word", token=token, object_id=object_id)
                self.save()
                return token, True
        token = f"OBJ{object_id}"
        self.object_words[object_id] = token
        self.save()
        return token, True

    def hear_demonstration(self, token: str, object_id: int, speaker_id: int) -> WordHypothesis:
        candidates = self.hypotheses.setdefault(token, {})
        candidate = candidates.get(object_id)
        if candidate is None:
            candidate = WordHypothesis(token=token, referent_id=object_id)
            candidates[object_id] = candidate
        reward = candidate.observe(object_id, speaker_id)
        # A single word cannot refer unambiguously to every conflicting object.
        for other_id, other in candidates.items():
            if other_id != object_id and other.status != "falsified":
                other.observe(object_id, speaker_id)
        key = f"speaker_holds:{object_id}|hear:{token}|same_referent"
        learned = self.skinnerian.setdefault(
            key,
            SkinnerianExpectation(
                context=f"speaker_holds:{object_id}",
                action=f"hear:{token}",
                outcome="same_referent",
            ),
        )
        learned.reinforce(reward)
        # A heard demonstration changes the listener's usable vocabulary.
        # One coherent demonstration is enough for tentative adoption, while
        # later contradictory evidence can still falsify the hypothesis.
        current = self.object_words.get(object_id)
        current_candidates = self.hypotheses.get(current, {}) if current else {}
        current_hypothesis = current_candidates.get(object_id)
        current_confidence = (
            current_hypothesis.confidence if current_hypothesis else -1.0
        )
        if current is None or candidate.confidence > current_confidence:
            self.object_words[object_id] = token
        self._record(
            "hear_label", token=token, object_id=object_id,
            speaker_id=speaker_id, confidence=candidate.confidence,
            status=candidate.status,
        )
        self.save()
        return candidate

    def hear_food_testimony(
        self, token: str, object_id: int, speaker_id: int
    ) -> WordHypothesis:
        """Store fallible testimony without turning it into lived experience."""
        hypothesis = self.hear_demonstration(token, object_id, speaker_id)
        claim = self.food_testimony.setdefault(
            object_id, {"confirmations": 0, "contradictions": 0, "sources": []}
        )
        claim["confirmations"] += 1
        if speaker_id not in claim["sources"]:
            claim["sources"].append(speaker_id)
        self._record(
            "hear_food_testimony", token=token, object_id=object_id,
            speaker_id=speaker_id,
        )
        self.save()
        return hypothesis

    def testimony_food_value(self, object_id: int) -> float:
        claim = self.food_testimony.get(object_id)
        if not claim:
            return 0.0
        confirmations = int(claim.get("confirmations", 0))
        contradictions = int(claim.get("contradictions", 0))
        return (confirmations + 1) / (confirmations + contradictions + 2)

    def known_food_objects(self) -> set[int]:
        """Return objects personally observed increasing food after SELF."""
        result: set[int] = set()
        pattern = re.compile(r"held:(\d+)\|target:-1\|action:SELF")
        for key, outcomes in self.transitions.items():
            match = pattern.fullmatch(key)
            if match and any(
                expectation.status != "falsified"
                and re.search(r"food_delta:([1-9]\d*)", expectation.predicted_outcome)
                for expectation in outcomes.values()
            ):
                result.add(int(match.group(1)))
        return result

    def inferred_referent(self, token: str) -> int | None:
        candidates = [
            candidate for candidate in self.hypotheses.get(token, {}).values()
            if candidate.status != "falsified"
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.confidence).referent_id

    def _record(self, event: str, **details: Any) -> None:
        self.episodes.append({"time": time.time(), "event": event, **details})
        del self.episodes[:-500]

    def observe_action_result(
        self, action: str, target_id: int, held_before: int, held_after: int,
        target_before: int, target_after: int, food_before: int | None,
        food_after: int | None,
    ) -> tuple[SkinnerianExpectation, TransitionExpectation, str, float]:
        food_delta = (
            0 if food_before is None or food_after is None
            else food_after - food_before
        )
        outcome = (
            f"held:{held_after}|target:{target_after}|food_delta:{food_delta}"
        )
        context = f"held:{held_before}|target:{target_before}"
        context_action = f"{context}|action:{action}"
        reward = 0.0
        if food_delta > 0:
            reward += min(5.0, float(food_delta) * 1.5)
        elif food_delta < 0:
            reward -= 0.05
        # A state change is evidence that an action worked, but it is not
        # automatically useful.  Earlier versions rewarded pickup and drop
        # merely for changing held/target state, creating a self-reinforcing
        # pick-up/drop loop.  Instrumental value now comes from consequences
        # such as food gain; novelty is handled separately by action selection.
        if outcome == f"held:{held_before}|target:{target_before}|food_delta:0":
            reward -= 0.2
        key = f"{context_action}|outcome:{outcome}"
        expectation = self.skinnerian.setdefault(
            key,
            SkinnerianExpectation(
                context=context,
                action=action,
                outcome=outcome,
            ),
        )
        expectation.reinforce(reward)
        outcomes = self.transitions.setdefault(context_action, {})
        popperian = outcomes.get(outcome)
        if popperian is None:
            popperian = TransitionExpectation(context, action, outcome)
            outcomes[outcome] = popperian
        for candidate_outcome, candidate in outcomes.items():
            candidate.observe(outcome, reward)
        self.action_counts[context_action] = self.action_counts.get(
            context_action, 0
        ) + 1
        self._record(
            "action_result",
            action=action,
            target_id=target_id,
            held_before=held_before,
            held_after=held_after,
            target_before=target_before,
            target_after=target_after,
            food_before=food_before,
            food_after=food_after,
            outcome=outcome,
            reward=reward,
            conjecture_status=popperian.status,
        )
        self.save()
        return expectation, popperian, outcome, reward

    def reinforce_social_context(
        self, nearby_ids: list[int], reward: float
    ) -> None:
        """Learn whether this agent's own outcomes improve around these peers."""
        band = "alone" if not nearby_ids else f"group:{min(3, len(nearby_ids))}"
        keys = [band] + [f"peer:{player_id}" for player_id in nearby_ids]
        for key in keys:
            expectation = self.social_values.setdefault(
                key,
                SkinnerianExpectation(
                    context=key, action="remain_near", outcome="experienced_reward"
                ),
            )
            expectation.reinforce(reward)
        self.save()

    def social_knowledge(self, nearby_ids: list[int]) -> tuple[int, float, float]:
        keys = (
            ["alone"] if not nearby_ids
            else [f"group:{min(3, len(nearby_ids))}"]
            + [f"peer:{player_id}" for player_id in nearby_ids]
        )
        records = [self.social_values[key] for key in keys if key in self.social_values]
        if not records:
            return 0, 0.0, 1.0
        trials = sum(record.trials for record in records)
        value = sum(record.value for record in records) / len(records)
        return trials, value, 1.0 / math.sqrt(1.0 + trials)

    def note_objects(self, object_ids: set[int]) -> None:
        changed = False
        for object_id in object_ids:
            if object_id > 0:
                self.encounter_counts[object_id] = (
                    self.encounter_counts.get(object_id, 0) + 1
                )
                changed = True
        if changed and sum(self.encounter_counts.values()) % 25 == 0:
            self.save()

    def action_knowledge(
        self, held: int, target: int, action: str
    ) -> tuple[int, float, float, str]:
        key = f"held:{held}|target:{target}|action:{action}"
        outcomes = self.transitions.get(key, {})
        trials = self.action_counts.get(key, 0)
        if not outcomes:
            return 0, 0.0, 1.0, "unknown"
        best = max(
            outcomes.values(),
            key=lambda value: (value.mean_reward, value.confidence),
        )
        uncertainty = 1.0 / math.sqrt(1.0 + trials)
        status = best.status
        if trials >= 6 and best.mean_reward <= 0.0:
            status = "provisionally_refuted"
        return trials, best.mean_reward, uncertainty, status

    def best_food_action(self, held: int) -> tuple[str, int] | None:
        """Return the best learned immediate action that increased food."""
        best: tuple[float, str, int] | None = None
        pattern = re.compile(
            rf"held:{held}\|target:(-?\d+)\|action:([A-Z]+)"
        )
        for key, outcomes in self.transitions.items():
            match = pattern.fullmatch(key)
            if not match:
                continue
            for expectation in outcomes.values():
                food_match = re.search(
                    r"food_delta:(-?\d+)", expectation.predicted_outcome
                )
                if (
                    food_match
                    and int(food_match.group(1)) > 0
                    and expectation.status != "falsified"
                ):
                    score = expectation.mean_reward * expectation.confidence
                    candidate = (score, match.group(2), int(match.group(1)))
                    if best is None or candidate[0] > best[0]:
                        best = candidate
        return None if best is None else (best[1], best[2])

    def learned_chain_first_step(
        self, held: int, max_depth: int = 5
    ) -> tuple[str, int, int] | None:
        """Search the learned transition graph for a chain ending in food gain."""
        edge_pattern = re.compile(
            r"held:(-?\d+)\|target:(-?\d+)\|action:([A-Z]+)"
        )
        graph: dict[int, list[tuple[int, str, int, bool, float]]] = {}
        for key, outcomes in self.transitions.items():
            match = edge_pattern.fullmatch(key)
            if not match:
                continue
            source = int(match.group(1))
            target = int(match.group(2))
            action = match.group(3)
            for expectation in outcomes.values():
                if expectation.status == "falsified":
                    continue
                held_match = re.search(
                    r"held:(-?\d+)", expectation.predicted_outcome
                )
                food_match = re.search(
                    r"food_delta:(-?\d+)", expectation.predicted_outcome
                )
                if not held_match or not food_match:
                    continue
                destination = int(held_match.group(1))
                feeds = int(food_match.group(1)) > 0
                reliability = expectation.confidence * max(
                    0.05, 1.0 + expectation.mean_reward
                )
                graph.setdefault(source, []).append(
                    (destination, action, target, feeds, reliability)
                )
        queue = deque([(held, [], 1.0)])
        visited = {held: 0}
        best: tuple[float, list[tuple[str, int]]] | None = None
        while queue:
            state, path, reliability = queue.popleft()
            if len(path) >= max_depth:
                continue
            for destination, action, target, feeds, edge_reliability in graph.get(
                state, []
            ):
                next_path = path + [(action, target)]
                next_reliability = reliability * edge_reliability
                if feeds and (best is None or next_reliability > best[0]):
                    best = (next_reliability, next_path)
                if visited.get(destination, max_depth + 1) > len(next_path):
                    visited[destination] = len(next_path)
                    queue.append((destination, next_path, next_reliability))
        if best is None:
            return None
        action, target = best[1][0]
        return action, target, len(best[1])


def parse_player_updates(message: str) -> list[PlayerView]:
    updates: list[PlayerView] = []
    now = time.monotonic()
    for line in message.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 20:
            continue
        try:
            held_field = fields[6].split(",", 1)[0]
            updates.append(
                PlayerView(
                    player_id=int(fields[0]),
                    x=int(fields[14]),
                    y=int(fields[15]),
                    held_object=int(held_field),
                    age=float(fields[16]),
                    updated_at=now,
                )
            )
        except ValueError:
            continue
    return updates


def parse_player_speech(message: str) -> list[tuple[int, str]]:
    speech: list[tuple[int, str]] = []
    for line in message.splitlines()[1:]:
        match = re.match(r"(-?\d+)(?:/\d+)?\s+(.+)", line)
        if match:
            speech.append((int(match.group(1)), match.group(2).strip().upper()))
    return speech


def parse_map_changes(message: str) -> list[tuple[int, int, int]]:
    changes: list[tuple[int, int, int]] = []
    for line in message.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 4:
            continue
        try:
            object_id = int(fields[3].split(",", 1)[0])
            changes.append((int(fields[0]), int(fields[1]), object_id))
        except ValueError:
            continue
    return changes


def parse_food_change(message: str) -> tuple[int, int] | None:
    fields = message.split()
    if len(fields) < 3 or fields[0] != "FX":
        return None
    try:
        return int(fields[1]), int(fields[2])
    except ValueError:
        return None


def grid_path(
    start: tuple[int, int],
    goals: set[tuple[int, int]],
    world: dict[tuple[int, int], int],
    max_nodes: int = 1200,
) -> list[tuple[int, int]]:
    """BFS over observed empty cells; returns start-through-goal."""
    if start in goals:
        return [start]
    queue = deque([start])
    previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    found: tuple[int, int] | None = None
    while queue and len(previous) <= max_nodes:
        current = queue.popleft()
        x, y = current
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nxt in previous:
                continue
            if world.get(nxt, -1) != 0 and nxt not in goals:
                continue
            previous[nxt] = current
            if nxt in goals:
                found = nxt
                queue.clear()
                break
            queue.append(nxt)
    if found is None:
        return []
    path = []
    cursor: tuple[int, int] | None = found
    while cursor is not None:
        path.append(cursor)
        cursor = previous[cursor]
    return list(reversed(path))


class AgentSession(threading.Thread):
    reservation_lock = threading.Lock()
    destination_reservations: dict[tuple[int, int], tuple[int, float]] = {}

    def __init__(self, index: int, args: argparse.Namespace,
                 credentials: tuple[str, str, str], stop: threading.Event) -> None:
        super().__init__(name=f"agent-{index}", daemon=True)
        self.index = index
        self.args = args
        base_email, self.account_key, self.server_password = credentials
        self.email = agent_email(base_email, index)
        self.stop = stop
        self.result = 1
        self.players: dict[int, PlayerView] = {}
        self.world: dict[tuple[int, int], int] = {}
        self.our_id: int | None = None
        self.move_sequence = 0
        self.pending_trial: ActionTrial | None = None
        self.motion: MotionIntent | None = None
        self.queued_action: ActionProposal | None = None
        self.last_action_at = 0.0
        self.last_position: tuple[int, int] | None = None
        self.position_history: deque[tuple[int, int]] = deque(maxlen=8)
        self.blocked_until: dict[tuple[int, int], float] = {}
        self.food_store: int | None = None
        self.food_capacity: int | None = None
        self.last_spoken: dict[str, float] = {}
        self.last_conversation_at = -math.inf
        self.taught_utterances: set[str] = set()
        self.life_number = 0
        self.pending_utterances: deque[str] = deque()
        self.home_location: tuple[int, int] | None = None
        self.home_source: int | None = None
        self.home_announced = False
        self.peer_requests: dict[int, tuple[int, int, int, float]] = {}
        self.last_need_at = 0.0
        self.last_liveness_log = 0.0
        self.last_speech_wait_log = 0.0
        self.identity_seen_at: float | None = None
        self.startup_wait_logged = False
        self.stationary_action_streak = 0
        self.mind = PrivateMind(
            index, Path(args.memory_dir) / f"agent_{index}_unborn.json"
        )

    def begin_new_life(self) -> None:
        """Create a blank mind; no private knowledge crosses a death boundary."""
        self.life_number += 1
        life_id = time.time_ns()
        self.mind = PrivateMind(
            self.index,
            Path(self.args.memory_dir)
            / f"agent_{self.index}_life_{self.life_number}_{life_id}.json",
        )
        self.pending_utterances.clear()
        self.last_spoken.clear()
        self.last_conversation_at = -math.inf
        self.taught_utterances.clear()
        self.home_location = None
        self.home_source = None
        self.home_announced = False
        self.peer_requests.clear()
        self.last_need_at = 0.0
        self.last_speech_wait_log = 0.0
        self.identity_seen_at = None
        self.startup_wait_logged = False
        self.stationary_action_streak = 0
        self.log(
            f"new life {self.life_number}: blank private mind "
            f"(knowledge must be experienced or heard)"
        )

    def log(self, text: str) -> None:
        print(f"[agent {self.index}] {text}", flush=True)

    @staticmethod
    def send(sock: socket.socket, message: str) -> None:
        sock.sendall(message.encode("utf-8"))

    def handle_pu(self, message: str) -> None:
        updates = parse_player_updates(message)
        for view in updates:
            self.players[view.player_id] = view
        # The official client identifies the final newly inserted object in
        # the first PU as self. Shared-spawn test servers send that birth PU
        # immediately after ACCEPTED.
        if self.our_id is None and updates:
            self.our_id = updates[-1].player_id
            self.identity_seen_at = time.monotonic()
            self.log(f"world identity is player {self.our_id}")

    def handle_map_chunk(self, chunk: MapChunk) -> None:
        for index, object_id in enumerate(chunk.cells):
            self.world[(chunk.x + index % chunk.size_x,
                        chunk.y + index // chunk.size_x)] = object_id
        self.mind.note_objects({value for value in chunk.cells if value > 0})

    def handle_mx(self, message: str) -> None:
        for x, y, object_id in parse_map_changes(message):
            self.world[(x, y)] = object_id
            if object_id > 0:
                self.mind.note_objects({object_id})

    def send_path(self, sock: socket.socket, path: list[tuple[int, int]]) -> bool:
        if len(path) < 2:
            return False
        # Keep paths short. The server validates every orthogonal step.
        path = path[: min(len(path), self.args.max_path_steps + 1)]
        self.move_sequence += 1
        sx, sy = path[0]
        fields = ["MOVE", str(sx), str(sy), f"@{self.move_sequence}"]
        fields.extend(
            value
            for x, y in path[1:]
            for value in (str(x - sx), str(y - sy))
        )
        self.send(sock, " ".join(fields) + "#")
        self.log(f"moving from ({sx},{sy}) toward {path[-1]}")
        return True

    def begin_motion(
        self, sock: socket.socket, proposal: ActionProposal, now: float,
        queued: ActionProposal | None = None,
    ) -> bool:
        commanded_path = proposal.path[
            : min(len(proposal.path), self.args.max_path_steps + 1)
        ]
        if not self.send_path(sock, commanded_path):
            return False
        start = commanded_path[0]
        self.motion = MotionIntent(
            proposal, now, start, now, start, commanded_path[-1]
        )
        with self.reservation_lock:
            self.destination_reservations[commanded_path[-1]] = (
                self.index, now + self.args.move_timeout
            )
        self.queued_action = queued
        return True

    def destination_available(
        self, destination: tuple[int, int], now: float
    ) -> bool:
        """Reject live body locations and short-lived goals of other runners."""
        if any(
            peer.player_id != self.our_id
            and (peer.x, peer.y) == destination
            for peer in self.players.values()
        ):
            return False
        with self.reservation_lock:
            expired = [
                pos for pos, (_, until) in self.destination_reservations.items()
                if until <= now
            ]
            for pos in expired:
                self.destination_reservations.pop(pos, None)
            reservation = self.destination_reservations.get(destination)
        return reservation is None or reservation[0] == self.index

    def release_destination(self, destination: tuple[int, int]) -> None:
        with self.reservation_lock:
            reservation = self.destination_reservations.get(destination)
            if reservation and reservation[0] == self.index:
                self.destination_reservations.pop(destination, None)

    def nearby_peer_ids(self, me: PlayerView, radius: float | None = None) -> list[int]:
        radius = self.args.social_radius if radius is None else radius
        return sorted(
            p.player_id for p in self.players.values()
            if p.player_id != self.our_id
            and math.hypot(p.x - me.x, p.y - me.y) <= radius
        )

    def _hunger_drive(self) -> float:
        if self.food_store is None or not self.food_capacity:
            return 0.5
        return max(0.0, min(1.0, 1.0 - self.food_store / self.food_capacity))

    def _adjacent_path(
        self, me: PlayerView, pos: tuple[int, int]
    ) -> list[tuple[int, int]]:
        x, y = pos
        goals = {
            p for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if self.world.get(p, -1) == 0 or p == (me.x, me.y)
        }
        return grid_path((me.x, me.y), goals, self.world)

    def propose_actions(self, me: PlayerView, now: float) -> list[ActionProposal]:
        """Generate available primitive actions; learned evidence supplies scores."""
        proposals: list[ActionProposal] = []
        hunger = self._hunger_drive()
        position = (me.x, me.y)
        movement_drive = min(
            self.args.max_movement_drive,
            self.stationary_action_streak * self.args.movement_drive_step,
        )
        # Do not let a queued statement cycle every decision.  Statements may
        # be taught again after the cooldown, which keeps language alive when
        # peers arrive late or miss the first utterance.
        self.pending_utterances = deque(
            dict.fromkeys(
                utterance for utterance in self.pending_utterances
                if now - self.last_spoken.get(utterance, -math.inf)
                >= self.args.teach_interval
            )
        )
        chain_step = self.mind.learned_chain_first_step(me.held_object)
        personally_known_food = self.mind.known_food_objects()
        self.peer_requests = {
            requester: request
            for requester, request in self.peer_requests.items()
            if now - request[3] <= self.args.request_ttl
        }

        if (
            self.home_location is None
            and self.world
            and self.nearby_peer_ids(me, self.args.language_radius)
            and self.our_id == min(self.players)
        ):
            self.home_location = position
            self.home_source = self.our_id
            self.pending_utterances.append("HOME HERE")
            self.home_announced = True
            self.log(f"proposed HOME at {position}")

        food_candidates = sorted(
            personally_known_food | set(self.mind.food_testimony),
            key=lambda object_id: (
                self.mind.testimony_food_value(object_id), -object_id
            ),
            reverse=True,
        )
        if (
            hunger >= self.args.request_hunger
            and me.held_object <= 0
            and food_candidates
            and now - self.last_need_at >= self.args.request_interval
        ):
            wanted = food_candidates[0]
            token, _ = self.mind.word_for_object(wanted)
            request = f"NEED {token}"
            if request not in self.pending_utterances:
                self.pending_utterances.append(request)
                self.last_need_at = now
                self.log(f"queued {request}; hunger={hunger:.2f}")

        # Naming is a persistent social intention, not something that only
        # exists during the instant a listener happens to be nearby.  M15
        # generated names below only after listener_nearby was true.  Once the
        # movement policy dispersed the group, that condition was rarely met,
        # so no utterance was queued and the approach-to-listener policy had
        # nothing to act on.
        if me.held_object > 0:
            token, invented = self.mind.word_for_object(me.held_object)
            if (
                token not in self.pending_utterances
                and now - self.last_spoken.get(token, -math.inf)
                >= self.args.teach_interval
            ):
                self.pending_utterances.append(token)
                self.log(
                    f"queued name {token} for held object {me.held_object}; "
                    f"source={'invented' if invented else 'adopted'}"
                )

        # Shared adult spawning can leave multiple bodies on the same square.
        # Deliberately disperse before they compete for the same local object.
        if any(
            peer.player_id != self.our_id
            and (peer.x, peer.y) == position
            for peer in self.players.values()
        ):
            directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
            for offset in range(4):
                dx, dy = directions[(self.index - 1 + offset) % 4]
                destination = (me.x + dx, me.y + dy)
                if (
                    self.world.get(destination, 0) == 0
                    and self.blocked_until.get(destination, 0.0) <= now
                    and self.destination_available(destination, now)
                ):
                    proposals.append(ActionProposal(
                        "DISPERSE", 3.5, "another agent occupies this tile",
                        destination[0], destination[1],
                        path=[position, destination],
                    ))
                    break

        # Any visible object can become an experiment.  No object ID is special.
        for pos, object_id in self.world.items():
            if object_id <= 0:
                continue
            distance = abs(pos[0] - me.x) + abs(pos[1] - me.y)
            if distance > self.args.search_radius:
                continue
            if self.blocked_until.get(pos, 0.0) > now:
                continue
            path = self._adjacent_path(me, pos)
            if not path:
                continue
            trials, learned_value, uncertainty, status = (
                self.mind.action_knowledge(me.held_object, object_id, "USE")
            )
            novelty = 1.0 / math.sqrt(
                1.0 + self.mind.encounter_counts.get(object_id, 0)
            )
            falsification = 0.8 if status == "tentative" and trials <= 3 else 0.0
            known_food = max(0.0, learned_value) * (1.0 + 2.5 * hunger)
            cache_food = (
                2.5 * hunger
                if object_id in personally_known_food
                else 1.5 * hunger * self.mind.testimony_food_value(object_id)
            )
            chain_bonus = (
                3.0 * hunger / chain_step[2]
                if chain_step
                and chain_step[0] == "USE"
                and chain_step[1] == object_id
                else 0.0
            )
            score = (
                known_food
                + cache_food
                + chain_bonus
                + self.args.curiosity_weight * uncertainty
                + self.args.novelty_weight * novelty
                + self.args.falsification_weight * falsification
                - 0.025 * distance
                - self.args.repetition_penalty * trials
                - (0.8 if pos in list(self.position_history)[-4:] else 0.0)
                + self.mind.rng.random() * self.args.choice_noise
            )
            proposals.append(
                ActionProposal(
                    "USE", score,
                    f"value={learned_value:.2f} uncertainty={uncertainty:.2f} "
                    f"novelty={novelty:.2f} food={cache_food:.2f} "
                    f"chain={chain_bonus:.2f} "
                    f"trials={trials}",
                    pos[0], pos[1], object_id, path,
                )
            )

        # Using a held item on self is just another falsifiable experiment.
        if me.held_object > 0:
            trials, value, uncertainty, status = self.mind.action_knowledge(
                me.held_object, -1, "SELF"
            )
            # A newly acquired unknown item gets one fair self-use experiment.
            # This schedules exploration; it does not assume the item is food.
            first_self_test = (
                self.args.first_self_test_bonus if trials == 0 else 0.0
            )
            if (
                trials == 0
                or value > 0
                or self.mind.testimony_food_value(me.held_object) > 0
                or (chain_step and chain_step[0] == "SELF")
            ):
                proposals.append(ActionProposal(
                    "SELF",
                    first_self_test
                    + max(0.0, value) * (1.0 + 4.0 * hunger)
                    + 1.25 * hunger
                    * self.mind.testimony_food_value(me.held_object)
                    + (
                        3.0 * hunger / chain_step[2]
                        if chain_step and chain_step[0] == "SELF" else 0.0
                    )
                    + self.args.curiosity_weight * uncertainty
                    + (
                        self.args.falsification_weight
                        if status == "tentative" and trials <= 3 else 0
                    )
                    - self.args.repetition_penalty * max(0, trials - 3)
                    + self.mind.rng.random() * self.args.choice_noise,
                    f"first_test={first_self_test:.2f} hunger={hunger:.2f} "
                    f"value={value:.2f} "
                    f"uncertainty={uncertainty:.2f} trials={trials}",
                    me.x, me.y, -1,
                ))
            # Dropping prevents a useless held object from freezing exploration.
            empty_neighbors = [
                (me.x + dx, me.y + dy)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if self.world.get((me.x + dx, me.y + dy), -1) == 0
            ]
            if empty_neighbors:
                dx, dy = self.mind.rng.choice(empty_neighbors)
                trials, value, uncertainty, status = self.mind.action_knowledge(
                    me.held_object, 0, "DROP"
                )
                self_trials, self_value, _, _ = self.mind.action_knowledge(
                    me.held_object, -1, "SELF"
                )
                # Releasing an item is especially useful after the agent has
                # personally tested it and found no benefit.  This is learned
                # from the outcome, not from the object's identity.
                release_bonus = (
                    2.25 if self_trials > 0 and self_value <= 0 else 0.0
                )
                requested_by = next(
                    (
                        requester
                        for requester, request in self.peer_requests.items()
                        if request[0] == me.held_object
                        and math.hypot(request[1] - me.x, request[2] - me.y) <= 2
                    ),
                    None,
                )
                delivery_bonus = 7.0 if requested_by is not None else 0.0
                cache_bonus = (
                    4.0
                    if (
                        me.held_object in personally_known_food
                        and self.home_location is not None
                        and abs(me.x - self.home_location[0])
                        + abs(me.y - self.home_location[1]) <= 1
                        and hunger < self.args.cache_max_hunger
                    )
                    else 0.0
                )
                proposals.append(
                    ActionProposal(
                        "DROP",
                        delivery_bonus + cache_bonus + release_bonus
                        + value + 0.35 * uncertainty
                        + self.mind.rng.random() * self.args.choice_noise,
                        f"delivery={delivery_bonus:.2f} cache={cache_bonus:.2f} "
                        f"release={release_bonus:.2f} value={value:.2f} "
                        f"uncertainty={uncertainty:.2f} trials={trials}",
                        dx, dy, 0,
                    )
                )

            for requester, request in self.peer_requests.items():
                object_id, request_x, request_y, _ = request
                if object_id != me.held_object:
                    continue
                distance = abs(request_x - me.x) + abs(request_y - me.y)
                if distance <= 2:
                    continue
                path = self._adjacent_path(me, (request_x, request_y))
                if len(path) > 1:
                    proposals.append(ActionProposal(
                        "DELIVER", 8.0 - 0.02 * distance,
                        f"answer request from player {requester}",
                        request_x, request_y, requester, path,
                    ))

            if (
                me.held_object in personally_known_food
                and self.home_location is not None
                and hunger < self.args.cache_max_hunger
            ):
                distance = abs(me.x - self.home_location[0]) + abs(
                    me.y - self.home_location[1]
                )
                if distance > 1:
                    path = self._adjacent_path(me, self.home_location)
                    if len(path) > 1:
                        proposals.append(ActionProposal(
                            "RETURN_HOME", 5.5 - 0.02 * distance,
                            "carry personally verified food to shared cache",
                            self.home_location[0], self.home_location[1],
                            me.held_object, path,
                        ))

        # Movement explores the boundary of the individually observed map.
        frontier = []
        for pos, object_id in self.world.items():
            if object_id != 0:
                continue
            unseen = sum(
                (pos[0] + dx, pos[1] + dy) not in self.world
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            )
            if unseen:
                path = grid_path(position, {pos}, self.world)
                if len(path) > 1:
                    goal = path[min(len(path), self.args.max_path_steps + 1) - 1]
                    if not self.destination_available(goal, now):
                        continue
                    frontier.append((unseen, len(path), pos, path))
        if frontier:
            unseen, distance, pos, path = max(
                frontier,
                key=lambda item: (
                    item[0] * self.args.novelty_weight - 0.02 * item[1]
                    + self.mind.rng.random() * self.args.choice_noise
                ),
            )
            proposals.append(
                ActionProposal(
                    "MOVE",
                    self.args.novelty_weight * unseen - 0.02 * distance
                    + movement_drive
                    + self.mind.rng.random() * self.args.choice_noise,
                    f"frontier_unseen={unseen} movement_drive={movement_drive:.2f}",
                    pos[0], pos[1], path=path,
                )
            )

        # Social contact is an experiment like any other.  There is no
        # "stay together" rule: approach is retained only if privately learned
        # social value plus remaining uncertainty beats other actions.
        for peer in self.players.values():
            if peer.player_id == self.our_id:
                continue
            distance = abs(peer.x - me.x) + abs(peer.y - me.y)
            if distance <= 1 or distance > self.args.social_search_radius:
                continue
            path = self._adjacent_path(me, (peer.x, peer.y))
            if len(path) < 2:
                continue
            trials, value, uncertainty = self.mind.social_knowledge([peer.player_id])
            score = (
                self.args.social_weight * max(-1.0, value)
                + self.args.social_exploration_weight * uncertainty
                + (5.0 if self.pending_utterances else 0.0)
                - 0.02 * distance
                + self.mind.rng.random() * self.args.choice_noise
            )
            proposals.append(ActionProposal(
                "APPROACH", score,
                f"peer={peer.player_id} learned_social={value:.2f} "
                f"uncertainty={uncertainty:.2f} trials={trials}",
                peer.x, peer.y, peer.player_id, path,
            ))

        listener_nearby = any(
            p.player_id != self.our_id
            and math.hypot(p.x - me.x, p.y - me.y) <= self.args.language_radius
            for p in self.players.values()
        )
        if (
            self.pending_utterances
            and not listener_nearby
            and now - self.last_speech_wait_log
            >= self.args.speech_wait_log_interval
        ):
            nearest = min(
                (
                    math.hypot(p.x - me.x, p.y - me.y)
                    for p in self.players.values()
                    if p.player_id != self.our_id
                ),
                default=math.inf,
            )
            nearest_text = "none visible" if math.isinf(nearest) else f"{nearest:.1f}"
            self.log(
                f"speech waiting: {self.pending_utterances[0]}; "
                f"nearest listener distance={nearest_text}"
            )
            self.last_speech_wait_log = now
        conversation_ready = (
            now - self.last_conversation_at >= self.args.conversation_interval
        )
        if self.pending_utterances and listener_nearby:
            utterance = self.pending_utterances[0]
            urgent = utterance.startswith(("NEED ", "HAVE "))
            if urgent or conversation_ready:
                proposals.append(
                    ActionProposal(
                        "SAY",
                        10.0 if urgent else self.args.conversation_score,
                        (
                            "urgent request/response"
                            if urgent else "bounded conversation turn"
                        ),
                        utterance=utterance,
                    )
                )

        # A frontier-only movement bonus cannot free an agent whose frontier is
        # exhausted while local in-place experiments remain available.  After
        # a bounded stationary streak, inject a real dominant movement turn.
        if self.stationary_action_streak >= self.args.force_move_after:
            recent = set(list(self.position_history)[-5:])
            forced_candidates: list[
                tuple[int, tuple[int, int], list[tuple[int, int]]]
            ] = []
            for pos, object_id in self.world.items():
                if object_id != 0 or pos == position or pos in recent:
                    continue
                if self.blocked_until.get(pos, 0.0) > now:
                    continue
                path = grid_path(position, {pos}, self.world)
                if len(path) > 1:
                    goal = path[min(
                        len(path), self.args.max_path_steps + 1
                    ) - 1]
                    if self.destination_available(goal, now):
                        forced_candidates.append((len(path), pos, path))
            if forced_candidates:
                _, pos, path = self.mind.rng.choice(
                    sorted(forced_candidates, reverse=True)[:12]
                )
                proposals.append(ActionProposal(
                    "ROAM", self.args.force_move_score,
                    f"forced after {self.stationary_action_streak} "
                    "stationary actions",
                    pos[0], pos[1], path=path,
                ))
            else:
                directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
                for offset in range(4):
                    dx, dy = directions[(self.index - 1 + offset) % 4]
                    destination = (me.x + dx, me.y + dy)
                    if (
                        self.blocked_until.get(destination, 0.0) <= now
                        and self.destination_available(destination, now)
                    ):
                        proposals.append(ActionProposal(
                            "WANDER", self.args.force_move_score,
                            f"forced adjacent probe after "
                            f"{self.stationary_action_streak} stationary actions",
                            destination[0], destination[1],
                            path=[position, destination],
                        ))
                        break

        # Once the visible frontier has been exhausted, keep behaving instead
        # of idling.  Roaming selects a reachable, relatively unrecent empty
        # location from the agent's own map and can expose new interaction and
        # communication opportunities.
        if not proposals:
            recent = set(list(self.position_history)[-5:])
            roam_candidates: list[tuple[int, tuple[int, int], list[tuple[int, int]]]] = []
            for pos, object_id in self.world.items():
                if object_id != 0 or pos == position or pos in recent:
                    continue
                path = grid_path(position, {pos}, self.world)
                if len(path) > 1:
                    roam_candidates.append((len(path), pos, path))
            if roam_candidates:
                _, pos, path = self.mind.rng.choice(
                    sorted(roam_candidates, reverse=True)[:12]
                )
                proposals.append(
                    ActionProposal(
                        "ROAM", 0.25, "no frontier/action; seek new context",
                        pos[0], pos[1], path=path,
                    )
                )
            else:
                # A newly connected agent may know only its current tile.  Try
                # one orthogonal probe instead of silently standing forever.
                directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
                for offset in range(4):
                    dx, dy = directions[(self.index - 1 + offset) % 4]
                    destination = (me.x + dx, me.y + dy)
                    if self.blocked_until.get(destination, 0.0) <= now:
                        if not self.destination_available(destination, now):
                            continue
                        proposals.append(ActionProposal(
                            "WANDER", 0.20,
                            "no reachable proposal; probe adjacent tile",
                            destination[0], destination[1],
                            path=[position, destination],
                        ))
                        break
                        break
        return proposals

    def autonomy_step(self, sock: socket.socket, now: float) -> bool:
        me = self.players.get(self.our_id) if self.our_id else None
        if me is None or now - self.last_action_at < self.args.action_interval:
            if me is None and now - self.last_liveness_log >= 10.0:
                self.log(
                    "waiting: no self player update yet"
                    if self.our_id is None
                    else f"waiting: player {self.our_id} absent from current view"
                )
                self.last_liveness_log = now
            return False

        if (
            self.identity_seen_at is not None
            and now - self.identity_seen_at < self.args.startup_group_wait
        ):
            if not self.startup_wait_logged:
                self.log(
                    f"waiting {self.args.startup_group_wait:g}s for peer "
                    "visibility before first decision"
                )
                self.startup_wait_logged = True
            return False

        position = (me.x, me.y)
        self.position_history.append(position)

        if self.motion:
            motion = self.motion
            if position != motion.last_position:
                motion.last_position = position
                motion.last_progress_at = now
            intended_goal = (
                motion.proposal.target_x, motion.proposal.target_y
            )
            interaction_arrived = (
                motion.proposal.kind == "APPROACH_OBJECT"
                and abs(position[0] - intended_goal[0])
                + abs(position[1] - intended_goal[1]) <= 1
            )
            arrived = position == motion.commanded_goal or interaction_arrived
            if arrived:
                self.log(f"movement confirmed at {position}")
                self.release_destination(motion.commanded_goal)
                self.stationary_action_streak = 0
                self.motion = None
                queued = self.queued_action
                self.queued_action = None
                if queued is not None and interaction_arrived:
                    target_before = self.world.get(
                        (queued.target_x, queued.target_y), queued.target_id
                    )
                    self.send(
                        sock,
                        f"USE {queued.target_x} {queued.target_y} "
                        f"{queued.target_id}#",
                    )
                    self.pending_trial = ActionTrial(
                        "USE", queued.target_id, queued.target_x, queued.target_y,
                        me.held_object, target_before, self.food_store, now,
                    )
                    self.last_action_at = now
                    return True
            elif now - motion.last_progress_at >= self.args.no_progress_timeout:
                self.release_destination(motion.commanded_goal)
                self.blocked_until[intended_goal] = now + self.args.blocked_cooldown
                self.log(
                    f"movement stalled; avoiding {intended_goal} temporarily"
                )
                self.motion = None
                self.queued_action = None
            elif now - motion.started_at >= self.args.move_timeout:
                self.release_destination(motion.commanded_goal)
                self.blocked_until[intended_goal] = now + self.args.blocked_cooldown
                self.log(
                    f"movement timed out; avoiding {intended_goal} temporarily"
                )
                self.motion = None
                self.queued_action = None
            else:
                return False

        if self.pending_trial and now - self.pending_trial.started_at >= 1.5:
            trial = self.pending_trial
            learned, conjecture, outcome, reward = self.mind.observe_action_result(
                trial.action, trial.target_id, trial.held_before, me.held_object,
                trial.target_before,
                (
                    trial.target_before
                    if trial.action == "SELF"
                    else self.world.get(
                        (trial.x, trial.y), trial.target_before
                    )
                ),
                trial.food_before, self.food_store,
            )
            self.log(
                f"experience {trial.action} context=(held {trial.held_before}, "
                f"target {trial.target_before}) -> {outcome}; reward={reward:.2f}, "
                f"Skinnerian value={learned.value:.2f}, "
                f"Popperian={conjecture.status}"
            )
            self.mind.reinforce_social_context(
                self.nearby_peer_ids(me), reward
            )
            communicated_object = (
                me.held_object if me.held_object > 0 else trial.held_before
            )
            if communicated_object > 0:
                token, _ = self.mind.word_for_object(communicated_object)
                if me.held_object > 0 and trial.held_before != me.held_object:
                    if (
                        token not in self.pending_utterances
                        and now - self.last_spoken.get(token, -math.inf)
                        >= self.args.teach_interval
                    ):
                        self.pending_utterances.append(token)
                        self.log(f"queued {token} for grounded communication")
                if (
                    trial.action == "SELF"
                    and trial.food_before is not None
                    and self.food_store is not None
                    and self.food_store > trial.food_before
                ):
                    claim = f"{token} FOOD"
                    if (
                        claim not in self.pending_utterances
                        and now - self.last_spoken.get(claim, -math.inf)
                        >= self.args.teach_interval
                    ):
                        self.pending_utterances.append(claim)
                        self.log(
                            f"queued {claim} after personally observed "
                            "hunger gain"
                        )
            if trial.action == "DROP":
                # Do not immediately reacquire the object just released.
                self.blocked_until[(trial.x, trial.y)] = (
                    now + self.args.dropped_object_cooldown
                )
            self.pending_trial = None
        if self.pending_trial:
            return False

        proposals = self.propose_actions(me, now)
        if not proposals:
            return False
        chosen = max(proposals, key=lambda proposal: proposal.score)
        self.log(
            f"chose {chosen.kind} score={chosen.score:.2f}: {chosen.reason}"
        )
        if chosen.kind in (
            "MOVE", "ROAM", "DISPERSE", "WANDER", "DELIVER", "RETURN_HOME"
        ):
            acted = self.begin_motion(sock, chosen, now)
        elif chosen.kind == "APPROACH":
            acted = self.begin_motion(sock, chosen, now)
        elif chosen.kind == "SAY":
            self.send(sock, f"SAY 0 0 {chosen.utterance}#")
            self.last_spoken[chosen.utterance] = now
            self.last_conversation_at = now
            self.taught_utterances.add(chosen.utterance)
            if (
                self.pending_utterances
                and self.pending_utterances[0] == chosen.utterance
            ):
                self.pending_utterances.popleft()
            self.log(f"said {chosen.utterance}")
            acted = True
        else:
            if chosen.kind == "USE" and len(chosen.path) > 1:
                move = ActionProposal(
                    "APPROACH_OBJECT", chosen.score, chosen.reason,
                    chosen.target_x, chosen.target_y, chosen.target_id, chosen.path,
                )
                acted = self.begin_motion(sock, move, now, queued=chosen)
            else:
                if chosen.kind == "USE":
                    message = (
                        f"USE {chosen.target_x} {chosen.target_y} "
                        f"{chosen.target_id}#"
                    )
                elif chosen.kind == "SELF":
                    message = f"SELF {me.x} {me.y} -1#"
                else:
                    message = f"DROP {chosen.target_x} {chosen.target_y} -1#"
                self.send(sock, message)
                # SELF has a semantic target of -1.  M9 replaced this with the
                # map value under the player (normally zero), so learned
                # results were stored under target:0 while scoring queried
                # target:-1.  Every SELF was consequently mistaken for the
                # first test forever.
                target_before = (
                    -1
                    if chosen.kind == "SELF"
                    else self.world.get(
                        (chosen.target_x, chosen.target_y), chosen.target_id
                    )
                )
                self.pending_trial = ActionTrial(
                    chosen.kind, chosen.target_id, chosen.target_x,
                    chosen.target_y, me.held_object, target_before,
                    self.food_store, now,
                )
                acted = True
        if acted:
            self.last_action_at = now
            if chosen.kind not in (
                "MOVE", "ROAM", "DISPERSE", "WANDER", "DELIVER",
                "RETURN_HOME", "APPROACH"
            ):
                self.stationary_action_streak += 1
        return acted

    def handle_ps(self, message: str) -> None:
        if self.our_id is None:
            return
        me = self.players.get(self.our_id)
        if me is None:
            return
        for speaker_id, text in parse_player_speech(message):
            if speaker_id == self.our_id:
                continue
            if text == "HOME HERE":
                speaker = self.players.get(speaker_id)
                if speaker is not None:
                    distance = math.hypot(speaker.x - me.x, speaker.y - me.y)
                    if distance <= self.args.language_radius:
                        if self.home_location is None:
                            self.home_location = (speaker.x, speaker.y)
                            self.home_source = speaker_id
                            self.log(
                                f"adopted HOME at {self.home_location} "
                                f"from player {speaker_id}"
                            )
                        if not self.home_announced:
                            self.pending_utterances.append("HOME HERE")
                            self.home_announced = True
                continue
            social = re.fullmatch(r"(NEED|HAVE) ([A-Z]{2,8})", text)
            if social:
                act, token = social.groups()
                speaker = self.players.get(speaker_id)
                object_id = self.mind.inferred_referent(token)
                if speaker is None or object_id is None:
                    continue
                if (
                    math.hypot(speaker.x - me.x, speaker.y - me.y)
                    > self.args.language_radius
                ):
                    continue
                if act == "NEED":
                    self.peer_requests[speaker_id] = (
                        object_id, speaker.x, speaker.y, time.monotonic()
                    )
                    self.log(
                        f"understood NEED {token} from player {speaker_id}; "
                        f"object={object_id}"
                    )
                    if me.held_object == object_id:
                        reply = f"HAVE {token}"
                        if reply not in self.pending_utterances:
                            self.pending_utterances.appendleft(reply)
                else:
                    self.log(
                        f"heard HAVE {token} from player {speaker_id}; "
                        f"object={object_id}"
                    )
                continue
            match = re.fullmatch(r"([A-Z]{2,8})(?: (FOOD))?", text)
            if not match:
                continue
            speaker = self.players.get(speaker_id)
            if speaker is None:
                continue
            distance = math.hypot(speaker.x - me.x, speaker.y - me.y)
            if distance > self.args.language_radius:
                continue
            token, claim = match.groups()
            grounded_object = (
                speaker.held_object if speaker.held_object > 0
                else self.mind.inferred_referent(token)
            )
            if grounded_object is None:
                continue
            if claim == "FOOD":
                hypothesis = self.mind.hear_food_testimony(
                    token, grounded_object, speaker_id
                )
            else:
                if speaker.held_object <= 0:
                    continue
                hypothesis = self.mind.hear_demonstration(
                    token, grounded_object, speaker_id
                )
            # Information received while co-present is a small experienced
            # social benefit; whether it outweighs solitary exploration is learned.
            self.mind.reinforce_social_context([speaker_id], 0.15)
            self.log(
                f"heard {text} while player {speaker_id} held "
                f"object {grounded_object}: {hypothesis.status} "
                f"confidence={hypothesis.confidence:.2f}; usable word="
                f"{self.mind.word_for_object(grounded_object)[0]}"
            )

    def run(self) -> None:
        life = 0
        while not self.stop.is_set():
            reader = ProtocolReader()
            accepted = False
            accepted_at = 0.0
            last_sent = time.monotonic()
            self.players.clear()
            self.world.clear()
            self.our_id = None
            self.pending_trial = None
            self.motion = None
            self.queued_action = None
            self.position_history.clear()
            self.blocked_until.clear()
            self.food_store = None
            self.food_capacity = None
            try:
                with socket.create_connection(
                    (self.args.server, self.args.port), timeout=10
                ) as sock:
                    sock.setblocking(False)
                    life += 1
                    self.begin_new_life()
                    self.log("TCP connected" if life == 1 else f"reconnected for life {life}")
                    while not self.stop.is_set():
                        readable, _, _ = select.select([sock], [], [], 0.25)
                        if readable:
                            data = sock.recv(65536)
                            if not data:
                                raise RuntimeError("life ended/server closed connection")
                            for message in reader.feed(data):
                                if isinstance(message, MapChunk):
                                    self.handle_map_chunk(message)
                                    continue
                                kind = message_kind(message)
                                if kind == "SN":
                                    self.send(
                                        sock,
                                        build_login(
                                            message, self.email, self.account_key,
                                            self.server_password, self.args.client_tag,
                                            self.args.tutorial,
                                        ),
                                    )
                                    last_sent = time.monotonic()
                                elif kind == "ACCEPTED":
                                    accepted = True
                                    accepted_at = time.monotonic()
                                    self.log("login accepted")
                                elif kind == "REJECTED":
                                    raise RuntimeError("login rejected")
                                elif kind == "PU":
                                    self.handle_pu(message)
                                elif kind == "PS":
                                    self.handle_ps(message)
                                elif kind == "MX":
                                    self.handle_mx(message)
                                elif kind == "FX":
                                    food = parse_food_change(message)
                                    if food is not None:
                                        self.food_store, self.food_capacity = food

                        now = time.monotonic()
                        if accepted and self.autonomy_step(sock, now):
                            last_sent = now
                        if accepted and now - last_sent >= 15:
                            self.send(sock, "KA 0 0#")
                            last_sent = now
                        if accepted and now - accepted_at > 15 and self.our_id is None:
                            self.log("warning: no player identity found in PU messages")
                            accepted_at = now
                    if accepted:
                        # Closing TCP is OneLife's voluntary disconnect.  The
                        # M8 server patch removes headless avatars on this event.
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                        self.log("connection closed; server removing headless body")
            except Exception as exc:
                if self.stop.is_set():
                    break
                self.log(f"{exc}; respawning in {self.args.respawn_delay:g}s")
                if self.stop.wait(self.args.respawn_delay):
                    break
        self.mind.save()
        self.result = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run open-ended private expectation-learning OneLife agents."
    )
    parser.add_argument("--server", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8005)
    parser.add_argument("--settings", default="gameSource/settings")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--stagger", type=float, default=2.0)
    parser.add_argument("--respawn-delay", type=float, default=2.0)
    parser.add_argument("--teach-interval", type=float, default=12.0)
    parser.add_argument("--language-radius", type=float, default=8.0)
    parser.add_argument("--action-interval", type=float, default=2.5)
    parser.add_argument("--search-radius", type=int, default=12)
    parser.add_argument("--max-path-steps", type=int, default=8)
    parser.add_argument("--curiosity-weight", type=float, default=1.0)
    parser.add_argument("--novelty-weight", type=float, default=0.65)
    parser.add_argument("--falsification-weight", type=float, default=0.8)
    parser.add_argument("--social-weight", type=float, default=0.55)
    parser.add_argument("--social-exploration-weight", type=float, default=0.45)
    parser.add_argument("--social-radius", type=float, default=8.0)
    parser.add_argument("--social-search-radius", type=float, default=24.0)
    parser.add_argument("--no-progress-timeout", type=float, default=5.0)
    parser.add_argument("--move-timeout", type=float, default=14.0)
    parser.add_argument("--blocked-cooldown", type=float, default=30.0)
    parser.add_argument("--dropped-object-cooldown", type=float, default=90.0)
    parser.add_argument("--request-hunger", type=float, default=0.55)
    parser.add_argument("--request-interval", type=float, default=20.0)
    parser.add_argument("--request-ttl", type=float, default=45.0)
    parser.add_argument("--cache-max-hunger", type=float, default=0.40)
    parser.add_argument("--choice-noise", type=float, default=0.15)
    parser.add_argument("--repetition-penalty", type=float, default=0.12)
    parser.add_argument("--startup-group-wait", type=float, default=5.0)
    parser.add_argument("--movement-drive-step", type=float, default=0.75)
    parser.add_argument("--max-movement-drive", type=float, default=4.5)
    parser.add_argument("--ordinary-speech-score", type=float, default=1.25)
    parser.add_argument("--conversation-score", type=float, default=6.0)
    parser.add_argument("--conversation-interval", type=float, default=8.0)
    parser.add_argument("--speech-wait-log-interval", type=float, default=10.0)
    parser.add_argument("--force-move-after", type=int, default=3)
    parser.add_argument("--force-move-score", type=float, default=11.0)
    parser.add_argument(
        "--first-self-test-bonus", type=float, default=3.0,
        help="One-time exploration priority for SELF with an untested held item.",
    )
    parser.add_argument("--memory-dir", default="agent_memory")
    parser.add_argument("--client-tag", default="client_official")
    parser.add_argument("--tutorial", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count < 1 or args.count > 20:
        print("--count must be between 1 and 20", file=sys.stderr)
        return 2
    settings = Path(args.settings).expanduser().resolve()
    credentials = (
        read_setting(settings, "email"),
        read_setting(settings, "accountKey"),
        read_setting(settings, "serverPassword", "x"),
    )
    stop = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        print("\nStopping all agents...", flush=True)
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    sessions: list[AgentSession] = []
    print(
        f"Starting {args.count} open-ended expectation-learning agents. "
        f"Private memories: {args.memory_dir}/. Press Ctrl+C to stop.",
        flush=True,
    )
    for index in range(1, args.count + 1):
        session = AgentSession(index, args, credentials, stop)
        sessions.append(session)
        session.start()
        if index != args.count and stop.wait(args.stagger):
            break
    for session in sessions:
        session.join()
    return 0 if sessions and all(s.result == 0 for s in sessions) else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Open-ended OneLife agents with private expectations and grounded cooperation.

Milestone 26 (planning, society, and experiment controls):
* explicit temporal planning: expected value weighs immediate effect,
  discounted *learned* delayed effects, dependants, and information
  against effort, resources, and risk, so persistent investments become
  worthwhile only once their later pay-offs have been felt;
* delayed and persistent effects credited back to the acts that caused
  them, which is what makes infrastructure valuable without ever
  rewarding building as such;
* task selection with competence feedback, switching costs, and
  duplication avoidance, closing the specialization loop: doing a thing
  well makes doing it again cheaper, and roles appear with no labels;
* the full social model per agent -- kinship, familiarity, caregiving,
  cooperation, commitments kept and broken, competence, current task --
  feeding a mixed utility that puts self and dependants first, kin and
  trusted cooperators next, strangers last;
* the remaining structured messages: COMMIT, HELP, FOLLOW, AVOID, BRING;
* experiment controls: id randomization (--id-shuffle-seed), disabled
  communication (--no-communication), disabled observation
  (--no-observation), property-blind and prior-free ablations
  (--no-properties, --no-priors).

Milestone 25 (perception, generalization, development, place, role):
* visual perception derived from sprite pixels alone (never object
  names, recipes, or food data): appearances such as pointed, fibrous,
  stone-like, container, green, warm-coloured;
* uncertain general priors over appearances -- a sharp-looking thing may
  alter a fibrous one -- which prune the search the way a human player's
  physical intuition does, and which remain falsifiable conjectures;
* property-level expectations generalizing outcomes across object types,
  so learning transfers to objects never encountered;
* developmental stages (infant, child, adult, elder) from age alone:
  infants stay near adults where demonstrations happen, elders shift
  toward transmission before death;
* care for dependants: an adult offers what its own trials proved
  nourishing to a nearby infant, with no knowledge of what food is;
* learned location value, so places accumulate worth from food, comfort,
  company, infrastructure, and danger -- the basis for settlement;
* task competence tracking, from which specialization can emerge with no
  role labels anywhere in the architecture;
* structured per-life JSONL event logs for analysis.

Milestone 23 (reflective priorities): agents appraise their situation
from their own sensors and adopt an explicit, named priority mode --
SAFE, FEED, NEST, CRAFT, or LEARN -- that reweights the existing learned
score channels (never injecting game knowledge).  Urgency (threat,
hunger) is innate like pain; discretionary allocation is chosen by mode
weights the agent *reflects on* (each finished mode is credited against
the need it served) and that culture can shift ("WAY FEED GOOD"
endorsements through the shared trust ledger).  The Gregorian question
extends to what to care about next.

Milestone 21 (the Lexical Workspace: fully Gregorian reasoning):
* rules, food claims, and warnings are kept in token form even when
  ungrounded, so thought can run over words for things never perceived;
* symbolic chaining over token rules derives value for absent and
  unknown referents, generating WHAT/WHERE questions and journeys that
  follow spoken WAY directions, with informants verified on arrival;
* unrehearsed chains decay and idle contemplation rehearses them,
  extracts recipes, replays mistake narratives, and reconsiders habits:
  language literally sustains long predictive chains;
* taught recipes (TEACH <product> then ordered rules) carry plans
  deeper than any individual search; recipe steps guide action;
* harm is felt (involuntary held changes), witnessed (deaths), and
  attributed (movers); "<T> HURTS" installs graded, trust-weighted
  vetoes on acts never tried, softened only by desperation;
* peers' hand changes beside a lone candidate object are witnessed
  causal evidence: imitation, calibrated by the same trust ledger;
* mistakes become narratives, confessed as "MISTAKE <A> ON <B>"; a
  trusted correction demotes a settled belief and forces a re-test;
* habits of mind (VERIFY, TRUST, STAPLE, ASK, REHEARSE) are meta-
  conjectures credited by outcomes, falsified when they fail, endorsed
  as "WAY <HABIT> GOOD/BAD", and adopted from trusted endorsement: the
  agent learns, and is taught, how to think about what to think next;
* agents introduce themselves ("I AM <NAME>") and teach reputations
  ("<NAME> GOOD/BAD") through the shared trust ledger.

Milestone 20 (survival strategy: annealed exploration, commitment,
staples, unique identities):
* exploration terms are annealed by competence and hunger: an agent with
  a known food plan explores when safe and exploits when starving, while
  an ignorant agent keeps exploring because it must;
* frequently encountered but untested objects earn a staple bonus, so
  agents learn the abundant resources that sustain a life first;
* a short-lived committed goal adds hysteresis, so agents finish what
  they start instead of dithering between near-equal options;
* world identities are claimed through a shared registry so two runner
  threads can never adopt the same player id (an agent that did would
  watch another body forever and appear permanently stationary);
* a periodic status line makes every agent's position, food, and held
  object visible in the log.

Milestone 19 (emergent settlement: sensed comfort, earned help, liveness):
* agents measure their own hunger-drain intervals and associate slower
  drain with nearby objects, learning place quality (warmth, shelter)
  from experienced consequences rather than object identity;
* HOME is proposed where the proposer's own evidence (verified food,
  trusted testimony, learned comfort) supports it, with a patience
  fallback so the group never deadlocks;
* idle agents seek learned-comfort places, making resting near warmth
  an emergent behavior;
* a fulfilled NEED request credits the giver's reputation, so reliable
  helpers earn the trust that gates rule and food adoption;
* unsendable movement proposals are blocked and counted, so the stuck
  watchdog can always eventually fire instead of spinning silently.

Milestone 18 (instrumental planning, rule teaching, liveness watchdog):
* learned transitions gain instrumental value by propagating reward
  backward through the private causal graph, so crafting steps with no
  immediate food payoff become worth taking when they reliably lead to
  food later;
* corroborated causal rules are taught as "<A> ON <B> MAKES <C>" and
  heard as fallible, trust-weighted testimony that demands independent
  verification, exactly like Milestone 17 food claims;
* spontaneous world changes (decay, growth) are recorded as ambient
  transition expectations;
* a stuck watchdog escapes trapped positions by clearing stale blocks
  and probing adjacent tiles when no position change occurs for a long
  time despite issued movement.

Milestone 17 (calibrated Gregorian expectations):
* every speaker earns a private trust posterior from whether their food
  claims survive the listener's own tests;
* testimony value is claim evidence weighted by source trust;
* low-trust claims trigger independent falsification before reliance;
* failed verification is broadcast as "<TOKEN> BAD" so the group can
  correct false cultural knowledge, itself treated as fallible testimony;
* hungry agents travel back to the adopted HOME cache, completing the
  gather/request/give/cache/retrieve loop.

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


try:
    from visual_properties import (
        VisualPerception, prior_strength, GOAL_STATES, goal_satisfaction,
        production_candidates, wanted_ingredient_profiles, profile_match,
    )
except ImportError:  # running from another directory
    from open_ended_agents.visual_properties import (  # type: ignore
        VisualPerception, prior_strength, GOAL_STATES, goal_satisfaction,
        production_candidates, wanted_ingredient_profiles, profile_match,
    )


try:
    from hint_oracle import HintOracle
except ImportError:  # running from another directory
    from open_ended_agents.hint_oracle import HintOracle  # type: ignore


# The game's own hint sheet, treated as a source like any other
# so its influence stays measurable and its claims falsifiable.
HINT_SOURCE_ID = -2


LIFE_STAGES = ("infant", "child", "adult", "elder")


def life_stage(age: float) -> str:
    """Developmental stage from age alone (Module 8)."""
    if age < 3.0:
        return "infant"
    if age < 14.0:
        return "child"
    if age < 45.0:
        return "adult"
    return "elder"


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
    habit_tags: tuple = ()


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


MODE_NAMES = ("SAFE", "FEED", "NEST", "CRAFT", "LEARN")

# Multiplier profiles over the existing score channels.  LEARN is the
# neutral profile: reflective prioritization only ever *re-weights* the
# same learned quantities; it never injects game knowledge.
MODE_PROFILES: dict[str, dict[str, float]] = {
    "LEARN": {},
    "FEED": {"food": 1.5, "staple": 1.3, "lead": 1.6, "craft": 0.6,
             "recipe": 1.2, "explore": 0.5, "comfort": 0.3, "nest": 1.5},
    "SAFE": {"danger": 2.0, "social": 1.5, "explore": 0.3, "staple": 0.5,
             "craft": 0.5, "lead": 0.5, "verify": 0.5, "comfort": 0.8},
    "NEST": {"comfort": 1.8, "nest": 1.6, "food": 0.8, "staple": 0.7,
             "explore": 0.6, "craft": 0.9, "lead": 0.7, "verify": 0.8,
             "danger": 1.2},
    "CRAFT": {"craft": 1.7, "recipe": 1.7, "verify": 1.5, "explore": 0.8,
              "food": 0.8, "comfort": 0.6, "nest": 0.8},
}


def mode_factor(mode: str, channel: str) -> float:
    return MODE_PROFILES.get(mode, {}).get(channel, 1.0)


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
    habit_tags: tuple = ()


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
        # Per-speaker Beta evidence: how often did this speaker's food claims
        # survive my own tests?  Trust is earned, never assumed.
        self.source_trust: dict[int, dict[str, int]] = {}
        # Testified causal rules "<held> ON <target> MAKES <result>", stored
        # like food claims: fallible evidence awaiting my own verification.
        self.rule_testimony: dict[str, dict[str, Any]] = {}
        # Experienced hunger-drain intervals associated with nearby objects:
        # the agent's own sensor for warmth/shelter quality of places.
        self.comfort: dict[int, dict[str, float]] = {}
        # ---- The Lexical Workspace: knowledge held in token form ----
        # Rules kept even when tokens cannot yet be grounded, so thought can
        # run over words for things never perceived.
        self.token_rules: dict[str, dict[str, Any]] = {}
        self.token_food_claims: dict[str, dict[str, Any]] = {}
        self.token_danger_claims: dict[str, dict[str, Any]] = {}
        # Grounded danger: own harm experience plus trust-weighted warnings.
        self.danger: dict[int, dict[str, Any]] = {}
        # Chunked plans: ordered token-rule sequences, taught or self-derived.
        self.recipes: dict[str, dict[str, Any]] = {}
        # Habits of mind: named thinking policies held as meta-conjectures.
        self.habits: dict[str, dict[str, Any]] = {
            name: {"active": True, "helpful": 0, "failed": 0,
                   "endorse_conf": 0, "endorse_contra": 0, "sources": []}
            for name in ("VERIFY", "TRUST", "STAPLE", "ASK", "REHEARSE")
        }
        # Names read from the game's labels when hints are on.
        self.hint_words: dict[int, str] = {}
        # What has actually satisfied a wanted state (M28).
        self.goal_evidence: dict[str, dict[str, float]] = {}
        # Social memory (Module 11): a full belief record per known agent,
        # of which SourceTrust is the testimony-accuracy component.
        self.agent_beliefs: dict[str, dict[str, Any]] = {}
        # Delayed and persistent effects (Module 5): outcomes that arrive
        # after the act that caused them.
        self.delayed_effects: dict[str, dict[str, float]] = {}
        # Commitments heard from others (Module 13), used to avoid
        # duplicating work someone has already taken on.
        self.heard_commitments: dict[str, dict[str, float]] = {}
        # Property-level expectations (Module 3/4): what *appearances*
        # afford, so learning transfers to objects never seen before.
        self.property_expectations: dict[str, dict[str, Any]] = {}
        # Location value (Module 6): places accrue worth from outcomes.
        self.location_value: dict[str, dict[str, float]] = {}
        # Task competence (Module 13): repeated success lowers future cost,
        # from which specialization can emerge without role labels.
        self.competence: dict[str, dict[str, float]] = {}
        # Reflective priorities: drive modes held as meta-conjectures,
        # credited against the need each served, endorsable in speech.
        self.modes: dict[str, dict[str, Any]] = {
            name: {"helpful": 0, "failed": 0,
                   "endorse_conf": 0, "endorse_contra": 0, "sources": []}
            for name in MODE_NAMES
        }
        # Second-order language: names for speakers, enabling taught trust.
        self.person_names: dict[str, int] = {}
        # Mistakes as narratives: token-form episodes for later contemplation.
        self.narratives: list[dict[str, Any]] = []
        # Pairs flagged for priority re-testing after trusted correction.
        self.retest_pairs: set[str] = set()
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
        self.source_trust = {
            int(k): {"helpful": int(v.get("helpful", 0)),
                     "failed": int(v.get("failed", 0))}
            for k, v in data.get("source_trust", {}).items()
        }
        self.rule_testimony = {
            str(k): dict(v) for k, v in data.get("rule_testimony", {}).items()
        }
        self.comfort = {
            int(k): {"total": float(v.get("total", 0.0)),
                     "count": float(v.get("count", 0.0))}
            for k, v in data.get("comfort", {}).items()
        }
        self.token_rules = {
            str(k): dict(v) for k, v in data.get("token_rules", {}).items()
        }
        self.token_food_claims = {
            str(k): dict(v)
            for k, v in data.get("token_food_claims", {}).items()
        }
        self.token_danger_claims = {
            str(k): dict(v)
            for k, v in data.get("token_danger_claims", {}).items()
        }
        self.danger = {
            int(k): dict(v) for k, v in data.get("danger", {}).items()
        }
        self.recipes = {
            str(k): dict(v) for k, v in data.get("recipes", {}).items()
        }
        loaded_habits = data.get("habits", {})
        for name, record in loaded_habits.items():
            if name in self.habits:
                self.habits[name] = dict(record)
        self.hint_words = {
            int(k): str(v) for k, v in data.get("hint_words", {}).items()
        }
        self.goal_evidence = {
            str(k): dict(v) for k, v in data.get("goal_evidence", {}).items()
        }
        self.agent_beliefs = {
            str(k): dict(v) for k, v in data.get("agent_beliefs", {}).items()
        }
        self.delayed_effects = {
            str(k): dict(v)
            for k, v in data.get("delayed_effects", {}).items()
        }
        self.heard_commitments = {
            str(k): dict(v)
            for k, v in data.get("heard_commitments", {}).items()
        }
        self.property_expectations = {
            str(k): dict(v)
            for k, v in data.get("property_expectations", {}).items()
        }
        self.location_value = {
            str(k): dict(v) for k, v in data.get("location_value", {}).items()
        }
        self.competence = {
            str(k): dict(v) for k, v in data.get("competence", {}).items()
        }
        for name, record in data.get("modes", {}).items():
            if name in self.modes:
                self.modes[name] = dict(record)
        self.person_names = {
            str(k): int(v) for k, v in data.get("person_names", {}).items()
        }
        self.narratives = list(data.get("narratives", []))[-200:]
        self.retest_pairs = set(data.get("retest_pairs", []))
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
            "source_trust": {
                str(k): v for k, v in self.source_trust.items()
            },
            "rule_testimony": {
                str(k): v for k, v in self.rule_testimony.items()
            },
            "comfort": {
                str(k): v for k, v in self.comfort.items()
            },
            "token_rules": dict(self.token_rules),
            "token_food_claims": dict(self.token_food_claims),
            "token_danger_claims": dict(self.token_danger_claims),
            "danger": {str(k): v for k, v in self.danger.items()},
            "recipes": dict(self.recipes),
            "habits": dict(self.habits),
            "hint_words": {
                str(k): v for k, v in self.hint_words.items()
            },
            "goal_evidence": dict(self.goal_evidence),
            "agent_beliefs": dict(self.agent_beliefs),
            "delayed_effects": dict(self.delayed_effects),
            "heard_commitments": dict(self.heard_commitments),
            "property_expectations": dict(self.property_expectations),
            "location_value": dict(self.location_value),
            "competence": dict(self.competence),
            "modes": dict(self.modes),
            "person_names": dict(self.person_names),
            "narratives": self.narratives[-200:],
            "retest_pairs": sorted(self.retest_pairs),
            "episodes": self.episodes[-500:],
        }
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

    def _used_tokens(self) -> set[str]:
        return set(self.object_words.values()) | set(self.hypotheses)

    def invent_token(self) -> str:
        """Mint a fresh pronounceable token (used for self-naming)."""
        used = self._used_tokens() | set(self.person_names)
        for _ in range(500):
            token = self.rng.choice(self.SYLLABLES) + self.rng.choice(
                self.SYLLABLES
            )
            if token not in used:
                return token
        return f"NAME{self.rng.randrange(1000)}"

    def word_for_object(self, object_id: int) -> tuple[str, bool]:
        if object_id in self.object_words:
            return self.object_words[object_id], False
        # A name read off the game's own label, as a player reads
        # it on mouse-over: shared wording, not private synonyms.
        labelled = self.hint_words.get(object_id)
        if labelled:
            self.object_words[object_id] = labelled
            self.save()
            return labelled, False
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

    def trust_in(self, speaker_id: int) -> float:
        """Beta posterior that this speaker's claims survive my own tests."""
        record = self.source_trust.get(int(speaker_id))
        if not record:
            return 0.5
        helpful = int(record.get("helpful", 0))
        failed = int(record.get("failed", 0))
        return (helpful + 1) / (helpful + failed + 2)

    def testimony_claim_posterior(self, object_id: int) -> float:
        """Raw Beta posterior of the food claim, ignoring who said it."""
        claim = self.food_testimony.get(object_id)
        if not claim:
            return 0.0
        confirmations = int(claim.get("confirmations", 0))
        contradictions = int(claim.get("contradictions", 0))
        return (confirmations + 1) / (confirmations + contradictions + 2)

    def mean_source_trust(self, object_id: int) -> float:
        """Average earned trust across the claim's affirming sources."""
        claim = self.food_testimony.get(object_id)
        sources = list(claim.get("sources", [])) if claim else []
        if not sources:
            return 0.5
        return sum(self.trust_in(s) for s in sources) / len(sources)

    def testimony_food_value(self, object_id: int) -> float:
        """Trust-calibrated belief that a testified object is food.

        Claim evidence and source reliability are learned separately and
        multiplied here, so a well-supported claim from repeatedly wrong
        speakers is still discounted, and vice versa.
        """
        if object_id not in self.food_testimony:
            return 0.0
        return (
            self.testimony_claim_posterior(object_id)
            * self.mean_source_trust(object_id)
        )

    def hear_food_contradiction(
        self, token: str, object_id: int, speaker_id: int
    ) -> WordHypothesis:
        """Store a fallible denial ("<TOKEN> BAD") of a food claim."""
        hypothesis = self.hear_demonstration(token, object_id, speaker_id)
        claim = self.food_testimony.setdefault(
            object_id,
            {"confirmations": 0, "contradictions": 0, "sources": []},
        )
        claim["contradictions"] = int(claim.get("contradictions", 0)) + 1
        deniers = claim.setdefault("deniers", [])
        if speaker_id not in deniers:
            deniers.append(speaker_id)
        self._record(
            "hear_food_contradiction", token=token, object_id=object_id,
            speaker_id=speaker_id,
        )
        self.save()
        return hypothesis

    def record_testimony_outcome(
        self, object_id: int, verified: bool
    ) -> float:
        """Update the claim and every affirming source after my own test.

        This is the trust-gated falsification step: testimony only ever
        becomes reliable through the listener's independent verification,
        and each source's reputation is bound to that outcome.
        """
        claim = self.food_testimony.get(object_id)
        if not claim:
            return 0.5
        field_name = "confirmations" if verified else "contradictions"
        claim[field_name] = int(claim.get(field_name, 0)) + 1
        trust_key = "helpful" if verified else "failed"
        for speaker_id in claim.get("sources", []):
            record = self.source_trust.setdefault(
                int(speaker_id), {"helpful": 0, "failed": 0}
            )
            record[trust_key] = int(record.get(trust_key, 0)) + 1
        self._record(
            "testimony_outcome", object_id=object_id, verified=verified,
            mean_source_trust=self.mean_source_trust(object_id),
        )
        self.save()
        return self.mean_source_trust(object_id)

    def hear_rule_testimony(
        self, held_id: int, target_id: int, result_id: int, speaker_id: int
    ) -> None:
        """Store a testified causal rule as fallible, verifiable evidence."""
        key = f"{held_id}|{target_id}"
        claim = self.rule_testimony.setdefault(
            key,
            {"result": result_id, "confirmations": 0, "contradictions": 0,
             "sources": [], "deniers": []},
        )
        if int(claim.get("result", result_id)) == result_id:
            claim["confirmations"] = int(claim.get("confirmations", 0)) + 1
            if speaker_id not in claim["sources"]:
                claim["sources"].append(speaker_id)
        else:
            # A conflicting result claim is evidence against the stored rule,
            # not silent replacement of it.
            claim["contradictions"] = int(claim.get("contradictions", 0)) + 1
            deniers = claim.setdefault("deniers", [])
            if speaker_id not in deniers:
                deniers.append(speaker_id)
        self._record(
            "hear_rule", held_id=held_id, target_id=target_id,
            result_id=result_id, speaker_id=speaker_id,
        )
        self.save()

    def rule_claim_posterior(self, key: str) -> float:
        claim = self.rule_testimony.get(key)
        if not claim:
            return 0.0
        confirmations = int(claim.get("confirmations", 0))
        contradictions = int(claim.get("contradictions", 0))
        return (confirmations + 1) / (confirmations + contradictions + 2)

    def mean_rule_source_trust(self, key: str) -> float:
        claim = self.rule_testimony.get(key)
        sources = list(claim.get("sources", [])) if claim else []
        if not sources:
            return 0.5
        return sum(self.trust_in(s) for s in sources) / len(sources)

    def record_rule_outcome(self, key: str, verified: bool) -> float:
        """Bind every rule source's reputation to my own test of the rule."""
        claim = self.rule_testimony.get(key)
        if not claim:
            return 0.5
        field_name = "confirmations" if verified else "contradictions"
        claim[field_name] = int(claim.get(field_name, 0)) + 1
        trust_key = "helpful" if verified else "failed"
        for speaker_id in claim.get("sources", []):
            record = self.source_trust.setdefault(
                int(speaker_id), {"helpful": 0, "failed": 0}
            )
            record[trust_key] = int(record.get(trust_key, 0)) + 1
        self._record("rule_outcome", key=key, verified=verified)
        self.save()
        return self.mean_rule_source_trust(key)

    def instrumental_values(
        self, gamma: float = 0.9, iterations: int = 6
    ) -> dict[int, float]:
        """Propagate reward backward through the learned causal graph.

        A crafting step with no immediate food payoff earns derived value
        when non-falsified expectations connect its result, possibly over
        several steps, to a state that reliably produced reward.  This is
        planning over the agent's own conjectures, not over game data.
        """
        edge_pattern = re.compile(
            r"held:(-?\d+)\|target:(-?\d+)\|action:([A-Z]+)"
        )
        edges: dict[int, list[tuple[int, float, float]]] = {}
        for key, outcomes in self.transitions.items():
            match = edge_pattern.fullmatch(key)
            if not match:
                continue
            source = int(match.group(1))
            for expectation in outcomes.values():
                if expectation.status == "falsified":
                    continue
                held_match = re.search(
                    r"held:(-?\d+)", expectation.predicted_outcome
                )
                if not held_match:
                    continue
                edges.setdefault(source, []).append((
                    int(held_match.group(1)),
                    expectation.confidence,
                    expectation.mean_reward,
                ))
        values: dict[int, float] = {}
        for _ in range(iterations):
            updated: dict[int, float] = {}
            for source, outgoing in edges.items():
                best = 0.0
                for destination, confidence, reward in outgoing:
                    candidate = confidence * (
                        reward + gamma * values.get(destination, 0.0)
                    )
                    if candidate > best:
                        best = candidate
                updated[source] = best
            values = updated
        return values

    def predicted_next_held(
        self, held: int, target: int, action: str
    ) -> tuple[int, float] | None:
        """Best non-falsified prediction of the held state after an action."""
        outcomes = self.transitions.get(
            f"held:{held}|target:{target}|action:{action}"
        )
        if not outcomes:
            return None
        best = max(
            outcomes.values(),
            key=lambda value: (value.confidence, value.confirmations),
        )
        if best.status == "falsified":
            return None
        match = re.search(r"held:(-?\d+)", best.predicted_outcome)
        if not match:
            return None
        return int(match.group(1)), best.confidence

    def observe_ambient(self, old_id: int, new_id: int) -> None:
        """Record a spontaneous world change (decay/growth) as expectation."""
        key = f"ambient:{old_id}|action:TIME"
        outcome = f"target:{new_id}"
        outcomes = self.transitions.setdefault(key, {})
        expectation = outcomes.get(outcome)
        if expectation is None:
            expectation = TransitionExpectation(
                f"ambient:{old_id}", "TIME", outcome
            )
            outcomes[outcome] = expectation
        for candidate in outcomes.values():
            candidate.observe(outcome, 0.0)
        self._record("ambient_transition", old_id=old_id, new_id=new_id)
        self.save()

    def credit_warmth(self, object_ids: set[int]) -> None:
        """Slower hunger drain beside something is evidence it warms.

        This is how warmth becomes a knowable state without the agent
        ever being told what fire is: the drain measurements say so.
        """
        for object_id in object_ids:
            if self.comfort_value(object_id) > 0.15:
                self.note_goal_satisfied("warmth", object_id, 0.5)

    def observe_comfort(
        self, object_ids: set[int], drain_interval: float
    ) -> None:
        """Associate an experienced hunger-drain interval with nearby objects.

        Longer intervals mean slower starvation.  Objects that repeatedly
        co-occur with slow drain (fire, shelter) accumulate learned comfort
        without the agent ever being told what warmth is.
        """
        for object_id in object_ids:
            record = self.comfort.setdefault(
                int(object_id), {"total": 0.0, "count": 0.0}
            )
            record["total"] += float(drain_interval)
            record["count"] += 1.0
        self._record(
            "comfort_sample", interval=drain_interval,
            object_ids=sorted(int(o) for o in object_ids),
        )
        self.save()

    def comfort_value(self, object_id: int) -> float:
        """Relative learned comfort of an object versus overall experience."""
        record = self.comfort.get(int(object_id))
        if not record or record["count"] < 2:
            return 0.0
        total = sum(r["total"] for r in self.comfort.values())
        count = sum(r["count"] for r in self.comfort.values())
        if count <= 0 or total <= 0:
            return 0.0
        baseline = total / count
        mean = record["total"] / record["count"]
        return max(-1.0, min(1.0, mean / baseline - 1.0))

    # ---- Lexical Workspace: thought in token form ----

    def hear_token_rule(
        self, a_token: str, b_token: str, c_token: str, speaker_id: int,
        wall_now: float | None = None,
    ) -> None:
        """Store a rule in token form even when nothing grounds yet.

        This is the inner environment made of words: the agent can hold and
        chain over "FAPA ON ROKA MAKES BAK" without knowing what FAPA is.
        """
        key = f"{a_token}|{b_token}"
        record = self.token_rules.setdefault(
            key,
            {"result": c_token, "confirmations": 0, "contradictions": 0,
             "sources": [], "fresh": wall_now or time.time()},
        )
        if record.get("result") == c_token:
            record["confirmations"] = int(record.get("confirmations", 0)) + 1
            if speaker_id not in record["sources"]:
                record["sources"].append(speaker_id)
        else:
            record["contradictions"] = int(record.get("contradictions", 0)) + 1
        record["fresh"] = wall_now or time.time()
        self.save()

    def contradict_token_rule(self, a_token: str, b_token: str) -> None:
        record = self.token_rules.get(f"{a_token}|{b_token}")
        if record is not None:
            record["contradictions"] = int(record.get("contradictions", 0)) + 1
            self.save()

    def hear_token_food(self, token: str, speaker_id: int) -> None:
        claim = self.token_food_claims.setdefault(
            token, {"confirmations": 0, "contradictions": 0, "sources": []}
        )
        claim["confirmations"] = int(claim.get("confirmations", 0)) + 1
        if speaker_id not in claim["sources"]:
            claim["sources"].append(speaker_id)
        self.save()

    def note_danger_own(self, object_id: int, weight: float) -> None:
        record = self.danger.setdefault(
            int(object_id),
            {"own": 0.0, "confirmations": 0, "contradictions": 0,
             "sources": []},
        )
        record["own"] = float(record.get("own", 0.0)) + weight
        self._record("danger_experienced", object_id=object_id, weight=weight)
        self.save()

    def hear_danger_testimony(self, object_id: int, speaker_id: int) -> None:
        record = self.danger.setdefault(
            int(object_id),
            {"own": 0.0, "confirmations": 0, "contradictions": 0,
             "sources": []},
        )
        record["confirmations"] = int(record.get("confirmations", 0)) + 1
        if speaker_id not in record["sources"]:
            record["sources"].append(speaker_id)
        self.save()

    def hear_token_danger(self, token: str, speaker_id: int) -> None:
        claim = self.token_danger_claims.setdefault(
            token, {"confirmations": 0, "contradictions": 0, "sources": []}
        )
        claim["confirmations"] = int(claim.get("confirmations", 0)) + 1
        if speaker_id not in claim["sources"]:
            claim["sources"].append(speaker_id)
        self.save()

    def weaken_danger(self, object_id: int) -> None:
        """Surviving contact unharmed falsifies fear a step at a time."""
        record = self.danger.get(int(object_id))
        changed = False
        if record is not None:
            own = float(record.get("own", 0.0))
            if own > 0.0:
                record["own"] = own * 0.5 if own > 0.1 else 0.0
                changed = True
            if int(record.get("confirmations", 0)) > 0:
                record["contradictions"] = int(
                    record.get("contradictions", 0)
                ) + 1
                changed = True
        for token, claim in self.token_danger_claims.items():
            if self.inferred_referent(token) == object_id and int(
                claim.get("confirmations", 0)
            ) > 0:
                claim["contradictions"] = int(
                    claim.get("contradictions", 0)
                ) + 1
                changed = True
        if changed:
            self._record("danger_weakened", object_id=object_id)
            self.save()

    def danger_value(self, object_id: int) -> float:
        """Graded veto strength: own harm plus trust-weighted warnings."""
        token_component = 0.0
        for token, claim in self.token_danger_claims.items():
            if self.inferred_referent(token) == object_id:
                t_conf = int(claim.get("confirmations", 0))
                t_contra = int(claim.get("contradictions", 0))
                t_posterior = (t_conf + 1) / (t_conf + t_contra + 2)
                t_sources = claim.get("sources", [])
                t_trust = (
                    sum(self.trust_in(s) for s in t_sources) / len(t_sources)
                    if t_sources else 0.5
                )
                token_component = max(token_component, t_posterior * t_trust)
        record = self.danger.get(int(object_id))
        if record is None:
            return token_component
        own = min(1.0, float(record.get("own", 0.0)) / 2.0)
        confirmations = int(record.get("confirmations", 0))
        contradictions = int(record.get("contradictions", 0))
        testimony = 0.0
        if confirmations + contradictions > 0:
            posterior = (confirmations + 1) / (
                confirmations + contradictions + 2
            )
            sources = record.get("sources", [])
            trust = (
                sum(self.trust_in(s) for s in sources) / len(sources)
                if sources else 0.5
            )
            testimony = posterior * trust
        return max(own, testimony, token_component)

    def token_seed_value(self, token: str) -> float:
        """Immediate worth of a token: grounded food or spoken food claims."""
        claim = self.token_food_claims.get(token)
        claimed = 0.0
        if claim:
            claimed = (int(claim.get("confirmations", 0)) + 1) / (
                int(claim.get("confirmations", 0))
                + int(claim.get("contradictions", 0)) + 2
            )
        referent = self.inferred_referent(token)
        grounded = 0.0
        if referent is not None:
            if referent in self.known_food_objects():
                grounded = 1.0
            else:
                grounded = self.testimony_food_value(referent)
        return max(claimed, grounded)

    def decayed_rule_confidence(
        self, record: dict[str, Any], wall_now: float, halflife: float,
    ) -> float:
        """Unrehearsed chain links fade; rehearsal (refreshing) sustains them.

        This is the chess-notation clause made literal: without words being
        revisited, long predictive chains cannot be sustained.
        """
        confirmations = int(record.get("confirmations", 0))
        contradictions = int(record.get("contradictions", 0))
        posterior = (confirmations + 1) / (
            confirmations + contradictions + 2
        )
        age = max(0.0, wall_now - float(record.get("fresh", wall_now)))
        decay = max(0.2, 0.5 ** (age / max(1.0, halflife)))
        return posterior * decay

    def token_values(
        self, wall_now: float, halflife: float = 480.0, gamma: float = 0.85,
        iterations: int = 5,
    ) -> dict[str, float]:
        """Symbolic chaining over the workspace, ungrounded tokens included."""
        values: dict[str, float] = {}
        tokens: set[str] = set()
        for key, record in self.token_rules.items():
            a_token, b_token = key.split("|", 1)
            tokens.update((a_token, b_token, str(record.get("result"))))
        tokens.update(self.token_food_claims)
        for token in tokens:
            values[token] = 4.0 * self.token_seed_value(token)
        for _ in range(iterations):
            updated = dict(values)
            for key, record in self.token_rules.items():
                a_token, _ = key.split("|", 1)
                result = str(record.get("result"))
                confidence = self.decayed_rule_confidence(
                    record, wall_now, halflife
                )
                candidate = confidence * gamma * values.get(result, 0.0)
                if candidate > updated.get(a_token, 0.0):
                    updated[a_token] = candidate
            values = updated
        return values

    def add_narrative(self, kind: str, **details: Any) -> None:
        entry = {"kind": kind, "t": time.time()}
        entry.update(details)
        self.narratives.append(entry)
        self.narratives = self.narratives[-200:]
        self.save()

    def habit_factor(self, name: str) -> float:
        record = self.habits.get(name)
        return 1.0 if record and record.get("active", True) else 0.0

    def credit_habits(self, tags: tuple, success: bool) -> None:
        """Meta-level reinforcement: ways of thinking earn their keep."""
        key = "helpful" if success else "failed"
        for name in tags:
            record = self.habits.get(name)
            if record is not None:
                record[key] = int(record.get(key, 0)) + 1
        if tags:
            self.save()

    def hear_habit_endorsement(
        self, name: str, good: bool, speaker_id: int
    ) -> None:
        record = self.habits.get(name)
        if record is None:
            return
        key = "endorse_conf" if good else "endorse_contra"
        record[key] = int(record.get(key, 0)) + 1
        if speaker_id not in record["sources"]:
            record["sources"].append(speaker_id)
        self._record(
            "hear_habit", habit=name, good=good, speaker_id=speaker_id
        )
        self.save()

    def note_goal_satisfied(
        self, goal: str, object_id: int, amount: float = 1.0
    ) -> None:
        """This thing actually served the wanted state."""
        record = self.goal_evidence.setdefault(goal, {})
        key = str(int(object_id))
        record[key] = float(record.get(key, 0.0)) + amount
        self._record("goal_satisfied", goal=goal, object_id=object_id)
        self.save()

    def note_goal_failed(self, goal: str, object_id: int) -> None:
        record = self.goal_evidence.setdefault(goal, {})
        key = str(int(object_id))
        record[key] = float(record.get(key, 0.0)) - 0.5
        self.save()

    def learned_goal_value(self, goal: str, object_id: int) -> float:
        record = self.goal_evidence.get(goal, {})
        value = float(record.get(str(int(object_id)), 0.0))
        return max(-1.0, min(1.0, value / 3.0))

    def known_goal_objects(self, goal: str) -> list[int]:
        record = self.goal_evidence.get(goal, {})
        return [
            int(key) for key, value in record.items() if float(value) > 0.5
        ]

    def belief_about(self, player_id: int) -> dict[str, Any]:
        """Full social model of another agent (Module 11)."""
        return self.agent_beliefs.setdefault(
            str(int(player_id)),
            {"kinship": 0.0, "familiarity": 0.0, "caregiving": 0.0,
             "cooperation": 0.0, "commitments_kept": 0,
             "commitments_broken": 0, "competence": 0.0,
             "current_task": "", "danger_caused": 0.0},
        )

    def note_familiarity(self, player_id: int, amount: float = 0.05) -> None:
        belief = self.belief_about(player_id)
        belief["familiarity"] = min(
            1.0, float(belief.get("familiarity", 0.0)) + amount
        )

    def note_kinship(self, player_id: int, degree: float) -> None:
        belief = self.belief_about(player_id)
        belief["kinship"] = max(float(belief.get("kinship", 0.0)), degree)
        self.save()

    def note_caregiving(self, player_id: int, amount: float = 1.0) -> None:
        belief = self.belief_about(player_id)
        belief["caregiving"] = float(belief.get("caregiving", 0.0)) + amount
        self.save()

    def note_cooperation(self, player_id: int, amount: float = 1.0) -> None:
        belief = self.belief_about(player_id)
        belief["cooperation"] = float(belief.get("cooperation", 0.0)) + amount
        self.save()

    def note_commitment_outcome(self, player_id: int, kept: bool) -> None:
        belief = self.belief_about(player_id)
        key = "commitments_kept" if kept else "commitments_broken"
        belief[key] = int(belief.get(key, 0)) + 1
        record = self.source_trust.setdefault(
            int(player_id), {"helpful": 0, "failed": 0}
        )
        record["helpful" if kept else "failed"] = int(
            record.get("helpful" if kept else "failed", 0)
        ) + 1
        self.save()

    def note_danger_caused(self, player_id: int, amount: float = 1.0) -> None:
        belief = self.belief_about(player_id)
        belief["danger_caused"] = float(
            belief.get("danger_caused", 0.0)
        ) + amount
        record = self.source_trust.setdefault(
            int(player_id), {"helpful": 0, "failed": 0}
        )
        record["failed"] = int(record.get("failed", 0)) + 1
        self.save()

    def social_regard(self, player_id: int) -> float:
        """Mixed weighting of another agent (Module 14): self-interest
        first, then dependants and kin, then trusted group members."""
        belief = self.agent_beliefs.get(str(int(player_id)))
        if not belief:
            return 0.0
        return (
            0.5 * float(belief.get("kinship", 0.0))
            + 0.2 * min(1.0, float(belief.get("caregiving", 0.0)) / 3.0)
            + 0.2 * min(1.0, float(belief.get("cooperation", 0.0)) / 3.0)
            + 0.1 * float(belief.get("familiarity", 0.0))
        ) * (0.5 + self.trust_in(player_id))

    def note_commitment_heard(
        self, player_id: int, task: str, wall_now: float
    ) -> None:
        self.heard_commitments[task] = {
            "player": float(player_id), "at": wall_now,
        }
        self.belief_about(player_id)["current_task"] = task
        self.save()

    def task_is_taken(
        self, task: str, wall_now: float, ttl: float = 120.0
    ) -> bool:
        record = self.heard_commitments.get(task)
        if not record:
            return False
        return wall_now - float(record.get("at", 0.0)) <= ttl

    def note_delayed_effect(
        self, context: str, channel: str, amount: float
    ) -> None:
        """Effects that arrive later than the act (Module 5)."""
        record = self.delayed_effects.setdefault(context, {})
        record[channel] = float(record.get(channel, 0.0)) + amount
        record["samples"] = float(record.get("samples", 0.0)) + 1.0
        self.save()

    def delayed_value(self, context: str) -> float:
        record = self.delayed_effects.get(context)
        if not record:
            return 0.0
        samples = max(1.0, float(record.get("samples", 1.0)))
        return (
            float(record.get("comfort", 0.0))
            + float(record.get("food", 0.0))
            - float(record.get("danger", 0.0))
        ) / samples

    def note_property_outcome(
        self, actor_signature: tuple, target_signature: tuple,
        kind: str, success: bool,
    ) -> None:
        """Generalize an outcome to how things *looked* (Module 4)."""
        if not actor_signature and not target_signature:
            return
        key = f"{','.join(actor_signature)}|{','.join(target_signature)}|{kind}"
        record = self.property_expectations.setdefault(
            key, {"successes": 0, "failures": 0}
        )
        record["successes" if success else "failures"] = int(
            record.get("successes" if success else "failures", 0)
        ) + 1
        self.save()

    def property_confidence(
        self, actor_signature: tuple, target_signature: tuple, kind: str,
    ) -> tuple[float, int]:
        """Belief that this *kind* of appearance pairing pays off."""
        key = f"{','.join(actor_signature)}|{','.join(target_signature)}|{kind}"
        record = self.property_expectations.get(key)
        if not record:
            return 0.0, 0
        successes = int(record.get("successes", 0))
        failures = int(record.get("failures", 0))
        total = successes + failures
        if total == 0:
            return 0.0, 0
        return (successes + 1) / (total + 2), total

    def note_location_outcome(
        self, x: int, y: int, channel: str, amount: float,
        cell: int = 8,
    ) -> None:
        """Places accumulate value from what happens there (Module 6)."""
        key = f"{x // cell}:{y // cell}"
        record = self.location_value.setdefault(key, {})
        record[channel] = float(record.get(channel, 0.0)) + amount
        record["visits"] = float(record.get("visits", 0.0)) + 1.0
        self.save()

    def location_worth(self, x: int, y: int, cell: int = 8) -> float:
        record = self.location_value.get(f"{x // cell}:{y // cell}")
        if not record:
            return 0.0
        visits = max(1.0, float(record.get("visits", 1.0)))
        good = (
            float(record.get("food", 0.0))
            + float(record.get("comfort", 0.0))
            + 0.5 * float(record.get("infrastructure", 0.0))
            + 0.5 * float(record.get("company", 0.0))
        )
        bad = float(record.get("danger", 0.0))
        return (good - bad) / visits

    def note_task_outcome(self, task: str, success: bool) -> None:
        """Competence grows with repetition (Module 13)."""
        record = self.competence.setdefault(
            task, {"attempts": 0.0, "successes": 0.0}
        )
        record["attempts"] = float(record.get("attempts", 0.0)) + 1.0
        if success:
            record["successes"] = float(record.get("successes", 0.0)) + 1.0
        self.save()

    def task_competence(self, task: str) -> float:
        record = self.competence.get(task)
        if not record:
            return 0.0
        attempts = float(record.get("attempts", 0.0))
        if attempts <= 0:
            return 0.0
        rate = float(record.get("successes", 0.0)) / attempts
        experience = min(1.0, attempts / 12.0)
        return rate * experience

    def dominant_task(self) -> tuple[str, float]:
        best, best_value = "", 0.0
        for task in self.competence:
            value = self.task_competence(task)
            if value > best_value:
                best, best_value = task, value
        return best, best_value

    def credit_mode(self, name: str, success: bool) -> None:
        """Reflection: a priority mode is judged against the need it served."""
        record = self.modes.get(name)
        if record is None:
            return
        key = "helpful" if success else "failed"
        record[key] = int(record.get(key, 0)) + 1
        self._record("mode_credited", mode=name, success=success)
        self.save()

    def hear_mode_endorsement(
        self, name: str, good: bool, speaker_id: int
    ) -> None:
        record = self.modes.get(name)
        if record is None:
            return
        key = "endorse_conf" if good else "endorse_contra"
        record[key] = int(record.get(key, 0)) + 1
        if speaker_id not in record["sources"]:
            record["sources"].append(speaker_id)
        self._record("hear_mode", mode=name, good=good, speaker_id=speaker_id)
        self.save()

    def mode_weight(self, name: str) -> float:
        """Selection weight for a discretionary priority: own reflected
        experience blended with trust-weighted cultural endorsement."""
        record = self.modes.get(name)
        if record is None:
            return 0.5
        helpful = int(record.get("helpful", 0))
        failed = int(record.get("failed", 0))
        own = (helpful + 1) / (helpful + failed + 2)
        conf = int(record.get("endorse_conf", 0))
        contra = int(record.get("endorse_contra", 0))
        endorsed = (conf + 1) / (conf + contra + 2)
        sources = record.get("sources", [])
        trust = (
            sum(self.trust_in(s) for s in sources) / len(sources)
            if sources else 0.5
        )
        return 0.7 * own + 0.3 * endorsed * trust

    def demote_self_expectation(self, object_id: int) -> None:
        """A trusted correction reopens my own settled test."""
        outcomes = self.transitions.get(
            f"held:{object_id}|target:-1|action:SELF"
        )
        if not outcomes:
            return
        for expectation in outcomes.values():
            if expectation.status == "corroborated":
                expectation.status = "tentative"
                expectation.confirmations = min(1, expectation.confirmations)
        self.retest_pairs.add(f"{object_id}|-1")
        self._record("demoted_by_correction", object_id=object_id)
        self.save()

    def rehearse(self, wall_now: float, halflife: float) -> list[str]:
        """Contemplation: rehearse chains, extract recipes, replay mistakes,
        reconsider habits.  Returns habit endorsements worth teaching."""
        values = self.token_values(wall_now, halflife)
        ranked = sorted(
            self.token_rules.items(),
            key=lambda item: values.get(item[0].split("|", 1)[0], 0.0),
            reverse=True,
        )
        for key, record in ranked[:10]:
            record["fresh"] = wall_now
        # Self-derived recipes: chain token rules toward a food-valued token.
        for key, record in self.token_rules.items():
            a_token, b_token = key.split("|", 1)
            first_result = str(record.get("result"))
            if self.decayed_rule_confidence(record, wall_now, halflife) < 0.5:
                continue
            steps = [[a_token, b_token, first_result]]
            product = first_result
            for _ in range(3):
                extended = False
                for key2, record2 in self.token_rules.items():
                    a2, b2 = key2.split("|", 1)
                    if a2 != product:
                        continue
                    if self.decayed_rule_confidence(
                        record2, wall_now, halflife
                    ) < 0.5:
                        continue
                    steps.append([a2, b2, str(record2.get("result"))])
                    product = str(record2.get("result"))
                    extended = True
                    break
                if not extended:
                    break
            if len(steps) >= 2 and self.token_seed_value(product) > 0.3:
                existing = self.recipes.get(product)
                if existing is None or len(steps) < len(
                    existing.get("steps", steps)
                ):
                    self.recipes[product] = {
                        "steps": steps, "source": 0, "fresh": wall_now,
                    }
        # Replay: a mistake inexplicable then may be explicable now.
        for narrative in self.narratives[-30:]:
            if narrative.get("kind") != "falsified_use":
                continue
            a_token = narrative.get("a")
            b_token = narrative.get("b")
            record = self.token_rules.get(f"{a_token}|{b_token}")
            if record and self.decayed_rule_confidence(
                record, wall_now, halflife
            ) > 0.5:
                a_ref = (
                    0 if a_token == "HAND"
                    else self.inferred_referent(str(a_token))
                )
                b_ref = self.inferred_referent(str(b_token))
                if a_ref is not None and b_ref is not None:
                    self.retest_pairs.add(f"{a_ref}|{b_ref}")
        # Habit reconsideration: falsify losers, adopt endorsed conjectures.
        endorsements: list[str] = []
        for name, record in self.habits.items():
            helpful = int(record.get("helpful", 0))
            failed = int(record.get("failed", 0))
            if record.get("active", True) and failed >= 4 and                     failed > 2 * helpful:
                record["active"] = False
                self._record("habit_falsified", habit=name)
            elif not record.get("active", True):
                conf = int(record.get("endorse_conf", 0))
                contra = int(record.get("endorse_contra", 0))
                sources = record.get("sources", [])
                trust = (
                    sum(self.trust_in(s) for s in sources) / len(sources)
                    if sources else 0.5
                )
                posterior = (conf + 1) / (conf + contra + 2)
                if posterior * trust > 0.6:
                    record["active"] = True
                    record["helpful"] = 0
                    record["failed"] = 0
                    self._record("habit_adopted", habit=name)
            if record.get("active", True) and helpful - failed >= 3:
                endorsements.append(f"WAY {name} GOOD")
            elif not record.get("active", True) and failed - helpful >= 3:
                endorsements.append(f"WAY {name} BAD")
        for name, record in self.modes.items():
            helpful = int(record.get("helpful", 0))
            failed = int(record.get("failed", 0))
            if helpful - failed >= 3:
                endorsements.append(f"WAY {name} GOOD")
            elif failed - helpful >= 3:
                endorsements.append(f"WAY {name} BAD")
        self.save()
        return endorsements

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


_ID_SHUFFLE: dict[int, int] = {}
_ID_SHUFFLE_SEED = 0


def configure_id_shuffle(seed: int) -> None:
    """Control 2: deterministically remap the object ids an agent sees.

    The world is unchanged; only the labels the agent perceives are
    permuted.  An agent that memorized ids collapses; one that learned
    from appearances does not.
    """
    global _ID_SHUFFLE_SEED
    _ID_SHUFFLE_SEED = seed
    _ID_SHUFFLE.clear()


def shuffled_id(object_id: int) -> int:
    if _ID_SHUFFLE_SEED == 0 or object_id <= 0:
        return object_id
    mapped = _ID_SHUFFLE.get(object_id)
    if mapped is None:
        rng = random.Random(_ID_SHUFFLE_SEED * 1000003 + object_id)
        mapped = 100000 + rng.randrange(1, 899999)
        _ID_SHUFFLE[object_id] = mapped
    return mapped


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


class AgentTrackerFile:
    """Publishes agent positions for the game client's on-screen markers.

    Purely an observation aid: the file is written, never read back, and
    nothing in the agents' behaviour depends on it.
    """

    def __init__(self, path: str | None) -> None:
        self.path = Path(path) if path else None
        self.lock = threading.Lock()
        self.marks: dict[int, tuple[str, int, int, str]] = {}
        self.last_write = 0.0

    def update(
        self, index: int, label: str, x: int, y: int, note: str = "",
    ) -> None:
        if self.path is None:
            return
        with self.lock:
            self.marks[index] = (label, x, y, note)
            now = time.monotonic()
            if now - self.last_write < 0.5:
                return
            self.last_write = now
            lines = [
                f"{label} {mx} {my} {mnote}".rstrip()
                for label, mx, my, mnote in (
                    self.marks[key] for key in sorted(self.marks)
                )
            ]
            try:
                temporary = self.path.with_suffix(".tmp")
                temporary.write_text("\n".join(lines) + "\n",
                                     encoding="utf-8")
                temporary.replace(self.path)
            except OSError:
                pass

    def remove(self, index: int) -> None:
        if self.path is None:
            return
        with self.lock:
            self.marks.pop(index, None)


class AgentSession(threading.Thread):
    reservation_lock = threading.Lock()
    destination_reservations: dict[tuple[int, int], tuple[int, float]] = {}
    # Shared registry of claimed world identities.  Without it, agents born
    # into the same first PU can adopt the same player id and one of them
    # then observes a body it does not control, forever.
    claimed_identities: dict[int, int] = {}

    def __init__(self, index: int, args: argparse.Namespace,
                 credentials: tuple[str, str, str], stop: threading.Event,
                 perception: VisualPerception | None = None,
                 tracker: "AgentTrackerFile | None" = None) -> None:
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
        self.last_position_change_at = 0.0
        self.motions_since_progress = 0
        self.watchdog_attempts = 0
        self.last_need_object: int | None = None
        self.last_drain_at = 0.0
        self.committed_goal: tuple[str, int, int, float] | None = None
        self.last_status_log = 0.0
        self.peer_helds: dict[int, PlayerView] = {}
        self.spatial_leads: dict[str, tuple[tuple[int, int], int, float]] = {}
        self.recipe_buffers: dict[int, tuple[str, float]] = {}
        self.recent_vanish: dict[int, tuple[tuple[int, int], float]] = {}
        self.mover_ids: set[int] = set()
        self.last_own_held: int | None = None
        self.self_name: str | None = None
        self.last_ask_at = 0.0
        self.last_rehearse_at = 0.0
        self.last_reputation_at: dict[int, float] = {}
        self.life_started_at = time.monotonic()
        self.current_mode = "LEARN"
        self.mode_started_at = time.monotonic()
        self.mode_snapshot: dict[str, float] = {}
        self.affliction_count = 0
        self.food_gain_count = 0
        self.tracker = tracker
        self.hints = HintOracle(
            (perception or VisualPerception(
                getattr(args, "data_dir", None)
            )).data_dir,
            getattr(args, "hints", "off"),
        )
        self.consulted_hints: set[int] = set()
        self.perception = perception or VisualPerception(
            getattr(args, "data_dir", None)
        )
        if getattr(args, "no_properties", False):
            self.perception = VisualPerception("/dev/null/disabled")
        self.event_log_path: Path | None = None
        self.life_index = 0
        self.stage = "adult"
        self.last_stage_logged = ""
        self.dependents: dict[int, float] = {}
        self.current_task = ""
        self.task_started_at = 0.0
        self.last_commit_at = 0.0
        self.help_requests: dict[str, tuple[int, float]] = {}
        self.follow_target: tuple[int, float] | None = None
        self.requests_heard: dict[int, tuple[int, float]] = {}
        self.recent_contexts: deque = deque(maxlen=8)
        self.active_goal = ""
        self.last_goal_ask_at = 0.0
        self.goal_context: tuple[str, int, str] | None = None
        self.goal_target: tuple[str, int, tuple[int, int], float] | None = None
        self.goal_attempts: dict[str, float] = {}
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
        self.last_position = None
        self.last_position_change_at = 0.0
        self.motions_since_progress = 0
        self.watchdog_attempts = 0
        self.last_need_object = None
        self.last_drain_at = 0.0
        self.committed_goal = None
        self.last_status_log = 0.0
        self.peer_helds.clear()
        self.spatial_leads.clear()
        self.recipe_buffers.clear()
        self.recent_vanish.clear()
        self.mover_ids.clear()
        self.last_own_held = None
        self.self_name = None
        self.last_ask_at = 0.0
        self.last_rehearse_at = 0.0
        self.last_reputation_at.clear()
        self.life_started_at = time.monotonic()
        self.current_mode = "LEARN"
        self.mode_started_at = time.monotonic()
        self.mode_snapshot = {}
        self.affliction_count = 0
        self.food_gain_count = 0
        self.life_index += 1
        self.stage = "adult"
        self.last_stage_logged = ""
        self.dependents.clear()
        self.current_task = ""
        self.task_started_at = 0.0
        self.last_commit_at = 0.0
        self.help_requests.clear()
        self.follow_target = None
        self.requests_heard.clear()
        self.recent_contexts.clear()
        self.active_goal = ""
        self.last_goal_ask_at = 0.0
        self.goal_context = None
        self.goal_target = None
        self.goal_attempts.clear()
        self.consulted_hints.clear()
        self.open_event_log()
        self._release_identity()
        self.log(
            f"new life {self.life_number}: blank private mind "
            f"(knowledge must be experienced or heard)"
        )

    def _release_identity(self) -> None:
        with self.reservation_lock:
            for player_id in [
                pid for pid, owner in self.claimed_identities.items()
                if owner == self.index
            ]:
                self.claimed_identities.pop(player_id, None)

    def record_event(self, kind: str, **details: Any) -> None:
        """Structured per-life event log (Phase 1): one JSON object a line."""
        if self.event_log_path is None:
            return
        me = self.players.get(self.our_id) if self.our_id else None
        event = {
            "t": round(time.time(), 3),
            "agent": self.index,
            "life": self.life_index,
            "player_id": self.our_id,
            "kind": kind,
            "age": round(me.age, 2) if me else None,
            "stage": self.stage,
            "x": me.x if me else None,
            "y": me.y if me else None,
            "food": self.food_store,
            "food_capacity": self.food_capacity,
            "held": me.held_object if me else None,
            "mode": self.current_mode,
            "peers": max(0, len(self.players) - 1),
        }
        event.update(details)
        try:
            with self.event_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event) + "\n")
        except OSError:
            pass

    def open_event_log(self) -> None:
        directory = getattr(self.args, "event_log_dir", None)
        if not directory:
            self.event_log_path = None
            return
        path = Path(directory)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.event_log_path = None
            return
        self.event_log_path = path / (
            f"agent{self.index}_life{self.life_index}_"
            f"{int(time.time())}.jsonl"
        )
        self.record_event("life_start")

    def log(self, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        print(f"{stamp} [agent {self.index}] {text}", flush=True)

    @staticmethod
    def send(sock: socket.socket, message: str) -> None:
        sock.sendall(message.encode("utf-8"))

    def handle_pu(self, message: str) -> None:
        # Witnessed deaths: the deceased's final context becomes weak,
        # ambiguous danger evidence -- the honest common root of danger
        # knowledge and superstition, left to falsification to sort out.
        for line in message.splitlines()[1:]:
            death = re.match(r"\s*(-?\d+)(?:/\d+)?\s+X X", line)
            if death:
                dead_id = int(death.group(1))
                victim = self.players.pop(dead_id, None)
                self.peer_helds.pop(dead_id, None)
                if victim is not None and dead_id != self.our_id:
                    context = {
                        oid for pos, oid in self.world.items()
                        if oid > 0
                        and abs(pos[0] - victim.x) + abs(pos[1] - victim.y)
                        <= 2
                    }
                    if victim.held_object > 0:
                        context.add(victim.held_object)
                    for object_id in context:
                        self.mind.note_danger_own(object_id, 0.3)
                    self.mind.add_narrative(
                        "witnessed_death", player=dead_id,
                        context=sorted(context),
                    )
                    self.log(
                        f"witnessed death of player {dead_id}; weak danger "
                        f"evidence on {sorted(context)}"
                    )
        updates = parse_player_updates(message)
        for view in updates:
            previous = self.peer_helds.get(view.player_id)
            self.peer_helds[view.player_id] = view
            # Observational learning: a neighbor's hand changing beside a
            # lone candidate object is witnessed evidence for a causal rule,
            # imported without a word being spoken.
            if (
                previous is not None
                and self.our_id is not None
                and view.player_id != self.our_id
                and previous.held_object != view.held_object
                and view.held_object > 0
                and not getattr(self.args, "no_observation", False)
            ):
                candidates = [
                    oid for pos, oid in self.world.items()
                    if oid > 0
                    and max(
                        abs(pos[0] - previous.x), abs(pos[1] - previous.y)
                    ) <= 1
                ]
                if len(candidates) == 1:
                    held_before = previous.held_object
                    target = candidates[0]
                    result = view.held_object
                    a_token = (
                        "HAND" if held_before <= 0
                        else self.mind.word_for_object(held_before)[0]
                    )
                    b_token = self.mind.word_for_object(target)[0]
                    c_token = self.mind.word_for_object(result)[0]
                    self.mind.hear_token_rule(
                        a_token, b_token, c_token, view.player_id
                    )
                    self.mind.hear_rule_testimony(
                        max(0, held_before), target, result, view.player_id
                    )
                    self.log(
                        f"observed player {view.player_id}: "
                        f"{max(0, held_before)} on {target} -> {result}"
                    )
            self.players[view.player_id] = view
        # The official client identifies the final newly inserted object in
        # the first PU as self. Shared-spawn test servers send that birth PU
        # immediately after ACCEPTED.  Prefer the newest id no other runner
        # thread has already claimed.
        if self.our_id is None and updates:
            chosen_id = None
            with self.reservation_lock:
                for view in reversed(updates):
                    owner = self.claimed_identities.get(view.player_id)
                    if owner is None or owner == self.index:
                        chosen_id = view.player_id
                        self.claimed_identities[chosen_id] = self.index
                        break
            if chosen_id is None:
                self.log(
                    "identity wait: every visible player id is already "
                    "claimed by another agent"
                )
            else:
                self.our_id = chosen_id
                self.identity_seen_at = time.monotonic()
                self.log(f"world identity is player {self.our_id}")

    def handle_map_chunk(self, chunk: MapChunk) -> None:
        for index, object_id in enumerate(chunk.cells):
            self.world[(chunk.x + index % chunk.size_x,
                        chunk.y + index // chunk.size_x)] = object_id
        self.mind.note_objects({value for value in chunk.cells if value > 0})

    def handle_mx(self, message: str) -> None:
        for x, y, object_id in parse_map_changes(message):
            old_id = self.world.get((x, y))
            self.world[(x, y)] = object_id
            now_mono = time.monotonic()
            # Movers: an object vanishing here and reappearing nearby soon
            # is something that moves on its own -- a learnable perceptual
            # category (animals), used for harm attribution.
            if old_id is not None and old_id > 0 and old_id != object_id:
                self.recent_vanish[old_id] = ((x, y), now_mono)
            if object_id > 0 and object_id in self.recent_vanish:
                origin, seen_at = self.recent_vanish[object_id]
                if (
                    now_mono - seen_at <= 6.0
                    and 0 < abs(origin[0] - x) + abs(origin[1] - y) <= 4
                    and object_id not in self.mover_ids
                ):
                    self.mover_ids.add(object_id)
                    self.log(f"object {object_id} moves on its own")
            if object_id > 0:
                self.mind.note_objects({object_id})
            # A change with no agent nearby is the world acting on itself
            # (decay, growth); that is a learnable expectation too.
            if (
                old_id is not None
                and old_id > 0
                and old_id != object_id
                and not self._change_near_agents(x, y)
            ):
                self.mind.observe_ambient(old_id, object_id)
            # A requested object appearing beside me while a peer is close
            # is a fulfilled request: the giver earns real reputation, the
            # same currency that gates their claims and rules.
            if (
                self.last_need_object is not None
                and object_id == self.last_need_object
                and time.monotonic() - self.last_need_at
                <= self.args.request_ttl
            ):
                me = self.players.get(self.our_id) if self.our_id else None
                if me is not None and abs(x - me.x) + abs(y - me.y) <= 3:
                    candidates = [
                        (abs(p.x - x) + abs(p.y - y), p.player_id)
                        for p in self.players.values()
                        if p.player_id != self.our_id
                        and abs(p.x - x) + abs(p.y - y) <= 5
                    ]
                    if candidates:
                        _, giver = min(candidates)
                        record = self.mind.source_trust.setdefault(
                            int(giver), {"helpful": 0, "failed": 0}
                        )
                        record["helpful"] = int(
                            record.get("helpful", 0)
                        ) + 1
                        self.mind.reinforce_social_context([giver], 1.5)
                        self.mind.save()
                        self.log(
                            f"received requested object {object_id}; "
                            f"crediting player {giver}"
                        )
                        self.last_need_object = None

    def _change_near_agents(self, x: int, y: int) -> bool:
        if self.pending_trial is not None and (
            abs(self.pending_trial.x - x) + abs(self.pending_trial.y - y) <= 2
        ):
            return True
        return any(
            abs(p.x - x) + abs(p.y - y) <= 2 for p in self.players.values()
        )

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
        # Count the attempt whether or not a path is sendable, so the
        # stuck watchdog can always eventually fire.
        self.motions_since_progress += 1
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

    def _stuck_probe(self, me: PlayerView, now: float) -> ActionProposal | None:
        """Escape a trapped position that ordinary movement cannot leave.

        Repeated stalls accumulate blocked tiles and reservations that can
        themselves become the trap.  After a long interval with issued
        motion but no position change, clear the stale avoidance state and
        probe adjacent tiles directly; the server remains the judge of
        whether each step is possible.
        """
        if self.last_position_change_at <= 0.0:
            return None
        stuck_for = now - self.last_position_change_at
        if stuck_for < self.args.stuck_timeout:
            return None
        if self.motions_since_progress < 3:
            return None
        if self.blocked_until:
            self.log(
                f"stuck watchdog: clearing {len(self.blocked_until)} "
                "stale blocked tiles"
            )
            self.blocked_until.clear()
        directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
        dx, dy = directions[
            (self.index - 1 + self.watchdog_attempts) % 4
        ]
        self.watchdog_attempts += 1
        destination = (me.x + dx, me.y + dy)
        self.log(
            f"stuck watchdog: no position change for {stuck_for:.0f}s "
            f"after {self.motions_since_progress} motions; "
            f"probing {destination}"
        )
        return ActionProposal(
            "PROBE", self.args.force_move_score + 2.0,
            "stuck watchdog adjacent probe",
            destination[0], destination[1],
            path=[(me.x, me.y), destination],
        )

    def expected_value(
        self, kind: str, immediate: float, effort: float, risk: float,
        context: str = "", dependant_effect: float = 0.0,
        information: float = 0.0, resource_cost: float = 0.0,
    ) -> tuple[float, str]:
        """Compare acting now against investing for later (Module 7).

        expected_value = immediate need effect
                       + discounted future need effect
                       + effect on dependants
                       + information value
                       - effort - resource cost - risk

        The future term is *learned*: it comes from delayed effects the
        agent has actually experienced in this context and from the value
        the place itself has accrued.  Nothing here knows what a house,
        a farm, or a fire is; persistent things become worth doing only
        when their delayed pay-offs have been felt.
        """
        discount = max(0.0, min(1.0, self.args.future_discount))
        future = self.mind.delayed_value(context) if context else 0.0
        value = (
            immediate
            + discount * future
            + self.args.dependant_weight * dependant_effect
            + self.args.information_weight * information
            - self.args.effort_weight * effort
            - resource_cost
            - self.args.risk_weight * risk
        )
        reason = (
            f"ev[{kind}] now={immediate:.2f} future={discount * future:.2f} "
            f"dep={dependant_effect:.2f} info={information:.2f} "
            f"effort={effort:.2f} risk={risk:.2f}"
        )
        return value, reason

    def sensed_deficits(self, me: PlayerView, hunger: float
                        ) -> dict[str, float]:
        """Which wanted states are currently unmet, and how badly.

        Nothing here knows about fire or food: warmth is wanted when the
        agent's own hunger-drain measurements say this place drains it
        fast, nourishment when it is hungry with nothing known to eat,
        and a cutting tool when it holds nothing that looks like one.
        """
        deficits: dict[str, float] = {}

        # Warmth: drain measured here versus the best place known.
        nearby_ids = {
            oid for pos, oid in self.world.items()
            if oid > 0 and abs(pos[0] - me.x) + abs(pos[1] - me.y) <= 2
        }
        measured = [
            self.mind.comfort_value(oid) for oid in nearby_ids
            if oid in self.mind.comfort
        ]
        here = sum(measured) / len(measured) if measured else 0.0
        if self.mind.comfort and here < 0.0:
            deficits["warmth"] = min(1.0, -here)
        elif not self.mind.known_goal_objects("warmth") and hunger > 0.3:
            # Never yet found anything warming, and food is draining:
            # wanting warmth is a reasonable conjecture.
            deficits["warmth"] = 0.35

        known_food = self.mind.known_food_objects()
        if hunger > 0.3 and not known_food:
            deficits["nourishment"] = hunger

        if self.perception.available:
            holding_edge = goal_satisfaction(
                self.perception, me.held_object, "cutting_tool"
            ) if me.held_object > 0 else 0.0
            if holding_edge < 0.2 and not self.mind.known_goal_objects(
                "cutting_tool"
            ):
                deficits["cutting_tool"] = 0.4
        return deficits

    def goal_proposals(
        self, me: PlayerView, now: float, hunger: float,
        proposals: list[ActionProposal],
    ) -> None:
        """Backward chaining from a wanted state to something to do.

        goal -> does something in view already satisfy it?  If not, could
        combining two things in view produce it?  If not, is an
        ingredient worth acquiring, or worth asking about?
        """
        deficits = self.sensed_deficits(me, hunger)
        if not deficits:
            self.active_goal = ""
            return
        goal = max(deficits, key=lambda name: deficits[name])
        urgency = deficits[goal]
        if goal != self.active_goal:
            self.active_goal = goal
            self.record_event("goal_adopted", goal=goal,
                              urgency=round(urgency, 2))
            self.log(
                f"goal: {goal} (urgency {urgency:.2f}) -- searching for "
                f"something that satisfies it, or a way to make one"
            )

        # Goals supplement discovery, they must never starve it.
        discovery_scale = (
            0.4 if not self.mind.known_food_objects() else 1.0
        )
        weight = self.args.goal_weight * urgency * discovery_scale
        now_mono = time.monotonic()
        self.goal_attempts = {
            key: when for key, when in self.goal_attempts.items()
            if now_mono - when < self.args.goal_retry_interval
        }
        visible = [
            (pos, oid) for pos, oid in self.world.items()
            if oid > 0
            and abs(pos[0] - me.x) + abs(pos[1] - me.y)
            <= self.args.search_radius
        ]

        # Commit to a chosen target until it is reached, attempted, or
        # the goal itself changes: re-deciding every tick is how an agent
        # ends up walking in circles between equally good candidates.
        if self.goal_target is not None:
            target_goal, target_id, target_pos, chosen_at = self.goal_target
            if (
                target_goal == goal
                and now - chosen_at < self.args.goal_commit_ttl
                and self.world.get(target_pos) == target_id
                and f"{goal}|{target_id}" not in self.goal_attempts
            ):
                path = self._adjacent_path(me, target_pos)
                distance = (
                    abs(target_pos[0] - me.x) + abs(target_pos[1] - me.y)
                )
                if path or distance <= 1:
                    proposals.append(ActionProposal(
                        "GOAL_SEEK",
                        weight * 1.6 - 0.03 * distance,
                        f"{goal}: continuing toward committed object "
                        f"{target_id}",
                        target_pos[0], target_pos[1], target_id, path,
                    ))
                    return
            self.goal_target = None

        # 1. Something that already satisfies the goal, by learned
        #    experience first and by appearance second.
        for pos, object_id in visible:
            if f"{goal}|{object_id}" in self.goal_attempts:
                continue
            learned = self.mind.learned_goal_value(goal, object_id)
            looks = goal_satisfaction(self.perception, object_id, goal)
            merit = max(learned, looks)
            if merit <= 0.15:
                continue
            path = self._adjacent_path(me, pos)
            if not path:
                continue
            distance = abs(pos[0] - me.x) + abs(pos[1] - me.y)
            proposals.append(ActionProposal(
                "GOAL_SEEK", weight * merit * 1.5 - 0.03 * distance,
                f"{goal}: object {object_id} may satisfy it "
                f"(learned={learned:.2f} looks={looks:.2f})",
                pos[0], pos[1], object_id, path,
            ))

        # 2. A combination that might *produce* what is wanted.
        if me.held_object > 0:
            for pos, object_id in visible:
                if f"{goal}|{object_id}" in self.goal_attempts:
                    continue
                strength, note = production_candidates(
                    self.perception, goal, me.held_object, object_id
                )
                if strength <= 0.05:
                    continue
                trials, _, _, _ = self.mind.action_knowledge(
                    me.held_object, object_id, "USE"
                )
                if trials > 2:
                    continue
                path = self._adjacent_path(me, pos)
                if not path:
                    continue
                distance = abs(pos[0] - me.x) + abs(pos[1] - me.y)
                proposals.append(ActionProposal(
                    "GOAL_COMBINE",
                    weight * strength * 4.0 - 0.03 * distance,
                    f"{goal}: try {me.held_object} on {object_id} -- {note}",
                    pos[0], pos[1], object_id, path,
                ))

        # 3. Acquire an ingredient whose appearance the priors want.
        if self.perception.available:
            profiles = wanted_ingredient_profiles(goal)
            best_pick = None
            best_merit = 0.0
            for pos, object_id in visible:
                if f"{goal}|{object_id}" in self.goal_attempts:
                    continue
                properties = self.perception.properties(object_id)
                if not properties or properties.get("portable", 0.0) < 0.5:
                    continue
                # Only one agent can hold a thing.
                my_distance = abs(pos[0] - me.x) + abs(pos[1] - me.y)
                contested = any(
                    abs(view.x - pos[0]) + abs(view.y - pos[1])
                    < my_distance
                    for pid, view in self.players.items()
                    if pid != self.our_id
                )
                if contested:
                    continue
                merit = max(
                    (profile_match(properties, profile)
                     for profile in profiles), default=0.0
                )
                if merit > best_merit:
                    best_merit, best_pick = merit, (pos, object_id)
            if best_pick is not None and best_merit > 0.2 and (
                me.held_object <= 0
            ):
                pos, object_id = best_pick
                path = self._adjacent_path(me, pos)
                if path:
                    proposals.append(ActionProposal(
                        "GOAL_GATHER",
                        weight * best_merit * 2.0
                        - 0.03 * (abs(pos[0] - me.x) + abs(pos[1] - me.y)),
                        f"{goal}: picking up {object_id}, which looks like "
                        f"a plausible ingredient",
                        pos[0], pos[1], object_id, path,
                    ))

        # 4. Nothing to hand: ask the group about the wanted state.
        if (
            self.mind.habit_factor("ASK") > 0.0
            and self.nearby_peer_ids(me, self.args.language_radius)
            and now - self.last_goal_ask_at >= self.args.ask_interval * 2
        ):
            known = self.mind.known_goal_objects(goal)
            if not known:
                token = None
                for candidate in self.mind.known_food_objects():
                    token = self.mind.word_for_object(candidate)[0]
                    break
                if goal == "warmth" and token is None:
                    self.last_goal_ask_at = now
                    question = "WHAT WARM"
                    if question not in self.pending_utterances:
                        self.pending_utterances.append(question)

    def local_needs(self, me: PlayerView, hunger: float) -> dict[str, float]:
        """Shared picture of unmet local needs (Module 13)."""
        threat = 0.0
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                oid = self.world.get((me.x + dx, me.y + dy), 0)
                if oid > 0:
                    threat = max(threat, self.mind.danger_value(oid))
        infants = sum(
            1 for pid, view in self.players.items()
            if pid != self.our_id and view.age < 3.0
            and abs(view.x - me.x) + abs(view.y - me.y) <= 8
        )
        unknown_nearby = sum(
            1 for pos, oid in self.world.items()
            if oid > 0
            and abs(pos[0] - me.x) + abs(pos[1] - me.y) <= 6
            and self.mind.action_knowledge(oid, -1, "SELF")[0] == 0
        )
        return {
            "forage": min(1.0, hunger),
            "care": min(1.0, infants / 2.0),
            "safety": min(1.0, threat),
            "craft": min(1.0, len(self.mind.recipes) * 0.25
                         + len(self.mind.token_rules) * 0.05),
            "explore": min(1.0, unknown_nearby / 8.0),
        }

    def task_suitability(
        self, task: str, urgency: float, proximity: float, now: float,
    ) -> float:
        """task_score = urgency x competence x proximity - switching cost
        (Module 13).  Competence feeds back, closing the specialization
        loop: doing a thing well makes doing it again cheaper."""
        competence = self.mind.task_competence(task)
        switching = (
            0.0 if task == self.current_task
            else self.args.switching_cost
        )
        taken = (
            self.args.duplication_penalty
            if self.mind.task_is_taken(task, time.time()) else 0.0
        )
        return (
            urgency * (0.4 + competence) * proximity - switching - taken
        )

    def _priority_snapshot(self, hunger: float) -> dict[str, float]:
        corroborated = sum(
            1 for outcomes in self.mind.transitions.values()
            for e in outcomes.values() if e.status == "corroborated"
        )
        knowledge = (
            len(self.mind.object_words) + len(self.mind.rule_testimony)
            + len(self.mind.token_rules) + len(self.mind.hypotheses)
        )
        return {
            "hunger": hunger,
            "afflictions": float(self.affliction_count),
            "food_gains": float(self.food_gain_count),
            "corroborated": float(corroborated),
            "knowledge": float(knowledge),
            "comfort_entries": float(len(self.mind.comfort)),
        }

    def _settle_mode(self, hunger: float) -> None:
        """Reflection on a finished priority: did it serve its need?"""
        snapshot = self.mode_snapshot
        if not snapshot:
            return
        mode = self.current_mode
        after = self._priority_snapshot(hunger)
        if mode == "FEED":
            success = after.get("food_gains", 0.0) > snapshot.get(
                "food_gains", 0.0
            ) or after["hunger"] < snapshot["hunger"] - 0.05
        elif mode == "SAFE":
            success = after["afflictions"] <= snapshot["afflictions"]
        elif mode == "CRAFT":
            success = after["corroborated"] > snapshot["corroborated"]
        elif mode == "NEST":
            success = after["comfort_entries"] > snapshot["comfort_entries"]
        else:  # LEARN
            success = after["knowledge"] > snapshot["knowledge"]
        self.mind.credit_mode(mode, success)

    def appraise_priority(self, me: PlayerView, now: float,
                          hunger: float) -> None:
        """Adopt an explicit priority mode from own appraisal: urgency
        (threat, hunger) is innate like pain; discretionary allocation is
        chosen by reflected-on, culturally endorsable mode weights."""
        threat = 0.0
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                oid = self.world.get((me.x + dx, me.y + dy), 0)
                if oid > 0:
                    threat = max(threat, self.mind.danger_value(oid))
        has_plan = any(
            self.mind.action_knowledge(oid, -1, "SELF")[1] > 0.3
            or self.mind.testimony_food_value(oid) > 0.5
            for oid in set(self.world.values()) if oid > 0
        ) or any(
            self.mind.action_knowledge(oid, -1, "SELF")[1] > 0.3
            for oid in list(self.mind.object_words)[:64]
        )
        urgent = None
        in_mode_for = now - self.mode_started_at
        threat_clear = threat < 0.6 * self.args.threat_threshold
        if self.current_mode == "SAFE" and (
            not threat_clear or in_mode_for < self.args.urgency_dwell
        ):
            # Hysteresis: leave SAFE only once the threat has genuinely
            # receded and the mode has had time to act, so urgency cannot
            # thrash the agent between fear and hunger every tick.
            urgent = "SAFE"
        elif threat >= self.args.threat_threshold:
            urgent = "SAFE"
        elif hunger >= self.args.feed_hunger or (
            hunger >= 0.35 and not has_plan
        ):
            urgent = "FEED"
        target = None
        if urgent is not None and urgent != self.current_mode:
            target = urgent
        elif urgent is None:
            in_dwell = now - self.mode_started_at < self.args.mode_dwell
            if self.current_mode in ("SAFE", "FEED") or not in_dwell:
                eligible = ["LEARN"]
                if self.mind.comfort or self.home_location is not None:
                    eligible.append("NEST")
                if (
                    self.mind.recipes or self.mind.rule_testimony
                    or self.mind.token_rules
                ):
                    eligible.append("CRAFT")
                choice = max(
                    eligible,
                    key=lambda m: self.mind.mode_weight(m)
                    + self.mind.rng.random() * 0.05,
                )
                if choice != self.current_mode:
                    target = choice
        if target is None:
            return
        self._settle_mode(hunger)
        previous = self.current_mode
        self.current_mode = target
        self.mode_started_at = now
        self.mode_snapshot = self._priority_snapshot(hunger)
        self.log(
            f"priority: {target} (was {previous}; hunger={hunger:.2f} "
            f"threat={threat:.2f} plan={has_plan}) "
            f"weights={{{', '.join(f'{m}:{self.mind.mode_weight(m):.2f}' for m in MODE_NAMES)}}}"
        )

    def propose_actions(self, me: PlayerView, now: float) -> list[ActionProposal]:
        """Generate available primitive actions; learned evidence supplies scores."""
        proposals: list[ActionProposal] = []
        probe = self._stuck_probe(me, now)
        if probe is not None:
            proposals.append(probe)
        instrumental = self.mind.instrumental_values()
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
        # Strategy: exploration is annealed by competence and hunger.  An
        # agent with any credible route to food explores when safe and
        # exploits when starving; an agent with no food knowledge keeps
        # exploring at full strength because it has no alternative.
        mode = self.current_mode
        m_food = mode_factor(mode, "food")
        m_staple = mode_factor(mode, "staple")
        m_explore = mode_factor(mode, "explore")
        m_craft = mode_factor(mode, "craft")
        m_recipe = mode_factor(mode, "recipe")
        m_verify = mode_factor(mode, "verify")
        m_danger = mode_factor(mode, "danger")
        m_comfort = mode_factor(mode, "comfort")
        m_nest = mode_factor(mode, "nest")
        m_lead = mode_factor(mode, "lead")
        known_food_plan = bool(
            chain_step or personally_known_food or self.mind.food_testimony
        )
        exploration_scale = (
            1.0 if not known_food_plan else max(0.25, 1.0 - hunger)
        ) * m_explore
        habit_verify = self.mind.habit_factor("VERIFY")
        habit_trust = self.mind.habit_factor("TRUST")
        habit_staple = self.mind.habit_factor("STAPLE")
        committed = self.committed_goal
        if (
            committed is not None
            and now - committed[3] > self.args.commitment_ttl
        ):
            committed = self.committed_goal = None

        def commitment_bonus(kind: str, x: int, y: int) -> float:
            if committed is None:
                return 0.0
            if committed[0] == kind and committed[1] == x and committed[2] == y:
                return self.args.commitment_bonus
            return 0.0
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
            and self._home_evidence(me, now)
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
                self.last_need_object = wanted
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
            # A crafting step earns derived value when its predicted result
            # leads, through the agent's own corroborated expectations, to
            # reward later.  This is what lets tool making beat wandering.
            prediction = self.mind.predicted_next_held(
                me.held_object, object_id, "USE"
            )
            instrumental_bonus = 0.0
            if prediction is not None:
                next_held, prediction_confidence = prediction
                instrumental_bonus = m_craft * (
                    self.args.instrumental_weight
                    * prediction_confidence
                    * max(0.0, instrumental.get(next_held, 0.0))
                    * (0.5 + 0.5 * hunger)
                )
            # A testified rule about this exact pair demands independent
            # verification before it is relied on, scaled by source trust.
            rule_key = f"{me.held_object}|{object_id}"
            rule_verify = (
                m_verify * habit_verify
                * self.args.verify_weight
                * self.mind.rule_claim_posterior(rule_key)
                * (1.0 - self.mind.mean_rule_source_trust(rule_key))
                if trials == 0 and rule_key in self.mind.rule_testimony
                else 0.0
            )
            # Inherited veto: culture (or my own scars) argue against this
            # act, graded by trust and softened only by desperation.
            danger_penalty = (
                m_danger * 6.0 * self.mind.danger_value(object_id)
                * (1.0 - 0.5 * hunger)
            )
            # A taught recipe step that matches here carries the plan of a
            # chain deeper than my own search.
            held_token = (
                "HAND" if me.held_object <= 0
                else self.mind.word_for_object(me.held_object)[0]
            )
            target_token_word = self.mind.word_for_object(object_id)[0]
            recipe_bonus = 0.0
            for product, recipe in self.mind.recipes.items():
                for step in recipe.get("steps", []):
                    if step[0] == held_token and step[1] == target_token_word:
                        recipe_bonus = (2.0 + 2.0 * hunger) * m_recipe
                        break
                if recipe_bonus:
                    break
            retest_bonus = (
                self.args.verify_weight
                if rule_key in self.mind.retest_pairs else 0.0
            )
            # Abundant objects that remain untested are staple candidates:
            # learning what surrounds you pays more than chasing rarities.
            encounters = self.mind.encounter_counts.get(object_id, 0)
            staple = (
                self.args.staple_weight
                * min(1.0, encounters / 25.0)
                * uncertainty
                if trials == 0 else 0.0
            )
            commit = commitment_bonus("USE", pos[0], pos[1])
            # Appearance priors and property-level generalization
            # (Modules 2/4): a human does not brute-force combinations,
            # they try what *looks* like it might work.
            prior_bonus = 0.0
            general_bonus = 0.0
            if self.perception.available and trials == 0:
                prior_bonus = 0.0 if getattr(
                    self.args, "no_priors", False
                ) else self.args.prior_weight * prior_strength(
                    self.perception, me.held_object, object_id, "transform"
                )
                actor_signature = (
                    self.perception.descriptor(me.held_object)
                    if me.held_object > 0 else ()
                )
                target_signature = self.perception.descriptor(object_id)
                confidence, evidence = self.mind.property_confidence(
                    actor_signature, target_signature, "transform"
                )
                if evidence > 0:
                    general_bonus = self.args.generalization_weight * (
                        confidence - 0.5
                    ) * min(1.0, evidence / 4.0) * 2.0
            # Temporal planning (Module 7): a costly act with no immediate
            # pay-off can still win if its *learned* delayed effects and
            # the place's accrued value make it worth the effort.
            context_key = f"use:{me.held_object}|{object_id}"
            investment, investment_reason = self.expected_value(
                "invest",
                immediate=max(0.0, learned_value),
                effort=0.02 * distance + 0.1,
                risk=self.mind.danger_value(object_id),
                context=context_key,
                dependant_effect=(
                    0.3 if self.dependents else 0.0
                ),
                information=uncertainty,
            )
            place_bonus = self.args.location_weight * self.mind.location_worth(
                pos[0], pos[1]
            )
            trust_terms = m_food * habit_trust * cache_food
            score = (
                m_food * known_food
                + self.args.planning_weight * investment
                + prior_bonus
                + general_bonus
                + place_bonus
                + trust_terms
                + chain_bonus
                + instrumental_bonus
                + rule_verify
                + recipe_bonus
                + retest_bonus
                + commit
                - danger_penalty
                + exploration_scale * (
                    self.args.curiosity_weight * uncertainty
                    + self.args.novelty_weight * novelty
                    + self.args.falsification_weight * falsification
                    + m_staple * habit_staple * staple
                )
                - 0.025 * distance
                - self.args.repetition_penalty * trials
                - (0.8 if pos in list(self.position_history)[-4:] else 0.0)
                + self.mind.rng.random() * self.args.choice_noise
            )
            tags = tuple(
                name for name, value in (
                    ("VERIFY", rule_verify + retest_bonus),
                    ("TRUST", trust_terms + recipe_bonus),
                    ("STAPLE", habit_staple * staple),
                ) if value > 0.3
            )
            proposals.append(
                ActionProposal(
                    "USE", score,
                    f"value={learned_value:.2f} uncertainty={uncertainty:.2f} "
                    f"novelty={novelty:.2f} food={trust_terms:.2f} "
                    f"chain={chain_bonus:.2f} instr={instrumental_bonus:.2f} "
                    f"rule_verify={rule_verify:.2f} staple={staple:.2f} "
                    f"recipe={recipe_bonus:.2f} retest={retest_bonus:.2f} "
                    f"prior={prior_bonus:.2f} general={general_bonus:.2f} "
                    f"{investment_reason} "
                    f"place={place_bonus:.2f} "
                    f"danger={danger_penalty:.2f} "
                    f"commit={commit:.2f} explore={exploration_scale:.2f} "
                    f"trials={trials}",
                    pos[0], pos[1], object_id, path,
                    habit_tags=tags,
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
            # Trust-gated independent falsification: a personally untested
            # food claim demands verification, and the demand grows as the
            # claim's sources have earned less trust.  A high-trust claim can
            # be relied on through the ordinary testimony term instead.
            claim_posterior = self.mind.testimony_claim_posterior(
                me.held_object
            )
            source_trust = self.mind.mean_source_trust(me.held_object)
            verify_bonus = (
                m_verify * habit_verify
                * self.args.verify_weight
                * claim_posterior * (1.0 - source_trust)
                if trials == 0 and claim_posterior > 0.0
                else 0.0
            )
            self_retest = (
                self.args.verify_weight
                if f"{me.held_object}|-1" in self.mind.retest_pairs else 0.0
            )
            self_danger = (
                m_danger * 6.0 * self.mind.danger_value(me.held_object)
                * (1.0 - 0.5 * hunger)
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
                    + verify_bonus
                    + self_retest
                    - self_danger
                    + max(0.0, value) * (1.0 + 4.0 * hunger)
                    + habit_trust * 1.25 * hunger
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
                    f"first_test={first_self_test:.2f} "
                    f"verify={verify_bonus:.2f} retest={self_retest:.2f} "
                    f"danger={self_danger:.2f} hunger={hunger:.2f} "
                    f"value={value:.2f} "
                    f"uncertainty={uncertainty:.2f} trials={trials}",
                    me.x, me.y, -1,
                    habit_tags=tuple(
                        name for name, bonus in (
                            ("VERIFY", verify_bonus + self_retest),
                            ("TRUST", habit_trust * self.mind.
                             testimony_food_value(me.held_object)),
                        ) if bonus > 0.3
                    ),
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

        # A hungry, empty-handed agent can travel back to the adopted HOME.
        # The location is socially learned; what is actually cached there is
        # discovered by perception on arrival, never assumed.
        if (
            me.held_object <= 0
            and self.home_location is not None
            and hunger >= self.args.request_hunger
        ):
            home_distance = abs(me.x - self.home_location[0]) + abs(
                me.y - self.home_location[1]
            )
            if home_distance > 1:
                path = self._adjacent_path(me, self.home_location)
                if len(path) > 1:
                    proposals.append(ActionProposal(
                        "SEEK_CACHE",
                        m_nest * self.args.cache_seek_weight * hunger
                        - 0.02 * home_distance
                        + self.mind.rng.random() * self.args.choice_noise,
                        f"hunger={hunger:.2f}; travel to shared home cache",
                        self.home_location[0], self.home_location[1],
                        path=path,
                    ))

        # Familiarity grows with co-presence, and a persistent infant
        # nearby is inferred kin (Module 11/14).
        for pid, view in self.players.items():
            if pid == self.our_id:
                continue
            if abs(view.x - me.x) + abs(view.y - me.y) <= 6:
                self.mind.note_familiarity(pid, 0.01)
                if view.age < 2.0 and self.stage in ("adult", "elder"):
                    self.mind.note_kinship(pid, 0.5)

        # Follow when asked by someone I have reason to value (Module 10).
        if self.follow_target is not None:
            leader_id, asked_at = self.follow_target
            leader = self.players.get(leader_id)
            if leader is None or now - asked_at > 90.0:
                self.follow_target = None
            elif self.mind.social_regard(leader_id) > 0.1:
                distance = abs(leader.x - me.x) + abs(leader.y - me.y)
                if distance > 3:
                    step = (
                        me.x + (1 if leader.x > me.x else
                                -1 if leader.x < me.x else 0),
                        me.y,
                    )
                    if step == (me.x, me.y):
                        step = (
                            me.x, me.y + (1 if leader.y > me.y else -1),
                        )
                    if self.blocked_until.get(step, 0.0) <= now:
                        proposals.append(ActionProposal(
                            "FOLLOW",
                            self.args.follow_weight
                            * self.mind.social_regard(leader_id),
                            f"following player {leader_id} as asked",
                            leader.x, leader.y, leader_id,
                            path=[(me.x, me.y), step],
                        ))

        # Care for dependants (Module 14): an adult holding something its
        # own trials proved nourishing can offer it to a nearby infant.
        # Nothing here knows what food *is*; it uses only learned value.
        if self.dependents and me.held_object > 0 and self.stage in (
            "adult", "elder"
        ):
            _, held_value, _, _ = self.mind.action_knowledge(
                me.held_object, -1, "SELF"
            )
            if held_value > 0.3:
                for pid, age in self.dependents.items():
                    view = self.players.get(pid)
                    if view is None:
                        continue
                    distance = abs(view.x - me.x) + abs(view.y - me.y)
                    proposals.append(ActionProposal(
                        "CARE",
                        self.args.care_weight * held_value
                        * (0.5 + self.mind.social_regard(pid))
                        * (1.0 - 0.1 * distance),
                        f"offering held {me.held_object} to dependant {pid}",
                        view.x, view.y, pid,
                    ))
                    break

        # Consult the game's hints for what is in hand or in sight, the
        # way a player hovers and clicks.  Descriptions give shared
        # names; transitions arrive as claims from the hint sheet, so
        # they still pass through verification like any other testimony.
        if self.hints.available:
            to_read = [me.held_object] + [
                oid for pos, oid in self.world.items()
                if oid > 0
                and abs(pos[0] - me.x) + abs(pos[1] - me.y) <= 3
            ]
            for object_id in to_read[:8]:
                if object_id <= 0 or object_id in self.consulted_hints:
                    continue
                self.consulted_hints.add(object_id)
                word = self.hints.word_from_description(object_id)
                if word and object_id not in self.mind.object_words:
                    self.mind.hint_words[object_id] = word
                    self.mind.save()
                for actor, target, new_actor, new_target in \
                        self.hints.hints_for(object_id):
                    if target <= 0:
                        continue
                    result = new_actor if new_actor > 0 else new_target
                    if result <= 0:
                        continue
                    self.mind.hear_rule_testimony(
                        max(0, actor), target, result, HINT_SOURCE_ID
                    )
                    actor_token = (
                        "HAND" if actor <= 0
                        else self.mind.word_for_object(actor)[0]
                    )
                    self.mind.hear_token_rule(
                        actor_token,
                        self.mind.word_for_object(target)[0],
                        self.mind.word_for_object(result)[0],
                        HINT_SOURCE_ID,
                    )
                if self.hints.level == "full":
                    count = len(self.hints.hints_for(object_id))
                    if count:
                        self.record_event(
                            "hints_read", object_id=object_id, count=count
                        )
                        self.log(
                            f"read {count} hint(s) for object {object_id}"
                            + (f" ({word})" if word else "")
                        )

        # Goal-directed reasoning (M28): work backward from a
        # wanted state to something worth doing right now.
        self.goal_proposals(me, now, hunger, proposals)

        # SAFE is not paralysis: retreat a step away from the strongest
        # nearby learned danger, so fear produces movement, not starvation.
        if mode == "SAFE":
            worst = None
            worst_value = 0.0
            for dx in range(-6, 7):
                for dy in range(-6, 7):
                    oid = self.world.get((me.x + dx, me.y + dy), 0)
                    if oid > 0:
                        value = self.mind.danger_value(oid)
                        if value > worst_value:
                            worst_value = value
                            worst = (me.x + dx, me.y + dy)
            if worst is not None and worst_value > 0.2:
                options = [
                    (me.x + sx, me.y + sy)
                    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                ]
                options = [
                    step for step in options
                    if self.blocked_until.get(step, 0.0) <= now
                    and self.world.get(step, 0) <= 0
                ]
                if options:
                    step = max(
                        options,
                        key=lambda s: abs(s[0] - worst[0])
                        + abs(s[1] - worst[1]),
                    )
                    proposals.append(ActionProposal(
                        "RETREAT",
                        4.0 + 2.0 * worst_value,
                        f"retreating from learned danger at {worst}",
                        step[0], step[1],
                        path=[(me.x, me.y), step],
                    ))

        # Displaced reference in action: follow a spoken spatial lead
        # toward a valued referent nowhere in sight, and verify the
        # informant when the journey resolves.
        for token, (estimate, informant, heard_at) in list(
            self.spatial_leads.items()
        ):
            if now - heard_at > 180.0:
                self.spatial_leads.pop(token, None)
                continue
            referent = self.mind.inferred_referent(token)
            if referent is None:
                continue
            worth = max(
                1.0 if referent in personally_known_food else 0.0,
                self.mind.testimony_food_value(referent),
            )
            if worth <= 0.0 or hunger < 0.35:
                continue
            arrival = abs(me.x - estimate[0]) + abs(me.y - estimate[1])
            if arrival <= 3:
                found = any(
                    oid == referent
                    and abs(pos[0] - me.x) + abs(pos[1] - me.y) <= 6
                    for pos, oid in self.world.items()
                )
                trust_now = self.mind.record_testimony_outcome(
                    referent, found
                ) if referent in self.mind.food_testimony else None
                self.log(
                    f"spatial lead for {token} "
                    f"{'confirmed' if found else 'failed'} on arrival"
                    + (
                        f"; informant trust now {trust_now:.2f}"
                        if trust_now is not None else ""
                    )
                )
                self.spatial_leads.pop(token, None)
                continue
            step = (
                me.x + (1 if estimate[0] > me.x else -1 if estimate[0] < me.x
                        else 0),
                me.y + (1 if estimate[1] > me.y else -1 if estimate[1] < me.y
                        else 0),
            )
            step = (step[0], me.y) if step[0] != me.x else step
            if self.blocked_until.get(step, 0.0) <= now:
                proposals.append(ActionProposal(
                    "SEEK_LEAD",
                    m_lead * self.args.lead_weight * hunger * worth
                    - 0.01 * arrival,
                    f"following spoken lead toward {token}",
                    estimate[0], estimate[1],
                    path=[(me.x, me.y), step],
                ))
            break

        # Questions: the workspace makes absent and unknown referents
        # thinkable; ASK turns them into speech that recruits the group.
        if (
            self.mind.habit_factor("ASK") > 0.0
            and self.current_mode in ("FEED", "LEARN")
            and hunger >= self.args.request_hunger * 0.8
            and self.nearby_peer_ids(me, self.args.language_radius)
            and now - self.last_ask_at >= self.args.ask_interval
        ):
            token_worth = self.mind.token_values(
                time.time(), self.args.decay_halflife
            )
            question = None
            for token, worth in sorted(
                token_worth.items(), key=lambda item: -item[1]
            ):
                if worth <= 0.5:
                    break
                referent = self.mind.inferred_referent(token)
                if referent is None:
                    question = f"WHAT {token}"
                    break
                visible = any(oid == referent for oid in self.world.values())
                if not visible and token not in self.spatial_leads:
                    question = f"WHERE {token}"
                    break
            if question is not None and question not in                     self.pending_utterances:
                self.pending_utterances.appendleft(question)
                self.last_ask_at = now
                self.log(f"asking the group: {question}")

        # A comfortable, well-fed agent can seek a place its own drain
        # measurements identified as slow-starvation ground; resting near
        # warmth emerges from evidence, not from knowing what fire is.
        if hunger < 0.3:
            best_warmth = None
            for pos, object_id in self.world.items():
                if object_id <= 0:
                    continue
                comfort = self.mind.comfort_value(object_id)
                if comfort <= 0.15:
                    continue
                distance = abs(pos[0] - me.x) + abs(pos[1] - me.y)
                if distance <= 2 or distance > self.args.search_radius:
                    continue
                path = self._adjacent_path(me, pos)
                if len(path) < 2:
                    continue
                score = (m_comfort * self.args.comfort_weight * comfort
                         - 0.02 * distance)
                if best_warmth is None or score > best_warmth[0]:
                    best_warmth = (score, pos, path, object_id, comfort)
            if best_warmth is not None:
                proposals.append(ActionProposal(
                    "APPROACH_WARMTH", best_warmth[0],
                    f"learned comfort={best_warmth[4]:.2f} "
                    f"near object {best_warmth[3]}",
                    best_warmth[1][0], best_warmth[1][1],
                    path=best_warmth[2],
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
                    exploration_scale * self.args.novelty_weight * unseen
                    - 0.02 * distance
                    + movement_drive
                    + commitment_bonus("MOVE", pos[0], pos[1])
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
        if self.last_position != position:
            self.last_position = position
            self.last_position_change_at = now
            self.motions_since_progress = 0
            self.watchdog_attempts = 0
        elif self.last_position_change_at <= 0.0:
            self.last_position_change_at = now

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
                        habit_tags=queued.habit_tags,
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
            target_after = (
                trial.target_before
                if trial.action == "SELF"
                else self.world.get(
                    (trial.x, trial.y), trial.target_before
                )
            )
            learned, conjecture, outcome, reward = self.mind.observe_action_result(
                trial.action, trial.target_id, trial.held_before, me.held_object,
                trial.target_before,
                target_after,
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
                and trial.held_before > 0
                and trial.food_before is not None
                and self.food_store is not None
            ):
                # Claims are about the object that was actually tested, even
                # when eating left a different remainder object in hand.
                tested_token, _ = self.mind.word_for_object(trial.held_before)
                verified = self.food_store > trial.food_before
                if trial.held_before in self.mind.food_testimony:
                    trust_now = self.mind.record_testimony_outcome(
                        trial.held_before, verified
                    )
                    self.log(
                        f"verification of testified object "
                        f"{trial.held_before} "
                        f"{'succeeded' if verified else 'failed'}; "
                        f"mean source trust now {trust_now:.2f}"
                    )
                    if not verified:
                        correction = f"{tested_token} BAD"
                        if (
                            correction not in self.pending_utterances
                            and now - self.last_spoken.get(
                                correction, -math.inf
                            ) >= self.args.teach_interval
                        ):
                            self.pending_utterances.append(correction)
                            self.log(
                                f"queued {correction} after failed "
                                "verification of a food claim"
                            )
                if verified:
                    claim = f"{tested_token} FOOD"
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
            if self.perception.available and trial.action == "USE":
                # Learning transfers to how things *look*, not just to ids.
                self.mind.note_property_outcome(
                    self.perception.descriptor(trial.held_before)
                    if trial.held_before > 0 else (),
                    self.perception.descriptor(trial.target_before),
                    "transform",
                    reward > 0.4,
                )
            self.mind.note_task_outcome(
                "forage" if trial.action == "SELF" else "craft",
                reward > 0.4,
            )
            if self.goal_context is not None:
                goal, attempted_id, kind = self.goal_context
                self.goal_context = None
                if goal:
                    product = self.players.get(self.our_id)
                    produced = product.held_object if product else 0
                    if reward > 0.4:
                        # Whatever served the wanted state is now known to
                        # serve it, by experience rather than by prior.
                        self.mind.note_goal_satisfied(goal, attempted_id)
                        if produced > 0 and produced != trial.held_before:
                            self.mind.note_goal_satisfied(goal, produced, 0.5)
                        self.record_event(
                            "goal_progress", goal=goal, kind=kind,
                            object_id=attempted_id, produced=produced,
                        )
                        self.log(
                            f"{goal}: object {attempted_id} served it "
                            f"(produced {produced})"
                        )
                    elif kind == "GOAL_SEEK":
                        self.mind.note_goal_failed(goal, attempted_id)
            self.recent_contexts.append(
                f"use:{trial.held_before}|{trial.target_before}"
                if trial.action == "USE"
                else f"self:{trial.held_before}"
            )
            if reward > 0.4:
                self.mind.note_location_outcome(
                    trial.x, trial.y,
                    "food" if trial.action == "SELF" else "infrastructure",
                    min(1.0, reward),
                )
            self.record_event(
                "trial_result", action=trial.action,
                held_before=trial.held_before,
                target_before=trial.target_before,
                reward=round(reward, 3),
                status=conjecture.status,
            )
            if trial.habit_tags:
                # Meta-level reinforcement: the ways of thinking that chose
                # this act are themselves conjectures earning their keep.
                self.mind.credit_habits(trial.habit_tags, reward > 0.5)
            if reward >= 0.0:
                # Danger is a conjecture like any other: surviving contact
                # unharmed is evidence against it, so fear can be falsified
                # instead of accumulating forever.
                for contacted in (trial.target_before, trial.held_before):
                    if contacted > 0:
                        self.mind.weaken_danger(contacted)
            self.mind.retest_pairs.discard(
                f"{trial.held_before}|{trial.target_before}"
            )
            if trial.action == "SELF":
                self.mind.retest_pairs.discard(f"{trial.held_before}|-1")
            if (
                trial.action == "USE"
                and conjecture.status == "falsified"
                and trial.target_before > 0
            ):
                # Confession: a settled belief just failed me; saying so lets
                # others learn from a mistake they never made.
                a_token = (
                    "HAND" if trial.held_before <= 0
                    else self.mind.word_for_object(trial.held_before)[0]
                )
                b_token = self.mind.word_for_object(trial.target_before)[0]
                confession = f"MISTAKE {a_token} ON {b_token}"
                self.mind.add_narrative(
                    "falsified_use", a=a_token, b=b_token,
                )
                if (
                    confession not in self.pending_utterances
                    and now - self.last_spoken.get(confession, -math.inf)
                    >= self.args.teach_interval
                ):
                    self.pending_utterances.append(confession)
                    self.log(f"queued confession: {confession}")
            if trial.action == "USE":
                # My own test of a testified causal rule settles its sources'
                # reputations, exactly like Milestone 17 food claims.
                rule_key = f"{trial.held_before}|{trial.target_before}"
                rule_claim = self.mind.rule_testimony.get(rule_key)
                if rule_claim is not None:
                    expected_result = int(rule_claim.get("result", -999))
                    rule_verified = (
                        me.held_object == expected_result
                        or target_after == expected_result
                    )
                    trust_now = self.mind.record_rule_outcome(
                        rule_key, rule_verified
                    )
                    self.log(
                        f"verification of testified rule {rule_key} "
                        f"{'succeeded' if rule_verified else 'failed'}; "
                        f"mean source trust now {trust_now:.2f}"
                    )
                # A corroborated, useful transformation becomes teachable
                # culture: "<A> ON <B> MAKES <C>".
                if (
                    conjecture.status == "corroborated"
                    and trial.target_before > 0
                ):
                    if me.held_object != trial.held_before:
                        result_id = me.held_object
                    elif target_after != trial.target_before:
                        result_id = target_after
                    else:
                        result_id = 0
                    food_gain = "food_delta:0" not in outcome and re.search(
                        r"food_delta:[1-9]", outcome
                    )
                    useful = bool(food_gain) or (
                        result_id > 0
                        and self.mind.instrumental_values().get(
                            result_id, 0.0
                        ) > 0.0
                    )
                    if result_id > 0 and useful:
                        held_token = (
                            "HAND" if trial.held_before == 0
                            else self.mind.word_for_object(
                                trial.held_before
                            )[0]
                        )
                        target_token = self.mind.word_for_object(
                            trial.target_before
                        )[0]
                        result_token = self.mind.word_for_object(
                            result_id
                        )[0]
                        rule = (
                            f"{held_token} ON {target_token} "
                            f"MAKES {result_token}"
                        )
                        if (
                            rule not in self.pending_utterances
                            and now - self.last_spoken.get(rule, -math.inf)
                            >= self.args.teach_interval
                        ):
                            self.pending_utterances.append(rule)
                            self.log(
                                f"queued rule {rule} after corroborated "
                                "useful transformation"
                            )
            if trial.action == "DROP":
                # Do not immediately reacquire the object just released.
                self.blocked_until[(trial.x, trial.y)] = (
                    now + self.args.dropped_object_cooldown
                )
            self.pending_trial = None
        if self.pending_trial:
            return False

        if now - self.last_status_log >= self.args.status_interval:
            self.log(
                f"status: pos={position} "
                f"food={self.food_store}/{self.food_capacity} "
                f"held={me.held_object} peers={len(self.players) - 1} "
                f"goal={self.committed_goal[:3] if self.committed_goal else None}"
            )
            self.last_status_log = now
        if self.tracker is not None and self.our_id is not None:
            self.tracker.update(
                self.index, f"A{self.index}", me.x, me.y,
                self.current_mode,
            )

        # Affliction: an involuntary held-object change is felt harm.  The
        # wound and the nearest mover earn danger evidence, and the warning
        # becomes teachable culture.
        recently_acted = now - self.last_action_at <= 5.0
        wound_is_known_good = (
            me.held_object in self.mind.known_food_objects()
            or self.mind.action_knowledge(me.held_object, -1, "SELF")[1] > 0.2
        )
        if (
            self.last_own_held is not None
            and me.held_object != self.last_own_held
            and me.held_object > 0
            and self.pending_trial is None
            and self.motion is None
            # A held change right after my own action is my action's echo,
            # not harm; and a thing my own trials proved good is not a wound.
            and not recently_acted
            and not wound_is_known_good
        ):
            self.mind.note_danger_own(me.held_object, 1.0)
            culprit = None
            best = None
            for pos, oid in self.world.items():
                if oid in self.mover_ids:
                    d = abs(pos[0] - me.x) + abs(pos[1] - me.y)
                    if d <= 3 and (best is None or d < best):
                        best, culprit = d, oid
            if culprit is not None:
                self.mind.note_danger_own(culprit, 1.0)
            self.affliction_count += 1
            self.mind.note_location_outcome(me.x, me.y, "danger", 1.0)
            self.record_event("afflicted", wound=me.held_object)
            self.mind.add_narrative(
                "afflicted", wound=me.held_object, culprit=culprit,
            )
            warn_target = culprit if culprit is not None else me.held_object
            warn_token = self.mind.word_for_object(warn_target)[0]
            warning = f"{warn_token} HURTS"
            if warning not in self.pending_utterances:
                self.pending_utterances.appendleft(warning)
            self.log(
                f"afflicted: involuntary held change to {me.held_object}; "
                f"culprit={culprit}; queued {warning}"
            )
        self.last_own_held = me.held_object

        # Contemplation: safe idle time is spent rehearsing chains,
        # extracting recipes, replaying mistakes, reconsidering habits.
        hunger_now = (
            1.0 - self.food_store / max(1, self.food_capacity)
            if self.food_store is not None and self.food_capacity
            else 0.5
        )
        if getattr(self.args, "no_communication", False):
            # Control 5: speech disabled entirely, so only observation and
            # the world itself can carry knowledge between agents.
            self.pending_utterances.clear()
        # Developmental stage (Module 8) shapes what this life can do.
        stage_now = life_stage(me.age)
        if stage_now != self.stage:
            self.stage = stage_now
            if stage_now != self.last_stage_logged:
                self.last_stage_logged = stage_now
                self.log(f"life stage: {stage_now} (age {me.age:.1f})")
                self.record_event("stage_change", new_stage=stage_now)
        # Dependants nearby (Module 14): infants close enough to help.
        self.dependents = {
            pid: view.age for pid, view in self.players.items()
            if pid != self.our_id and view.age < 3.0
            and abs(view.x - me.x) + abs(view.y - me.y) <= 6
        }
        # Task selection (Module 13): pick the task whose urgency,
        # competence, and proximity beat switching and duplication costs.
        needs = self.local_needs(me, hunger_now)
        scored = {
            task: self.task_suitability(task, urgency, 1.0, now)
            for task, urgency in needs.items()
        }
        best_task = max(scored, key=lambda t: scored[t]) if scored else ""
        if best_task and best_task != self.current_task and (
            scored[best_task] > scored.get(self.current_task, -1.0)
        ):
            previous_task = self.current_task
            if previous_task:
                self.mind.note_task_outcome(previous_task, False)
            self.current_task = best_task
            self.task_started_at = now
            self.record_event(
                "task_switch", task=best_task,
                score=round(scored[best_task], 3),
                needs={k: round(v, 2) for k, v in needs.items()},
            )
            self.log(
                f"task: {best_task} "
                f"(competence {self.mind.task_competence(best_task):.2f})"
            )
            peers_here = self.nearby_peer_ids(me, self.args.language_radius)
            if peers_here and now - self.last_commit_at >= 30.0:
                utterance = f"COMMIT {best_task.upper()}"
                if utterance not in self.pending_utterances:
                    self.pending_utterances.append(utterance)
                    self.last_commit_at = now
        self.appraise_priority(me, now, hunger_now)
        if (
            self.mind.habit_factor("REHEARSE") > 0.0
            and hunger_now < 0.4
            and self.committed_goal is None
            and now - self.last_rehearse_at >= self.args.rehearse_interval
        ):
            if self.stage == "elder":
                # An elder has more to lose to death than to gain from
                # further testing: transmission becomes the priority.
                self.mind.habits.setdefault("REHEARSE", {})["active"] = True
            endorsements = self.mind.rehearse(
                time.time(), self.args.decay_halflife
            )
            for utterance in endorsements:
                if (
                    utterance not in self.pending_utterances
                    and now - self.last_spoken.get(utterance, -math.inf)
                    >= self.args.teach_interval
                ):
                    self.pending_utterances.append(utterance)
            self.last_rehearse_at = now
            self.log(
                f"contemplation: rehearsed workspace; "
                f"recipes={len(self.mind.recipes)} "
                f"retests={len(self.mind.retest_pairs)} "
                f"habits={[n for n, h in self.mind.habits.items() if h.get('active')]}"
            )

        # Infants cannot forage but they can watch and stay close: the
        # observation channel already runs, so what changes here is that
        # an infant prefers to remain beside adults, where demonstrations
        # and speech actually happen (Module 8).
        if self.stage == "infant":
            adults = [
                view for pid, view in self.players.items()
                if pid != self.our_id and view.age >= 14.0
            ]
            if adults:
                nearest = min(
                    adults,
                    key=lambda v: abs(v.x - me.x) + abs(v.y - me.y),
                )
                if abs(nearest.x - me.x) + abs(nearest.y - me.y) > 2:
                    self.mind.note_location_outcome(
                        me.x, me.y, "company", 0.5
                    )

        # Introduce myself once a listener exists, so reputation about me
        # can be spoken; endorse or warn about peers I have real evidence on.
        peers_close = self.nearby_peer_ids(me, self.args.language_radius)
        if peers_close and self.self_name is None:
            self.self_name = self.mind.invent_token()
            introduction = f"I AM {self.self_name}"
            if introduction not in self.pending_utterances:
                self.pending_utterances.append(introduction)
            self.log(f"introducing myself as {self.self_name}")
        if peers_close:
            for name, pid in list(self.mind.person_names.items()):
                if pid == self.our_id:
                    continue
                trust = self.mind.trust_in(pid)
                if 0.25 < trust < 0.8:
                    continue
                if now - self.last_reputation_at.get(pid, -math.inf) < 60.0:
                    continue
                verdict = "GOOD" if trust >= 0.8 else "BAD"
                gossip = f"{name} {verdict}"
                if gossip not in self.pending_utterances:
                    self.pending_utterances.append(gossip)
                    self.last_reputation_at[pid] = now
                    self.log(f"sharing reputation: {gossip}")

        proposals = self.propose_actions(me, now)
        if not proposals:
            return False
        chosen = max(proposals, key=lambda proposal: proposal.score)
        self.log(
            f"chose {chosen.kind} score={chosen.score:.2f}: {chosen.reason}"
        )
        if chosen.kind in (
            "MOVE", "ROAM", "DISPERSE", "WANDER", "DELIVER", "RETURN_HOME",
            "SEEK_CACHE", "PROBE", "APPROACH_WARMTH", "SEEK_LEAD", "RETREAT",
            "FOLLOW",
        ):
            acted = self.begin_motion(sock, chosen, now)
        elif chosen.kind in ("GOAL_SEEK", "GOAL_COMBINE", "GOAL_GATHER"):
            # Goal-directed acts are ordinary interactions: walk there and
            # use it, so the outcome is judged by the same machinery.
            queued = ActionProposal(
                "USE", chosen.score, chosen.reason,
                chosen.target_x, chosen.target_y, chosen.target_id,
                chosen.path,
            )
            acted = self.begin_motion(sock, queued, now)
            if acted:
                self.goal_context = (
                    self.active_goal, chosen.target_id, chosen.kind
                )
                self.goal_target = (
                    self.active_goal, chosen.target_id,
                    (chosen.target_x, chosen.target_y), now,
                )
                distance = abs(chosen.target_x - me.x) + abs(
                    chosen.target_y - me.y
                )
                if distance <= 1:
                    self.goal_attempts[
                        f"{self.active_goal}|{chosen.target_id}"
                    ] = time.monotonic()
                    self.goal_target = None
        elif chosen.kind == "APPROACH":
            acted = self.begin_motion(sock, chosen, now)
        elif chosen.kind == "SAY":
            if getattr(self.args, "no_communication", False):
                # Control 5: speech disabled, so only observation and the
                # world itself can carry knowledge between agents.
                self.pending_utterances.clear()
                return False
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
                    habit_tags=chosen.habit_tags,
                )
                acted = True
        if acted:
            self.last_action_at = now
            if chosen.kind in (
                "USE", "MOVE", "APPROACH", "SEEK_CACHE", "DELIVER",
                "RETURN_HOME",
            ):
                # Committing to the chosen goal adds hysteresis: finishing
                # what was started beats dithering between near-equal options.
                self.committed_goal = (
                    chosen.kind, chosen.target_x, chosen.target_y, now
                )
            if chosen.kind not in (
                "MOVE", "ROAM", "DISPERSE", "WANDER", "DELIVER",
                "RETURN_HOME", "APPROACH", "SEEK_CACHE", "PROBE",
                "APPROACH_WARMTH", "SEEK_LEAD", "RETREAT", "FOLLOW",
            ):
                self.stationary_action_streak += 1
        elif chosen.kind == "CARE":
            # Offer what I hold to a dependant: a USE aimed at the infant.
            payload = (
                f"USE {chosen.target_x} {chosen.target_y}\n#"
            ).encode()
            try:
                sock.sendall(payload)
                acted = True
                self.last_action_at = now
                self.mind.note_task_outcome("care", True)
                self.record_event(
                    "care_offered", dependant=chosen.target_id,
                    held=me.held_object,
                )
                self.log(
                    f"offering held object {me.held_object} to dependant "
                    f"{chosen.target_id}"
                )
            except OSError:
                acted = False
        elif chosen.kind in (
            "MOVE", "ROAM", "DISPERSE", "WANDER", "DELIVER",
            "RETURN_HOME", "APPROACH", "SEEK_CACHE", "PROBE",
            "APPROACH_WARMTH", "SEEK_LEAD", "RETREAT", "FOLLOW",
        ):
            # An unsendable movement must not spin the decision loop
            # forever on the same impossible goal.
            self.blocked_until[
                (chosen.target_x, chosen.target_y)
            ] = now + self.args.blocked_cooldown
            self.last_action_at = now
            self.log(
                f"movement proposal unsendable toward "
                f"({chosen.target_x},{chosen.target_y}); blocking briefly"
            )
        return acted

    def credit_delayed(self, channel: str, amount: float) -> None:
        """Attribute a later-arriving effect to what was recently done."""
        for context in list(self.recent_contexts)[-4:]:
            self.mind.note_delayed_effect(context, channel, amount / 4.0)

    def note_food_change(
        self, food: tuple[int, int], now: float
    ) -> None:
        """Track food and measure hunger-drain intervals as a comfort sensor.

        The interval between spontaneous one-point drops is the game's own
        signal for warmth and shelter quality; associating it with nearby
        objects lets place value be learned, never assumed.
        """
        store, capacity = food
        previous = self.food_store
        if previous is not None and store > previous:
            self.food_gain_count += 1
        self.food_store, self.food_capacity = store, capacity
        if previous is None or self.last_drain_at <= 0.0:
            self.last_drain_at = now
            return
        if store >= previous:
            # Eating or refill: restart the drain clock without a sample.
            self.last_drain_at = now
            return
        interval = now - self.last_drain_at
        self.last_drain_at = now
        eating = (
            self.pending_trial is not None
            and self.pending_trial.action == "SELF"
        )
        me = self.players.get(self.our_id) if self.our_id else None
        if eating or me is None or not 2.0 < interval < 90.0:
            return
        nearby = {
            object_id for pos, object_id in self.world.items()
            if object_id > 0
            and abs(pos[0] - me.x) + abs(pos[1] - me.y) <= 4
        }
        if nearby:
            self.mind.observe_comfort(nearby, interval)

    def _home_evidence(self, me: PlayerView, now: float) -> bool:
        """A HOME proposal must be backed by the proposer's own evidence.

        Evidence is anything this agent has learned to value near here:
        personally verified food, trusted testimony, or learned comfort.
        A patience fallback prevents a group that has learned nothing yet
        from deadlocking without any meeting place.
        """
        known_food = self.mind.known_food_objects()
        for pos, object_id in self.world.items():
            if object_id <= 0:
                continue
            if abs(pos[0] - me.x) + abs(pos[1] - me.y) > 6:
                continue
            if object_id in known_food:
                return True
            if self.mind.testimony_food_value(object_id) > 0.25:
                return True
            if self.mind.comfort_value(object_id) > 0.15:
                return True
            _, value, _, _ = self.mind.action_knowledge(0, object_id, "USE")
            if value > 0:
                return True
        if self.identity_seen_at is None:
            return True
        return now - self.identity_seen_at >= self.args.home_patience

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
            speaker = self.players.get(speaker_id)
            if speaker is None or (
                math.hypot(speaker.x - me.x, speaker.y - me.y)
                > self.args.language_radius
            ):
                continue
            commitment = re.fullmatch(r"COMMIT ([A-Z]+)", text)
            if commitment:
                task = commitment.group(1).lower()
                self.mind.note_commitment_heard(
                    speaker_id, task, time.time()
                )
                self.log(
                    f"player {speaker_id} committed to {task}; avoiding "
                    f"duplication"
                )
                continue
            help_request = re.fullmatch(r"HELP ([A-Z]+)", text)
            if help_request:
                task = help_request.group(1).lower()
                regard = self.mind.social_regard(speaker_id)
                if regard > 0.15 or self.mind.trust_in(speaker_id) > 0.6:
                    self.help_requests[task] = (speaker_id, time.monotonic())
                    self.log(
                        f"player {speaker_id} asked for help with {task} "
                        f"(regard {regard:.2f})"
                    )
                continue
            follow = re.fullmatch(r"FOLLOW ([A-Z]{2,8})", text)
            if follow:
                name = follow.group(1)
                subject = self.mind.person_names.get(name)
                if subject == self.our_id or name == self.self_name:
                    self.follow_target = (speaker_id, time.monotonic())
                    self.log(f"player {speaker_id} asked me to follow")
                continue
            avoid = re.fullmatch(r"AVOID ([A-Z]{2,8})", text)
            if avoid:
                token = avoid.group(1)
                referent = self.mind.inferred_referent(token)
                if referent is not None:
                    self.mind.hear_danger_testimony(referent, speaker_id)
                else:
                    self.mind.hear_token_danger(token, speaker_id)
                self.log(f"heard AVOID {token} from player {speaker_id}")
                continue
            bring = re.fullmatch(r"BRING ([A-Z]{2,8})", text)
            if bring:
                token = bring.group(1)
                referent = self.mind.inferred_referent(token)
                if referent is not None:
                    self.requests_heard[referent] = (
                        speaker_id, time.monotonic()
                    )
                    self.log(
                        f"player {speaker_id} asked for object {referent}"
                    )
                continue
            introduction = re.fullmatch(r"I AM ([A-Z]{2,8})", text)
            if introduction:
                name = introduction.group(1)
                self.mind.person_names[name] = speaker_id
                self.mind.save()
                self.log(f"player {speaker_id} is named {name}")
                continue
            endorsement = re.fullmatch(r"WAY ([A-Z]+) (GOOD|BAD)", text)
            if endorsement:
                name, verdict = endorsement.groups()
                if name in self.mind.modes:
                    self.mind.hear_mode_endorsement(
                        name, verdict == "GOOD", speaker_id
                    )
                    self.log(
                        f"heard priority endorsement: WAY {name} {verdict} "
                        f"from player {speaker_id}"
                    )
                else:
                    self.mind.hear_habit_endorsement(
                        name, verdict == "GOOD", speaker_id
                    )
                    self.log(
                        f"heard thinking-habit endorsement: WAY {name} "
                        f"{verdict} from player {speaker_id}"
                    )
                continue
            question = re.fullmatch(r"(WHAT|WHERE) ([A-Z]{2,8})", text)
            if question:
                _, token = question.groups()
                referent = self.mind.inferred_referent(token)
                if referent is None:
                    continue
                if me.held_object == referent:
                    if token not in self.pending_utterances:
                        self.pending_utterances.appendleft(token)
                    continue
                location = None
                best = None
                for pos, oid in self.world.items():
                    if oid != referent:
                        continue
                    d = abs(pos[0] - me.x) + abs(pos[1] - me.y)
                    if best is None or d < best:
                        best, location = d, pos
                if location is None:
                    continue
                dx = location[0] - me.x
                dy = location[1] - me.y
                direction = (
                    ("E" if dx >= 0 else "W")
                    if abs(dx) >= abs(dy)
                    else ("N" if dy >= 0 else "S")
                )
                bucket = "NEAR" if best <= 10 else "FAR"
                answer = f"{token} WAY {direction} {bucket}"
                if answer not in self.pending_utterances:
                    self.pending_utterances.appendleft(answer)
                self.log(f"answering {text} with {answer}")
                continue
            lead = re.fullmatch(
                r"([A-Z]{2,8}) WAY (N|S|E|W) (NEAR|FAR)", text
            )
            if lead:
                token, direction, bucket = lead.groups()
                distance = 6 if bucket == "NEAR" else 16
                vector = {
                    "N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0),
                }[direction]
                estimate = (
                    me.x + vector[0] * distance, me.y + vector[1] * distance
                )
                self.spatial_leads[token] = (
                    estimate, speaker_id, time.monotonic()
                )
                self.log(
                    f"spatial lead: {token} around {estimate} per player "
                    f"{speaker_id}"
                )
                continue
            hurts = re.fullmatch(r"([A-Z]{2,8}) HURTS", text)
            if hurts:
                token = hurts.group(1)
                referent = self.mind.inferred_referent(token)
                if referent is not None:
                    self.mind.hear_danger_testimony(referent, speaker_id)
                else:
                    self.mind.hear_token_danger(token, speaker_id)
                self.log(f"heard warning {text} from player {speaker_id}")
                continue
            teach = re.fullmatch(r"TEACH ([A-Z]{2,8})", text)
            if teach:
                self.recipe_buffers[speaker_id] = (
                    teach.group(1), time.monotonic()
                )
                self.log(
                    f"player {speaker_id} is teaching a recipe for "
                    f"{teach.group(1)}"
                )
                continue
            mistake = re.fullmatch(
                r"MISTAKE (HAND|[A-Z]{2,8}) ON ([A-Z]{2,8})", text
            )
            if mistake:
                a_token, b_token = mistake.groups()
                self.mind.contradict_token_rule(a_token, b_token)
                self.mind.add_narrative(
                    "heard_mistake", a=a_token, b=b_token,
                    speaker=speaker_id,
                )
                self.log(f"heard confession {text} from player {speaker_id}")
                continue
            rule = re.fullmatch(
                r"(HAND|[A-Z]{2,8}) ON ([A-Z]{2,8}) MAKES (HAND|[A-Z]{2,8})",
                text,
            )
            if rule:
                held_token, target_token, result_token = rule.groups()
                # The workspace keeps the rule in token form even when
                # nothing grounds: thought can run over words for things
                # never perceived, and grounding can arrive later.
                self.mind.hear_token_rule(
                    held_token, target_token, result_token, speaker_id
                )
                buffer = self.recipe_buffers.get(speaker_id)
                if buffer is not None:
                    product, opened_at = buffer
                    if time.monotonic() - opened_at <= 45.0:
                        recipe = self.mind.recipes.setdefault(
                            product,
                            {"steps": [], "source": speaker_id,
                             "fresh": time.time()},
                        )
                        if recipe.get("source") == speaker_id:
                            recipe["steps"].append(
                                [held_token, target_token, result_token]
                            )
                            recipe["fresh"] = time.time()
                            self.mind.save()
                    else:
                        self.recipe_buffers.pop(speaker_id, None)
                held_id = (
                    0 if held_token == "HAND"
                    else self.mind.inferred_referent(held_token)
                )
                target_id = self.mind.inferred_referent(target_token)
                result_id = (
                    0 if result_token == "HAND"
                    else self.mind.inferred_referent(result_token)
                )
                if held_id is not None and target_id is not None \
                        and result_id:
                    self.mind.hear_rule_testimony(
                        held_id, target_id, result_id, speaker_id
                    )
                self.mind.reinforce_social_context([speaker_id], 0.15)
                self.log(f"heard rule {text} from player {speaker_id}")
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
            match = re.fullmatch(r"([A-Z]{2,8})(?: (FOOD|BAD|GOOD))?", text)
            if not match:
                continue
            token, claim = match.groups()
            # Second-order language: a claim about a named *speaker* teaches
            # reputation through the same trust ledger everything else uses.
            if claim in ("GOOD", "BAD") and token in self.mind.person_names:
                subject = self.mind.person_names[token]
                if subject not in (speaker_id, self.our_id):
                    record = self.mind.source_trust.setdefault(
                        int(subject), {"helpful": 0, "failed": 0}
                    )
                    key = "helpful" if claim == "GOOD" else "failed"
                    record[key] = int(record.get(key, 0)) + 1
                    self.mind.save()
                    self.log(
                        f"taught reputation: {token} ({subject}) {claim} "
                        f"per player {speaker_id}"
                    )
                continue
            if claim == "GOOD":
                continue
            grounded_object = (
                speaker.held_object if speaker.held_object > 0
                else self.mind.inferred_referent(token)
            )
            if grounded_object is None:
                if claim == "FOOD":
                    # An ungrounded food claim still enters the workspace:
                    # the word alone can make its referent worth seeking.
                    self.mind.hear_token_food(token, speaker_id)
                    self.log(
                        f"heard ungrounded claim {text} from player "
                        f"{speaker_id}; stored in token form"
                    )
                continue
            if claim == "FOOD":
                hypothesis = self.mind.hear_food_testimony(
                    token, grounded_object, speaker_id
                )
                trials, value, _, _ = self.mind.action_knowledge(
                    grounded_object, -1, "SELF"
                )
                if trials >= 1 and value <= 0:
                    # Second-person correction: my own trials contradict the
                    # claim, so I tell the claimant, now.
                    counter = f"{token} BAD"
                    if counter not in self.pending_utterances:
                        self.pending_utterances.appendleft(counter)
                        self.log(
                            f"correcting player {speaker_id}: my own trials "
                            f"contradict {token} FOOD"
                        )
            elif claim == "BAD":
                hypothesis = self.mind.hear_food_contradiction(
                    token, grounded_object, speaker_id
                )
                if self.mind.trust_in(speaker_id) > 0.65:
                    # A trusted correction reopens my own settled test.
                    self.mind.demote_self_expectation(grounded_object)
                    self.log(
                        f"trusted correction from player {speaker_id}: "
                        f"re-testing object {grounded_object}"
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
            self._release_identity()
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
                                        self.note_food_change(
                                            food, time.monotonic()
                                        )

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
                lived = time.monotonic() - self.life_started_at
                self.record_event(
                    "life_end", lived_seconds=round(lived, 1),
                    cause=str(exc)[:120],
                    words=len(self.mind.object_words),
                    token_rules=len(self.mind.token_rules),
                    recipes=len(self.mind.recipes),
                )
                self.log(
                    f"life ended after {lived:.0f}s ({exc}); "
                    f"respawning in {self.args.respawn_delay:g}s"
                )
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
    parser.add_argument(
        "--verify-weight", type=float, default=1.5,
        help="Priority of independently testing a personally unverified food "
             "claim; scaled up as the claim's sources have earned less trust.",
    )
    parser.add_argument(
        "--cache-seek-weight", type=float, default=6.0,
        help="Priority of a hungry, empty-handed return trip to the adopted "
             "HOME cache, scaled by hunger.",
    )
    parser.add_argument(
        "--instrumental-weight", type=float, default=1.2,
        help="Weight of derived value propagated backward through the "
             "learned causal graph; makes useful crafting steps competitive "
             "even without immediate food payoff.",
    )
    parser.add_argument(
        "--staple-weight", type=float, default=0.9,
        help="Extra exploration priority for abundant, still-untested "
             "objects: learn the environment's staples first.",
    )
    parser.add_argument(
        "--commitment-bonus", type=float, default=1.0,
        help="Hysteresis in favor of continuing the currently committed "
             "goal instead of switching between near-equal options.",
    )
    parser.add_argument(
        "--commitment-ttl", type=float, default=20.0,
        help="Seconds a committed goal keeps its bonus before expiring.",
    )
    parser.add_argument(
        "--status-interval", type=float, default=30.0,
        help="Seconds between periodic per-agent status log lines.",
    )
    parser.add_argument(
        "--comfort-weight", type=float, default=0.8,
        help="Priority of moving toward objects whose learned comfort "
             "(slower measured hunger drain) is high, when well fed.",
    )
    parser.add_argument(
        "--home-patience", type=float, default=90.0,
        help="Seconds after first identity before HOME may be proposed "
             "without any learned evidence supporting the location.",
    )
    parser.add_argument(
        "--future-discount", type=float, default=0.6,
        help="Discount on learned delayed effects in temporal planning.",
    )
    parser.add_argument(
        "--planning-weight", type=float, default=0.8,
        help="Weight of the expected-value comparison in action choice.",
    )
    parser.add_argument(
        "--dependant-weight", type=float, default=0.6,
        help="Weight of effects on dependants in expected value.",
    )
    parser.add_argument(
        "--information-weight", type=float, default=0.4,
        help="Weight of information gain in expected value.",
    )
    parser.add_argument(
        "--effort-weight", type=float, default=0.5,
        help="Weight of effort cost in expected value.",
    )
    parser.add_argument(
        "--risk-weight", type=float, default=1.5,
        help="Weight of risk in expected value.",
    )
    parser.add_argument(
        "--switching-cost", type=float, default=0.25,
        help="Cost of abandoning the current task for another.",
    )
    parser.add_argument(
        "--duplication-penalty", type=float, default=0.4,
        help="Penalty for taking a task another agent has committed to.",
    )
    parser.add_argument(
        "--follow-weight", type=float, default=3.0,
        help="Priority of following an agent who asked, scaled by regard.",
    )
    parser.add_argument(
        "--no-communication", action="store_true",
        help="Control 5: disable all speech, to measure how much "
             "generational persistence depends on teaching.",
    )
    parser.add_argument(
        "--no-observation", action="store_true",
        help="Ablation: disable learning by watching peers.",
    )
    parser.add_argument(
        "--no-properties", action="store_true",
        help="Ablation: ignore visual properties and priors, so the agent "
             "must memorize object ids (the comparison agent for "
             "Phase 4 transfer tests).",
    )
    parser.add_argument(
        "--no-priors", action="store_true",
        help="Ablation: keep property generalization but drop the general "
             "appearance priors.",
    )
    parser.add_argument(
        "--id-shuffle-seed", type=int, default=0,
        help="Control 2: deterministically remap object ids as perceived "
             "by the agent.  Memorizers collapse; property learners do "
             "not.  0 disables remapping.",
    )
    parser.add_argument(
        "--goal-weight", type=float, default=4.0,
        help="Priority of goal-directed action: pursuing a wanted "
             "state by seeking something that satisfies it or "
             "trying to make one.",
    )
    parser.add_argument(
        "--hints", choices=("off", "names", "full"), default="off",
        help="How much of the game's own hint system the agents "
             "may use, as a player does: 'names' gives object "
             "descriptions on sight, 'full' adds the transition "
             "list shown on click.",
    )
    parser.add_argument(
        "--goal-commit-ttl", type=float, default=25.0,
        help="Seconds committed to a chosen goal target.",
    )
    parser.add_argument(
        "--goal-retry-interval", type=float, default=90.0,
        help="Seconds before the same object may be tried again "
             "for the same goal.",
    )
    parser.add_argument(
        "--tracker-file", type=str, default=None,
        help="Write agent positions here for the game client's "
             "on-screen markers.",
    )
    parser.add_argument(
        "--event-log-dir", type=str, default=None,
        help="Directory for structured per-life JSONL event logs.",
    )
    parser.add_argument(
        "--data-dir", type=str, default=None,
        help="OneLife data directory (containing objects/ and sprites/) "
             "used for visual perception; auto-detected when omitted.",
    )
    parser.add_argument(
        "--prior-weight", type=float, default=2.0,
        help="Weight of general appearance priors when choosing untried "
             "interactions.",
    )
    parser.add_argument(
        "--generalization-weight", type=float, default=2.0,
        help="Weight of property-level generalization from past outcomes.",
    )
    parser.add_argument(
        "--location-weight", type=float, default=1.5,
        help="Weight of learned place value in action choice.",
    )
    parser.add_argument(
        "--care-weight", type=float, default=5.0,
        help="Priority of offering held nourishment to a nearby infant.",
    )
    parser.add_argument(
        "--urgency-dwell", type=float, default=8.0,
        help="Minimum seconds in SAFE before hunger may preempt it; "
             "with threat hysteresis this prevents fear/hunger thrash.",
    )
    parser.add_argument(
        "--mode-dwell", type=float, default=20.0,
        help="Seconds a discretionary priority mode is committed to "
             "before reflective reallocation.",
    )
    parser.add_argument(
        "--threat-threshold", type=float, default=0.5,
        help="Nearby danger value at which the SAFE priority preempts "
             "everything else.",
    )
    parser.add_argument(
        "--feed-hunger", type=float, default=0.55,
        help="Hunger at which the FEED priority preempts discretionary "
             "modes.",
    )
    parser.add_argument(
        "--decay-halflife", type=float, default=480.0,
        help="Seconds for an unrehearsed token rule's confidence to halve; "
             "rehearsal (inner speech) is what sustains long chains.",
    )
    parser.add_argument(
        "--rehearse-interval", type=float, default=45.0,
        help="Seconds between contemplation windows when safe and idle.",
    )
    parser.add_argument(
        "--lead-weight", type=float, default=3.5,
        help="Priority of following a spoken spatial lead toward a valued "
             "referent that is nowhere in sight.",
    )
    parser.add_argument(
        "--ask-interval", type=float, default=25.0,
        help="Minimum seconds between spoken WHAT/WHERE questions.",
    )
    parser.add_argument(
        "--stuck-timeout", type=float, default=40.0,
        help="Seconds without any position change, despite issued motion, "
             "before the stuck watchdog clears stale avoidance state and "
             "probes adjacent tiles directly.",
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
    # One shared perception cache: sprite analysis is identical for every
    # agent and expensive to repeat.  Perceiving is not knowing -- what an
    # appearance affords must still be learned by each agent alone.
    configure_id_shuffle(getattr(args, "id_shuffle_seed", 0) or 0)
    tracker = AgentTrackerFile(getattr(args, "tracker_file", None))
    perception = VisualPerception(getattr(args, "data_dir", None))
    print(
        f"Starting {args.count} open-ended expectation-learning agents. "
        f"Private memories: {args.memory_dir}/. "
        + (
            f"Visual perception: {perception.data_dir}. "
            if perception.available
            else "Visual perception: unavailable (running property-blind). "
        )
        + f"Hints: {getattr(args, 'hints', 'off')}. "
        + "Press Ctrl+C to stop.",
        flush=True,
    )
    for index in range(1, args.count + 1):
        session = AgentSession(
            index, args, credentials, stop, perception, tracker
        )
        sessions.append(session)
        session.start()
        if index != args.count and stop.wait(args.stagger):
            break
    for session in sessions:
        session.join()
    return 0 if sessions and all(s.result == 0 for s in sessions) else 1


if __name__ == "__main__":
    raise SystemExit(main())

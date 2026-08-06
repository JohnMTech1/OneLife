#!/usr/bin/env python3
"""Metrics harness for the emergent-survival roadmap.

Reads the structured per-life JSONL event logs and the persisted minds,
and reports the measures the roadmap asks for, phase by phase.

Usage:
    python3 experiment_metrics.py events_m26/ agent_memory_m26/
    python3 experiment_metrics.py events_m26/ agent_memory_m26/ --json out.json

Reported:
    Phase 2  survival baseline: lifespans, causes, distance, interactions
    Phase 3  object beliefs: transitions discovered, reuse, failure rate
    Phase 4  generalization: property expectations and their evidence
    Phase 5  experimentation: discoveries per life, attempts per discovery,
             time to first food
    Phase 6  transmission: what crossed lives and by which channel
    Phase 7  maintenance: repeat interaction with the same context
    Phase 8  infrastructure: investment acts and delayed pay-offs
    Phase 9  coordination: task shares, switching, duplication, roles
    Phase 10 settlement: occupancy clustering and persistence
    Phase 11 divergence: how far apart two populations' cultures drifted
"""
import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_events(directory: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.jsonl")):
        for line in path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    events.sort(key=lambda event: event.get("t", 0.0))
    return events


def load_minds(directory: Path) -> dict[str, dict[str, Any]]:
    minds: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            minds[path.stem] = json.loads(
                path.read_text(encoding="utf-8", errors="replace")
            )
        except (OSError, json.JSONDecodeError):
            continue
    return minds


def heading(title: str) -> None:
    print(f"\n=== {title} " + "=" * max(0, 60 - len(title)))


def phase2_survival(events: list[dict], report: dict) -> None:
    heading("Phase 2  survival baseline")
    ends = [e for e in events if e.get("kind") == "life_end"]
    starts = [e for e in events if e.get("kind") == "life_start"]
    durations = [
        float(e.get("lived_seconds", 0.0)) for e in ends
        if e.get("lived_seconds") is not None
    ]
    causes = Counter(str(e.get("cause", "unknown"))[:40] for e in ends)
    positions: dict[tuple, list[tuple[int, int]]] = defaultdict(list)
    for event in events:
        if event.get("x") is not None:
            positions[(event.get("agent"), event.get("life"))].append(
                (event["x"], event["y"])
            )
    travel = []
    for track in positions.values():
        distance = sum(
            abs(track[i][0] - track[i - 1][0])
            + abs(track[i][1] - track[i - 1][1])
            for i in range(1, len(track))
        )
        travel.append(distance)
    trials = [e for e in events if e.get("kind") == "trial_result"]
    useful = [e for e in trials if float(e.get("reward", 0.0)) > 0.4]
    report["lives_started"] = len(starts)
    report["lives_ended"] = len(ends)
    report["mean_lifespan_s"] = (
        sum(durations) / len(durations) if durations else None
    )
    print(f"  lives started/ended: {len(starts)}/{len(ends)}")
    if durations:
        durations_sorted = sorted(durations)
        median = durations_sorted[len(durations_sorted) // 2]
        print(f"  lifespan min/median/mean/max: {min(durations):.0f}s / "
              f"{median:.0f}s / {sum(durations) / len(durations):.0f}s / "
              f"{max(durations):.0f}s")
    else:
        print("  no completed lives yet (agents may still be alive, or "
              "mortality is disabled on the server)")
    if causes:
        print("  death causes: " + ", ".join(
            f"{cause} x{count}" for cause, count in causes.most_common(5)
        ))
    if travel:
        print(f"  distance travelled per life (mean): "
              f"{sum(travel) / len(travel):.0f} tiles")
    print(f"  interactions: {len(trials)} "
          f"({len(useful)} rewarding, "
          f"{100.0 * len(useful) / max(1, len(trials)):.0f}%)")


def phase3_beliefs(minds: dict, events: list[dict], report: dict) -> None:
    heading("Phase 3  object belief memory")
    for name, mind in minds.items():
        transitions = mind.get("transitions", {})
        corroborated = sum(
            1 for outcomes in transitions.values()
            for record in outcomes.values()
            if record.get("status") == "corroborated"
        )
        falsified = sum(
            1 for outcomes in transitions.values()
            for record in outcomes.values()
            if record.get("status") == "falsified"
        )
        print(f"  {name[:34]:34} contexts={len(transitions):4} "
              f"corroborated={corroborated:4} falsified={falsified:4} "
              f"words={len(mind.get('object_words', {})):3}")
    report["corroborated_total"] = sum(
        sum(
            1 for outcomes in mind.get("transitions", {}).values()
            for record in outcomes.values()
            if record.get("status") == "corroborated"
        ) for mind in minds.values()
    )


def phase4_generalization(minds: dict, report: dict) -> None:
    heading("Phase 4  property-based generalization")
    total = 0
    for name, mind in minds.items():
        properties = mind.get("property_expectations", {})
        total += len(properties)
        strong = [
            (key, record) for key, record in properties.items()
            if int(record.get("successes", 0)) >= 2
        ]
        print(f"  {name[:34]:34} property rules={len(properties):3} "
              f"well-evidenced={len(strong):3}")
        for key, record in sorted(
            strong, key=lambda item: -int(item[1].get("successes", 0))
        )[:3]:
            successes = int(record.get("successes", 0))
            failures = int(record.get("failures", 0))
            print(f"      {key[:64]}  +{successes}/-{failures}")
    report["property_rules"] = total
    if total == 0:
        print("  (none yet: check that visual perception found the game "
              "data, and that agents have made successful interactions)")


def phase5_experimentation(events: list[dict], report: dict) -> None:
    heading("Phase 5  hypothesis-driven experimentation")
    by_life: dict[tuple, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("kind") == "trial_result":
            by_life[(event.get("agent"), event.get("life"))].append(event)
    discoveries_per_life = []
    attempts_per_discovery = []
    for trials in by_life.values():
        discoveries = [
            t for t in trials if float(t.get("reward", 0.0)) > 0.4
        ]
        discoveries_per_life.append(len(discoveries))
        if discoveries:
            attempts_per_discovery.append(len(trials) / len(discoveries))
    first_food = []
    starts = {
        (e.get("agent"), e.get("life")): e.get("t")
        for e in events if e.get("kind") == "life_start"
    }
    seen: set = set()
    for event in events:
        key = (event.get("agent"), event.get("life"))
        if (
            event.get("kind") == "trial_result"
            and event.get("action") == "SELF"
            and float(event.get("reward", 0.0)) > 0.4
            and key not in seen and key in starts
        ):
            seen.add(key)
            first_food.append(float(event["t"]) - float(starts[key]))
    if discoveries_per_life:
        print(f"  useful discoveries per life (mean): "
              f"{sum(discoveries_per_life) / len(discoveries_per_life):.2f}")
    if attempts_per_discovery:
        print(f"  attempts per discovery (mean): "
              f"{sum(attempts_per_discovery) / len(attempts_per_discovery):.1f}")
    if first_food:
        print(f"  time to first food (mean): "
              f"{sum(first_food) / len(first_food):.0f}s over "
              f"{len(first_food)} lives")
        report["time_to_first_food_s"] = (
            sum(first_food) / len(first_food)
        )
    else:
        print("  no rewarding SELF trial recorded yet")


def phase6_transmission(minds: dict, events: list[dict],
                        report: dict) -> None:
    heading("Phase 6  transmission across lives")
    lives = defaultdict(set)
    for name in minds:
        parts = name.split("_")
        if len(parts) >= 4:
            lives[parts[1]].add(parts[3])
    heard = Counter()
    for mind in minds.values():
        for record in mind.get("rule_testimony", {}).values():
            provenance = record.get("provenance", "spoken")
            heard[provenance] += 1
        heard["food_claims"] += len(mind.get("food_testimony", {}))
        heard["token_rules"] += len(mind.get("token_rules", {}))
        heard["recipes"] += len(mind.get("recipes", {}))
    print("  knowledge held by cultural channel:")
    for channel, count in heard.most_common():
        print(f"      {channel:14} {count}")
    shared: Counter = Counter()
    for mind in minds.values():
        for key in mind.get("token_rules", {}):
            shared[key] += 1
    redundant = [key for key, count in shared.items() if count >= 2]
    print(f"  rules held by 2+ living minds (survive one death): "
          f"{len(redundant)} of {len(shared)}")
    report["redundant_rules"] = len(redundant)


def phase7_maintenance(events: list[dict], report: dict) -> None:
    heading("Phase 7  maintenance behaviour")
    contexts = Counter(
        f"{e.get('held_before')}|{e.get('target_before')}"
        for e in events if e.get("kind") == "trial_result"
    )
    repeated = [(key, count) for key, count in contexts.items() if count >= 3]
    print(f"  repeatedly revisited interactions: {len(repeated)}")
    for key, count in sorted(repeated, key=lambda item: -item[1])[:5]:
        print(f"      {key:20} x{count}")
    report["repeated_contexts"] = len(repeated)


def phase8_infrastructure(minds: dict, report: dict) -> None:
    heading("Phase 8  infrastructure and delayed value")
    total_delayed = 0
    for name, mind in minds.items():
        delayed = mind.get("delayed_effects", {})
        total_delayed += len(delayed)
        places = mind.get("location_value", {})
        best = sorted(
            places.items(),
            key=lambda item: -(
                float(item[1].get("food", 0.0))
                + float(item[1].get("comfort", 0.0))
                + float(item[1].get("infrastructure", 0.0))
            ),
        )[:3]
        print(f"  {name[:34]:34} delayed-effect contexts={len(delayed):3} "
              f"valued places={len(places):3}")
        for key, record in best:
            summary = ", ".join(
                f"{channel}={value:.1f}"
                for channel, value in record.items() if channel != "visits"
            )
            print(f"      cell {key:10} {summary}")
    report["delayed_contexts"] = total_delayed


def phase9_coordination(events: list[dict], minds: dict,
                        report: dict) -> None:
    heading("Phase 9  task coordination and roles")
    switches = [e for e in events if e.get("kind") == "task_switch"]
    tasks = Counter(e.get("task") for e in switches)
    per_agent: dict[Any, Counter] = defaultdict(Counter)
    for event in switches:
        per_agent[event.get("agent")][event.get("task")] += 1
    print(f"  task switches: {len(switches)}; distribution: "
          + ", ".join(f"{task}:{count}" for task, count in tasks.most_common()))
    for agent, counts in sorted(per_agent.items(), key=lambda kv: str(kv[0])):
        total = sum(counts.values())
        dominant, share = counts.most_common(1)[0]
        print(f"      agent {agent}: dominant={dominant} "
              f"({100.0 * share / max(1, total):.0f}% of switches)")
    for name, mind in minds.items():
        competence = mind.get("competence", {})
        if not competence:
            continue
        ranked = sorted(
            competence.items(),
            key=lambda item: -(
                float(item[1].get("successes", 0.0))
                / max(1.0, float(item[1].get("attempts", 1.0)))
            ),
        )
        summary = ", ".join(
            f"{task} {float(rec.get('successes', 0)):.0f}/"
            f"{float(rec.get('attempts', 0)):.0f}"
            for task, rec in ranked[:4]
        )
        print(f"  {name[:34]:34} competence: {summary}")
    report["task_switches"] = len(switches)


def phase10_settlement(events: list[dict], report: dict) -> None:
    heading("Phase 10  settlement emergence")
    cell = 8
    occupancy: Counter = Counter()
    occupants: dict[str, set] = defaultdict(set)
    times: dict[str, list[float]] = defaultdict(list)
    for event in events:
        if event.get("x") is None:
            continue
        key = f"{event['x'] // cell}:{event['y'] // cell}"
        occupancy[key] += 1
        occupants[key].add(event.get("agent"))
        times[key].append(float(event.get("t", 0.0)))
    settlements = []
    for key, count in occupancy.items():
        span = (
            max(times[key]) - min(times[key]) if len(times[key]) > 1 else 0.0
        )
        if count >= 20 and len(occupants[key]) >= 2 and span >= 120.0:
            settlements.append((key, count, len(occupants[key]), span))
    print(f"  candidate settlements (>=2 agents, >=20 samples, >=2 min): "
          f"{len(settlements)}")
    for key, count, agents, span in sorted(
        settlements, key=lambda item: -item[1]
    )[:5]:
        print(f"      cell {key:10} samples={count:5} agents={agents} "
              f"occupied over {span / 60.0:.1f} min")
    report["settlements"] = len(settlements)
    if not settlements:
        print("  (none: agents have not yet co-located persistently)")


def phase11_divergence(minds: dict, report: dict) -> None:
    heading("Phase 11  cultural divergence")
    vocabularies = {
        name: set(mind.get("object_words", {}).items())
        for name, mind in minds.items()
    }
    names = list(vocabularies)
    if len(names) < 2:
        print("  need at least two minds to compare")
        return
    print("  pairwise vocabulary agreement (shared name for same object):")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            first, second = vocabularies[names[i]], vocabularies[names[j]]
            union = first | second
            shared = first & second
            agreement = len(shared) / max(1, len(union))
            print(f"      {names[i][:22]:22} vs {names[j][:22]:22} "
                  f"{100.0 * agreement:.0f}%")
    report["vocab_pairs"] = len(names) * (len(names) - 1) // 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("events_dir")
    parser.add_argument("memory_dir")
    parser.add_argument("--json", dest="json_out", default=None)
    args = parser.parse_args()
    events_dir, memory_dir = Path(args.events_dir), Path(args.memory_dir)
    if not events_dir.is_dir():
        print(f"no event directory: {events_dir}")
        print("run the agents with --event-log-dir to produce one")
        return 2
    events = load_events(events_dir)
    minds = load_minds(memory_dir)
    print(f"loaded {len(events)} events and {len(minds)} minds")
    report: dict[str, Any] = {}
    phase2_survival(events, report)
    phase3_beliefs(minds, events, report)
    phase4_generalization(minds, report)
    phase5_experimentation(events, report)
    phase6_transmission(minds, events, report)
    phase7_maintenance(events, report)
    phase8_infrastructure(minds, report)
    phase9_coordination(events, minds, report)
    phase10_settlement(events, report)
    phase11_divergence(minds, report)
    heading("Controls in force")
    print("  Control 1 (no object names): perception reads sprite pixels")
    print("             only; object name lines are skipped by design.")
    print("  Control 2 (id randomization): rerun with --id-shuffle-seed N")
    print("  Control 3 (novel objects): compare property rules before and")
    print("             after introducing unseen but similar objects.")
    print("  Control 4 (no construction reward): no term anywhere rewards")
    print("             building; value comes from delayed effects only.")
    print("  Control 5 (no communication): rerun with --no-communication")
    print("  Control 6 (no observation): rerun with --no-observation")
    print("  Control 7 (memory reset at death): every life starts blank by")
    print("             construction; see 'new life' lines in the log.")
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(f"\nwrote summary to {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

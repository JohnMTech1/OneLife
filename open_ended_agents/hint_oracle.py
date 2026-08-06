"""The in-game hint system, made available to the agents.

Human players do not face an unlabelled world.  Hovering an object shows
its description, and clicking it lists the transitions it takes part in,
cycled with the tab key.  This module gives the agents the same two
affordances, read from the same game data the client reads, so a run can
put agents on a par with a person sitting at the keyboard.

Three levels, chosen at run time:

    off     nothing (pure discovery: the agent learns everything itself)
    names   object descriptions only, as on mouse-over
    full    descriptions plus the transition hints shown on click

The transition filter mirrors the client's own getTransHintable rules --
no category or pattern objects, no last-use variants, no generic
one-time-use transitions -- so what an agent can consult is what a
player can actually read on screen, not the raw table.

Hints are *available*, not injected: the agent must look at the object,
and what it learns arrives tagged with a hint provenance so its
influence stays measurable and it remains falsifiable like any other
second-hand claim.
"""
from __future__ import annotations

import re
from pathlib import Path


class HintOracle:
    """Object descriptions and transition hints from the game data."""

    def __init__(self, data_dir: Path | None, level: str = "off") -> None:
        self.level = level if level in ("off", "names", "full") else "off"
        self.data_dir = data_dir if self.level != "off" else None
        self._descriptions: dict[int, str] = {}
        self._by_actor: dict[int, list[tuple[int, int, int, int]]] = {}
        self._loaded_transitions = False
        self._categories: set[int] = set()

    @property
    def available(self) -> bool:
        return self.level != "off" and self.data_dir is not None

    # ---- names, as shown on mouse-over ----

    def description(self, object_id: int) -> str:
        """The object's own description line, exactly as a player sees."""
        if not self.available or object_id <= 0:
            return ""
        cached = self._descriptions.get(object_id)
        if cached is not None:
            return cached
        text = ""
        try:
            path = self.data_dir / "objects" / f"{object_id}.txt"
            lines = path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            if len(lines) > 1:
                # Line 0 is "id=N"; line 1 is the description.
                text = lines[1].strip()
        except OSError:
            text = ""
        # Descriptions carry variant suffixes after '#'; players see the
        # base name, so strip them.
        text = text.split("#", 1)[0].strip()
        self._descriptions[object_id] = text
        return text

    def word_from_description(self, object_id: int) -> str:
        """Return the complete visible label as a stable language token.

        The earlier implementation kept only one word (for example STONE
        from SHARP STONE), which collapsed distinct in-game objects back
        into an invented vocabulary.  Underscores preserve the complete
        human-visible name while keeping it a single token for the agent's
        existing speech grammar.
        """
        text = self.description(object_id)
        if not text:
            return ""
        words = re.findall(r"[A-Za-z0-9]+", text.upper())
        if not words:
            return ""
        return "_".join(words)[:80]

    # ---- transitions, as shown on click ----

    def _category_ids(self) -> set[int]:
        if self._categories or self.data_dir is None:
            return self._categories
        folder = self.data_dir / "categories"
        if folder.is_dir():
            for path in folder.glob("*.txt"):
                try:
                    self._categories.add(int(path.stem))
                except ValueError:
                    continue
        return self._categories

    def _load_transitions(self) -> None:
        if self._loaded_transitions or self.data_dir is None:
            return
        self._loaded_transitions = True
        folder = self.data_dir / "transitions"
        if not folder.is_dir():
            return
        categories = self._category_ids()
        name_pattern = re.compile(r"^(-?\d+)_(-?\d+)(_[A-Z]+)*$")
        for path in folder.glob("*.txt"):
            match = name_pattern.match(path.stem)
            if match is None:
                continue
            # Last-use variants are not shown as hints.
            if match.group(3):
                continue
            actor = int(match.group(1))
            target = int(match.group(2))
            try:
                first = path.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()[0]
            except (OSError, IndexError):
                continue
            parts = first.split()
            if len(parts) < 2:
                continue
            try:
                new_actor = int(parts[0])
                new_target = int(parts[1])
            except ValueError:
                continue
            # Mirror the client's hintable filter.
            if actor < 0 or (target <= 0 and target != -1):
                continue
            if new_actor <= 0 and new_target <= 0:
                continue
            if actor in categories or target in categories:
                continue
            if target == -1 and new_target == 0:
                continue
            self._by_actor.setdefault(actor, []).append(
                (actor, target, new_actor, new_target)
            )
            if target > 0:
                self._by_actor.setdefault(target, []).append(
                    (actor, target, new_actor, new_target)
                )

    def hints_for(
        self, object_id: int, limit: int = 12,
    ) -> list[tuple[int, int, int, int]]:
        """Transitions this object takes part in, as listed on click."""
        if not self.available or self.level != "full" or object_id <= 0:
            return []
        self._load_transitions()
        return self._by_actor.get(object_id, [])[:limit]

    def hint_count(self, object_id: int) -> int:
        return len(self.hints_for(object_id, limit=10 ** 6))

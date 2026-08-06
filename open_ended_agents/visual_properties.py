"""Visual perception for the open-ended agents.

Human players do not face raw combinatorics when they pick up a sharp
stone and a branch: they *see* that one is pointed and the other is long
and fibrous, and that prunes the search enormously.  This module gives
the agents the same kind of pruning, and it does so honestly.

What it reads:
    * sprite bitmaps (.tga) referenced by an object definition, from
      which it computes geometry (elongation, taper/pointedness, fill,
      size) and colour statistics;
    * the object definition's *numeric* fields only -- permanence,
      sprite ids, held offsets -- which describe what is visible.

What it deliberately never reads:
    * the object's NAME (that would smuggle in "sharp stone" as
      knowledge rather than perception);
    * any transition, recipe, or food data.

Everything downstream is uncertain: properties are graded appearances,
and what an appearance is *good for* must still be learned, taught, or
falsified by the agent itself.

If the game data cannot be found, every function degrades to "no
properties known" and the agents behave exactly as they did before.
"""
from __future__ import annotations

import os
import re
import struct
from pathlib import Path
from typing import Any

# Property names are domain-general appearances, not game functions.
PROPERTY_NAMES = (
    "elongated",     # long and thin
    "pointed",       # tapers to a narrow end
    "large",
    "portable",      # not fixed to the ground
    "stone_like",    # grey, low saturation, compact
    "wooden",        # brown hues
    "green_growth",  # green hues (plants, foliage)
    "fibrous",       # thin, stringy, high edge density
    "container",     # wide with an open/hollow interior
    "bright",        # high luminance (fire, metal, water glare)
    "warm_coloured",  # red/orange/yellow dominant
)


def _candidate_data_roots(explicit: str | None = None) -> list[Path]:
    roots: list[Path] = []
    if explicit:
        roots.append(Path(explicit))
    env = os.environ.get("OHOL_DATA_DIR")
    if env:
        roots.append(Path(env))
    here = Path(__file__).resolve().parent
    for base in (here.parent, here.parent.parent, here.parent.parent.parent):
        roots.extend([
            base / "OneLifeData7",
            base / "gameSource" / "OneLifeData7",
            base / "server" / "OneLifeData7",
            base / "gameSource",
            base / "OneLife" / "gameSource",
        ])
    return roots


def find_data_dir(explicit: str | None = None) -> Path | None:
    """Locate a directory containing objects/ and sprites/ subfolders.

    An explicitly supplied path is authoritative: if it does not hold the
    data, perception stays unavailable rather than silently falling back
    to some other directory.  That matters for the ablation runs, where
    property-blind really has to mean blind.
    """
    if explicit:
        root = Path(explicit)
        try:
            if (root / "objects").is_dir() and (root / "sprites").is_dir():
                return root
        except OSError:
            pass
        return None
    for root in _candidate_data_roots(explicit):
        try:
            if (root / "objects").is_dir() and (root / "sprites").is_dir():
                return root
        except OSError:
            continue
    return None


def _read_tga_mask(path: Path, max_pixels: int = 65536
                   ) -> tuple[int, int, list[tuple[int, int, int, int]]] | None:
    """Minimal TGA reader: returns (width, height, pixels RGBA).

    Handles uncompressed and RLE truecolour images, which is what the
    game ships.  Returns None on anything unexpected rather than raising.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 18:
        return None
    id_length = data[0]
    image_type = data[2]
    width, height = struct.unpack_from("<HH", data, 12)
    depth = data[16]
    descriptor = data[17]
    if width <= 0 or height <= 0 or width * height > max_pixels:
        return None
    if depth not in (24, 32) or image_type not in (2, 10):
        return None
    bytes_per_pixel = depth // 8
    offset = 18 + id_length
    pixels: list[tuple[int, int, int, int]] = []
    total = width * height
    try:
        if image_type == 2:
            for index in range(total):
                start = offset + index * bytes_per_pixel
                blue, green, red = data[start], data[start + 1], data[start + 2]
                alpha = data[start + 3] if bytes_per_pixel == 4 else 255
                pixels.append((red, green, blue, alpha))
        else:  # RLE
            index = offset
            while len(pixels) < total and index < len(data):
                packet = data[index]
                index += 1
                count = (packet & 0x7F) + 1
                if packet & 0x80:
                    blue, green, red = (
                        data[index], data[index + 1], data[index + 2]
                    )
                    alpha = (
                        data[index + 3] if bytes_per_pixel == 4 else 255
                    )
                    index += bytes_per_pixel
                    pixels.extend([(red, green, blue, alpha)] * count)
                else:
                    for _ in range(count):
                        blue, green, red = (
                            data[index], data[index + 1], data[index + 2]
                        )
                        alpha = (
                            data[index + 3] if bytes_per_pixel == 4 else 255
                        )
                        index += bytes_per_pixel
                        pixels.append((red, green, blue, alpha))
    except IndexError:
        return None
    if len(pixels) < total:
        return None
    pixels = pixels[:total]
    # TGA origin: bit 5 of descriptor set means top-left already.
    if not descriptor & 0x20:
        rows = [
            pixels[row * width:(row + 1) * width] for row in range(height)
        ]
        rows.reverse()
        pixels = [pixel for row in rows for pixel in row]
    return width, height, pixels


def _shape_stats(width: int, height: int,
                 pixels: list[tuple[int, int, int, int]]) -> dict[str, float]:
    """Geometry and colour statistics from an alpha-masked sprite."""
    opaque: list[tuple[int, int]] = []
    reds = greens = blues = 0
    for index, (red, green, blue, alpha) in enumerate(pixels):
        if alpha > 40:
            opaque.append((index % width, index // width))
            reds += red
            greens += green
            blues += blue
    if not opaque:
        return {}
    count = len(opaque)
    xs = [point[0] for point in opaque]
    ys = [point[1] for point in opaque]
    span_x = max(xs) - min(xs) + 1
    span_y = max(ys) - min(ys) + 1
    long_side = max(span_x, span_y)
    short_side = max(1, min(span_x, span_y))
    fill = count / float(span_x * span_y)

    # Taper: compare the widths of the extremes along the long axis.
    if span_y >= span_x:
        rows: dict[int, int] = {}
        for x, y in opaque:
            rows[y] = rows.get(y, 0) + 1
        ordered = [rows.get(y, 0) for y in range(min(ys), max(ys) + 1)]
    else:
        cols: dict[int, int] = {}
        for x, y in opaque:
            cols[x] = cols.get(x, 0) + 1
        ordered = [cols.get(x, 0) for x in range(min(xs), max(xs) + 1)]
    slice_count = max(1, len(ordered) // 4)
    head = sum(ordered[:slice_count]) / slice_count
    tail = sum(ordered[-slice_count:]) / slice_count
    widest = max(1.0, float(max(ordered)))
    taper = 1.0 - (min(head, tail) / widest)

    # Hollowness: opaque border with sparse interior suggests a container.
    interior_x = (min(xs) + max(xs)) / 2.0
    interior_y = (min(ys) + max(ys)) / 2.0
    near_centre = sum(
        1 for x, y in opaque
        if abs(x - interior_x) < span_x * 0.2
        and abs(y - interior_y) < span_y * 0.2
    )
    expected_centre = max(1.0, 0.16 * span_x * span_y)
    hollow = 1.0 - min(1.0, near_centre / expected_centre)

    red_mean = reds / count
    green_mean = greens / count
    blue_mean = blues / count
    luminance = (0.299 * red_mean + 0.587 * green_mean + 0.114 * blue_mean)
    channel_max = max(red_mean, green_mean, blue_mean)
    channel_min = min(red_mean, green_mean, blue_mean)
    saturation = (
        0.0 if channel_max <= 0 else (channel_max - channel_min) / channel_max
    )
    return {
        "aspect": long_side / float(short_side),
        "fill": fill,
        "taper": max(0.0, min(1.0, taper)),
        "hollow": max(0.0, min(1.0, hollow)),
        "area": float(count),
        "span": float(long_side),
        "red": red_mean,
        "green": green_mean,
        "blue": blue_mean,
        "luminance": luminance,
        "saturation": saturation,
    }


def _properties_from_stats(stats: dict[str, float],
                           permanent: bool) -> dict[str, float]:
    """Map raw appearance statistics onto graded property beliefs."""
    if not stats:
        return {}
    aspect = stats["aspect"]
    red, green, blue = stats["red"], stats["green"], stats["blue"]
    properties = {
        "elongated": max(0.0, min(1.0, (aspect - 1.4) / 2.5)),
        "pointed": max(0.0, min(1.0, stats["taper"] * min(
            1.0, (aspect - 0.8) / 1.6
        ))),
        "large": max(0.0, min(1.0, (stats["span"] - 40.0) / 90.0)),
        "portable": 0.0 if permanent else 1.0,
        "stone_like": max(0.0, min(1.0, (
            (1.0 - stats["saturation"]) * 1.2
        ) * (0.5 + 0.5 * stats["fill"]))),
        "wooden": max(0.0, min(1.0, (
            (red - blue) / 90.0
        ) * (1.0 if red > green > blue else 0.4))),
        "green_growth": max(0.0, min(1.0, (
            green - max(red, blue)
        ) / 60.0)),
        "fibrous": max(0.0, min(1.0, (
            (1.0 - stats["fill"]) * min(1.0, aspect / 2.2)
        ) * 1.4)),
        "container": max(0.0, min(1.0, stats["hollow"] * (
            1.0 if aspect < 1.8 else 0.4
        ))),
        "bright": max(0.0, min(1.0, (stats["luminance"] - 120.0) / 110.0)),
        "warm_coloured": max(0.0, min(1.0, (
            (red - blue) / 80.0
        ) * (0.6 + 0.4 * stats["saturation"]))),
    }
    return {name: round(value, 3) for name, value in properties.items()}


_SPRITE_LINE = re.compile(r"^spriteID=(\d+)", re.MULTILINE)
_PERMANENT_LINE = re.compile(r"^permanent=(\d+)", re.MULTILINE)


def load_object_properties(
    data_dir: Path, object_id: int, sprite_cache: dict[int, dict[str, float]],
) -> dict[str, float]:
    """Perceive one object type from its sprites.  Never reads its name."""
    definition = data_dir / "objects" / f"{object_id}.txt"
    try:
        text = definition.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    # Line 0 is "id=N" and line 1 is the object's NAME.  The name is
    # deliberately discarded: perceiving is not being told.
    lines = text.splitlines()
    body = "\n".join(lines[2:]) if len(lines) > 2 else ""
    permanent_match = _PERMANENT_LINE.search(body)
    permanent = bool(permanent_match and int(permanent_match.group(1)) != 0)
    sprite_ids = [int(match) for match in _SPRITE_LINE.findall(body)]
    if not sprite_ids:
        return {}
    merged: dict[str, float] = {}
    weight_total = 0.0
    for sprite_id in sprite_ids[:6]:
        stats = sprite_cache.get(sprite_id)
        if stats is None:
            image = _read_tga_mask(
                data_dir / "sprites" / f"{sprite_id}.tga"
            )
            stats = _shape_stats(*image) if image else {}
            sprite_cache[sprite_id] = stats
        if not stats:
            continue
        weight = max(1.0, stats.get("area", 1.0))
        properties = _properties_from_stats(stats, permanent)
        for name, value in properties.items():
            merged[name] = merged.get(name, 0.0) + value * weight
        weight_total += weight
    if weight_total <= 0:
        return {}
    result = {
        name: round(value / weight_total, 3) for name, value in merged.items()
    }
    result["portable"] = 0.0 if permanent else 1.0
    return result


class VisualPerception:
    """Lazily perceives object appearances; silent no-op without data."""

    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = find_data_dir(data_dir)
        self._objects: dict[int, dict[str, float]] = {}
        self._sprites: dict[int, dict[str, float]] = {}

    @property
    def available(self) -> bool:
        return self.data_dir is not None

    def properties(self, object_id: int) -> dict[str, float]:
        if object_id <= 0 or self.data_dir is None:
            return {}
        cached = self._objects.get(object_id)
        if cached is None:
            cached = load_object_properties(
                self.data_dir, object_id, self._sprites
            )
            self._objects[object_id] = cached
        return cached

    def descriptor(self, object_id: int, threshold: float = 0.45) -> tuple:
        """A hashable, coarse appearance signature for generalization."""
        properties = self.properties(object_id)
        return tuple(sorted(
            name for name, value in properties.items() if value >= threshold
        ))

    def similarity(self, first: int, second: int) -> float:
        """How alike two object types look, in [0, 1]."""
        one = self.properties(first)
        two = self.properties(second)
        if not one or not two:
            return 0.0
        shared = set(one) & set(two)
        if not shared:
            return 0.0
        distance = sum(abs(one[name] - two[name]) for name in shared)
        return max(0.0, 1.0 - distance / len(shared))


# General, domain-independent priors: uncertain expectations a human
# brings to any survival setting.  They mention appearances only -- never
# specific objects, foods, recipes, or game mechanics -- and every one of
# them is a conjecture the agent must confirm or falsify by acting.
GENERAL_PRIORS: tuple[dict[str, Any], ...] = (
    {
        "name": "sharp_alters_fibrous",
        "actor": {"pointed": 0.5},
        "target": {"fibrous": 0.45},
        "expectation": "transform",
        "confidence": 0.40,
    },
    {
        "name": "sharp_alters_growth",
        "actor": {"pointed": 0.5},
        "target": {"green_growth": 0.45},
        "expectation": "transform",
        "confidence": 0.35,
    },
    {
        "name": "rigid_strikes_stone",
        "actor": {"stone_like": 0.5, "elongated": 0.4},
        "target": {"stone_like": 0.5},
        "expectation": "transform",
        "confidence": 0.30,
    },
    {
        "name": "container_holds",
        "actor": {"portable": 0.5},
        "target": {"container": 0.5},
        "expectation": "transform",
        "confidence": 0.30,
    },
    {
        "name": "growth_may_feed",
        "actor": {},
        "target": {"green_growth": 0.4, "warm_coloured": 0.35},
        "expectation": "consume",
        "confidence": 0.35,
    },
    {
        "name": "bright_may_warm",
        "actor": {},
        "target": {"bright": 0.55, "warm_coloured": 0.5},
        "expectation": "comfort",
        "confidence": 0.35,
    },
)


def prior_strength(
    perception: VisualPerception, held_id: int, target_id: int, kind: str,
) -> float:
    """How strongly general appearance priors favour trying this pairing."""
    if not perception.available:
        return 0.0
    held = perception.properties(held_id) if held_id > 0 else {}
    target = perception.properties(target_id) if target_id > 0 else {}
    best = 0.0
    for prior in GENERAL_PRIORS:
        if prior["expectation"] != kind:
            continue
        score = 1.0
        for name, needed in prior["actor"].items():
            value = held.get(name, 0.0)
            if value < needed:
                score = 0.0
                break
            score *= min(1.0, value / max(0.01, needed))
        if score <= 0.0:
            continue
        for name, needed in prior["target"].items():
            value = target.get(name, 0.0)
            if value < needed:
                score = 0.0
                break
            score *= min(1.0, value / max(0.01, needed))
        if score > 0.0:
            best = max(best, score * float(prior["confidence"]))
    return best


# ---- General world knowledge: goals and how things might be made ----
#
# These are the expectations a human brings to any survival setting, not
# facts about One Hour One Life.  They speak only of *appearances* and
# *states*: a bright warm-coloured thing gives off heat; a pointed rigid
# thing cuts; rubbing long dry wooden things together may make heat.  No
# object, recipe, or food is named anywhere, and every one is an
# uncertain conjecture the agent must confirm or falsify by acting.

GOAL_STATES = ("warmth", "nourishment", "cutting_tool")


# What an already-existing thing must look like to satisfy a goal.
GOAL_PRIORS: tuple[dict[str, Any], ...] = (
    {
        "goal": "warmth",
        "satisfied_by": {"bright": 0.5, "warm_coloured": 0.45},
        "confidence": 0.45,
    },
    {
        "goal": "nourishment",
        "satisfied_by": {"green_growth": 0.4},
        "confidence": 0.3,
    },
    {
        "goal": "nourishment",
        "satisfied_by": {"warm_coloured": 0.5, "green_growth": 0.3},
        "confidence": 0.3,
    },
    {
        "goal": "cutting_tool",
        "satisfied_by": {"pointed": 0.5, "stone_like": 0.4},
        "confidence": 0.45,
    },
)


# How a thing satisfying a goal might be *produced* by combining
# appearances: the hypotheses a person tries when the thing they want
# does not already exist in front of them.
PRODUCTION_PRIORS: tuple[dict[str, Any], ...] = (
    {
        "goal": "warmth",
        "actor": {"elongated": 0.45, "wooden": 0.35},
        "target": {"wooden": 0.35},
        "confidence": 0.30,
        "note": "friction between dry wooden things may make heat",
    },
    {
        "goal": "warmth",
        "actor": {"stone_like": 0.5},
        "target": {"stone_like": 0.5},
        "confidence": 0.25,
        "note": "striking hard things together may throw sparks",
    },
    {
        "goal": "warmth",
        "actor": {"bright": 0.5, "warm_coloured": 0.45},
        "target": {"wooden": 0.4},
        "confidence": 0.35,
        "note": "something already hot may set dry things alight",
    },
    {
        "goal": "warmth",
        "actor": {"fibrous": 0.45},
        "target": {"bright": 0.5, "warm_coloured": 0.45},
        "confidence": 0.30,
        "note": "dry fibres may feed a small heat source",
    },
    {
        "goal": "cutting_tool",
        "actor": {"stone_like": 0.5},
        "target": {"stone_like": 0.5},
        "confidence": 0.30,
        "note": "stone worked against stone may make an edge",
    },
    {
        "goal": "cutting_tool",
        "actor": {"pointed": 0.5},
        "target": {"elongated": 0.4, "wooden": 0.35},
        "confidence": 0.25,
        "note": "an edge fixed to a handle may make a better tool",
    },
    {
        "goal": "nourishment",
        "actor": {"pointed": 0.5},
        "target": {"green_growth": 0.45},
        "confidence": 0.30,
        "note": "cutting growing things may yield something edible",
    },
    {
        "goal": "nourishment",
        "actor": {"green_growth": 0.4},
        "target": {"bright": 0.5, "warm_coloured": 0.45},
        "confidence": 0.30,
        "note": "heating raw growth may make it better food",
    },
)


def profile_match(
    properties: dict[str, float], profile: dict[str, float]
) -> float:
    """How well an appearance matches a wanted profile, in [0, 1]."""
    if not properties or not profile:
        return 0.0
    score = 1.0
    for name, needed in profile.items():
        value = properties.get(name, 0.0)
        if value < needed:
            return 0.0
        score *= min(1.0, value / max(0.01, needed))
    return score


def goal_satisfaction(
    perception: "VisualPerception", object_id: int, goal: str
) -> float:
    """Might this thing, as it looks, already satisfy the goal?"""
    if not perception.available:
        return 0.0
    properties = perception.properties(object_id)
    best = 0.0
    for prior in GOAL_PRIORS:
        if prior["goal"] != goal:
            continue
        best = max(
            best,
            profile_match(properties, prior["satisfied_by"])
            * float(prior["confidence"]),
        )
    return best


def production_candidates(
    perception: "VisualPerception", goal: str, held_id: int, target_id: int,
) -> tuple[float, str]:
    """Might combining these two make something that satisfies the goal?"""
    if not perception.available:
        return 0.0, ""
    held = perception.properties(held_id) if held_id > 0 else {}
    target = perception.properties(target_id) if target_id > 0 else {}
    best = 0.0
    note = ""
    for prior in PRODUCTION_PRIORS:
        if prior["goal"] != goal:
            continue
        actor_score = profile_match(held, prior["actor"])
        target_score = profile_match(target, prior["target"])
        if actor_score <= 0.0 or target_score <= 0.0:
            continue
        strength = actor_score * target_score * float(prior["confidence"])
        if strength > best:
            best = strength
            note = str(prior.get("note", ""))
    return best, note


def wanted_ingredient_profiles(goal: str) -> list[dict[str, float]]:
    """Appearance profiles worth acquiring in service of a goal."""
    profiles: list[dict[str, float]] = []
    for prior in PRODUCTION_PRIORS:
        if prior["goal"] != goal:
            continue
        profiles.append(dict(prior["actor"]))
        profiles.append(dict(prior["target"]))
    return profiles

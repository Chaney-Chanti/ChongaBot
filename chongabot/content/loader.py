"""Load content/*.yaml into a validated, immutable Content object."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from chongabot.content.bots import build_bosses, build_bots
from chongabot.content.models import (
    ROLES,
    Age,
    Boss,
    BotNation,
    Building,
    Cost,
    Effect,
    ExplorationEvent,
    Hero,
    Lore,
    Research,
    Resource,
    Role,
    Settings,
    Unit,
    UnlockUnit,
    Wonder,
)

CONTENT_DIR = Path(__file__).parent


class ContentError(ValueError):
    """The YAML is inconsistent. The message lists every problem found."""


@dataclass(frozen=True)
class Content:
    ages: tuple[Age, ...]
    units: Mapping[str, Unit]
    buildings: Mapping[str, Building]
    research: Mapping[str, Research]
    wonders: Mapping[str, Wonder]
    counters: Mapping[Role, Role]  # role -> the role it beats
    exploration: tuple[ExplorationEvent, ...]
    settings: Settings
    bots: Mapping[str, BotNation]
    heroes: Mapping[str, Hero]
    lore: Lore
    bosses: Mapping[str, Boss]

    def age(self, age_id: str) -> Age:
        for age in self.ages:
            if age.id == age_id:
                return age
        raise KeyError(age_id)

    def age_index(self, age_id: str) -> int:
        return [a.id for a in self.ages].index(age_id)

    def next_age(self, age_id: str) -> Age | None:
        i = self.age_index(age_id) + 1
        return self.ages[i] if i < len(self.ages) else None


def _read(directory: Path, name: str) -> Any:
    with (directory / name).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _by_age(raw: Mapping[str, Mapping[str, Any]]) -> Iterable[dict[str, Any]]:
    """Flatten {age: {id: fields}} into dicts carrying their own id and age."""
    for age_id, items in raw.items():
        for item_id, fields in (items or {}).items():
            yield {"id": item_id, "age": age_id, **fields}


def load_content(directory: Path = CONTENT_DIR) -> Content:
    ages = tuple(
        Age.model_validate({"id": k, **v}) for k, v in _read(directory, "ages.yaml").items()
    )
    units = {u.id: u for u in map(Unit.model_validate, _by_age(_read(directory, "units.yaml")))}
    raw_buildings = _read(directory, "buildings.yaml")
    buildings = {
        b.id: b
        for kind in ("production", "defense")
        for b in (
            Building.model_validate({"id": k, "kind": kind, **v})
            for k, v in raw_buildings[kind].items()
        )
    }
    research = {
        r.id: r for r in map(Research.model_validate, _by_age(_read(directory, "research.yaml")))
    }
    wonders = {
        w.id: w for w in map(Wonder.model_validate, _by_age(_read(directory, "wonders.yaml")))
    }
    heroes = {h.id: h for h in map(Hero.model_validate, _by_age(_read(directory, "heroes.yaml")))}
    lore = Lore.model_validate(_read(directory, "lore.yaml"))
    counters: dict[Role, Role] = _read(directory, "counters.yaml")
    exploration = tuple(
        ExplorationEvent.model_validate({"id": k, **v})
        for k, v in _read(directory, "exploration.yaml").items()
    )
    settings = Settings.model_validate(_read(directory, "settings.yaml"))
    bot_names: dict[str, list[str]] = _read(directory, "bots.yaml") or {}
    bots = build_bots(ages, units, buildings, bot_names, settings)
    bosses = build_bosses(ages, units, _read(directory, "bosses.yaml") or {}, settings)

    content = Content(
        ages,
        units,
        buildings,
        research,
        wonders,
        counters,
        exploration,
        settings,
        bots,
        heroes,
        lore,
        bosses,
    )
    problems = list(_cross_check(content, raw_unit_count=_count_raw(directory)))
    problems += list(_check_bots(content, bot_names))
    problems += list(_check_bosses(content))
    if problems:
        raise ContentError("Invalid game content:\n  - " + "\n  - ".join(problems))
    return content


def _check_bots(c: Content, names: Mapping[str, list[str]]) -> Iterable[str]:
    age_ids = {a.id for a in c.ages}
    for age_id in names:
        if age_id not in age_ids:
            yield f"bots.yaml names unknown age {age_id!r}"
    for age_id in age_ids:
        if not names.get(age_id):
            yield f"bots.yaml has no bot names for {age_id}"
    seen: set[str] = set()
    for bot in c.bots.values():
        key = bot.name.casefold()
        if key in seen:
            yield f"bot name {bot.name!r} is used twice"
        seen.add(key)


def _check_bosses(c: Content) -> Iterable[str]:
    age_ids = {a.id for a in c.ages}
    names: set[str] = {b.name.casefold() for b in c.bots.values()}
    for boss in c.bosses.values():
        if boss.age not in age_ids:
            yield f"boss {boss.id} has unknown age {boss.age!r}"
        if not boss.units:
            yield f"boss {boss.id} has no army (its age has no regular units)"
        if boss.name.casefold() in names:
            yield f"boss name {boss.name!r} is used twice (or clashes with a bot nation)"
        names.add(boss.name.casefold())


def _count_raw(directory: Path) -> dict[str, int]:
    """How many entries each file declared, to catch ids silently overwritten by duplicates."""
    return {
        "units": sum(len(v or {}) for v in _read(directory, "units.yaml").values()),
        "research": sum(len(v or {}) for v in _read(directory, "research.yaml").values()),
        "wonders": sum(len(v or {}) for v in _read(directory, "wonders.yaml").values()),
        "heroes": sum(len(v or {}) for v in _read(directory, "heroes.yaml").values()),
        "bosses": sum(len(v or {}) for v in (_read(directory, "bosses.yaml") or {}).values()),
    }


def _cross_check(c: Content, raw_unit_count: dict[str, int]) -> Iterable[str]:
    age_ids = [a.id for a in c.ages]

    # Ages: the first is free, every later one costs something.
    if c.ages and c.ages[0].advance_cost:
        yield f"the first age ({c.ages[0].id}) can't have an advance_cost"
    for age in c.ages[1:]:
        if not age.advance_cost:
            yield f"age {age.id} needs an advance_cost"

    # Duplicate ids across ages collapse silently in a dict; count them instead.
    for name, count in raw_unit_count.items():
        actual = len(getattr(c, name))
        if actual != count:
            yield f"{name}.yaml has {count - actual} duplicate id(s) across ages"

    # One id namespace for everything a player can own or buy.
    seen: dict[str, str] = {}
    for kind, items in (
        ("unit", c.units),
        ("building", c.buildings),
        ("research", c.research),
        ("wonder", c.wonders),
        ("hero", c.heroes),
    ):
        for item_id in items:
            if item_id in seen:
                yield f"id {item_id!r} is used by both a {seen[item_id]} and a {kind}"
            seen[item_id] = kind

    # Every age reference exists.
    aged: list[tuple[str, Unit | Building | Research | Wonder | Hero]] = [
        *(("hero", h) for h in c.heroes.values()),
        *(("unit", u) for u in c.units.values()),
        *(("building", b) for b in c.buildings.values()),
        *(("research", r) for r in c.research.values()),
        *(("wonder", w) for w in c.wonders.values()),
    ]
    bad_age = False
    for kind, item in aged:
        if item.age not in age_ids:
            bad_age = True
            yield f"{kind} {item.id} names unknown age {item.age!r}"
    if bad_age:
        return  # the checks below index ages

    # A cost can only use resources the player can produce by then.
    def producible_by(age_id: str) -> set[Resource]:
        i = c.age_index(age_id)
        out: set[Resource] = {r for r, v in c.settings.base_rates.items() if v > 0}
        for b in c.buildings.values():
            if b.produces and c.age_index(b.age) <= i:
                out.add(b.produces)
        return out

    def check_cost(label: str, age_id: str, cost: Cost) -> Iterable[str]:
        missing = set(cost) - producible_by(age_id)
        if missing:
            yield f"{label} costs {sorted(missing)}, which nobody can produce in {age_id}"

    for u in c.units.values():
        yield from check_cost(f"unit {u.id}", u.age, u.cost)
    for b in c.buildings.values():
        yield from check_cost(f"building {b.id}", b.age, b.cost)
    for r in c.research.values():
        yield from check_cost(f"research {r.id}", r.age, r.cost)
    for i, age in enumerate(c.ages[1:], start=1):
        yield from check_cost(f"advancing to {age.id}", age_ids[i - 1], age.advance_cost)

    # Effects that point at units must point at real, unlockable ones.
    owners: list[Hero | Research | Wonder] = [
        *c.heroes.values(),
        *c.research.values(),
        *c.wonders.values(),
    ]
    all_effects: list[tuple[str, Effect]] = [(o.id, e) for o in owners for e in o.effects]
    unlocked: set[str] = set()
    for owner, effect in all_effects:
        if isinstance(effect, UnlockUnit):
            target = c.units.get(effect.unit)
            if target is None:
                yield f"{owner} unlocks unknown unit {effect.unit!r}"
            elif not target.requires_unlock:
                yield f"{owner} unlocks {effect.unit}, which doesn't have requires_unlock"
            unlocked.add(effect.unit)
    for u in c.units.values():
        if u.requires_unlock and u.id not in unlocked:
            yield f"unit {u.id} requires an unlock, but nothing unlocks it"

    # Counters form a cycle: every role beats exactly one and is beaten by exactly one.
    if set(c.counters) != set(ROLES) or set(c.counters.values()) != set(ROLES):
        yield f"counters must list every role once as a key and once as a value: {ROLES}"
    for attacker, beaten in c.counters.items():
        if attacker == beaten:
            yield f"role {attacker} can't counter itself"

    # Settings that point at content.
    for unit_id in c.settings.starting_units:
        unit = c.units.get(unit_id)
        if unit is None:
            yield f"starting unit {unit_id!r} doesn't exist"
        elif unit.age != age_ids[0] or unit.requires_unlock:
            yield f"starting unit {unit_id} must be a regular unit from {age_ids[0]}"
    tiers = c.settings.building_tiers
    if list(tiers) != sorted(set(tiers)):
        yield f"building_tiers must be strictly increasing: {tiers}"

    # Each age needs something to fight with and something to research.
    for age_id in age_ids:
        if not any(u.age == age_id and not u.requires_unlock for u in c.units.values()):
            yield f"age {age_id} has no regular units"
        if not any(b.age == age_id and b.kind == "defense" for b in c.buildings.values()):
            yield f"age {age_id} has no defense building"

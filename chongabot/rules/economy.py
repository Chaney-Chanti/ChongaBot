"""Production, claiming, costs and what a player may buy. Pure functions only."""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from chongabot.content import Content
from chongabot.content.models import RESOURCES, Age, Building, Research, Resource, Unit
from chongabot.domain.errors import GameError, NotEnough, OnCooldown, WrongAge
from chongabot.domain.models import Player
from chongabot.rules.effects import Modifiers, modifiers

Cost = dict[Resource, int]

# --- small cost helpers ------------------------------------------------------


def scale(cost: Mapping[Resource, int], factor: float) -> Cost:
    return {r: math.ceil(v * factor) for r, v in cost.items() if v}


def affordable(have: Mapping[Resource, int], cost: Mapping[Resource, int]) -> bool:
    return all(have.get(r, 0) >= v for r, v in cost.items())


def shortfall(have: Mapping[Resource, int], cost: Mapping[Resource, int]) -> Cost:
    return {r: v - have.get(r, 0) for r, v in cost.items() if have.get(r, 0) < v}


def require(have: Mapping[Resource, int], cost: Mapping[Resource, int]) -> None:
    missing = shortfall(have, cost)
    if missing:
        parts = ", ".join(f"{n:,} {r}" for r, n in missing.items())
        raise NotEnough(f"You're short {parts}.")


def max_affordable(
    have: Mapping[Resource, int], cost_for: Callable[[int], Cost], cap: int = 1_000_000
) -> int:
    """Largest n with cost_for(n) affordable, assuming cost grows with n."""
    if not affordable(have, cost_for(1)):
        return 0
    lo, hi = 1, 2
    while hi <= cap and affordable(have, cost_for(hi)):
        lo, hi = hi, hi * 2
    hi = min(hi, cap + 1)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if affordable(have, cost_for(mid)):
            lo = mid
        else:
            hi = mid
    return lo


# --- production --------------------------------------------------------------


def production_rates(
    player: Player, content: Content, mods: Modifiers | None = None
) -> dict[Resource, float]:
    """Per-hour production. Derived every time, never stored."""
    mods = mods or modifiers(player, content)
    base: dict[Resource, float] = {
        r: float(content.settings.base_rates.get(r, 0)) for r in RESOURCES
    }
    for building_id, count in player.buildings.items():
        b = content.buildings.get(building_id)
        if b and b.kind == "production" and b.produces and b.yield_per_hour:
            base[b.produces] += b.yield_per_hour * count
    age_mult = content.age(player.age).production_multiplier
    return {r: base[r] * age_mult * mods.rate[r] for r in RESOURCES}


@dataclass(frozen=True)
class ClaimResult:
    hours: float
    gained: Cost


def next_claim_at(player: Player, content: Content) -> datetime:
    return player.last_claim + timedelta(hours=content.settings.claim_min_hours)


def claim(player: Player, content: Content, now: datetime) -> ClaimResult:
    s = content.settings
    hours = (now - player.last_claim).total_seconds() / 3600
    if hours < s.claim_min_hours:
        ready = next_claim_at(player, content)
        raise OnCooldown(f"Nothing to claim yet. Next claim <t:{int(ready.timestamp())}:R>.")
    hours = min(hours, s.claim_cap_hours)
    mods = modifiers(player, content)
    rates = production_rates(player, content, mods)
    gained = {r: int(rates[r] * hours * mods.claim) for r in RESOURCES if rates[r] > 0}
    return ClaimResult(hours=hours, gained=gained)


# --- buildings ---------------------------------------------------------------


def check_buildable(player: Player, content: Content, building: Building) -> None:
    here, built_in = content.age_index(player.age), content.age_index(building.age)
    if building.kind == "production" and built_in > here:
        raise WrongAge(f"{building.name} unlocks in the {content.age(building.age).name} age.")
    if building.kind == "defense" and built_in != here:
        raise WrongAge(
            f"{building.name} can only be built in the {content.age(building.age).name} age."
        )


def buildable(player: Player, content: Content) -> list[Building]:
    here = content.age_index(player.age)
    return [
        b
        for b in content.buildings.values()
        if (b.kind == "production" and content.age_index(b.age) <= here)
        or (b.kind == "defense" and b.age == player.age)
    ]


def building_cost(
    player: Player, content: Content, building: Building, count: int, mods: Modifiers | None = None
) -> Cost:
    """Total cost of `count` more copies. Each owned copy makes the next one pricier."""
    if count <= 0:
        return {}
    mods = mods or modifiers(player, content)
    g = content.settings.building_cost_growth
    owned = player.buildings.get(building.id, 0)
    factor = g**owned * (g**count - 1) / (g - 1)  # sum of g^owned .. g^(owned+count-1)
    return scale(building.cost, factor * mods.building_cost)


def max_buildings(player: Player, content: Content, building: Building) -> int:
    mods = modifiers(player, content)
    return max_affordable(
        player.resources, lambda n: building_cost(player, content, building, n, mods), cap=10_000
    )


# --- units -------------------------------------------------------------------


def check_trainable(player: Player, content: Content, unit: Unit) -> None:
    if unit.age != player.age:
        raise WrongAge(f"{unit.name} belongs to the {content.age(unit.age).name} age.")
    if unit.requires_unlock and unit.id not in modifiers(player, content).unlocked_units:
        raise WrongAge(unit.desc or f"{unit.name} hasn't been unlocked yet.")


def trainable(player: Player, content: Content) -> list[Unit]:
    unlocked = modifiers(player, content).unlocked_units
    return [
        u
        for u in content.units.values()
        if u.age == player.age and (not u.requires_unlock or u.id in unlocked)
    ]


def unit_cost(
    player: Player, content: Content, unit: Unit, count: int, mods: Modifiers | None = None
) -> Cost:
    mods = mods or modifiers(player, content)
    return scale(unit.cost, count * mods.unit_cost) if count > 0 else {}


def max_units(player: Player, content: Content, unit: Unit) -> int:
    mods = modifiers(player, content)
    return max_affordable(player.resources, lambda n: unit_cost(player, content, unit, n, mods))


# --- research ----------------------------------------------------------------


def check_researchable(player: Player, content: Content, research: Research) -> None:
    if research.id in player.research:
        raise GameError(f"You've already researched {research.name}.")
    if content.age_index(research.age) > content.age_index(player.age):
        raise WrongAge(f"{research.name} unlocks in the {content.age(research.age).name} age.")


def researchable(player: Player, content: Content) -> list[Research]:
    here = content.age_index(player.age)
    options = [
        r
        for r in content.research.values()
        if r.id not in player.research and content.age_index(r.age) <= here
    ]
    # current age first, then anything older that was skipped
    return sorted(options, key=lambda r: (r.age != player.age, -content.age_index(r.age)))


def research_cost(player: Player, content: Content, research: Research) -> Cost:
    return scale(research.cost, modifiers(player, content).research_cost)


# --- ages --------------------------------------------------------------------


def next_age(player: Player, content: Content) -> Age:
    age = content.next_age(player.age)
    if age is None:
        raise GameError("You're already in the final age.")
    return age


# --- advancing ---------------------------------------------------------------------


@dataclass(frozen=True)
class Retraining:
    """Older units retrained into one unit of the new age."""

    into: str  # new unit id
    count: int  # how many of it they became
    old: dict[str, int]  # the older units used up


def retrain_army(units: Mapping[str, int], to_age: str, content: Content) -> list[Retraining]:
    """On entering an age, every regular unit from an older age becomes the new age's unit
    of the same role (the cheapest, if there are several).

    Resource value is kept, not head count: 100 Clubmen (40 each) become 20 Knights
    (200 each). Units unlocked by heroes, and roles the new age doesn't have, stay as they are.
    """
    here = content.age_index(to_age)
    newest: dict[str, Unit] = {}
    for u in content.units.values():
        if u.age == to_age and not u.requires_unlock:
            best = newest.get(u.role)
            if best is None or sum(u.cost.values()) < sum(best.cost.values()):
                newest[u.role] = u

    groups: dict[str, dict[str, int]] = {}
    for unit_id, n in units.items():
        old = content.units.get(unit_id)
        if old is None or n <= 0 or old.requires_unlock or content.age_index(old.age) >= here:
            continue
        if (target := newest.get(old.role)) is not None:
            groups.setdefault(target.id, {})[unit_id] = n

    out = []
    for into, used in groups.items():
        value = sum(sum(content.units[u].cost.values()) * n for u, n in used.items())
        count = round(value / sum(content.units[into].cost.values()))
        out.append(Retraining(into, count, used))
    return out

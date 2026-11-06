"""Generate bot nations from bots.yaml names and each age's units.

Strength is measured in resources (the army's total cost) against the age's "scale": the
cost of advancing out of it. Tiers grow geometrically from bot_strength_min x scale to
bot_strength_max x scale, and the army is split evenly over every regular unit of the age,
so every role is represented and the counter system matters.
"""

from collections.abc import Mapping, Sequence

from chongabot.content.models import (
    RESOURCES,
    Age,
    Boss,
    BotNation,
    Building,
    Resource,
    Settings,
    Unit,
)


def age_scale(ages: Sequence[Age], index: int) -> float:
    if index + 1 < len(ages):
        return float(sum(ages[index + 1].advance_cost.values()))
    return 1.5 * float(sum(ages[index].advance_cost.values()))


def build_bots(
    ages: Sequence[Age],
    units: Mapping[str, Unit],
    buildings: Mapping[str, Building],
    names: Mapping[str, Sequence[str]],
    s: Settings,
) -> dict[str, BotNation]:
    bots: dict[str, BotNation] = {}
    for i, age in enumerate(ages):
        roster = _roster(age, units)
        defense = next(
            (b for b in buildings.values() if b.age == age.id and b.kind == "defense"), None
        )
        age_names = list(names.get(age.id, ()))
        if not roster or not age_names:
            continue
        scale = age_scale(ages, i)
        n = len(age_names)
        for tier, name in enumerate(age_names, start=1):
            step = (tier - 1) / (n - 1) if n > 1 else 0.0
            target = scale * s.bot_strength_min * (s.bot_strength_max / s.bot_strength_min) ** step
            army = _army(target, roster)
            value, loot = _value_and_loot(army, units, s.bot_loot_share)
            forts = {defense.id: (tier - 1) // 3} if defense and tier > 3 else {}
            bot_id = f"{age.id}_{tier}"
            bots[bot_id] = BotNation(
                id=bot_id,
                name=name,
                age=age.id,
                tier=tier,
                units=army,
                buildings=forts,
                loot=loot,
                value=value,
            )
    return bots


def _roster(age: Age, units: Mapping[str, Unit]) -> list[Unit]:
    return [u for u in units.values() if u.age == age.id and not u.requires_unlock]


def _army(target: float, roster: Sequence[Unit]) -> dict[str, int]:
    """Spend `target` resources evenly over every unit in the roster."""
    share = target / len(roster)
    return {u.id: max(1, round(share / sum(u.cost.values()))) for u in roster}


def _value_and_loot(
    army: Mapping[str, int], units: Mapping[str, Unit], loot_share: float
) -> tuple[int, dict[Resource, int]]:
    """The army's total cost, and loot worth loot_share of it in the resources it's made of."""
    value = sum(sum(units[u].cost.values()) * c for u, c in army.items())
    spent: dict[Resource, int] = dict.fromkeys(RESOURCES, 0)
    for u_id, c in army.items():
        for r, v in units[u_id].cost.items():
            spent[r] += v * c
    total = sum(spent.values()) or 1
    loot = {r: round(value * loot_share * v / total) for r, v in spent.items()}
    return value, {r: v for r, v in loot.items() if v > 0}


def build_bosses(
    ages: Sequence[Age],
    units: Mapping[str, Unit],
    raw: Mapping[str, Mapping[str, Mapping[str, object]]],
    s: Settings,
) -> dict[str, Boss]:
    bosses: dict[str, Boss] = {}
    for i, age in enumerate(ages):
        roster = _roster(age, units)
        for boss_id, fields in (raw.get(age.id) or {}).items():
            boss = Boss.model_validate({"id": boss_id, "age": age.id, **fields})
            if not roster:
                bosses[boss_id] = boss
                continue
            army = _army(age_scale(ages, i) * boss.strength, roster)
            value, loot = _value_and_loot(army, units, s.boss_loot_share)
            bosses[boss_id] = boss.model_copy(update={"units": army, "loot": loot, "value": value})
    return bosses

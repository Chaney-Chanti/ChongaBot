"""Exploration: pick an event by weight and work out its reward."""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from chongabot.content import Content
from chongabot.content.models import ExplorationEvent, Resource
from chongabot.domain.errors import OnCooldown
from chongabot.domain.models import Player
from chongabot.rules import economy
from chongabot.rules.effects import modifiers

Kind = Literal["resources", "units", "building", "hero", "wonder", "pirates"]


@dataclass
class Outcome:
    event: ExplorationEvent
    kind: Kind
    resources: dict[Resource, int] = field(default_factory=dict)
    units: dict[str, int] = field(default_factory=dict)
    building: str | None = None
    hero: str | None = None
    wonder: str | None = None
    pirate_units: dict[str, int] = field(default_factory=dict)  # army to fight


def check_ready(player: Player, content: Content, now: datetime) -> None:
    if player.last_explore is None:
        return
    ready = player.last_explore + timedelta(hours=content.settings.exploration_cooldown_hours)
    if now < ready:
        raise OnCooldown(f"Your explorers are still out. Back <t:{int(ready.timestamp())}:R>.")


def production_value(player: Player, content: Content, hours: float) -> dict[Resource, int]:
    mods = modifiers(player, content)
    rates = economy.production_rates(player, content, mods)
    return {r: int(v * hours * mods.exploration) for r, v in rates.items() if v > 0}


def roll(player: Player, content: Content, rng: random.Random) -> Outcome:
    events = list(content.exploration)
    event = rng.choices(events, weights=[e.weight for e in events])[0]

    def hours() -> float:
        return rng.uniform(event.min_hours or 1, event.max_hours or 1)

    def resources() -> Outcome:
        return Outcome(event, "resources", resources=production_value(player, content, hours()))

    match event.id:
        case "free_units":
            options = economy.trainable(player, content)
            if not options:
                return resources()
            unit = rng.choice(options)
            budget = sum(production_value(player, content, hours()).values())
            count = max(1, math.floor(budget / sum(unit.cost.values())))
            return Outcome(event, "units", units={unit.id: count})
        case "free_building":
            producers = [b for b in economy.buildable(player, content) if b.kind == "production"]
            return Outcome(event, "building", building=rng.choice(producers).id)
        case "hero":
            # Any hero from your age or earlier that you haven't found yet.
            here = content.age_index(player.age)
            heroes = [
                h
                for h in content.heroes.values()
                if content.age_index(h.age) <= here and h.id not in player.heroes
            ]
            if not heroes:
                return resources()
            return Outcome(event, "hero", hero=rng.choice(heroes).id)
        case "wonder":
            wonders = [
                w
                for w in content.wonders.values()
                if w.age == player.age and w.id not in player.wonders
            ]
            if not wonders:
                return resources()
            return Outcome(event, "wonder", wonder=rng.choice(wonders).id)
        case "pirates":
            army = {u: c for u, c in player.units.items() if c > 0 and u in content.units}
            if not army:
                return resources()
            # Lanchester strength grows with count squared, so scale counts by sqrt(share).
            share = rng.uniform(event.min_strength or 0.5, event.max_strength or 1.0)
            pirates = {u: max(1, round(c * math.sqrt(share))) for u, c in army.items()}
            loot = production_value(player, content, hours())
            return Outcome(event, "pirates", resources=loot, pirate_units=pirates)
        case _:
            return resources()

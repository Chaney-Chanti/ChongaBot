"""Fold every effect a player owns (research, wonders, heroes) into one Modifiers."""

from collections.abc import Iterable
from dataclasses import dataclass, field

from chongabot.content import Content
from chongabot.content.models import (
    RESOURCES,
    ROLES,
    AttackMultiplier,
    ClaimMultiplier,
    CostMultiplier,
    Effect,
    RateMultiplier,
    Resource,
    Role,
    UnlockUnit,
    ValueMultiplier,
)
from chongabot.domain.models import Player


def _ones_r() -> dict[Resource, float]:
    return dict.fromkeys(RESOURCES, 1.0)


def _ones_role() -> dict[Role, float]:
    return dict.fromkeys(ROLES, 1.0)


@dataclass
class Modifiers:
    rate: dict[Resource, float] = field(default_factory=_ones_r)
    claim: float = 1.0
    building_cost: float = 1.0
    unit_cost: float = 1.0
    research_cost: float = 1.0
    attack: dict[Role, float] = field(default_factory=_ones_role)
    enemy_attack: dict[Role, float] = field(default_factory=_ones_role)  # applied to enemies
    tribute: float = 1.0
    exploration: float = 1.0
    unlocked_units: set[str] = field(default_factory=set)


def player_effects(player: Player, content: Content) -> Iterable[Effect]:
    """Effects from everything the player owns. Ids no longer in content are skipped."""
    for research_id in player.research:
        if r := content.research.get(research_id):
            yield from r.effects
    for wonder_id in player.wonders:
        if w := content.wonders.get(wonder_id):
            yield from w.effects
    # Only the Second in Command's passive applies, and only if they're really yours.
    if player.hero in player.heroes and (h := content.heroes.get(player.hero or "")):
        yield from h.effects


def fold(effects: Iterable[Effect]) -> Modifiers:
    m = Modifiers()
    for e in effects:
        match e:
            case RateMultiplier():
                for res, value in e.resources.items():
                    targets = RESOURCES if res == "all" else (res,)
                    for r in targets:
                        m.rate[r] *= value
            case ClaimMultiplier():
                m.claim *= e.value
            case CostMultiplier(kind="building_cost_multiplier"):
                m.building_cost *= e.value
            case CostMultiplier(kind="unit_cost_multiplier"):
                m.unit_cost *= e.value
            case CostMultiplier(kind="research_cost_multiplier"):
                m.research_cost *= e.value
            case AttackMultiplier(kind="attack_multiplier"):
                for role in e.roles:
                    m.attack[role] *= e.value
            case AttackMultiplier(kind="enemy_attack_multiplier"):
                for role in e.roles:
                    m.enemy_attack[role] *= e.value
            case ValueMultiplier(kind="tribute_multiplier"):
                m.tribute *= e.value
            case ValueMultiplier(kind="exploration_reward_multiplier"):
                m.exploration *= e.value
            case UnlockUnit():
                m.unlocked_units.add(e.unit)
    return m


def modifiers(player: Player, content: Content) -> Modifiers:
    return fold(player_effects(player, content))

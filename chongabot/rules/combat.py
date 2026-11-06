"""Volley-round combat.

Every round, every squad on both sides fires at once. A squad's damage is split across
enemy squads in proportion to their remaining HP, with extra weight (and a damage bonus)
on the role it counters. Damage lands simultaneously, so firing order never matters.

`resolve` is pure: give it the same armies and the same seeded RNG and it returns the
same result, plus a log the Activity can replay.
"""

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from chongabot.content import Content
from chongabot.content.models import Role
from chongabot.domain.models import Player
from chongabot.rules.effects import Modifiers

Side = Literal["attacker", "defender"]
Source = Literal["unit", "building", "ally"]


@dataclass
class Squad:
    key: str  # e.g. "defender.keep", "defender.ally.spearman"
    unit_id: str
    name: str
    role: Role
    attack: int
    hp: int
    count: int
    source: Source = "unit"
    wounds: float = 0.0  # damage carried into the next round

    @property
    def alive(self) -> bool:
        return self.count > 0

    @property
    def remaining_hp(self) -> float:
        return self.count * self.hp - self.wounds

    @property
    def power(self) -> float:
        return float(self.count * self.attack * self.hp)


@dataclass
class BattleResult:
    winner: Side
    attacker_losses: dict[str, int]
    defender_losses: dict[str, int]  # units only: defense buildings come back after
    ally_losses: dict[str, int]  # the defender's alliance army
    attacker_share_left: float
    defender_share_left: float
    log: dict[str, Any] = field(default_factory=dict)


def army_from_units(
    content: Content, side: Side, units: Mapping[str, int], source: Source = "unit"
) -> list[Squad]:
    prefix = f"{side}.ally" if source == "ally" else side
    squads = []
    for unit_id, count in units.items():
        u = content.units.get(unit_id)
        if u and count > 0:
            squads.append(
                Squad(f"{prefix}.{u.id}", u.id, u.name, u.role, u.attack, u.hp, int(count), source)
            )
    return squads


def player_army(
    content: Content, player: Player, side: Side, allies: Mapping[str, int] | None = None
) -> list[Squad]:
    """A player's units. Defending, they add defense buildings and their alliance army.

    Heroes never fight: they help through their passive, from behind the lines.
    """
    squads = army_from_units(content, side, player.units)
    if side == "defender":
        squads += army_from_units(content, side, allies or {}, source="ally")
        squads += defenses(content, side, player.buildings)
    return squads


def defenses(content: Content, side: Side, buildings: Mapping[str, int]) -> list[Squad]:
    """Defense buildings as squads. They fight but are never lost."""
    squads = []
    for b_id, count in buildings.items():
        b = content.buildings.get(b_id)
        if b and b.kind == "defense" and b.attack and b.hp and count > 0:
            squads.append(
                Squad(f"{side}.{b.id}", b.id, b.name, "defense", b.attack, b.hp, count, "building")
            )
    return squads


def army_power(squads: list[Squad]) -> float:
    return sum(s.power for s in squads if s.alive)


def resolve(
    attacker: list[Squad],
    defender: list[Squad],
    content: Content,
    rng: random.Random,
    attacker_mods: Modifiers | None = None,
    defender_mods: Modifiers | None = None,
    names: tuple[str, str] = ("Attacker", "Defender"),
) -> BattleResult:
    s = content.settings
    a_mods, d_mods = attacker_mods or Modifiers(), defender_mods or Modifiers()
    start = {sq.key: sq.count for sq in (*attacker, *defender)}
    start_power = {"attacker": army_power(attacker), "defender": army_power(defender)}
    log: dict[str, Any] = {
        "sides": {
            "attacker": {"name": names[0], "squads": {sq.key: sq.count for sq in attacker}},
            "defender": {"name": names[1], "squads": {sq.key: sq.count for sq in defender}},
        },
        "rounds": [],
    }

    for _ in range(s.combat_rounds):
        if not any(sq.alive for sq in attacker) or not any(sq.alive for sq in defender):
            break
        incoming: dict[str, float] = {}
        hits = []
        for shooters, targets, own, enemy in (
            (attacker, defender, a_mods, d_mods),
            (defender, attacker, d_mods, a_mods),
        ):
            alive_targets = [t for t in targets if t.alive]
            for sq in shooters:
                if not sq.alive:
                    continue
                damage = (
                    sq.count
                    * sq.attack
                    * own.attack[sq.role]
                    * enemy.enemy_attack[sq.role]
                    * rng.uniform(1 - s.damage_variance, 1 + s.damage_variance)
                )
                countered = content.counters[sq.role]
                weights = [
                    t.remaining_hp * (s.counter_target_weight if t.role == countered else 1)
                    for t in alive_targets
                ]
                total = sum(weights)
                for t, w in zip(alive_targets, weights, strict=True):
                    dealt = damage * w / total
                    if t.role == countered:
                        dealt *= s.counter_multiplier
                    incoming[t.key] = incoming.get(t.key, 0.0) + dealt
                    hits.append({"from": sq.key, "to": t.key, "damage": round(dealt)})

        losses = {}
        for sq in (*attacker, *defender):
            if sq.key not in incoming:
                continue
            total = incoming[sq.key] + sq.wounds
            killed = min(sq.count, int(total // sq.hp))
            sq.count -= killed
            sq.wounds = total - killed * sq.hp if sq.count else 0.0
            if killed:
                losses[sq.key] = killed
        log["rounds"].append({"hits": hits, "losses": losses})

    def share(side: list[Squad], key: Side) -> float:
        return army_power(side) / start_power[key] if start_power[key] else 0.0

    a_left, d_left = share(attacker, "attacker"), share(defender, "defender")
    winner: Side = "attacker" if a_left > d_left else "defender"
    log["winner"] = winner

    def lost(side: list[Squad], source: Source) -> dict[str, int]:
        return {
            sq.unit_id: start[sq.key] - sq.count
            for sq in side
            if start[sq.key] > sq.count and sq.source == source
        }

    return BattleResult(
        winner=winner,
        attacker_losses=lost(attacker, "unit"),
        defender_losses=lost(defender, "unit"),
        ally_losses=lost(defender, "ally"),
        attacker_share_left=a_left,
        defender_share_left=d_left,
        log=log,
    )


def strength(squads: list[Squad]) -> float:
    """A rough fighting-strength score for comparing armies before a battle.

    Lanchester-style: an army's strength grows with the square of its size, so compare
    (sum of count x sqrt(attack x hp)) squared. Used for difficulty labels only; the real
    fight is `resolve`.
    """
    return sum(sq.count * math.sqrt(sq.attack * sq.hp) for sq in squads if sq.alive) ** 2

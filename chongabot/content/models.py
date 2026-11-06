"""Typed game content. Loaded once from YAML, validated, then frozen.

Rules code reads these models; nothing here does I/O or game logic.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

Resource = Literal["food", "timber", "metal", "wealth", "knowledge", "oil"]
RESOURCES: tuple[Resource, ...] = ("food", "timber", "metal", "wealth", "knowledge", "oil")

Role = Literal["melee", "ranged", "cavalry", "siege", "defense"]
ROLES: tuple[Role, ...] = ("melee", "ranged", "cavalry", "siege", "defense")

Cost = dict[Resource, PositiveInt]
Multiplier = Annotated[float, Field(gt=0)]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- effects ---------------------------------------------------------------
# A small closed set of effect kinds. Research, wonders and heroes all use them,
# and one rules function applies them, so content never contains code.


class RateMultiplier(Frozen):
    kind: Literal["rate_multiplier"]
    resources: dict[Resource | Literal["all"], Multiplier]


class ClaimMultiplier(Frozen):
    kind: Literal["claim_multiplier"]
    value: Multiplier


class CostMultiplier(Frozen):
    kind: Literal["building_cost_multiplier", "unit_cost_multiplier", "research_cost_multiplier"]
    value: Multiplier


class AttackMultiplier(Frozen):
    """Own units hit harder (or, for enemy_attack_multiplier, enemies hit softer)."""

    kind: Literal["attack_multiplier", "enemy_attack_multiplier"]
    value: Multiplier
    roles: tuple[Role, ...] = ROLES


class ValueMultiplier(Frozen):
    kind: Literal["tribute_multiplier", "exploration_reward_multiplier"]
    value: Multiplier


class UnlockUnit(Frozen):
    kind: Literal["unlock_unit"]
    unit: str


Effect = Annotated[
    RateMultiplier
    | ClaimMultiplier
    | CostMultiplier
    | AttackMultiplier
    | ValueMultiplier
    | UnlockUnit,
    Field(discriminator="kind"),
]


# --- content types -----------------------------------------------------------


class Age(Frozen):
    id: str
    name: str
    tagline: str = ""  # lore, e.g. "The Age of Mud"
    advance_cost: Cost = Field(default_factory=dict)  # cost to enter this age
    production_multiplier: Multiplier


class Unit(Frozen):
    id: str
    name: str
    age: str
    role: Role
    attack: PositiveInt
    hp: PositiveInt
    cost: Cost
    requires_unlock: bool = False  # buyable only after an unlock_unit effect
    desc: str = ""
    sprite: str = ""


class Hero(Frozen):
    """Found by luck while exploring. One can serve as your Second in Command at a time;
    only that one's passive applies. Heroes never fight."""

    id: str
    name: str
    age: str  # found from this age on
    desc: str  # lore
    effects: tuple[Effect, ...] = Field(min_length=1)
    sprite: str = ""


class Building(Frozen):
    id: str
    name: str
    age: str  # first age it can be built in
    kind: Literal["production", "defense"]
    cost: Cost
    produces: Resource | None = None
    yield_per_hour: PositiveInt | None = None
    attack: PositiveInt | None = None
    hp: PositiveInt | None = None
    # Defense buildings can only be built in their own age; production ones from then on.
    sprite: str = ""

    @model_validator(mode="after")
    def _check(self) -> "Building":
        if self.kind == "production" and (self.produces is None or self.yield_per_hour is None):
            raise ValueError(f"production building {self.id} needs produces and yield_per_hour")
        if self.kind == "defense" and (self.attack is None or self.hp is None):
            raise ValueError(f"defense building {self.id} needs attack and hp")
        return self


class Research(Frozen):
    id: str
    name: str
    age: str
    cost: Cost
    effects: tuple[Effect, ...]
    desc: str = ""


class Region(Frozen):
    name: str
    desc: str


class Lore(Frozen):
    title: str
    intro: str
    regions: tuple[Region, ...]


class Wonder(Frozen):
    id: str
    name: str
    age: str
    desc: str
    effects: tuple[Effect, ...]


class ExplorationEvent(Frozen):
    id: str
    weight: PositiveInt
    desc: str
    # Rewards are measured in hours of the player's own production, so they scale
    # with progress instead of needing a table per age.
    min_hours: float | None = None
    max_hours: float | None = None
    # pirates: enemy strength as a share of the player's army strength
    min_strength: float | None = None
    max_strength: float | None = None


class Settings(Frozen):
    claim_min_hours: Multiplier
    claim_cap_hours: Multiplier
    base_rates: dict[Resource, int]
    starting_resources: dict[Resource, int]
    starting_units: dict[str, PositiveInt]
    building_cost_growth: Multiplier
    building_tiers: tuple[PositiveInt, ...]
    battle_rating_range: PositiveInt
    battle_rating_base_change: PositiveInt
    battle_rating_min_change: PositiveInt
    battle_rating_max_change: PositiveInt
    tribute_share: Annotated[float, Field(gt=0, lt=1)]
    tribute_bonus: Annotated[float, Field(ge=0)]
    shield_hours: Multiplier
    attack_cooldown_minutes: Multiplier
    exploration_cooldown_hours: Multiplier
    combat_rounds: PositiveInt
    counter_multiplier: Multiplier
    counter_target_weight: Multiplier
    damage_variance: Annotated[float, Field(ge=0, lt=1)]
    alliance_member_cap: PositiveInt
    bot_strength_min: Multiplier
    bot_strength_max: Multiplier
    bot_loot_share: Annotated[float, Field(ge=0)]
    bot_cooldown_hours: Multiplier
    hero_swap_cooldown_hours: Annotated[float, Field(ge=0)]
    boss_loot_share: Annotated[float, Field(ge=0)]
    boss_cooldown_hours: Multiplier


class BotNation(Frozen):
    """An always-available target for one age. Generated from bots.yaml and the units."""

    id: str  # e.g. "ancient_3"
    name: str
    age: str
    tier: int  # 1 = weakest
    units: dict[str, PositiveInt]
    buildings: dict[str, PositiveInt]
    loot: dict[Resource, PositiveInt]
    value: int  # total resource cost of the army


class Boss(Frozen):
    """An alliance raid target. The army is generated from the age's units, like bots."""

    id: str
    name: str
    age: str
    desc: str
    strength: Multiplier  # army value as a multiple of the age's scale
    units: dict[str, PositiveInt] = {}
    loot: dict[Resource, PositiveInt] = {}
    value: int = 0  # total resource cost of the army

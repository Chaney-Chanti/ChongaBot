"""Plain game state, as loaded from storage. No behaviour beyond small helpers."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from chongabot.content.models import Resource

AllianceRole = Literal["owner", "officer", "member"]
RulerTitle = Literal["king", "queen", "ruler"]
RULER_TITLES: dict[RulerTitle, str] = {"king": "King", "queen": "Queen", "ruler": "Ruler"}
EPITHETS: tuple[str, ...] = (
    "the Great",
    "the Wise",
    "the Brave",
    "the Warrior",
    "the Graceful",
    "the Just",
    "the Bold",
    "the Conqueror",
    "the Magnificent",
    "the Builder",
    "the Merciful",
    "the Lionheart",
    "the Explorer",
    "the Terrible",
    "the Unready",
)
ROLE_RANK: dict[AllianceRole, int] = {"member": 0, "officer": 1, "owner": 2}


@dataclass
class Player:
    id: int
    name: str
    username: str
    age: str
    resources: dict[Resource, int]
    last_claim: datetime
    created_at: datetime
    motto: str = ""
    battle_rating: int = 0
    wins: int = 0
    losses: int = 0
    buildings: dict[str, int] = field(default_factory=dict)
    units: dict[str, int] = field(default_factory=dict)
    research: frozenset[str] = frozenset()
    wonders: frozenset[str] = frozenset()
    heroes: frozenset[str] = frozenset()  # every hero found
    hero: str | None = None  # the one serving as Second in Command
    hero_appointed_at: datetime | None = None
    shield_until: datetime | None = None
    last_explore: datetime | None = None
    last_attack: datetime | None = None
    alliance_id: int | None = None
    alliance_role: AllianceRole | None = None
    origin_guild_id: int | None = None
    ruler_title: RulerTitle = "ruler"
    epithet: str = ""

    @property
    def ruler(self) -> str:
        """e.g. "King Chonga the Great"."""
        return " ".join(
            part for part in (RULER_TITLES[self.ruler_title], self.username, self.epithet) if part
        )

    @property
    def ruler_mention(self) -> str:
        """e.g. "King @chaney the Great". Renders as a mention in embed descriptions/fields."""
        return " ".join(
            part for part in (RULER_TITLES[self.ruler_title], f"<@{self.id}>", self.epithet) if part
        )


@dataclass(frozen=True)
class Member:
    id: int
    name: str
    username: str
    role: AllianceRole
    battle_rating: int
    stake: int = 0  # resource value of their units in the alliance army


@dataclass(frozen=True)
class JoinRequest:
    player_id: int
    name: str
    battle_rating: int
    created_at: datetime


@dataclass
class Alliance:
    id: int
    name: str
    created_at: datetime
    members: list[Member] = field(default_factory=list)
    units: dict[str, int] = field(default_factory=dict)
    requests: list[JoinRequest] = field(default_factory=list)

    @property
    def battle_rating(self) -> int:
        return sum(m.battle_rating for m in self.members)

    @property
    def owner(self) -> Member | None:
        return next((m for m in self.members if m.role == "owner"), None)

    def member(self, player_id: int) -> Member | None:
        return next((m for m in self.members if m.id == player_id), None)


@dataclass(frozen=True)
class AllianceSummary:
    id: int
    name: str
    members: int
    battle_rating: int


@dataclass(frozen=True)
class Target:
    id: int
    name: str
    username: str
    battle_rating: int
    alliance: str | None = None

"""SQLite schema. Alembic migrations are generated from this metadata.

Resources are columns with CHECK (>= 0), so a bug that would overspend fails loudly in
the database instead of saving a negative balance. Production rates are never stored:
they are derived from buildings, research, wonders and heroes on every read.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Dialect,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    TypeDecorator,
)

from chongabot.content.models import RESOURCES


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC datetimes stored as ISO-8601 text (sorts correctly)."""

    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime; use datetime.now(UTC)")
        return value.astimezone(UTC).isoformat(timespec="seconds")

    def process_result_value(self, value: str | None, dialect: Dialect) -> datetime | None:
        return None if value is None else datetime.fromisoformat(value)


metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

players = Table(
    "players",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),  # Discord user ID
    Column("name", String(32, collation="NOCASE"), nullable=False, unique=True),
    Column("username", String(64), nullable=False),
    Column("ruler_title", String(16), nullable=False, server_default="ruler"),
    Column("epithet", String(32), nullable=False, server_default=""),
    Column("origin_guild_id", Integer),
    Column("age", String(32), nullable=False),
    Column("motto", String(200), nullable=False, server_default=""),
    Column("alliance_id", Integer, ForeignKey("alliances.id", ondelete="SET NULL")),
    Column("alliance_role", String(16)),
    # Resource value of this member's units in the alliance army. Shrinks with the army's
    # losses, and resets on leaving. Boss loot is split by it.
    Column("alliance_stake", Integer, nullable=False, server_default="0"),
    Column("battle_rating", Integer, nullable=False, server_default="0"),
    Column("wins", Integer, nullable=False, server_default="0"),
    Column("losses", Integer, nullable=False, server_default="0"),
    *(Column(r, Integer, nullable=False, server_default="0") for r in RESOURCES),
    Column("last_claim", UTCDateTime, nullable=False),
    Column("last_explore", UTCDateTime),
    Column("last_attack", UTCDateTime),
    Column("shield_until", UTCDateTime),
    Column("hero", String(64)),  # Second in Command; must be one of the player's heroes
    Column("hero_appointed_at", UTCDateTime),
    Column("created_at", UTCDateTime, nullable=False),
    *(CheckConstraint(f"{r} >= 0", name=f"{r}_not_negative") for r in RESOURCES),
    CheckConstraint("battle_rating >= 0", name="battle_rating_not_negative"),
    CheckConstraint(
        "alliance_role IS NULL OR alliance_role IN ('owner', 'officer', 'member')",
        name="alliance_role_valid",
    ),
    CheckConstraint(
        "(alliance_id IS NULL) = (alliance_role IS NULL)", name="alliance_role_iff_member"
    ),
)
Index("ix_players_battle_rating", players.c.battle_rating.desc())
Index("ix_players_alliance_id", players.c.alliance_id)


def _counts(name: str, owner: str, owner_table: str, item: str) -> Table:
    return Table(
        name,
        metadata,
        Column(
            owner,
            Integer,
            ForeignKey(f"{owner_table}.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        Column(item, String(64), primary_key=True),
        Column("count", Integer, nullable=False),
        CheckConstraint("count >= 0", name="count_not_negative"),
    )


player_buildings = _counts("player_buildings", "player_id", "players", "building")
player_units = _counts("player_units", "player_id", "players", "unit")
alliance_units = _counts("alliance_units", "alliance_id", "alliances", "unit")

player_unlocks = Table(
    "player_unlocks",
    metadata,
    Column("player_id", Integer, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True),
    Column("kind", String(16), primary_key=True),
    Column("key", String(64), primary_key=True),
    Column("created_at", UTCDateTime, nullable=False),
    CheckConstraint("kind IN ('research', 'wonder', 'hero')", name="kind_valid"),
)

alliances = Table(
    "alliances",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(32, collation="NOCASE"), nullable=False, unique=True),
    # no owner_id: the owner is the member whose alliance_role is 'owner'
    Column("origin_guild_id", Integer),
    Column("created_at", UTCDateTime, nullable=False),
)

alliance_requests = Table(
    "alliance_requests",
    metadata,
    Column(
        "alliance_id", Integer, ForeignKey("alliances.id", ondelete="CASCADE"), primary_key=True
    ),
    # unique: one pending request per player at a time
    Column(
        "player_id",
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        primary_key=True,
        unique=True,
    ),
    Column("created_at", UTCDateTime, nullable=False),
)

battles = Table(
    "battles",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("attacker_id", Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
    Column("defender_id", Integer, ForeignKey("players.id", ondelete="CASCADE")),
    Column("defender_kind", String(16), nullable=False),
    Column("defender_bot", String(64)),  # bot nation id, for defender_kind = 'bot'
    Column("winner", String(16), nullable=False),
    Column("log", JSON, nullable=False),
    Column("attacker_seen_at", UTCDateTime),
    Column("defender_seen_at", UTCDateTime),
    Column("created_at", UTCDateTime, nullable=False),
    CheckConstraint(
        "defender_kind IN ('player', 'pirate', 'boss', 'bot')", name="defender_kind_valid"
    ),
    CheckConstraint("winner IN ('attacker', 'defender')", name="winner_valid"),
)
Index("ix_battles_attacker", battles.c.attacker_id, battles.c.created_at.desc())
Index("ix_battles_defender", battles.c.defender_id, battles.c.created_at.desc())
Index("ix_battles_bot", battles.c.attacker_id, battles.c.defender_bot, battles.c.created_at)


boss_fights = Table(
    "boss_fights",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("alliance_id", Integer, ForeignKey("alliances.id", ondelete="CASCADE"), nullable=False),
    Column("boss", String(64), nullable=False),
    Column("started_by", Integer, ForeignKey("players.id", ondelete="SET NULL")),
    Column("winner", String(16), nullable=False),
    Column("payouts", JSON, nullable=False),  # {player_id: {resource: amount}}
    Column("log", JSON, nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
    CheckConstraint("winner IN ('attacker', 'defender')", name="winner_valid"),
)
Index(
    "ix_boss_fights_alliance",
    boss_fights.c.alliance_id,
    boss_fights.c.boss,
    boss_fights.c.created_at,
)

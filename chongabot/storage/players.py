"""Player persistence. Every function takes the connection of the caller's transaction."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast

from sqlalchemy import and_, delete, func, insert, or_, select, update
from sqlalchemy.dialects.sqlite import insert as upsert
from sqlalchemy.ext.asyncio import AsyncConnection

from chongabot.content.models import RESOURCES, Resource
from chongabot.domain.errors import NotEnough
from chongabot.domain.models import AllianceRole, Player, RulerTitle, Target
from chongabot.storage.schema import (
    alliances,
    player_buildings,
    player_units,
    player_unlocks,
    players,
)

UnlockKind = str  # "research" | "wonder" | "hero"


def _player(row: Any, counts: dict[str, dict[str, int]], unlocks: dict[str, set[str]]) -> Player:
    return Player(
        id=row["id"],
        name=row["name"],
        username=row["username"],
        age=row["age"],
        resources={r: row[r] for r in RESOURCES},
        last_claim=row["last_claim"],
        created_at=row["created_at"],
        motto=row["motto"],
        battle_rating=row["battle_rating"],
        wins=row["wins"],
        losses=row["losses"],
        buildings=counts.get("buildings", {}),
        units=counts.get("units", {}),
        research=frozenset(unlocks.get("research", ())),
        wonders=frozenset(unlocks.get("wonder", ())),
        heroes=frozenset(unlocks.get("hero", ())),
        hero=row["hero"],
        hero_appointed_at=row["hero_appointed_at"],
        shield_until=row["shield_until"],
        last_explore=row["last_explore"],
        last_attack=row["last_attack"],
        alliance_id=row["alliance_id"],
        alliance_role=cast(AllianceRole | None, row["alliance_role"]),
        origin_guild_id=row["origin_guild_id"],
        ruler_title=cast(RulerTitle, row["ruler_title"]),
        epithet=row["epithet"],
    )


async def _load(conn: AsyncConnection, where: Any) -> Player | None:
    row = (await conn.execute(select(players).where(where))).mappings().first()
    if row is None:
        return None
    pid = row["id"]
    buildings = await conn.execute(
        select(player_buildings.c.building, player_buildings.c.count).where(
            player_buildings.c.player_id == pid, player_buildings.c.count > 0
        )
    )
    units = await conn.execute(
        select(player_units.c.unit, player_units.c.count).where(
            player_units.c.player_id == pid, player_units.c.count > 0
        )
    )
    unlocks: dict[str, set[str]] = {}
    for kind, key in await conn.execute(
        select(player_unlocks.c.kind, player_unlocks.c.key).where(player_unlocks.c.player_id == pid)
    ):
        unlocks.setdefault(kind, set()).add(key)
    counts = {"buildings": dict(buildings.all()), "units": dict(units.all())}
    return _player(row, counts, unlocks)


async def get(conn: AsyncConnection, player_id: int) -> Player | None:
    return await _load(conn, players.c.id == player_id)


async def get_by_name(conn: AsyncConnection, name: str) -> Player | None:
    return await _load(conn, players.c.name == name)  # column collation is NOCASE


async def name_taken(conn: AsyncConnection, name: str) -> bool:
    found = await conn.scalar(select(players.c.id).where(players.c.name == name))
    return found is not None


async def create(
    conn: AsyncConnection,
    *,
    player_id: int,
    name: str,
    username: str,
    age: str,
    resources: Mapping[Resource, int],
    units: Mapping[str, int],
    guild_id: int | None,
    now: datetime,
    ruler_title: RulerTitle = "ruler",
    epithet: str = "",
) -> None:
    await conn.execute(
        insert(players).values(
            id=player_id,
            name=name,
            username=username,
            ruler_title=ruler_title,
            epithet=epithet,
            age=age,
            origin_guild_id=guild_id,
            last_claim=now,
            created_at=now,
            **{r: resources.get(r, 0) for r in RESOURCES},
        )
    )
    await add_units(conn, player_id, units)


async def update_fields(conn: AsyncConnection, player_id: int, **values: Any) -> None:
    await conn.execute(update(players).where(players.c.id == player_id).values(**values))


# --- resources -----------------------------------------------------------------


async def spend(conn: AsyncConnection, player_id: int, cost: Mapping[Resource, int]) -> None:
    """Subtract `cost`, but only if every resource covers it. One conditional UPDATE.

    Callers check affordability first to show a friendly message; this is the guarantee.
    """
    cost = {r: v for r, v in cost.items() if v > 0}
    if not cost:
        return
    result = await conn.execute(
        update(players)
        .where(players.c.id == player_id, *(players.c[r] >= v for r, v in cost.items()))
        .values({r: players.c[r] - v for r, v in cost.items()})
    )
    if result.rowcount != 1:
        raise NotEnough("You can't afford that any more.")


async def give(conn: AsyncConnection, player_id: int, amounts: Mapping[Resource, int]) -> None:
    amounts = {r: v for r, v in amounts.items() if v > 0}
    if amounts:
        await conn.execute(
            update(players)
            .where(players.c.id == player_id)
            .values({r: players.c[r] + v for r, v in amounts.items()})
        )


async def take(conn: AsyncConnection, player_id: int, amounts: Mapping[Resource, int]) -> None:
    """Subtract up to `amounts`, flooring each resource at zero (used for tribute)."""
    amounts = {r: v for r, v in amounts.items() if v > 0}
    if amounts:
        await conn.execute(
            update(players)
            .where(players.c.id == player_id)
            .values({r: func.max(players.c[r] - v, 0) for r, v in amounts.items()})
        )


# --- buildings, units, unlocks -------------------------------------------------


async def _add_counts(
    conn: AsyncConnection, table: Any, item_col: str, player_id: int, counts: Mapping[str, int]
) -> None:
    for item, n in counts.items():
        if n == 0:
            continue
        stmt = upsert(table).values(player_id=player_id, **{item_col: item}, count=max(n, 0))
        await conn.execute(
            stmt.on_conflict_do_update(
                index_elements=["player_id", item_col], set_={"count": table.c.count + n}
            )
        )


async def add_buildings(conn: AsyncConnection, player_id: int, counts: Mapping[str, int]) -> None:
    await _add_counts(conn, player_buildings, "building", player_id, counts)


async def add_units(conn: AsyncConnection, player_id: int, counts: Mapping[str, int]) -> None:
    """Add (or, with negative counts, remove) units. Removing below zero violates CHECK."""
    await _add_counts(conn, player_units, "unit", player_id, counts)


async def add_unlock(
    conn: AsyncConnection, player_id: int, kind: UnlockKind, key: str, now: datetime
) -> None:
    await conn.execute(
        upsert(player_unlocks)
        .values(player_id=player_id, kind=kind, key=key, created_at=now)
        .on_conflict_do_nothing()
    )


# --- lists -----------------------------------------------------------------------


def _target(row: Any) -> Target:
    return Target(id=row.id, name=row.name, username=row.username, battle_rating=row.battle_rating)


async def leaderboard(conn: AsyncConnection, limit: int = 10, offset: int = 0) -> list[Target]:
    rows = await conn.execute(
        select(
            players.c.id,
            players.c.name,
            players.c.username,
            players.c.battle_rating,
            alliances.c.name.label("alliance"),
        )
        .join(alliances, alliances.c.id == players.c.alliance_id, isouter=True)
        .order_by(players.c.battle_rating.desc(), players.c.wins.desc(), players.c.id)
        .limit(limit)
        .offset(offset)
    )
    return [
        Target(
            id=r.id,
            name=r.name,
            username=r.username,
            battle_rating=r.battle_rating,
            alliance=r.alliance,
        )
        for r in rows
    ]


async def rank(conn: AsyncConnection, battle_rating: int) -> int:
    above = await conn.scalar(
        select(func.count()).select_from(players).where(players.c.battle_rating > battle_rating)
    )
    return int(above or 0) + 1


async def count(conn: AsyncConnection) -> int:
    return int(await conn.scalar(select(func.count()).select_from(players)) or 0)


async def targets(
    conn: AsyncConnection, attacker: Player, rating_range: int, now: datetime, limit: int = 15
) -> list[Target]:
    """Nations the attacker could hit right now: in range, unshielded, not allied."""
    conditions = [
        players.c.id != attacker.id,
        players.c.battle_rating.between(
            attacker.battle_rating - rating_range, attacker.battle_rating + rating_range
        ),
        or_(players.c.shield_until.is_(None), players.c.shield_until <= now),
    ]
    if attacker.alliance_id is not None:
        conditions.append(
            or_(players.c.alliance_id.is_(None), players.c.alliance_id != attacker.alliance_id)
        )
    rows = await conn.execute(
        select(players.c.id, players.c.name, players.c.username, players.c.battle_rating)
        .where(and_(*conditions))
        .order_by(func.abs(players.c.battle_rating - attacker.battle_rating), players.c.name)
        .limit(limit)
    )
    return [_target(r) for r in rows]


async def search(conn: AsyncConnection, text: str, limit: int = 25) -> list[Target]:
    """Autocomplete: names starting with `text`, then names containing it."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = await conn.execute(
        select(players.c.id, players.c.name, players.c.username, players.c.battle_rating)
        .where(players.c.name.ilike(f"%{escaped}%", escape="\\"))
        .order_by(players.c.name.ilike(f"{escaped}%", escape="\\").desc(), players.c.name)
        .limit(limit)
    )
    return [_target(r) for r in rows]


async def all_ids(conn: AsyncConnection) -> list[int]:
    return list((await conn.scalars(select(players.c.id))).all())


async def delete_player(conn: AsyncConnection, player_id: int) -> None:
    await conn.execute(delete(players).where(players.c.id == player_id))

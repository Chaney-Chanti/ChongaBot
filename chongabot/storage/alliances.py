"""Alliance persistence."""

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from sqlalchemy import Integer, case, delete, func, insert, select, update
from sqlalchemy import cast as cast_
from sqlalchemy.dialects.sqlite import insert as upsert
from sqlalchemy.ext.asyncio import AsyncConnection

from chongabot.domain.models import (
    ROLE_RANK,
    Alliance,
    AllianceRole,
    AllianceSummary,
    JoinRequest,
    Member,
)
from chongabot.storage.schema import alliance_requests, alliance_units, alliances, players


async def create(conn: AsyncConnection, name: str, guild_id: int | None, now: datetime) -> int:
    result = await conn.execute(
        insert(alliances).values(name=name, origin_guild_id=guild_id, created_at=now)
    )
    pk = result.inserted_primary_key
    assert pk is not None
    return int(pk[0])


async def name_taken(conn: AsyncConnection, name: str) -> bool:
    return await conn.scalar(select(alliances.c.id).where(alliances.c.name == name)) is not None


async def get(conn: AsyncConnection, alliance_id: int) -> Alliance | None:
    row = (await conn.execute(select(alliances).where(alliances.c.id == alliance_id))).first()
    if row is None:
        return None
    members = [
        Member(
            id=m.id,
            name=m.name,
            username=m.username,
            role=cast(AllianceRole, m.alliance_role),
            battle_rating=m.battle_rating,
            stake=m.alliance_stake,
        )
        for m in await conn.execute(
            select(
                players.c.id,
                players.c.name,
                players.c.username,
                players.c.alliance_role,
                players.c.battle_rating,
                players.c.alliance_stake,
            ).where(players.c.alliance_id == alliance_id)
        )
    ]
    members.sort(key=lambda m: (-ROLE_RANK[m.role], -m.battle_rating, m.name.lower()))
    units = dict(
        (
            await conn.execute(
                select(alliance_units.c.unit, alliance_units.c.count).where(
                    alliance_units.c.alliance_id == alliance_id, alliance_units.c.count > 0
                )
            )
        ).all()
    )
    requests = [
        JoinRequest(
            player_id=r.player_id,
            name=r.name,
            battle_rating=r.battle_rating,
            created_at=r.created_at,
        )
        for r in await conn.execute(
            select(
                alliance_requests.c.player_id,
                alliance_requests.c.created_at,
                players.c.name,
                players.c.battle_rating,
            )
            .join(players, players.c.id == alliance_requests.c.player_id)
            .where(alliance_requests.c.alliance_id == alliance_id)
            .order_by(alliance_requests.c.created_at)
        )
    ]
    return Alliance(
        id=row.id,
        name=row.name,
        created_at=row.created_at,
        members=members,
        units=units,
        requests=requests,
    )


async def get_by_name(conn: AsyncConnection, name: str) -> Alliance | None:
    alliance_id = await conn.scalar(select(alliances.c.id).where(alliances.c.name == name))
    return None if alliance_id is None else await get(conn, alliance_id)


async def browse(conn: AsyncConnection, limit: int = 25, offset: int = 0) -> list[AllianceSummary]:
    """Alliances ranked by total battle rating: the sum of their members' ratings."""
    members = func.count(players.c.id)
    rating = func.coalesce(func.sum(players.c.battle_rating), 0)
    rows = await conn.execute(
        select(alliances.c.id, alliances.c.name, members.label("members"), rating.label("br"))
        .join(players, players.c.alliance_id == alliances.c.id, isouter=True)
        .group_by(alliances.c.id)
        .order_by(rating.desc(), members.desc(), alliances.c.name)
        .limit(limit)
        .offset(offset)
    )
    return [
        AllianceSummary(id=r.id, name=r.name, members=r.members, battle_rating=r.br) for r in rows
    ]


async def count(conn: AsyncConnection) -> int:
    return int(await conn.scalar(select(func.count()).select_from(alliances)) or 0)


async def member_count(conn: AsyncConnection, alliance_id: int) -> int:
    n = await conn.scalar(
        select(func.count()).select_from(players).where(players.c.alliance_id == alliance_id)
    )
    return int(n or 0)


async def set_membership(
    conn: AsyncConnection, player_id: int, alliance_id: int | None, role: AllianceRole | None
) -> None:
    # A stake belongs to one alliance's army: moving or leaving forfeits it.
    stake = case(
        (players.c.alliance_id.is_not_distinct_from(alliance_id), players.c.alliance_stake),
        else_=0,
    )
    await conn.execute(
        update(players)
        .where(players.c.id == player_id)
        .values(alliance_id=alliance_id, alliance_role=role, alliance_stake=stake)
    )


async def add_stake(conn: AsyncConnection, player_id: int, value: int) -> None:
    await conn.execute(
        update(players)
        .where(players.c.id == player_id)
        .values(alliance_stake=players.c.alliance_stake + value)
    )


async def scale_stakes(conn: AsyncConnection, alliance_id: int, before: int, after: int) -> None:
    """The army shrank from `before` to `after` in value: shrink every stake to match."""
    if before <= 0 or after >= before:
        return
    await conn.execute(
        update(players)
        .where(players.c.alliance_id == alliance_id)
        .values(alliance_stake=cast_(players.c.alliance_stake * (max(after, 0) / before), Integer))
    )


async def add_request(
    conn: AsyncConnection, alliance_id: int, player_id: int, now: datetime
) -> None:
    await conn.execute(
        insert(alliance_requests).values(
            alliance_id=alliance_id, player_id=player_id, created_at=now
        )
    )


async def pending_request(conn: AsyncConnection, player_id: int) -> int | None:
    """The alliance this player has a pending request with, if any."""
    return await conn.scalar(
        select(alliance_requests.c.alliance_id).where(alliance_requests.c.player_id == player_id)
    )


async def remove_request(conn: AsyncConnection, player_id: int) -> bool:
    result = await conn.execute(
        delete(alliance_requests).where(alliance_requests.c.player_id == player_id)
    )
    return result.rowcount > 0


async def add_units(conn: AsyncConnection, alliance_id: int, counts: Mapping[str, int]) -> None:
    for unit, n in counts.items():
        if n == 0:
            continue
        stmt = upsert(alliance_units).values(alliance_id=alliance_id, unit=unit, count=max(n, 0))
        await conn.execute(
            stmt.on_conflict_do_update(
                index_elements=["alliance_id", "unit"],
                set_={"count": alliance_units.c.count + n},
            )
        )


async def disband(conn: AsyncConnection, alliance_id: int) -> None:
    # players.alliance_id is ON DELETE SET NULL, but the role must be cleared with it
    await conn.execute(
        update(players)
        .where(players.c.alliance_id == alliance_id)
        .values(alliance_id=None, alliance_role=None, alliance_stake=0)
    )
    await conn.execute(delete(alliances).where(alliances.c.id == alliance_id))

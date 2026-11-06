"""Alliance boss fights: the record, and per-boss cooldowns."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from chongabot.content.models import Resource
from chongabot.storage.schema import boss_fights


async def record(
    conn: AsyncConnection,
    *,
    alliance_id: int,
    boss: str,
    started_by: int,
    winner: str,
    payouts: Mapping[int, Mapping[Resource, int]],
    log: dict[str, Any],
    now: datetime,
) -> int:
    result = await conn.execute(
        insert(boss_fights).values(
            alliance_id=alliance_id,
            boss=boss,
            started_by=started_by,
            winner=winner,
            payouts={str(p): dict(c) for p, c in payouts.items()},
            log=log,
            created_at=now,
        )
    )
    pk = result.inserted_primary_key
    assert pk is not None
    return int(pk[0])


async def last_fights(conn: AsyncConnection, alliance_id: int) -> dict[str, datetime]:
    """When this alliance last fought each boss."""
    rows = await conn.execute(
        select(boss_fights.c.boss, func.max(boss_fights.c.created_at))
        .where(boss_fights.c.alliance_id == alliance_id)
        .group_by(boss_fights.c.boss)
    )
    out: dict[str, datetime] = {}
    for boss, when in rows:
        out[boss] = when if isinstance(when, datetime) else datetime.fromisoformat(when)
    return out

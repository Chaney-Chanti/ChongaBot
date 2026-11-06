"""Battle records, kept for the Activity's replays and /stats history."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncConnection

from chongabot.storage.schema import battles

DefenderKind = Literal["player", "pirate", "boss", "bot"]


@dataclass(frozen=True)
class BattleRecord:
    id: int
    attacker_id: int
    defender_id: int | None
    defender_kind: DefenderKind
    defender_bot: str | None
    winner: str
    log: dict[str, Any]
    created_at: datetime


async def record(
    conn: AsyncConnection,
    *,
    attacker_id: int,
    defender_id: int | None,
    defender_kind: DefenderKind,
    winner: str,
    log: dict[str, Any],
    now: datetime,
    defender_bot: str | None = None,
) -> int:
    result = await conn.execute(
        insert(battles).values(
            attacker_id=attacker_id,
            defender_id=defender_id,
            defender_kind=defender_kind,
            defender_bot=defender_bot,
            winner=winner,
            log=log,
            created_at=now,
        )
    )
    pk = result.inserted_primary_key
    assert pk is not None
    return int(pk[0])


def _record(r: Any) -> BattleRecord:
    return BattleRecord(
        id=r.id,
        attacker_id=r.attacker_id,
        defender_id=r.defender_id,
        defender_kind=r.defender_kind,
        defender_bot=r.defender_bot,
        winner=r.winner,
        log=r.log,
        created_at=r.created_at,
    )


async def get(conn: AsyncConnection, battle_id: int) -> BattleRecord | None:
    row = (await conn.execute(select(battles).where(battles.c.id == battle_id))).first()
    return None if row is None else _record(row)


async def recent(conn: AsyncConnection, player_id: int, limit: int = 5) -> list[BattleRecord]:
    rows = await conn.execute(
        select(battles)
        .where(or_(battles.c.attacker_id == player_id, battles.c.defender_id == player_id))
        .order_by(battles.c.created_at.desc(), battles.c.id.desc())
        .limit(limit)
    )
    return [_record(r) for r in rows]


async def last_bot_attacks(conn: AsyncConnection, player_id: int) -> dict[str, datetime]:
    """bot id -> when this player last attacked it."""
    rows = await conn.execute(
        select(battles.c.defender_bot, func.max(battles.c.created_at))
        .where(battles.c.attacker_id == player_id, battles.c.defender_kind == "bot")
        .group_by(battles.c.defender_bot)
    )
    # func.max keeps the column's UTCDateTime type, but be safe if a driver returns text
    return {
        bot: ts if isinstance(ts, datetime) else datetime.fromisoformat(ts)
        for bot, ts in rows
        if bot and ts
    }

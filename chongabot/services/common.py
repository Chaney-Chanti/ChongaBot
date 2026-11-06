"""Shared service plumbing: the game context, the clock and item lookup."""

import random
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol, TypeVar

from sqlalchemy.ext.asyncio import AsyncConnection

from chongabot.content import Content
from chongabot.domain.errors import GameError, NoNation
from chongabot.domain.models import Player
from chongabot.storage import players as player_repo
from chongabot.storage.db import Database

Clock = Callable[[], datetime]
Count = int | Literal["max"]


def utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


@dataclass
class GameContext:
    """What every service needs. `content` is swapped in place by /reload."""

    db: Database
    content: Content
    clock: Clock = utcnow
    rng: random.Random = field(default_factory=random.Random)


class Named(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...


T = TypeVar("T", bound=Named)


def _norm(text: str) -> str:
    return re.sub(r"[\s_\-']+", "", text).casefold()


def lookup(items: Mapping[str, T], text: str, what: str) -> T:
    """Find an item by id or display name, ignoring case, spaces and underscores."""
    if text in items:
        return items[text]
    key = _norm(text)
    for item in items.values():
        if _norm(item.id) == key or _norm(item.name) == key:
            return item
    raise GameError(f"There's no {what} called **{text}**.")


async def load_player(conn: AsyncConnection, player_id: int) -> Player:
    player = await player_repo.get(conn, player_id)
    if player is None:
        raise NoNation()
    return player


def check_count(count: Count) -> None:
    if count != "max" and count < 1:
        raise GameError("The amount has to be at least 1.")

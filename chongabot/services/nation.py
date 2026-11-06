"""Creating and looking up nations."""

import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncConnection

from chongabot.domain.errors import GameError
from chongabot.domain.models import EPITHETS, RULER_TITLES, Player, RulerTitle, Target
from chongabot.services.common import GameContext, load_player
from chongabot.storage import battles as battle_repo
from chongabot.storage import players as player_repo
from chongabot.storage.battles import BattleRecord

NAME_RE = re.compile(r"^[\w][\w '\-.]*[\w.]$")
NAME_MIN, NAME_MAX = 3, 24
MOTTO_MAX = 150


def clean_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not NAME_MIN <= len(name) <= NAME_MAX:
        raise GameError(f"Nation names are {NAME_MIN} to {NAME_MAX} characters.")
    if not NAME_RE.match(name) or name.startswith("<@"):
        raise GameError("Use letters, numbers, spaces, apostrophes, dots and dashes only.")
    return name


@dataclass(frozen=True)
class Profile:
    player: Player
    rank: int
    battles: list[BattleRecord]


class NationService:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    async def check_new(self, user_id: int, raw_name: str) -> str:
        """Validate a nation name before showing the founding menu. Returns it cleaned."""
        name = clean_name(raw_name)
        async with self.ctx.db.transaction() as conn:
            await self._check_new(conn, user_id, name)
        return name

    async def _check_new(self, conn: AsyncConnection, user_id: int, name: str) -> None:
        if await player_repo.get(conn, user_id):
            raise GameError("You already have a nation. See it with `/stats`.")
        if await player_repo.name_taken(conn, name):
            raise GameError(f"**{name}** is taken. Pick another name.")
        if any(b.name.casefold() == name.casefold() for b in self.ctx.content.bots.values()):
            raise GameError(f"**{name}** is a bot nation's name. Pick another name.")

    async def create(
        self,
        user_id: int,
        username: str,
        raw_name: str,
        guild_id: int | None,
        *,
        ruler_title: RulerTitle = "ruler",
        epithet: str = "",
    ) -> Player:
        name = clean_name(raw_name)
        if ruler_title not in RULER_TITLES:
            raise GameError("Pick King, Queen or Ruler.")
        if epithet and epithet not in EPITHETS:
            raise GameError("Pick an epithet from the list.")
        content = self.ctx.content
        s = content.settings
        async with self.ctx.db.transaction() as conn:
            await self._check_new(conn, user_id, name)
            await player_repo.create(
                conn,
                player_id=user_id,
                name=name,
                username=username,
                age=content.ages[0].id,
                resources=s.starting_resources,
                units=s.starting_units,
                guild_id=guild_id,
                now=self.ctx.clock(),
                ruler_title=ruler_title,
                epithet=epithet,
            )
            return await load_player(conn, user_id)

    async def get(self, user_id: int) -> Player:
        async with self.ctx.db.transaction() as conn:
            return await load_player(conn, user_id)

    async def maybe_get(self, user_id: int) -> Player | None:
        async with self.ctx.db.transaction() as conn:
            return await player_repo.get(conn, user_id)

    async def find(self, name: str) -> Player:
        async with self.ctx.db.transaction() as conn:
            player = await player_repo.get_by_name(conn, " ".join(name.split()))
        if player is None:
            raise GameError(f"There's no nation called **{name}**.")
        return player

    async def profile(self, user_id: int) -> Profile:
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            rank = await player_repo.rank(conn, player.battle_rating)
            battles = await battle_repo.recent(conn, user_id, limit=3)
        return Profile(player, rank, battles)

    async def set_motto(self, user_id: int, motto: str) -> str:
        motto = " ".join(motto.split())
        if len(motto) > MOTTO_MAX:
            raise GameError(f"Mottos are at most {MOTTO_MAX} characters.")
        async with self.ctx.db.transaction() as conn:
            await load_player(conn, user_id)
            await player_repo.update_fields(conn, user_id, motto=motto)
        return motto

    async def leaderboard(self, page: int = 0, per_page: int = 10) -> tuple[list[Target], int]:
        async with self.ctx.db.transaction() as conn:
            rows = await player_repo.leaderboard(conn, per_page, page * per_page)
            total = await player_repo.count(conn)
        return rows, total

    async def search(self, text: str) -> list[Target]:
        async with self.ctx.db.transaction() as conn:
            return await player_repo.search(conn, text)

    async def all_ids(self) -> list[int]:
        async with self.ctx.db.transaction() as conn:
            return await player_repo.all_ids(conn)

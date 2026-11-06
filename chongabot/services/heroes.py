"""Appointing and dismissing your Second in Command."""

from chongabot.domain.errors import GameError
from chongabot.domain.models import Player
from chongabot.rules import heroes
from chongabot.services.common import GameContext, load_player, lookup
from chongabot.storage import players as player_repo


class HeroService:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    async def appoint(self, user_id: int, hero: str) -> Player:
        content, now = self.ctx.content, self.ctx.clock()
        h = lookup(content.heroes, hero, "hero")
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            heroes.check_can_appoint(player, h, content, now)
            await player_repo.update_fields(conn, user_id, hero=h.id, hero_appointed_at=now)
            return await load_player(conn, user_id)

    async def dismiss(self, user_id: int) -> Player:
        """Leave the post empty. Doesn't reset the swap cooldown."""
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            if player.hero is None:
                raise GameError("You don't have a Second in Command.")
            await player_repo.update_fields(conn, user_id, hero=None)
            return await load_player(conn, user_id)

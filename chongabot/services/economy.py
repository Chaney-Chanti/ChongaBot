"""Claiming and buying: buildings, units, research and ages.

Each method is one transaction: load, check, spend, apply. BEGIN IMMEDIATE means nothing
else writes in between, and `spend` re-checks balances in its UPDATE as a final guard.
"""

from dataclasses import dataclass

from chongabot.content.models import Age
from chongabot.domain.errors import GameError
from chongabot.domain.models import Player
from chongabot.rules import economy
from chongabot.rules.economy import ClaimResult, Cost
from chongabot.services.common import Count, GameContext, check_count, load_player, lookup
from chongabot.storage import players as player_repo


@dataclass(frozen=True)
class Purchase:
    item: str  # display name
    count: int
    cost: Cost
    player: Player  # state after the purchase


@dataclass(frozen=True)
class Claimed:
    result: ClaimResult
    player: Player


class EconomyService:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    async def claim(self, user_id: int) -> Claimed:
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            now = self.ctx.clock()
            result = economy.claim(player, self.ctx.content, now)
            await player_repo.give(conn, user_id, result.gained)
            await player_repo.update_fields(conn, user_id, last_claim=now)
            return Claimed(result, await load_player(conn, user_id))

    async def build(self, user_id: int, building: str, count: Count) -> Purchase:
        check_count(count)
        content = self.ctx.content
        b = lookup(content.buildings, building, "building")
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            economy.check_buildable(player, content, b)
            n = economy.max_buildings(player, content, b) if count == "max" else count
            if n == 0:
                raise GameError(f"You can't afford a single {b.name} yet.")
            cost = economy.building_cost(player, content, b, n)
            economy.require(player.resources, cost)
            await player_repo.spend(conn, user_id, cost)
            await player_repo.add_buildings(conn, user_id, {b.id: n})
            return Purchase(b.name, n, cost, await load_player(conn, user_id))

    async def train(self, user_id: int, unit: str, count: Count) -> Purchase:
        check_count(count)
        content = self.ctx.content
        u = lookup(content.units, unit, "unit")
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            economy.check_trainable(player, content, u)
            n = economy.max_units(player, content, u) if count == "max" else count
            if n == 0:
                raise GameError(f"You can't afford a single {u.name} yet.")
            cost = economy.unit_cost(player, content, u, n)
            economy.require(player.resources, cost)
            await player_repo.spend(conn, user_id, cost)
            await player_repo.add_units(conn, user_id, {u.id: n})
            return Purchase(u.name, n, cost, await load_player(conn, user_id))

    async def research(self, user_id: int, topic: str) -> Purchase:
        content = self.ctx.content
        r = lookup(content.research, topic, "research topic")
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            economy.check_researchable(player, content, r)
            cost = economy.research_cost(player, content, r)
            economy.require(player.resources, cost)
            await player_repo.spend(conn, user_id, cost)
            await player_repo.add_unlock(conn, user_id, "research", r.id, self.ctx.clock())
            return Purchase(r.name, 1, cost, await load_player(conn, user_id))

    async def advance(self, user_id: int) -> tuple[Age, Player, list[economy.Retraining]]:
        """Enter the next age. Older units are retrained into the new age's units."""
        content = self.ctx.content
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            age = economy.next_age(player, content)
            economy.require(player.resources, age.advance_cost)
            await player_repo.spend(conn, user_id, age.advance_cost)
            await player_repo.update_fields(conn, user_id, age=age.id)
            retrained = economy.retrain_army(player.units, age.id, content)
            delta: dict[str, int] = {}
            for r in retrained:
                for old, n in r.old.items():
                    delta[old] = delta.get(old, 0) - n
                delta[r.into] = delta.get(r.into, 0) + r.count
            await player_repo.add_units(conn, user_id, delta)
            return age, await load_player(conn, user_id), retrained

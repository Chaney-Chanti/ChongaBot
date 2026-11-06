"""Alliances: founding, joining by request, roles, and the shared army.

Roles: owner > officer > member. Officers handle join requests and kick members;
the owner also promotes, demotes, transfers ownership and disbands.
"""

from sqlalchemy.ext.asyncio import AsyncConnection

from chongabot.domain.errors import GameError, NotEnough
from chongabot.domain.models import ROLE_RANK, Alliance, AllianceRole, AllianceSummary, Player
from chongabot.services.common import Count, GameContext, check_count, load_player, lookup
from chongabot.services.nation import clean_name
from chongabot.storage import alliances as alliance_repo
from chongabot.storage import players as player_repo


async def _require_alliance(conn: AsyncConnection, player: Player) -> Alliance:
    if player.alliance_id is None:
        raise GameError("You're not in an alliance.")
    alliance = await alliance_repo.get(conn, player.alliance_id)
    assert alliance is not None  # FK guarantees it
    return alliance


def _require_role(player: Player, role: AllianceRole) -> None:
    if player.alliance_role is None or ROLE_RANK[player.alliance_role] < ROLE_RANK[role]:
        raise GameError(
            f"Only the alliance {role} can do that."
            if role == "owner"
            else "Only officers and the owner can do that."
        )


class AllianceService:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    # --- reading -----------------------------------------------------------------

    async def mine(self, user_id: int) -> tuple[Player, Alliance | None, int | None]:
        """The player, their alliance (if any), and their pending request's alliance id."""
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            alliance = (
                await alliance_repo.get(conn, player.alliance_id) if player.alliance_id else None
            )
            pending = await alliance_repo.pending_request(conn, user_id)
        return player, alliance, pending

    async def get(self, alliance_id: int) -> Alliance:
        async with self.ctx.db.transaction() as conn:
            alliance = await alliance_repo.get(conn, alliance_id)
        if alliance is None:
            raise GameError("That alliance no longer exists.")
        return alliance

    async def browse(self) -> list[AllianceSummary]:
        async with self.ctx.db.transaction() as conn:
            return await alliance_repo.browse(conn)

    async def leaderboard(
        self, page: int = 0, per_page: int = 10
    ) -> tuple[list[AllianceSummary], int]:
        async with self.ctx.db.transaction() as conn:
            rows = await alliance_repo.browse(conn, per_page, page * per_page)
            total = await alliance_repo.count(conn)
        return rows, total

    # --- joining and leaving -----------------------------------------------------

    async def create(self, user_id: int, raw_name: str, guild_id: int | None) -> Alliance:
        name = clean_name(raw_name)
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            if player.alliance_id is not None:
                raise GameError("Leave your current alliance first.")
            if await alliance_repo.name_taken(conn, name):
                raise GameError(f"An alliance called **{name}** already exists.")
            await alliance_repo.remove_request(conn, user_id)
            alliance_id = await alliance_repo.create(conn, name, guild_id, self.ctx.clock())
            await alliance_repo.set_membership(conn, user_id, alliance_id, "owner")
            return await _require_alliance(conn, await load_player(conn, user_id))

    async def request_join(self, user_id: int, alliance_id: int) -> Alliance:
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            if player.alliance_id is not None:
                raise GameError("You're already in an alliance.")
            alliance = await alliance_repo.get(conn, alliance_id)
            if alliance is None:
                raise GameError("That alliance no longer exists.")
            if len(alliance.members) >= self.ctx.content.settings.alliance_member_cap:
                raise GameError(f"**{alliance.name}** is full.")
            await alliance_repo.remove_request(conn, user_id)  # replaces any older request
            await alliance_repo.add_request(conn, alliance_id, user_id, self.ctx.clock())
            return alliance

    async def cancel_request(self, user_id: int) -> None:
        async with self.ctx.db.transaction() as conn:
            if not await alliance_repo.remove_request(conn, user_id):
                raise GameError("You don't have a pending request.")

    async def answer_request(self, actor_id: int, player_id: int, accept: bool) -> Player:
        async with self.ctx.db.transaction() as conn:
            actor = await load_player(conn, actor_id)
            _require_role(actor, "officer")
            alliance = await _require_alliance(conn, actor)
            if all(r.player_id != player_id for r in alliance.requests):
                raise GameError("That request was already handled.")
            await alliance_repo.remove_request(conn, player_id)
            applicant = await load_player(conn, player_id)
            if accept:
                if applicant.alliance_id is not None:
                    raise GameError(f"{applicant.name} already joined another alliance.")
                if len(alliance.members) >= self.ctx.content.settings.alliance_member_cap:
                    raise GameError("Your alliance is full.")
                await alliance_repo.set_membership(conn, player_id, alliance.id, "member")
            return applicant

    async def leave(self, user_id: int) -> str:
        """Returns the alliance name. A sole owner leaving disbands it."""
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            alliance = await _require_alliance(conn, player)
            if player.alliance_role == "owner":
                if len(alliance.members) > 1:
                    raise GameError(
                        "You're the owner. Transfer ownership first, or disband the alliance."
                    )
                await alliance_repo.disband(conn, alliance.id)
            else:
                await alliance_repo.set_membership(conn, user_id, None, None)
            return alliance.name

    # --- officer and owner actions -------------------------------------------------

    async def _member_action(
        self, conn: AsyncConnection, actor_id: int, target_id: int, role: AllianceRole
    ) -> tuple[Player, Alliance, AllianceRole]:
        actor = await load_player(conn, actor_id)
        _require_role(actor, role)
        alliance = await _require_alliance(conn, actor)
        target = alliance.member(target_id)
        if target is None:
            raise GameError("They're not in your alliance any more.")
        if target_id == actor_id:
            raise GameError("You can't do that to yourself.")
        return actor, alliance, target.role

    async def kick(self, actor_id: int, target_id: int) -> None:
        async with self.ctx.db.transaction() as conn:
            actor, _, target_role = await self._member_action(conn, actor_id, target_id, "officer")
            assert actor.alliance_role
            if ROLE_RANK[target_role] >= ROLE_RANK[actor.alliance_role]:
                raise GameError("You can only kick members ranked below you.")
            await alliance_repo.set_membership(conn, target_id, None, None)

    async def set_role(self, actor_id: int, target_id: int, role: AllianceRole) -> None:
        """Promote to officer, demote to member, or (role="owner") transfer ownership."""
        async with self.ctx.db.transaction() as conn:
            _, alliance, current = await self._member_action(conn, actor_id, target_id, "owner")
            if current == role:
                raise GameError(f"They're already {'the' if role == 'owner' else 'a'} {role}.")
            await alliance_repo.set_membership(conn, target_id, alliance.id, role)
            if role == "owner":
                await alliance_repo.set_membership(conn, actor_id, alliance.id, "officer")

    async def disband(self, actor_id: int) -> str:
        async with self.ctx.db.transaction() as conn:
            actor = await load_player(conn, actor_id)
            _require_role(actor, "owner")
            alliance = await _require_alliance(conn, actor)
            await alliance_repo.disband(conn, alliance.id)
            return alliance.name

    # --- the shared army -------------------------------------------------------------

    async def contribute(self, user_id: int, unit: str, count: Count) -> tuple[str, int]:
        """Move units into the alliance army, which defends members and fights bosses.

        The units' resource value is added to the player's stake, which sets their share of
        boss loot.
        """
        check_count(count)
        u = lookup(self.ctx.content.units, unit, "unit")
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            alliance = await _require_alliance(conn, player)
            have = player.units.get(u.id, 0)
            n = have if count == "max" else count
            if n == 0 or n > have:
                raise NotEnough(f"You have {have:,} {u.name}.")
            await player_repo.add_units(conn, user_id, {u.id: -n})
            await alliance_repo.add_units(conn, alliance.id, {u.id: n})
            await alliance_repo.add_stake(conn, user_id, sum(u.cost.values()) * n)
            return u.name, n

"""Development helpers behind the owner-only /dev commands. Never loaded in production.

Fake nations use IDs 1-999. Real Discord IDs are 17+ digits, so they can never collide,
and `wipe` can remove exactly the fake ones.
"""

from collections.abc import Mapping

from sqlalchemy import delete, func, select

from chongabot.content.models import RESOURCES, Resource
from chongabot.domain.errors import GameError
from chongabot.domain.models import EPITHETS, RULER_TITLES, Player
from chongabot.services.common import GameContext, load_player, lookup
from chongabot.services.military import AttackReport, MilitaryService
from chongabot.services.nation import clean_name
from chongabot.storage import players as player_repo
from chongabot.storage.schema import alliances, battles, players

FAKE_MAX_ID = 999


def is_fake(player_id: int) -> bool:
    return 0 < player_id <= FAKE_MAX_ID


def parse_army(text: str) -> dict[str, int]:
    """'spearman:100, archer:50' -> {'spearman': 100, 'archer': 50} (names checked later)."""
    army: dict[str, int] = {}
    for part in text.split(","):
        if not part.strip():
            continue
        name, sep, count = part.rpartition(":")
        if not sep or not count.strip().isdigit():
            raise GameError("Write armies like `spearman:100, archer:50`.")
        army[name.strip()] = army.get(name.strip(), 0) + int(count)
    return army


class DevService:
    def __init__(self, ctx: GameContext, military: MilitaryService) -> None:
        self.ctx = ctx
        self.military = military

    def _units(self, army: Mapping[str, int]) -> dict[str, int]:
        content = self.ctx.content
        units: dict[str, int] = {}
        for name, n in army.items():
            u = lookup(content.units, name, "unit")
            units[u.id] = units.get(u.id, 0) + n
        return units

    async def spawn(
        self, owner_id: int, raw_name: str, age: str | None, army: str | None
    ) -> Player:
        """A fake nation near the owner: same age, battle rating, buildings and army
        (unless given), so a fight against it is close."""
        content = self.ctx.content
        name = clean_name(raw_name)
        async with self.ctx.db.transaction() as conn:
            me = await player_repo.get(conn, owner_id)
            if await player_repo.name_taken(conn, name):
                raise GameError(f"**{name}** is taken.")
            age_id = (
                lookup({a.id: a for a in content.ages}, age, "age").id
                if age
                else (me.age if me else content.ages[0].id)
            )
            if army:
                units = self._units(parse_army(army))
            elif me and any(me.units.values()):
                units = dict(me.units)
            else:
                units = {k: v * 10 for k, v in content.settings.starting_units.items()}

            taken = set(
                (await conn.scalars(select(players.c.id).where(players.c.id <= FAKE_MAX_ID))).all()
            )
            fake_id = next((i for i in range(1, FAKE_MAX_ID + 1) if i not in taken), None)
            if fake_id is None:
                raise GameError("Too many fake nations. Use `/dev wipe`.")

            rng = self.ctx.rng
            await player_repo.create(
                conn,
                player_id=fake_id,
                name=name,
                username=f"{name} Bot",
                age=age_id,
                resources=dict.fromkeys(RESOURCES, 5_000),
                units=units,
                guild_id=None,
                now=self.ctx.clock(),
                ruler_title=rng.choice(list(RULER_TITLES)),
                epithet=rng.choice(EPITHETS),
            )
            if me:
                await player_repo.update_fields(conn, fake_id, battle_rating=me.battle_rating)
                await player_repo.add_buildings(conn, fake_id, me.buildings)
            return await load_player(conn, fake_id)

    async def give(self, player_id: int, resource: str, amount: int) -> Player:
        if resource.lower() == "all":
            amounts: dict[Resource, int] = dict.fromkeys(RESOURCES, amount)
        elif resource.lower() in RESOURCES:
            amounts = {resource.lower(): amount}  # type: ignore[dict-item]
        else:
            raise GameError(f"Resources are: {', '.join(RESOURCES)}, or `all`.")
        async with self.ctx.db.transaction() as conn:
            await load_player(conn, player_id)
            await player_repo.give(conn, player_id, amounts)
            return await load_player(conn, player_id)

    async def units(self, player_id: int, unit: str, count: int) -> tuple[str, Player]:
        """Add (or with a negative count, remove) units."""
        u = lookup(self.ctx.content.units, unit, "unit")
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, player_id)
            count = max(count, -player.units.get(u.id, 0))
            await player_repo.add_units(conn, player_id, {u.id: count})
            return u.name, await load_player(conn, player_id)

    async def hero(self, player_id: int, hero: str) -> tuple[str, Player]:
        """Grant a hero as if found while exploring (it isn't appointed)."""
        h = lookup(self.ctx.content.heroes, hero, "hero")
        async with self.ctx.db.transaction() as conn:
            await load_player(conn, player_id)
            await player_repo.add_unlock(conn, player_id, "hero", h.id, self.ctx.clock())
            return h.name, await load_player(conn, player_id)

    async def reset(self, player_id: int) -> None:
        """Clear claim, explore, attack and hero-swap cooldowns and the shield."""
        async with self.ctx.db.transaction() as conn:
            await load_player(conn, player_id)
            await player_repo.update_fields(
                conn,
                player_id,
                last_claim=self.ctx.clock().replace(year=self.ctx.clock().year - 1),
                last_explore=None,
                last_attack=None,
                shield_until=None,
                hero_appointed_at=None,
            )

    async def set_age(self, player_id: int, age: str) -> str:
        content = self.ctx.content
        a = lookup({x.id: x for x in content.ages}, age, "age")
        async with self.ctx.db.transaction() as conn:
            await load_player(conn, player_id)
            await player_repo.update_fields(conn, player_id, age=a.id)
        return a.name

    async def set_rating(self, player_id: int, rating: int) -> None:
        if rating < 0:
            raise GameError("Battle rating can't be negative.")
        async with self.ctx.db.transaction() as conn:
            await load_player(conn, player_id)
            await player_repo.update_fields(conn, player_id, battle_rating=rating)

    async def attack_me(self, owner_id: int, attacker_id: int) -> AttackReport:
        """Have a fake nation attack the owner, ignoring its cooldown and the owner's shield."""
        if not is_fake(attacker_id):
            raise GameError("Only fake nations can be made to attack.")
        async with self.ctx.db.transaction() as conn:
            await player_repo.update_fields(conn, attacker_id, last_attack=None)
            await player_repo.update_fields(conn, owner_id, shield_until=None)
        return await self.military.attack(attacker_id, owner_id)

    async def wipe(self) -> int:
        """Delete every fake nation, its battles, and any alliance left empty."""
        async with self.ctx.db.transaction() as conn:
            n = int(
                await conn.scalar(
                    select(func.count()).select_from(players).where(players.c.id <= FAKE_MAX_ID)
                )
                or 0
            )
            fake = select(players.c.id).where(players.c.id <= FAKE_MAX_ID)
            await conn.execute(
                delete(battles).where(
                    battles.c.attacker_id.in_(fake) | battles.c.defender_id.in_(fake)
                )
            )
            await conn.execute(delete(players).where(players.c.id <= FAKE_MAX_ID))
            members = select(players.c.alliance_id).where(players.c.alliance_id.is_not(None))
            await conn.execute(delete(alliances).where(alliances.c.id.not_in(members)))
            return n

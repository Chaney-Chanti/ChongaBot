"""Attacking other nations and exploring."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func

from chongabot.content import Content
from chongabot.content.models import BotNation
from chongabot.domain.errors import GameError
from chongabot.domain.models import Player, Target
from chongabot.rules import bosses, exploration, pvp
from chongabot.rules.combat import (
    BattleResult,
    Squad,
    army_from_units,
    defenses,
    player_army,
    resolve,
    strength,
)
from chongabot.rules.economy import Cost
from chongabot.rules.effects import modifiers
from chongabot.rules.exploration import Outcome
from chongabot.services.common import GameContext, load_player
from chongabot.storage import alliances as alliance_repo
from chongabot.storage import battles as battle_repo
from chongabot.storage import players as player_repo
from chongabot.storage.schema import players as players_table


@dataclass(frozen=True)
class AttackReport:
    attacker: Player  # state after the battle
    defender: Player
    result: BattleResult
    rating_change: int
    tribute: Cost  # what the attacker received (empty if they lost)
    battle_id: int


@dataclass(frozen=True)
class BotStatus:
    bot: BotNation
    ready_at: datetime | None  # None: can attack now
    ratio: float  # bot strength / your strength, for the difficulty label


@dataclass(frozen=True)
class BotAttackReport:
    attacker: Player  # state after the battle
    bot: BotNation
    result: BattleResult
    loot: Cost  # empty if the attacker lost
    battle_id: int


@dataclass(frozen=True)
class ExploreReport:
    path: str
    outcome: Outcome
    battle: BattleResult | None  # pirates only
    battle_id: int | None
    player: Player


# Where explorers can go: regions of the Land of Chonga (see lore.yaml).
PATHS: dict[str, str] = {
    "mountains": "The Chongalayas",
    "forest": "The Whispering Woods",
    "coast": "The Chonga Coast",
}


def bot_army(content: Content, bot: BotNation) -> list[Squad]:
    return army_from_units(content, "defender", bot.units) + defenses(
        content, "defender", bot.buildings
    )


class MilitaryService:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    async def targets(self, user_id: int) -> list[Target]:
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            return await player_repo.targets(
                conn, player, self.ctx.content.settings.battle_rating_range, self.ctx.clock()
            )

    async def attack(self, attacker_id: int, defender_id: int) -> AttackReport:
        content, now = self.ctx.content, self.ctx.clock()
        s = content.settings
        async with self.ctx.db.transaction() as conn:
            attacker = await load_player(conn, attacker_id)
            defender = await player_repo.get(conn, defender_id)
            if defender is None:
                raise GameError("That nation doesn't exist any more.")
            pvp.check_can_attack(attacker, defender, content, now)

            allies: dict[str, int] = {}
            if defender.alliance_id is not None:
                alliance = await alliance_repo.get(conn, defender.alliance_id)
                allies = alliance.units if alliance else {}

            a_mods, d_mods = modifiers(attacker, content), modifiers(defender, content)
            result = resolve(
                player_army(content, attacker, "attacker"),
                player_army(content, defender, "defender", allies),
                content,
                self.ctx.rng,
                a_mods,
                d_mods,
                names=(attacker.name, defender.name),
            )

            # losses
            await player_repo.add_units(
                conn, attacker.id, {u: -n for u, n in result.attacker_losses.items()}
            )
            await player_repo.add_units(
                conn, defender.id, {u: -n for u, n in result.defender_losses.items()}
            )
            if result.ally_losses and defender.alliance_id is not None:
                await alliance_repo.add_units(
                    conn, defender.alliance_id, {u: -n for u, n in result.ally_losses.items()}
                )
                before = bosses.army_value(content, allies)
                lost = bosses.army_value(content, result.ally_losses)
                await alliance_repo.scale_stakes(conn, defender.alliance_id, before, before - lost)

            # rating, record, tribute, shield
            attacker_won = result.winner == "attacker"
            winner, loser = (attacker, defender) if attacker_won else (defender, attacker)
            change = pvp.rating_change(winner.battle_rating, loser.battle_rating, content)
            br, wins, losses = (
                players_table.c.battle_rating,
                players_table.c.wins,
                players_table.c.losses,
            )
            await player_repo.update_fields(
                conn, winner.id, battle_rating=br + change, wins=wins + 1
            )
            await player_repo.update_fields(
                conn, loser.id, battle_rating=func.max(br - change, 0), losses=losses + 1
            )

            given: Cost = {}
            if attacker_won:
                taken, given = pvp.tribute(defender.resources, content, a_mods)
                await player_repo.take(conn, defender.id, taken)
                await player_repo.give(conn, attacker.id, given)
                await player_repo.update_fields(
                    conn, defender.id, shield_until=now + timedelta(hours=s.shield_hours)
                )
            # attacking drops your own shield
            await player_repo.update_fields(conn, attacker.id, last_attack=now, shield_until=None)

            battle_id = await battle_repo.record(
                conn,
                attacker_id=attacker.id,
                defender_id=defender.id,
                defender_kind="player",
                winner=result.winner,
                log=result.log,
                now=now,
            )
            return AttackReport(
                attacker=await load_player(conn, attacker.id),
                defender=await load_player(conn, defender.id),
                result=result,
                rating_change=change,
                tribute=given,
                battle_id=battle_id,
            )

    # --- bot nations -------------------------------------------------------------

    def find_bot(self, name: str) -> BotNation | None:
        key = " ".join(name.split()).casefold()
        return next(
            (b for b in self.ctx.content.bots.values() if b.name.casefold() == key or b.id == key),
            None,
        )

    async def bots(self, user_id: int) -> list[BotStatus]:
        """The bot nations of the player's age, weakest first, with when each is ready."""
        content, now = self.ctx.content, self.ctx.clock()
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            last = await battle_repo.last_bot_attacks(conn, user_id)
        mine = strength(player_army(content, player, "attacker"))
        out = []
        for bot in sorted(content.bots.values(), key=lambda b: b.tier):
            if bot.age != player.age:
                continue
            ready = pvp.bot_ready_at(last.get(bot.id), content)
            theirs = strength(bot_army(content, bot))
            ratio = theirs / mine if mine else float("inf")
            out.append(BotStatus(bot, ready if ready and ready > now else None, ratio))
        return out

    async def attack_bot(self, user_id: int, bot_id: str) -> BotAttackReport:
        content, now = self.ctx.content, self.ctx.clock()
        bot = content.bots.get(bot_id)
        if bot is None:
            raise GameError("That bot nation doesn't exist any more.")
        async with self.ctx.db.transaction() as conn:
            attacker = await load_player(conn, user_id)
            last = (await battle_repo.last_bot_attacks(conn, user_id)).get(bot.id)
            pvp.check_can_attack_bot(attacker, bot, content, now, last)

            result = resolve(
                player_army(content, attacker, "attacker"),
                bot_army(content, bot),
                content,
                self.ctx.rng,
                modifiers(attacker, content),
                names=(attacker.name, bot.name),
            )
            await player_repo.add_units(
                conn, user_id, {u: -n for u, n in result.attacker_losses.items()}
            )
            loot: Cost = {}
            if result.winner == "attacker":
                mods = modifiers(attacker, content)
                loot = {r: int(v * mods.tribute) for r, v in bot.loot.items()}
                await player_repo.give(conn, user_id, loot)
            battle_id = await battle_repo.record(
                conn,
                attacker_id=user_id,
                defender_id=None,
                defender_kind="bot",
                defender_bot=bot.id,
                winner=result.winner,
                log=result.log,
                now=now,
            )
            return BotAttackReport(await load_player(conn, user_id), bot, result, loot, battle_id)

    async def check_explore(self, user_id: int) -> Player:
        """Fail early (before showing the path buttons) if explorers are still out."""
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
        exploration.check_ready(player, self.ctx.content, self.ctx.clock())
        return player

    async def explore(self, user_id: int, path: str) -> ExploreReport:
        content, now = self.ctx.content, self.ctx.clock()
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            exploration.check_ready(player, content, now)
            outcome = exploration.roll(player, content, self.ctx.rng)
            battle: BattleResult | None = None
            battle_id: int | None = None

            match outcome.kind:
                case "resources":
                    await player_repo.give(conn, user_id, outcome.resources)
                case "units":
                    await player_repo.add_units(conn, user_id, outcome.units)
                case "building":
                    assert outcome.building
                    await player_repo.add_buildings(conn, user_id, {outcome.building: 1})
                case "hero":
                    assert outcome.hero
                    await player_repo.add_unlock(conn, user_id, "hero", outcome.hero, now)
                    if player.hero is None:  # an empty post is filled straight away
                        await player_repo.update_fields(conn, user_id, hero=outcome.hero)
                case "wonder":
                    assert outcome.wonder
                    await player_repo.add_unlock(conn, user_id, "wonder", outcome.wonder, now)
                case "pirates":
                    battle = resolve(
                        player_army(content, player, "attacker"),
                        army_from_units(content, "defender", outcome.pirate_units),
                        content,
                        self.ctx.rng,
                        modifiers(player, content),
                        names=(player.name, "Pirates"),
                    )
                    await player_repo.add_units(
                        conn, user_id, {u: -n for u, n in battle.attacker_losses.items()}
                    )
                    if battle.winner == "attacker":
                        await player_repo.give(conn, user_id, outcome.resources)
                    battle_id = await battle_repo.record(
                        conn,
                        attacker_id=user_id,
                        defender_id=None,
                        defender_kind="pirate",
                        winner=battle.winner,
                        log=battle.log,
                        now=now,
                    )

            await player_repo.update_fields(conn, user_id, last_explore=now)
            return ExploreReport(path, outcome, battle, battle_id, await load_player(conn, user_id))

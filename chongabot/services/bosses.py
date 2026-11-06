"""Alliance bosses: an officer sends the whole alliance army against a boss."""

from dataclasses import dataclass
from datetime import datetime

from chongabot.content.models import Boss
from chongabot.domain.errors import GameError
from chongabot.domain.models import Alliance, Player
from chongabot.rules import bosses
from chongabot.rules.combat import BattleResult, army_from_units, resolve, strength
from chongabot.rules.economy import Cost
from chongabot.services.common import GameContext, load_player
from chongabot.storage import alliances as alliance_repo
from chongabot.storage import bosses as boss_repo
from chongabot.storage import players as player_repo


@dataclass(frozen=True)
class BossStatus:
    boss: Boss
    ready_at: datetime | None  # None: can fight now
    ratio: float  # boss strength / alliance army strength (inf with no army)


@dataclass(frozen=True)
class Payout:
    player_id: int
    name: str
    share: float  # 0..1 of the pot
    loot: Cost


@dataclass(frozen=True)
class BossReport:
    alliance: Alliance  # state after the fight
    boss: Boss
    result: BattleResult
    payouts: list[Payout]  # biggest first; empty if the alliance lost
    fight_id: int


def _require_alliance_id(player: Player) -> int:
    if player.alliance_id is None:
        raise GameError("You're not in an alliance. Join or found one with `/alliance`.")
    return player.alliance_id


class BossService:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    def find(self, name: str) -> Boss | None:
        key = name.strip().casefold()
        return next(
            (b for b in self.ctx.content.bosses.values() if key in (b.id, b.name.casefold())),
            None,
        )

    async def overview(self, user_id: int) -> tuple[Player, Alliance | None, list[BossStatus]]:
        """Every boss. Status and difficulty are for the player's alliance, if they have one."""
        content, now = self.ctx.content, self.ctx.clock()
        alliance: Alliance | None = None
        last: dict[str, datetime] = {}
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            if player.alliance_id is not None:
                alliance = await alliance_repo.get(conn, player.alliance_id)
                last = await boss_repo.last_fights(conn, player.alliance_id)
        ours = strength(army_from_units(content, "attacker", alliance.units if alliance else {}))
        out = []
        order = {a.id: i for i, a in enumerate(content.ages)}
        for boss in sorted(content.bosses.values(), key=lambda b: (order[b.age], b.strength)):
            ready = bosses.ready_at(last.get(boss.id), content)
            theirs = strength(army_from_units(content, "defender", boss.units))
            ratio = theirs / ours if ours else float("inf")
            out.append(BossStatus(boss, ready if ready and ready > now else None, ratio))
        return player, alliance, out

    async def challenge(self, user_id: int, boss_id: str) -> BossReport:
        content, now = self.ctx.content, self.ctx.clock()
        boss = content.bosses.get(boss_id)
        if boss is None:
            raise GameError("That boss doesn't exist any more.")
        async with self.ctx.db.transaction() as conn:
            player = await load_player(conn, user_id)
            alliance = await alliance_repo.get(conn, _require_alliance_id(player))
            assert alliance is not None
            last = (await boss_repo.last_fights(conn, alliance.id)).get(boss.id)
            bosses.check_can_challenge(
                player.alliance_role, alliance.units, boss, content, now, last
            )

            result = resolve(
                army_from_units(content, "attacker", alliance.units),
                army_from_units(content, "defender", boss.units),
                content,
                self.ctx.rng,
                names=(alliance.name, boss.name),
            )

            # Shares come from stakes as they stood going into the fight.
            stakes = {m.id: m.stake for m in alliance.members}
            before = bosses.army_value(content, alliance.units)
            lost = bosses.army_value(content, result.attacker_losses)
            await alliance_repo.add_units(
                conn, alliance.id, {u: -n for u, n in result.attacker_losses.items()}
            )
            await alliance_repo.scale_stakes(conn, alliance.id, before, before - lost)

            won = result.winner == "attacker"
            split = bosses.split_loot(boss.loot, stakes) if won else {}
            for pid, cut in split.items():
                await player_repo.give(conn, pid, cut)

            fight_id = await boss_repo.record(
                conn,
                alliance_id=alliance.id,
                boss=boss.id,
                started_by=player.id,
                winner=result.winner,
                payouts=split,
                log=result.log,
                now=now,
            )
            after = await alliance_repo.get(conn, alliance.id)
            assert after is not None

        names = {m.id: m.name for m in alliance.members}
        total = sum(s for p, s in stakes.items() if p in split and s > 0)
        payouts = [
            Payout(
                pid,
                names.get(pid, "?"),
                (stakes[pid] / total) if total else 1 / len(split),
                cut,
            )
            for pid, cut in split.items()
        ]
        payouts.sort(key=lambda p: -p.share)
        return BossReport(after, boss, result, payouts, fight_id)

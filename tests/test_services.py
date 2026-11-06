"""Services against a real, migrated SQLite file."""

import asyncio
import random
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from chongabot.content import Content
from chongabot.domain.errors import GameError, NoNation, NotEnough, OnCooldown
from chongabot.services import GameContext, Services
from chongabot.storage import alliances as alliance_repo
from chongabot.storage import players as player_repo
from chongabot.storage.db import Database
from tests.conftest import NOW


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kw: float) -> None:
        self.now += timedelta(**kw)


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
async def svc(tmp_path: Path, content: Content, clock: Clock) -> AsyncIterator[Services]:
    db = Database(tmp_path / "test.db")
    await db.migrate()
    yield Services(GameContext(db, content, clock, random.Random(1)))
    await db.close()


async def give(svc: Services, user_id: int, **amounts: int) -> None:
    async with svc.ctx.db.transaction() as conn:
        await player_repo.give(conn, user_id, amounts)  # type: ignore[arg-type]


async def set_units(svc: Services, user_id: int, **units: int) -> None:
    async with svc.ctx.db.transaction() as conn:
        await player_repo.add_units(conn, user_id, units)


# --- nations ---------------------------------------------------------------------


async def test_create_and_load(svc: Services, content: Content) -> None:
    p = await svc.nation.create(1, "chaney", "  Chonga   Land ", 99)
    assert p.name == "Chonga Land"
    assert p.resources == {**dict.fromkeys(p.resources, 0), **content.settings.starting_resources}
    assert p.units == content.settings.starting_units
    assert p.age == "ancient"
    assert (await svc.nation.find("chonga land")).id == 1


async def test_names_are_unique_ignoring_case(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    with pytest.raises(GameError, match="taken"):
        await svc.nation.create(2, "b", "ROME", None)
    with pytest.raises(GameError, match="already have"):
        await svc.nation.create(1, "a", "Carthage", None)
    with pytest.raises(GameError):
        await svc.nation.create(3, "c", "<@123>", None)


async def test_no_nation(svc: Services) -> None:
    with pytest.raises(NoNation):
        await svc.economy.claim(42)


# --- economy -----------------------------------------------------------------------


async def test_claim_then_cooldown(svc: Services, clock: Clock) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    clock.advance(hours=3)
    claimed = await svc.economy.claim(1)
    assert claimed.result.gained["food"] == 150
    assert claimed.player.resources["food"] == 650
    with pytest.raises(OnCooldown):
        await svc.economy.claim(1)


async def test_build_spends_and_adds(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    bought = await svc.economy.build(1, "Granary", 2)
    assert bought.count == 2 and bought.player.buildings == {"granary": 2}
    assert bought.player.resources["timber"] == 500 - bought.cost["timber"]


async def test_build_max_and_not_enough(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    bought = await svc.economy.build(1, "granary", "max")
    assert bought.count >= 1
    with pytest.raises(GameError, match="can't afford"):
        await svc.economy.build(1, "granary", "max")
    with pytest.raises(NotEnough):
        await svc.economy.build(1, "granary", 5)


async def test_concurrent_buys_never_overspend(svc: Services) -> None:
    """Ten simultaneous purchases that could each afford one: exactly the affordable ones win."""
    await svc.nation.create(1, "a", "Rome", None)
    results = await asyncio.gather(
        *(svc.economy.train(1, "slinger", 5) for _ in range(10)), return_exceptions=True
    )
    ok = [r for r in results if not isinstance(r, BaseException)]
    failed = [r for r in results if isinstance(r, BaseException)]
    assert all(isinstance(f, NotEnough) for f in failed)
    p = await svc.nation.get(1)
    assert p.resources["food"] >= 0
    assert p.units["slinger"] == 10 + 5 * len(ok)
    assert 500 - p.resources["food"] == 5 * 35 * len(ok)


async def test_concurrent_claims_pay_once(svc: Services, clock: Clock) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    clock.advance(hours=5)
    results = await asyncio.gather(
        *(svc.economy.claim(1) for _ in range(5)), return_exceptions=True
    )
    assert sum(not isinstance(r, BaseException) for r in results) == 1
    assert (await svc.nation.get(1)).resources["food"] == 500 + 250


async def test_database_rejects_negative_balances(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    with pytest.raises(IntegrityError):
        async with svc.ctx.db.transaction() as conn:
            await player_repo.update_fields(conn, 1, food=-1)
    with pytest.raises(NotEnough):
        async with svc.ctx.db.transaction() as conn:
            await player_repo.spend(conn, 1, {"food": 10_000})


async def test_research_and_advance(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    await give(svc, 1, knowledge=10_000, wealth=10_000)
    r = await svc.economy.research(1, "pastures")
    assert "pastures" in r.player.research
    with pytest.raises(GameError, match="already"):
        await svc.economy.research(1, "pastures")
    await set_units(svc, 1, clubman=100, spearman=40)
    age, p, retrained = await svc.economy.advance(1)
    assert age.id == "medieval" and p.age == "medieval"
    assert {r.into: r.count for r in retrained}["knight"] == 33
    assert p.units.get("clubman", 0) == 0 and p.units.get("spearman", 0) == 0
    assert p.units["knight"] == 33


# --- military ------------------------------------------------------------------------


async def test_attack_moves_rating_tribute_and_shields(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    await svc.nation.create(2, "b", "Gaul", None)
    await set_units(svc, 1, spearman=200)
    report = await svc.military.attack(1, 2)
    assert report.result.winner == "attacker"
    assert report.attacker.battle_rating == report.rating_change
    assert report.defender.battle_rating == 0  # floored
    assert report.attacker.wins == 1 and report.defender.losses == 1
    assert report.tribute["food"] == int(50 * 1.5)
    assert report.defender.resources["food"] == 450
    assert report.defender.shield_until is not None
    assert report.battle_id > 0
    with pytest.raises(OnCooldown):
        await svc.military.attack(1, 2)


async def test_targets_skip_shielded_and_allies(svc: Services, clock: Clock) -> None:
    for i, name in enumerate(["Rome", "Gaul", "Iberia"], start=1):
        await svc.nation.create(i, str(i), name, None)
    await set_units(svc, 1, spearman=200)
    await svc.military.attack(1, 2)  # Gaul is now shielded
    assert {t.name for t in await svc.military.targets(1)} == {"Iberia"}
    alliance = await svc.alliance.create(1, "Pax", None)
    await svc.alliance.request_join(3, alliance.id)
    await svc.alliance.answer_request(1, 3, accept=True)
    assert await svc.military.targets(1) == []


async def test_alliance_army_defends(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    await svc.nation.create(2, "b", "Gaul", None)
    await set_units(svc, 1, spearman=100)
    await set_units(svc, 2, spearman=300)
    alliance = await svc.alliance.create(2, "Gallia", None)
    name, n = await svc.alliance.contribute(2, "spearman", "max")
    assert (name, n) == ("Spearman", 300)
    report = await svc.military.attack(1, 2)
    assert report.result.winner == "defender"
    left = (await svc.alliance.get(alliance.id)).units["spearman"]
    assert left == 300 - report.result.ally_losses["spearman"]


async def test_explore_applies_outcome_and_cooldown(svc: Services, clock: Clock) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    seen = set()
    for _ in range(25):
        report = await svc.military.explore(1, "forest")
        seen.add(report.outcome.kind)
        with pytest.raises(OnCooldown):
            await svc.military.explore(1, "coast")
        clock.advance(hours=6)
    assert len(seen) >= 4


# --- alliances ------------------------------------------------------------------------


async def test_alliance_roles(svc: Services) -> None:
    for i, name in enumerate(["Owner", "Officer", "Member", "Outsider"], start=1):
        await svc.nation.create(i, str(i), name, None)
    a = await svc.alliance.create(1, "League", None)
    for pid in (2, 3):
        await svc.alliance.request_join(pid, a.id)
        await svc.alliance.answer_request(1, pid, accept=True)
    await svc.alliance.set_role(1, 2, "officer")

    with pytest.raises(GameError, match="Only"):
        await svc.alliance.kick(3, 2)
    with pytest.raises(GameError, match="below you"):
        await svc.alliance.kick(2, 1)
    with pytest.raises(GameError, match="owner"):
        await svc.alliance.set_role(2, 3, "officer")

    await svc.alliance.request_join(4, a.id)
    await svc.alliance.answer_request(2, 4, accept=False)  # officers can answer
    assert (await svc.alliance.get(a.id)).requests == []

    await svc.alliance.kick(2, 3)
    with pytest.raises(GameError, match="Transfer"):
        await svc.alliance.leave(1)
    await svc.alliance.set_role(1, 2, "owner")
    league = await svc.alliance.get(a.id)
    assert league.owner and league.owner.id == 2
    assert league.member(1) and league.member(1).role == "officer"  # type: ignore[union-attr]
    await svc.alliance.leave(1)
    assert await svc.alliance.leave(2) == "League"  # sole owner leaving disbands
    async with svc.ctx.db.transaction() as conn:
        assert await alliance_repo.get(conn, a.id) is None


async def test_disband_clears_roles(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    await svc.nation.create(2, "b", "Gaul", None)
    a = await svc.alliance.create(1, "Pax", None)
    await svc.alliance.request_join(2, a.id)
    await svc.alliance.answer_request(1, 2, accept=True)
    await svc.alliance.disband(1)
    for pid in (1, 2):
        p = await svc.nation.get(pid)
        assert p.alliance_id is None and p.alliance_role is None


async def test_leaderboard_and_search(svc: Services) -> None:
    for i, name in enumerate(["Rome", "Romania", "Gaul"], start=1):
        await svc.nation.create(i, str(i), name, None)
    rows, total = await svc.nation.leaderboard()
    assert total == 3 and len(rows) == 3
    assert [t.name for t in await svc.nation.search("rom")] == ["Romania", "Rome"] or [
        t.name for t in await svc.nation.search("rom")
    ] == ["Rome", "Romania"]
    assert [t.name for t in await svc.nation.search("au")] == ["Gaul"]


async def test_create_with_title_and_epithet(svc: Services) -> None:
    assert await svc.nation.check_new(1, " Chonga  Land ") == "Chonga Land"
    p = await svc.nation.create(1, "Chonga", "Rome", None, ruler_title="king", epithet="the Great")
    assert p.ruler == "King Chonga the Great"
    with pytest.raises(GameError):
        await svc.nation.create(2, "b", "Gaul", None, ruler_title="king", epithet="the Smelly")
    with pytest.raises(GameError, match="already have"):
        await svc.nation.check_new(1, "Carthage")


async def test_ruler_mention(svc: Services) -> None:
    p = await svc.nation.create(7, "Chonga", "Rome", None, ruler_title="queen", epithet="the Bold")
    assert p.ruler_mention == "Queen <@7> the Bold"


# --- dev tools -------------------------------------------------------------------------


async def test_dev_spawn_mirrors_me_and_can_be_fought(svc: Services) -> None:
    await svc.nation.create(1000, "me", "Rome", None)
    await svc.dev.units(1000, "spearman", 100)
    await svc.dev.set_rating(1000, 300)
    npc = await svc.dev.spawn(1000, "Carthage", None, None)
    assert npc.id == 1 and npc.battle_rating == 300
    assert npc.units == (await svc.nation.get(1000)).units

    custom = await svc.dev.spawn(1000, "Gaul", "medieval", "knight:50, Crossbowman:20")
    assert custom.id == 2 and custom.age == "medieval"
    assert custom.units == {"knight": 50, "crossbowman": 20}

    report = await svc.military.attack(1000, npc.id)
    assert report.battle_id
    await svc.dev.reset(1000)
    await svc.military.attack(1000, custom.id)  # cooldown cleared

    hit_back = await svc.dev.attack_me(1000, custom.id)
    assert hit_back.defender.id == 1000

    assert await svc.dev.wipe() == 2
    assert (await svc.nation.leaderboard())[1] == 1


async def test_dev_give_units_age(svc: Services) -> None:
    await svc.nation.create(1000, "me", "Rome", None)
    p = await svc.dev.give(1000, "all", 1000)
    assert p.resources["oil"] == 1000
    with pytest.raises(GameError):
        await svc.dev.give(1000, "gold", 5)
    _, p = await svc.dev.units(1000, "slinger", -500)
    assert "slinger" not in p.units
    _, p = await svc.dev.hero(1000, "chief bonk")
    assert "chief_bonk" in p.heroes and p.hero is None
    assert await svc.dev.set_age(1000, "Space") == "Space"
    with pytest.raises(GameError, match="fake"):
        await svc.dev.attack_me(1000, 1000)


# --- bot nations and leaderboards -------------------------------------------------------


async def test_bots_listed_for_my_age_with_difficulty(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    bots = await svc.military.bots(1)
    assert [s.bot.tier for s in bots] == list(range(1, 11))
    assert all(s.bot.age == "ancient" and s.ready_at is None for s in bots)
    assert bots[0].ratio < bots[-1].ratio


async def test_attack_bot_gives_loot_not_rating(svc: Services, clock: Clock) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    await set_units(svc, 1, spearman=300, archer=300)
    before = await svc.nation.get(1)
    report = await svc.military.attack_bot(1, "ancient_1")
    assert report.result.winner == "attacker"
    after = report.attacker
    assert report.loot and all(
        after.resources[r] == before.resources[r] + v for r, v in report.loot.items()
    )
    assert after.battle_rating == 0 and after.wins == 0
    assert after.last_attack is None  # bots don't use the PvP cooldown

    with pytest.raises(OnCooldown, match="recovering"):
        await svc.military.attack_bot(1, "ancient_1")
    await svc.military.attack_bot(1, "ancient_2")  # other bots are still open
    statuses = {s.bot.id: s for s in await svc.military.bots(1)}
    assert statuses["ancient_1"].ready_at is not None
    clock.advance(hours=12)
    await svc.military.attack_bot(1, "ancient_1")


async def test_bot_rules(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    with pytest.raises(GameError, match="own age"):
        await svc.military.attack_bot(1, "medieval_1")
    assert svc.military.find_bot("  mudhollow ") is not None
    with pytest.raises(GameError, match="bot nation"):
        await svc.nation.create(2, "b", "Mudhollow", None)
    await set_units(svc, 1, slinger=-10)
    with pytest.raises(GameError, match="no army"):
        await svc.military.attack_bot(1, "ancient_1")


async def test_alliance_leaderboard_sums_member_ratings(svc: Services) -> None:
    for i, (name, br) in enumerate([("A", 100), ("B", 150), ("C", 400), ("D", 10)], start=1):
        await svc.nation.create(i, name.lower(), f"Nation {name}", None)
        await svc.dev.set_rating(i, br)
    big = await svc.alliance.create(1, "Big", None)
    await svc.alliance.request_join(2, big.id)
    await svc.alliance.answer_request(1, 2, accept=True)
    await svc.alliance.create(3, "Solo", None)

    rows, total = await svc.alliance.leaderboard()
    assert total == 2
    assert [(a.name, a.battle_rating, a.members) for a in rows] == [
        ("Solo", 400, 1),
        ("Big", 250, 2),
    ]
    nations, _ = await svc.nation.leaderboard()
    assert [(t.name, t.alliance) for t in nations] == [
        ("Nation C", "Solo"),
        ("Nation B", "Big"),
        ("Nation A", "Big"),
        ("Nation D", None),
    ]


# --- heroes ------------------------------------------------------------------------------


async def test_appoint_and_swap_second_in_command(svc: Services, clock: Clock) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    with pytest.raises(GameError, match="haven't found"):
        await svc.heroes.appoint(1, "chief_bonk")
    await svc.dev.hero(1, "chief_bonk")
    await svc.dev.hero(1, "grubnar")

    p = await svc.heroes.appoint(1, "Chief Bonk")
    assert p.hero == "chief_bonk"
    with pytest.raises(GameError, match="already"):
        await svc.heroes.appoint(1, "chief_bonk")
    with pytest.raises(OnCooldown):
        await svc.heroes.appoint(1, "grubnar")
    clock.advance(hours=4)
    assert (await svc.heroes.appoint(1, "grubnar")).hero == "grubnar"

    p = await svc.heroes.dismiss(1)
    assert p.hero is None
    with pytest.raises(OnCooldown):  # dismissing doesn't reset the wait
        await svc.heroes.appoint(1, "chief_bonk")


async def test_first_hero_found_fills_an_empty_post(svc: Services, clock: Clock) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    heroes_seen = 0
    for _ in range(60):
        report = await svc.military.explore(1, "forest")
        clock.advance(hours=6)
        if report.outcome.kind == "hero":
            heroes_seen += 1
            if heroes_seen == 1:
                assert report.player.hero == report.outcome.hero
            else:
                assert report.player.hero != report.outcome.hero  # post already filled
    assert heroes_seen >= 2


# --- alliance bosses ----------------------------------------------------------------


async def _boss_alliance(svc: Services) -> int:
    """Owner 1 (big contributor), officer 2 (small contributor), member 3 (none)."""
    for i, name in enumerate(["Rome", "Gaul", "Iberia"], start=1):
        await svc.nation.create(i, str(i), name, None)
    a = await svc.alliance.create(1, "League", None)
    for pid in (2, 3):
        await svc.alliance.request_join(pid, a.id)
        await svc.alliance.answer_request(1, pid, accept=True)
    await svc.alliance.set_role(1, 2, "officer")
    await set_units(svc, 1, knight=60)  # 200 each: 12,000
    await set_units(svc, 2, spearman=10)  # 65 each: 650
    await svc.alliance.contribute(1, "knight", "max")
    await svc.alliance.contribute(2, "spearman", "max")
    return a.id


async def test_contributing_builds_a_stake(svc: Services) -> None:
    alliance_id = await _boss_alliance(svc)
    stakes = {m.id: m.stake for m in (await svc.alliance.get(alliance_id)).members}
    assert stakes == {1: 12_000, 2: 650, 3: 0}


async def test_boss_loot_is_split_by_stake(svc: Services, content: Content) -> None:
    await _boss_alliance(svc)
    boss = content.bosses["the_mud_golem"]
    before = {i: (await svc.nation.get(i)).resources for i in (1, 2, 3)}

    report = await svc.bosses.challenge(2, boss.id)  # officers can lead

    assert report.result.winner == "attacker"
    got = {
        i: sum((await svc.nation.get(i)).resources.values()) - sum(before[i].values())
        for i in (1, 2, 3)
    }
    pot = sum(boss.loot.values())
    assert sum(got.values()) == pot
    assert got[3] == 0  # contributed nothing, gets nothing
    assert got[2] < pot * 0.06  # 650 of 12,650: about 5%
    assert [p.player_id for p in report.payouts] == [1, 2]
    # the army took losses, and stakes shrank with it
    left = report.alliance
    assert sum(m.stake for m in left.members) < 12_650


async def test_boss_rules(svc: Services, clock: Clock, content: Content) -> None:
    await _boss_alliance(svc)
    with pytest.raises(GameError, match="Only officers"):
        await svc.bosses.challenge(3, "the_mud_golem")
    await svc.bosses.challenge(1, "the_mud_golem")
    with pytest.raises(OnCooldown):
        await svc.bosses.challenge(1, "the_mud_golem")
    _, _, statuses = await svc.bosses.overview(3)
    assert next(s for s in statuses if s.boss.id == "the_mud_golem").ready_at is not None
    clock.advance(hours=content.settings.boss_cooldown_hours)
    await svc.bosses.challenge(1, "the_mud_golem")


async def test_losing_to_a_boss_pays_nothing(svc: Services) -> None:
    alliance_id = await _boss_alliance(svc)
    report = await svc.bosses.challenge(1, "the_ghost_of_chonga_the_first")
    assert report.result.winner == "defender"
    assert report.payouts == []
    assert sum((await svc.alliance.get(alliance_id)).units.values()) < 70


async def test_leaving_forfeits_stake(svc: Services) -> None:
    alliance_id = await _boss_alliance(svc)
    await svc.alliance.leave(2)
    a = await svc.alliance.get(alliance_id)
    assert a.member(2) is None
    assert (await svc.alliance.mine(2))[0].alliance_id is None
    async with svc.ctx.db.transaction() as conn:
        await alliance_repo.set_membership(conn, 2, alliance_id, "member")  # rejoin
    assert (await svc.alliance.get(alliance_id)).member(2).stake == 0  # type: ignore[union-attr]
    # role changes inside the alliance keep the stake
    await svc.alliance.set_role(1, 3, "officer")
    assert (await svc.alliance.get(alliance_id)).member(1).stake == 12_000  # type: ignore[union-attr]


async def test_defending_shrinks_stakes(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    await svc.nation.create(2, "b", "Gaul", None)
    await set_units(svc, 1, spearman=100)
    await set_units(svc, 2, spearman=300)
    alliance = await svc.alliance.create(2, "Gallia", None)
    await svc.alliance.contribute(2, "spearman", "max")
    report = await svc.military.attack(1, 2)
    lost = report.result.ally_losses["spearman"]
    assert lost > 0
    stake = (await svc.alliance.get(alliance.id)).member(2).stake  # type: ignore[union-attr]
    assert stake == 65 * (300 - lost)

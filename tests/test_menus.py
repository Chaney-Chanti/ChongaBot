"""Build every menu and embed in each state without Discord, checking Discord's limits."""

import random
import time
from collections.abc import AsyncIterator
from pathlib import Path

import discord
import pytest

from chongabot.content import Content
from chongabot.menus.alliance import AllianceMenu
from chongabot.menus.buy import BuyMenu
from chongabot.services import GameContext, Services
from chongabot.storage import players as player_repo
from chongabot.storage.db import Database
from chongabot.views import embeds
from tests.test_services import Clock


def check_embed(e: discord.Embed) -> None:
    assert len(e) <= 6000
    assert len(e.description or "") <= 4096
    assert len(e.fields) <= 25
    for f in e.fields:
        assert f.value and len(f.value) <= 1024, f.name
        assert len(f.name or "") <= 256


def check_view(v: discord.ui.View) -> None:
    rows: dict[int, int] = {}
    for child in v.children:
        assert child.row is not None
        width = 5 if isinstance(child, discord.ui.Select) else 1
        rows[child.row] = rows.get(child.row, 0) + width
        if isinstance(child, discord.ui.Select):
            assert 1 <= len(child.options) <= 25
            for o in child.options:
                assert len(o.label) <= 100 and len(o.description or "") <= 100
    assert all(n <= 5 for n in rows.values()) and all(0 <= r < 5 for r in rows)


@pytest.fixture
async def svc(tmp_path: Path, content: Content) -> AsyncIterator[Services]:
    db = Database(tmp_path / "menus.db")
    await db.migrate()
    yield Services(GameContext(db, content, Clock(), random.Random(3)))
    await db.close()


async def rich(svc: Services, user_id: int, name: str, age: str = "ancient") -> None:
    await svc.nation.create(user_id, name.lower(), name, None)
    async with svc.ctx.db.transaction() as conn:
        await player_repo.give(
            conn,
            user_id,
            dict.fromkeys(("food", "timber", "metal", "wealth", "knowledge", "oil"), 10_000_000),
        )  # type: ignore[arg-type]
        await player_repo.update_fields(conn, user_id, age=age)


@pytest.mark.parametrize("age", ["ancient", "medieval", "enlightenment", "modern", "space"])
@pytest.mark.parametrize("kind", ["building", "unit", "research"])
async def test_buy_menu_every_age(svc: Services, age: str, kind: str) -> None:
    await rich(svc, 1, "Rome", age)
    player = await svc.nation.get(1)
    menu = BuyMenu(svc, player, kind)  # type: ignore[arg-type]
    check_view(menu)
    check_embed(menu.embed())
    confirm = next(c for c in menu.children if getattr(c, "label", None) == "Confirm")
    assert not confirm.disabled  # type: ignore[attr-defined]


async def test_buy_menu_disables_confirm_when_short(svc: Services) -> None:
    await svc.nation.create(1, "a", "Rome", None)
    menu = BuyMenu(svc, await svc.nation.get(1), "unit", "spearman")
    menu.qty = 10_000
    menu.render()
    confirm = next(c for c in menu.children if getattr(c, "label", None) == "Confirm")
    assert confirm.disabled  # type: ignore[attr-defined]
    assert "short" in (menu.embed().description or "")


async def test_alliance_menu_for_every_role(svc: Services) -> None:
    for i, name in enumerate(["Owner", "Officer", "Member", "Applicant", "Loner"], start=1):
        await rich(svc, i, name)
    a = await svc.alliance.create(1, "League", None)
    for pid in (2, 3):
        await svc.alliance.request_join(pid, a.id)
        await svc.alliance.answer_request(1, pid, accept=True)
    await svc.alliance.set_role(1, 2, "officer")
    await svc.alliance.request_join(4, a.id)

    for uid in range(1, 6):
        menu = await AllianceMenu.open(svc, uid, None)
        check_view(menu)
        check_embed(menu.embed())
        labels = {getattr(c, "label", None) for c in menu.children}
        if uid == 1:
            assert {"Promote", "Demote", "Make owner", "Kick", "Accept", "Disband"} <= labels
        elif uid == 2:
            assert {"Kick", "Accept", "Leave"} <= labels and "Promote" not in labels
        elif uid == 3:
            assert "Kick" not in labels and "Leave" in labels
        else:
            assert "Request to join" in labels


async def test_embeds_build(svc: Services, content: Content) -> None:
    await rich(svc, 1, "Rome")
    await rich(svc, 2, "Gaul")
    await svc.economy.build(1, "granary", 5)
    await svc.economy.train(1, "spearman", 300)
    profile = await svc.nation.profile(1)
    check_embed(embeds.stats(profile, content, time.time()))
    report = await svc.military.attack(1, 2)
    check_embed(embeds.attack(report, content))
    player = await svc.nation.get(1)
    for e in (
        embeds.ages(player, content),
        embeds.lore(content),
        embeds.wonders(player, content),
    ):
        check_embed(e)
    rows, total = await svc.nation.leaderboard()
    check_embed(embeds.leaderboard(rows, 0, total, 10))
    for _ in range(15):
        rep = await svc.military.explore(1, "coast")
        check_embed(embeds.explore(rep, content))
        svc.ctx.clock.advance(hours=6)  # type: ignore[attr-defined]


async def test_founding_view(svc: Services) -> None:
    from types import SimpleNamespace

    from chongabot.menus.founding import FoundingView

    user = SimpleNamespace(id=1, name="chonga", display_name="Chonga")
    view = FoundingView(svc, user, "Rome", None)  # type: ignore[arg-type]
    check_view(view)
    check_embed(view.embed())
    found = next(c for c in view.children if str(getattr(c, "label", "")).startswith("Found"))
    assert found.disabled  # type: ignore[attr-defined]
    view.title, view.epithet = "queen", "the Wise"
    view.render()
    assert "Queen <@1> the Wise" in (view.embed().description or "")


async def test_targets_embed_and_bots(svc: Services, content: Content) -> None:
    await rich(svc, 1, "Rome")
    await rich(svc, 2, "Gaul")
    player = await svc.nation.get(1)
    bots = await svc.military.bots(1)
    targets = await svc.military.targets(1)
    check_embed(embeds.targets(targets, player, bots, content))
    rows, total = await svc.alliance.leaderboard()
    check_embed(embeds.alliance_leaderboard(rows, 0, total, 10))
    await svc.dev.units(1, "spearman", 400)
    rep = await svc.military.attack_bot(1, "ancient_3")
    check_embed(embeds.bot_attack(rep, content))


async def test_hero_menu_and_stats_second_in_command(svc: Services, content: Content) -> None:
    from chongabot.menus.heroes import HeroMenu

    await rich(svc, 1, "Rome")
    menu = HeroMenu(svc, await svc.nation.get(1))
    check_view(menu)
    check_embed(menu.embed())
    assert "vacant" in menu.embed().fields[0].name  # type: ignore[operator]
    for h in content.heroes:
        await svc.dev.hero(1, h)
    await svc.heroes.appoint(1, "gerald")
    menu = HeroMenu(svc, await svc.nation.get(1))
    check_view(menu)
    check_embed(menu.embed())
    stats = embeds.stats(await svc.nation.profile(1), content, time.time())
    check_embed(stats)
    second = next(f for f in stats.fields if f.name == "Second in Command")
    assert "Gerald" in (second.value or "")


class _Response:
    def __init__(self) -> None:
        self.edits: list[discord.Embed] = []

    async def edit_message(self, *, embed: discord.Embed, view: discord.ui.View) -> None:
        self.edits.append(embed)


class _Followup:
    def __init__(self) -> None:
        self.sent: list[discord.Embed] = []

    async def send(self, *, embed: discord.Embed) -> None:
        self.sent.append(embed)


class _Interaction:
    def __init__(self) -> None:
        self.response, self.followup = _Response(), _Followup()


async def test_boss_menu(svc: Services, content: Content) -> None:
    from chongabot.menus.bosses import BossMenu

    await rich(svc, 1, "Rome")
    await rich(svc, 2, "Gaul")
    a = await svc.alliance.create(1, "League", None)
    await svc.alliance.request_join(2, a.id)
    await svc.alliance.answer_request(1, 2, accept=True)
    async with svc.ctx.db.transaction() as conn:
        await player_repo.add_units(conn, 1, {"knight": 80})
    await svc.alliance.contribute(1, "knight", "max")

    await rich(svc, 3, "Iberia")
    outsider = await BossMenu.open(svc, 3)  # no alliance: can still see the list
    check_embed(outsider.embed())
    assert outsider.children == []
    assert len(outsider.embed().fields) == len(content.ages)

    member = await BossMenu.open(svc, 2)
    check_embed(member.embed())
    assert member.children == []  # members can look, not lead

    menu = await BossMenu.open(svc, 1)
    check_view(menu)
    check_embed(menu.embed())
    it = _Interaction()
    await menu._pick(it, "the_mud_golem")  # type: ignore[arg-type]
    await menu._fight(it)  # type: ignore[arg-type]  # arms
    assert not it.followup.sent
    await menu._fight(it)  # type: ignore[arg-type]  # fights
    [result] = it.followup.sent
    check_embed(result)
    assert "defeated" in (result.title or "")
    check_embed(embeds.alliance(await svc.alliance.get(a.id), content))

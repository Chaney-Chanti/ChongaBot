"""Embeds: presentation only. No database access, no game rules beyond reading."""

from datetime import UTC, datetime

import discord

from chongabot.content import Content
from chongabot.content.models import RESOURCES
from chongabot.domain.models import ROLE_RANK, Alliance, AllianceSummary, Player, Target
from chongabot.rules import bosses as rules_bosses
from chongabot.rules import economy
from chongabot.rules.combat import BattleResult
from chongabot.services.bosses import BossReport, BossStatus
from chongabot.services.economy import Claimed, Purchase
from chongabot.services.military import (
    PATHS,
    AttackReport,
    BotAttackReport,
    BotStatus,
    ExploreReport,
)
from chongabot.services.nation import Profile
from chongabot.views import fmt


def success(message: str) -> discord.Embed:
    return discord.Embed(description=message, colour=fmt.GREEN)


def stats(profile: Profile, content: Content, now_ts: float) -> discord.Embed:
    p = profile.player
    age = content.age(p.age)
    e = discord.Embed(title=p.name, colour=fmt.GOLD)
    e.description = f"Ruled by {p.ruler_mention}" + (f"\n*{p.motto}*" if p.motto else "")
    e.set_author(name=f"{age.name} Age")

    rates = economy.production_rates(p, content)
    e.add_field(
        name="Resources",
        value=fmt.table(
            [
                [fmt.resource(r), fmt.num(p.resources[r]), f"+{fmt.num(rates[r])}/h"]
                for r in RESOURCES
                if p.resources[r] or rates[r]
            ],
            right={1, 2},
        ),
        inline=False,
    )
    e.add_field(name="Army", value=fmt.army(p.units, content), inline=False)

    built = [
        [fmt.clip(b.name, 22), fmt.num(n)]
        for b_id, n in p.buildings.items()
        if n and (b := content.buildings.get(b_id))
    ]
    e.add_field(
        name="Buildings", value=fmt.table(built, right={1}) if built else "None yet", inline=False
    )

    record = f"{p.battle_rating} BR, rank #{profile.rank}\n{p.wins} wins, {p.losses} losses"
    e.add_field(name="Battle", value=record)
    found = sum(1 for h in p.heroes if h in content.heroes)
    extras = [f"{len(p.research)} research", f"{found} heroes found"]
    if p.wonders:
        extras.append(", ".join(content.wonders[w].name for w in p.wonders if w in content.wonders))
    e.add_field(name="Progress", value="\n".join(extras))

    timers = []
    ready = economy.next_claim_at(p, content)
    timers.append(f"Claim {'ready' if ready.timestamp() <= now_ts else fmt.ts(ready)}")
    if p.shield_until and p.shield_until.timestamp() > now_ts:
        timers.append(f"Shield ends {fmt.ts(p.shield_until)}")
    e.add_field(name="Timers", value="\n".join(timers))

    hero = content.heroes.get(p.hero or "")
    e.add_field(
        name="Second in Command",
        value=f"**{hero.name}**\n{fmt.effects_text(hero.effects, content)}"
        if hero
        else "Vacant. Heroes turn up while exploring; appoint one with `/hero`.",
        inline=False,
    )
    return e


def claimed(c: Claimed) -> discord.Embed:
    gained = c.result.gained
    rows = [[fmt.resource(r), f"+{fmt.num(v)}"] for r, v in gained.items() if v]
    e = discord.Embed(
        title=f"Collected {c.result.hours:.1f} hours of production",
        description=fmt.table(rows, right={1}) if rows else "Nothing produced.",
        colour=fmt.GREEN,
    )
    if c.result.hours >= 24:
        e.set_footer(text="Storage is full after 24 hours. Claim more often to not miss out.")
    return e


def purchase(p: Purchase, verb: str) -> discord.Embed:
    what = p.item if p.count == 1 else f"{fmt.num(p.count)} × {p.item}"
    return success(f"{verb} **{what}** for {fmt.cost(p.cost)}.")


def leaderboard(rows: list[Target], page: int, total: int, per_page: int) -> discord.Embed:
    cells = [
        [
            f"#{page * per_page + i + 1}",
            fmt.clip(t.name, 20),
            fmt.clip(t.alliance or "", 14),
            f"{t.battle_rating:,}",
        ]
        for i, t in enumerate(rows)
    ]
    pages = max(1, -(-total // per_page))
    e = discord.Embed(
        title="Leaderboard: Nations",
        description=fmt.table(cells, header=["", "Nation", "Alliance", "BR"], right={0, 3})
        if cells
        else "No nations yet.",
        colour=fmt.GOLD,
    )
    e.set_footer(text=f"Page {page + 1} of {pages} · {total} nations")
    return e


def alliance_leaderboard(
    rows: list[AllianceSummary], page: int, total: int, per_page: int
) -> discord.Embed:
    cells = [
        [
            f"#{page * per_page + i + 1}",
            fmt.clip(a.name, 22),
            str(a.members),
            f"{a.battle_rating:,}",
        ]
        for i, a in enumerate(rows)
    ]
    pages = max(1, -(-total // per_page))
    e = discord.Embed(
        title="Leaderboard: Alliances",
        description=fmt.table(cells, header=["", "Alliance", "Members", "BR"], right={0, 2, 3})
        if cells
        else "No alliances yet. Found one with `/alliance`.",
        colour=fmt.GOLD,
    )
    e.set_footer(
        text=f"Page {page + 1} of {pages} · {total} alliances · "
        "rating is the sum of members' ratings"
    )
    return e


DIFFICULTY = ((0.5, "Easy"), (0.85, "Fair"), (1.2, "Even"), (2.0, "Hard"))


def difficulty(ratio: float) -> str:
    """Enemy strength / your strength -> a label."""
    return next((label for limit, label in DIFFICULTY if ratio < limit), "Deadly")


def targets(
    rows: list[Target], me: Player, bots: list[BotStatus], content: Content
) -> discord.Embed:
    e = discord.Embed(title="Who you can attack", colour=fmt.RED)
    players = [
        [
            fmt.clip(t.name, 20),
            fmt.clip(t.alliance or "", 12),
            f"{t.battle_rating:,}",
            f"{t.battle_rating - me.battle_rating:+}",
        ]
        for t in rows[:15]
    ]
    e.add_field(
        name="Nations in range",
        value=fmt.table(players, header=["Nation", "Alliance", "BR", "vs you"], right={2, 3})
        if players
        else "Nobody in range. Everyone nearby is shielded or allied.",
        inline=False,
    )
    if bots:
        now = datetime.now(UTC)
        cells = []
        for status in bots:
            b = status.bot
            if status.ready_at:
                hours = max(0.0, (status.ready_at - now).total_seconds() / 3600)
                when = f"back in {hours:.0f}h" if hours >= 1 else "back soon"
            else:
                when = difficulty(status.ratio)
            cells.append([f"T{b.tier}", fmt.clip(b.name, 24), when, fmt.num(sum(b.loot.values()))])
        e.add_field(
            name="Bot nations of your age",
            value=fmt.table(cells, header=["", "Nation", "Status", "Loot"], right={3})[:1024],
            inline=False,
        )
    hours = content.settings.bot_cooldown_hours
    e.set_footer(
        text="Pick one below, or use /attack <nation>. Bots give loot but no battle rating, "
        f"and each can be attacked once every {hours:g} hours."
    )
    return e


def _battle_fields(
    e: discord.Embed, r: BattleResult, content: Content, left: str, right: str
) -> None:
    def losses(d: dict[str, int]) -> str:
        rows = [[fmt.clip(content.units[u].name, 18), f"-{fmt.num(n)}"] for u, n in d.items()]
        return fmt.table(rows, right={1}) if rows else "None"

    e.add_field(name=f"{left} lost", value=losses(r.attacker_losses))
    e.add_field(name=f"{right} lost", value=losses(r.defender_losses))
    if r.ally_losses:
        e.add_field(name="Alliance army lost", value=losses(r.ally_losses))
    e.set_footer(text=f"{len(r.log['rounds'])} rounds")


def attack(rep: AttackReport, content: Content) -> discord.Embed:
    a, d, r = rep.attacker, rep.defender, rep.result
    won = r.winner == "attacker"
    e = discord.Embed(
        title=f"{a.name} {'defeated' if won else 'was repelled by'} {d.name}",
        colour=fmt.GREEN if won else fmt.RED,
    )
    lines = [
        f"**{a.name if won else d.name}** wins and gains **{rep.rating_change} BR**.",
    ]
    if won and rep.tribute:
        lines.append(f"Tribute: {fmt.cost(rep.tribute)}")
        lines.append(f"{d.name} is shielded for {content.settings.shield_hours:g} hours.")
    e.description = "\n".join(lines)
    _battle_fields(e, r, content, a.name, d.name)
    return e


def bot_attack(rep: BotAttackReport, content: Content) -> discord.Embed:
    won = rep.result.winner == "attacker"
    a, b = rep.attacker, rep.bot
    e = discord.Embed(
        title=f"{a.name} {'defeated' if won else 'was repelled by'} {b.name}",
        colour=fmt.GREEN if won else fmt.RED,
        description=(f"Loot: {fmt.cost(rep.loot)}" if won else "No loot. Train up and try again.")
        + f"\n{b.name} can be attacked again in {content.settings.bot_cooldown_hours:g} hours.",
    )
    _battle_fields(e, rep.result, content, a.name, b.name)
    return e


def explore(rep: ExploreReport, content: Content) -> discord.Embed:
    o = rep.outcome
    region = PATHS.get(rep.path, rep.path)
    title = f"Your explorers return from {region}"
    e = discord.Embed(title=title, description=o.event.desc, colour=fmt.BLUE)
    match o.kind:
        case "resources":
            e.add_field(name="Found", value=fmt.cost(o.resources))
        case "units":
            e.add_field(name="Recruited", value=fmt.army(o.units, content))
        case "building":
            assert o.building
            e.add_field(name="Built for free", value=content.buildings[o.building].name)
        case "hero":
            assert o.hero
            h = content.heroes[o.hero]
            appointed = rep.player.hero == h.id
            e.add_field(
                name=f"{h.name} joins your court!",
                value=f"*{h.desc}*\n**{fmt.effects_text(h.effects, content)}**\n\n"
                + (
                    "Your Second in Command post was empty, so they've taken it."
                    if appointed
                    else "Make them your Second in Command with `/hero`."
                ),
                inline=False,
            )
            e.colour = fmt.GOLD
        case "wonder":
            assert o.wonder
            w = content.wonders[o.wonder]
            e.add_field(name=f"You found {w.name}", value=w.desc)
            e.colour = fmt.GOLD
        case "pirates":
            assert rep.battle
            won = rep.battle.winner == "attacker"
            e.colour = fmt.GREEN if won else fmt.RED
            e.add_field(
                name="You beat them off" if won else "They got away",
                value=f"Loot: {fmt.cost(o.resources)}" if won else "No loot this time.",
                inline=False,
            )
            _battle_fields(e, rep.battle, content, "You", "Pirates")
    return e


def ages(player: Player, content: Content) -> discord.Embed:
    here = content.age_index(player.age)
    cells = [
        [
            age.name,
            age.tagline or "",
            f"x{age.production_multiplier:g}",
            "done" if i < here else "you are here" if i == here else "locked",
        ]
        for i, age in enumerate(content.ages)
    ]
    e = discord.Embed(
        title="The Ages of Chonga",
        description=fmt.table(cells, header=["Age", "Known as", "Output", ""], right={2}),
        colour=fmt.GOLD,
    )
    if here + 1 < len(content.ages):
        nxt = content.ages[here + 1]
        e.add_field(name=f"To reach the {nxt.name} Age", value=fmt.cost(nxt.advance_cost))
    return e


def lore(content: Content) -> discord.Embed:
    world = content.lore
    e = discord.Embed(title=world.title, description=world.intro, colour=fmt.GOLD)
    for region in world.regions:
        e.add_field(name=region.name, value=region.desc, inline=False)
    ages = " → ".join(a.tagline or a.name for a in content.ages)
    e.set_footer(text=ages)
    return e


def wonders(player: Player, content: Content) -> discord.Embed:
    e = discord.Embed(
        title="Wonders of Chonga",
        description="Wonders are discovered through `/explore`, one age at a time, and their "
        "bonuses always apply.",
        colour=fmt.GOLD,
    )
    for age in content.ages:
        rows = [
            f"**{w.name}**{' (found)' if w.id in player.wonders else ''} · "
            f"{fmt.effects_text(w.effects, content)}\n*{w.desc}*"
            for w in content.wonders.values()
            if w.age == age.id
        ]
        if rows:
            e.add_field(name=age.name, value="\n".join(rows), inline=False)
    return e


def alliance(a: Alliance, content: Content) -> discord.Embed:
    e = discord.Embed(title=a.name, colour=fmt.BLUE)
    cap = content.settings.alliance_member_cap
    e.description = f"{a.battle_rating:,} BR · {len(a.members)} / {cap} members"
    members = sorted(a.members, key=lambda m: (-ROLE_RANK[m.role], -m.battle_rating))
    staked = sum(m.stake for m in members)

    def share(stake: int) -> str:
        return f"{stake / staked:.0%}" if staked and stake else "-"

    cells = [
        [fmt.clip(m.name, 20), m.role, f"{m.battle_rating:,}", share(m.stake)] for m in members[:20]
    ]
    if len(members) > 20:
        cells.append([f"and {len(members) - 20} more", "", "", ""])
    e.add_field(
        name="Members",
        value=fmt.table(cells, header=["Nation", "Role", "BR", "Army share"], right={2, 3}),
        inline=False,
    )
    e.add_field(
        name="Alliance army",
        value=fmt.army(a.units, content)
        + "\n*Defends any member who is attacked, and fights bosses with `/boss`.*",
        inline=False,
    )
    if a.requests:
        e.add_field(
            name=f"Join requests ({len(a.requests)})",
            value="\n".join(f"{r.name} · {r.battle_rating} BR" for r in a.requests[:10]),
            inline=False,
        )
    return e


def _hours_until(when: datetime) -> str:
    hours = max(0.0, (when - datetime.now(UTC)).total_seconds() / 3600)
    return f"back in {hours:.0f}h" if hours >= 1 else "back soon"


def bosses(
    a: Alliance | None, me: Player, statuses: list[BossStatus], content: Content
) -> discord.Embed:
    if a is None:
        e = discord.Embed(
            title="Alliance bosses",
            description="Giant foes that only a whole alliance army can beat, for big loot "
            "split by how much of the army each member contributed. Join or found an alliance "
            "with `/alliance` to fight them.",
            colour=fmt.RED,
        )
        for age in content.ages:
            rows = [
                [fmt.clip(st.boss.name, 30), fmt.num(sum(st.boss.loot.values()))]
                for st in statuses
                if st.boss.age == age.id
            ]
            if rows:
                e.add_field(
                    name=f"{age.name} Age",
                    value=fmt.table(rows, header=["Boss", "Loot"], right={1}),
                    inline=False,
                )
        return e
    staked = sum(m.stake for m in a.members)
    mine = next((m.stake for m in a.members if m.id == me.id), 0)
    army = rules_bosses.army_value(content, a.units)
    lines = [
        "Bosses are fought by the whole alliance army in one battle. Win, and the loot is "
        "split by how much of the army each member contributed. Officers start the fight.",
        "",
        f"Alliance army: **{fmt.num(army)}** resources' worth of units.",
        f"Your share: **{mine / staked:.0%}**" if staked else "Nobody has a share yet.",
    ]
    e = discord.Embed(title=f"Bosses for {a.name}", description="\n".join(lines), colour=fmt.RED)
    for age in content.ages:
        cells = [
            [
                fmt.clip(st.boss.name, 26),
                _hours_until(st.ready_at) if st.ready_at else difficulty(st.ratio),
                fmt.num(sum(st.boss.loot.values())),
            ]
            for st in statuses
            if st.boss.age == age.id
        ]
        if cells:
            e.add_field(
                name=f"{age.name} Age",
                value=fmt.table(cells, header=["Boss", "Status", "Loot"], right={2}),
                inline=False,
            )
    e.set_footer(
        text="Add units to the alliance army with Contribute units in /alliance. "
        f"Each boss can be fought once every {content.settings.boss_cooldown_hours:g} hours."
    )
    return e


def boss_fight(rep: BossReport, content: Content) -> discord.Embed:
    a, b, r = rep.alliance, rep.boss, rep.result
    won = r.winner == "attacker"
    e = discord.Embed(
        title=f"{a.name} {'defeated' if won else 'was beaten by'} {b.name}",
        colour=fmt.GOLD if won else fmt.RED,
    )
    if won:
        e.description = f"*{b.desc}*\n\nLoot: {fmt.cost(b.loot)}"
        cells = [
            [fmt.clip(p.name, 20), f"{p.share:.0%}", fmt.num(sum(p.loot.values()))]
            for p in rep.payouts[:15]
        ]
        if len(rep.payouts) > 15:
            cells.append([f"and {len(rep.payouts) - 15} more", "", ""])
        e.add_field(
            name="Loot split by army share",
            value=fmt.table(cells, header=["Nation", "Share", "Loot"], right={1, 2}),
            inline=False,
        )
    else:
        e.description = f"*{b.desc}*\n\nNo loot. Build up the alliance army and try again."
    _battle_fields(e, r, content, a.name, b.name)
    return e


def retrained(rows: list[economy.Retraining], content: Content) -> str:
    """`100 Clubman + 50 Spearman  ->  33 Knight`, one line per new unit, aligned."""
    cells = [
        [
            " + ".join(f"{fmt.num(n)} {content.units[u].name}" for u, n in r.old.items()),
            "->",
            f"{fmt.num(r.count)} {content.units[r.into].name}",
        ]
        for r in rows
    ]
    return fmt.table(cells)[:1024]

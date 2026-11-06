import contextlib

import discord
from discord import app_commands
from discord.ext import commands

from chongabot.bot import ChongaBot, Ctx
from chongabot.cogs.economy import buy_directly, item_choices, open_menu
from chongabot.cogs.nation import nation_choices
from chongabot.domain.errors import GameError
from chongabot.domain.models import Target
from chongabot.menus.base import OwnedView
from chongabot.menus.heroes import HeroMenu
from chongabot.services.military import PATHS, BotStatus
from chongabot.views import embeds, fmt


class TargetPicker(OwnedView):
    """One dropdown with bots of your age (ready ones) and players in range."""

    def __init__(
        self, bot: ChongaBot, owner_id: int, targets: list[Target], bots: list[BotStatus]
    ) -> None:
        super().__init__(owner_id)
        self.bot = bot
        options = [
            discord.SelectOption(
                label=s.bot.name,
                value=f"bot:{s.bot.id}",
                description=f"Tier {s.bot.tier} · {embeds.difficulty(s.ratio)}"[:100],
            )
            for s in bots
            if s.ready_at is None
        ]
        options += [
            discord.SelectOption(
                label=t.name, value=f"player:{t.id}", description=f"{t.battle_rating} BR"
            )
            for t in targets[: 25 - len(options)]
        ]
        if options:
            self.select("Attack…", options, self._attack)

    async def _attack(self, interaction: discord.Interaction, value: str) -> None:
        kind, _, target = value.partition(":")
        mil, content = self.bot.services.military, self.bot.content
        self.stop()
        if kind == "bot":
            bot_report = await mil.attack_bot(self.owner_id, target)
            await interaction.response.edit_message(
                embed=embeds.bot_attack(bot_report, content), view=None
            )
            return
        report = await mil.attack(self.owner_id, int(target))
        await interaction.response.edit_message(embed=embeds.attack(report, content), view=None)
        await notify_defender(self.bot, report.defender.id, report)


class ExploreView(OwnedView):
    def __init__(self, bot: ChongaBot, owner_id: int) -> None:
        super().__init__(owner_id, timeout=180)
        self.bot = bot
        for path, label in PATHS.items():
            self.button(label, self._go(path), style=discord.ButtonStyle.primary)

    def _go(self, path: str):  # type: ignore[no-untyped-def]
        async def callback(interaction: discord.Interaction) -> None:
            report = await self.bot.services.military.explore(self.owner_id, path)
            self.stop()
            await interaction.response.edit_message(
                embed=embeds.explore(report, self.bot.content), view=None
            )

        return callback


async def notify_defender(bot: ChongaBot, defender_id: int, report) -> None:  # type: ignore[no-untyped-def]
    """DM the defender. Best effort: closed DMs are fine."""
    with contextlib.suppress(discord.HTTPException):
        user = bot.get_user(defender_id) or await bot.fetch_user(defender_id)
        e = embeds.attack(report, bot.content)
        e.title = f"You were attacked by {report.attacker.name}"
        await user.send(embed=e)


class Military(commands.Cog):
    """Training, attacking and exploring."""

    def __init__(self, bot: ChongaBot) -> None:
        self.bot = bot

    @commands.hybrid_command(description="Train units for your army (opens a menu)")
    @app_commands.describe(unit="Skip the menu and train this", amount="A number, or max")
    async def train(self, ctx: Ctx, unit: str | None = None, amount: str | None = None) -> None:
        if unit is None:
            await open_menu(self.bot, ctx, "unit")
        else:
            await buy_directly(self.bot, ctx, "unit", unit, amount)

    @train.autocomplete("unit")
    async def _train_ac(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await item_choices(self.bot, interaction, current, "unit")

    @commands.hybrid_command(description="Attack a nation or bot, or see who you can attack")
    @app_commands.describe(nation="Who to attack. Leave empty to see who's in range.")
    async def attack(self, ctx: Ctx, *, nation: str | None = None) -> None:
        mil = self.bot.services.military
        if nation is None:
            player = await self.bot.services.nation.get(ctx.author.id)
            targets = await mil.targets(ctx.author.id)
            bots = await mil.bots(ctx.author.id)
            view = TargetPicker(self.bot, ctx.author.id, targets, bots)
            view.message = await ctx.send(
                embed=embeds.targets(targets, player, bots, self.bot.content),
                view=view,
                ephemeral=True,
            )
            return
        if bot_nation := mil.find_bot(nation):
            bot_report = await mil.attack_bot(ctx.author.id, bot_nation.id)
            await ctx.send(embed=embeds.bot_attack(bot_report, self.bot.content))
            return
        defender = await self.bot.services.nation.find(nation)
        report = await mil.attack(ctx.author.id, defender.id)
        await ctx.send(embed=embeds.attack(report, self.bot.content))
        await notify_defender(self.bot, defender.id, report)

    @attack.autocomplete("nation")
    async def _attack_ac(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        mil = self.bot.services.military
        try:
            bots = await mil.bots(interaction.user.id)
            targets = await mil.targets(interaction.user.id) if not current else []
        except GameError:
            return []
        needle = current.casefold()
        choices = [
            app_commands.Choice(
                name=f"{s.bot.name} · tier {s.bot.tier}" + (" · recovering" if s.ready_at else ""),
                value=s.bot.name,
            )
            for s in bots
            if needle in s.bot.name.casefold()
        ]
        if current:
            choices += await nation_choices(self.bot, current)
        else:
            choices += [
                app_commands.Choice(name=f"{t.name} · {t.battle_rating} BR", value=t.name)
                for t in targets
            ]
        return choices[:25]

    @commands.hybrid_command(
        description="Explore Chonga for loot, heroes and wonders (every 6 hours)"
    )
    async def explore(self, ctx: Ctx) -> None:
        await self.bot.services.military.check_explore(ctx.author.id)
        view = ExploreView(self.bot, ctx.author.id)
        e = discord.Embed(
            title="Where in Chonga should your explorers go?",
            description="They might find resources, recruits, a free building, a wonder, a "
            "hero for your court… or pirates.",
            colour=fmt.BLUE,
        )
        view.message = await ctx.send(embed=e, view=view)

    @commands.hybrid_command(description="Your heroes, and your Second in Command")
    async def hero(self, ctx: Ctx) -> None:
        player = await self.bot.services.nation.get(ctx.author.id)
        menu = HeroMenu(self.bot.services, player)
        menu.message = await ctx.send(embed=menu.embed(), view=menu, ephemeral=True)

    @commands.hybrid_command(description="Every wonder of Chonga and its bonus")
    async def wonder(self, ctx: Ctx) -> None:
        player = await self.bot.services.nation.get(ctx.author.id)
        await ctx.send(embed=embeds.wonders(player, self.bot.content), ephemeral=True)


async def setup(bot: ChongaBot) -> None:
    await bot.add_cog(Military(bot))

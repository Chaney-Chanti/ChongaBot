import discord
from discord import app_commands
from discord.ext import commands

from chongabot.bot import ChongaBot, Ctx
from chongabot.domain.errors import GameError
from chongabot.menus.base import ConfirmView
from chongabot.menus.buy import BuyMenu, Kind
from chongabot.rules import economy
from chongabot.services.common import Count
from chongabot.views import embeds, fmt


def parse_count(text: str | None) -> Count:
    if text is None:
        return 1
    cleaned = text.replace(",", "").strip().lower()
    if cleaned in ("max", "all"):
        return "max"
    if cleaned.isdigit() and int(cleaned) > 0:
        return int(cleaned)
    raise GameError(f"`{text}` isn't an amount. Use a number like `5`, or `max`.")


def split_amount(text: str) -> tuple[str, str | None]:
    """'oil rig 5' -> ('oil rig', '5'). Lets prefix users type names with spaces."""
    name, _, last = text.rpartition(" ")
    if name and (last.replace(",", "").isdigit() or last.lower() in ("max", "all")):
        return name, last
    return text, None


async def open_menu(bot: ChongaBot, ctx: Ctx, kind: Kind, selected: str | None = None) -> None:
    player = await bot.services.nation.get(ctx.author.id)
    menu = BuyMenu(bot.services, player, kind, selected)
    menu.message = await ctx.send(embed=menu.embed(), view=menu, ephemeral=True)


async def item_choices(
    bot: ChongaBot, interaction: discord.Interaction, current: str, kind: Kind
) -> list[app_commands.Choice[str]]:
    player = await bot.services.nation.maybe_get(interaction.user.id)
    if player is None:
        return []
    c = bot.content
    items = (
        economy.buildable(player, c)
        if kind == "building"
        else economy.trainable(player, c)
        if kind == "unit"
        else economy.researchable(player, c)
    )
    needle = current.lower()
    return [
        app_commands.Choice(name=i.name, value=i.id) for i in items if needle in i.name.lower()
    ][:25]


async def buy_directly(bot: ChongaBot, ctx: Ctx, kind: Kind, item: str, amount: str | None) -> None:
    if amount is None and ctx.interaction is None:
        item, amount = split_amount(item)
    count = parse_count(amount)
    econ = bot.services.economy
    if kind == "building":
        bought = await econ.build(ctx.author.id, item, count)
        verb = "Built"
    elif kind == "unit":
        bought = await econ.train(ctx.author.id, item, count)
        verb = "Trained"
    else:
        bought = await econ.research(ctx.author.id, item)
        verb = "Researched"
    await ctx.send(embed=embeds.purchase(bought, verb))


class Economy(commands.Cog):
    """Claiming, building, research and ages."""

    def __init__(self, bot: ChongaBot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        description="Collect what your nation has produced (hourly, stores up to 24 hours)"
    )
    async def claim(self, ctx: Ctx) -> None:
        claimed = await self.bot.services.economy.claim(ctx.author.id)
        await ctx.send(embed=embeds.claimed(claimed))

    @commands.hybrid_command(description="Build farms, mills, mines and defenses (opens a menu)")
    @app_commands.describe(building="Skip the menu and build this", amount="A number, or max")
    async def build(self, ctx: Ctx, building: str | None = None, amount: str | None = None) -> None:
        if building is None:
            await open_menu(self.bot, ctx, "building")
        else:
            await buy_directly(self.bot, ctx, "building", building, amount)

    @build.autocomplete("building")
    async def _build_ac(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await item_choices(self.bot, interaction, current, "building")

    @commands.hybrid_command(description="Research upgrades that boost production (opens a menu)")
    @app_commands.describe(topic="Skip the menu and research this")
    async def research(self, ctx: Ctx, *, topic: str | None = None) -> None:
        if topic is None:
            await open_menu(self.bot, ctx, "research")
        else:
            await buy_directly(self.bot, ctx, "research", topic, "1")

    @research.autocomplete("topic")
    async def _research_ac(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await item_choices(self.bot, interaction, current, "research")

    @commands.hybrid_command(description="Every age and what it costs to reach")
    async def ages(self, ctx: Ctx) -> None:
        player = await self.bot.services.nation.get(ctx.author.id)
        await ctx.send(embed=embeds.ages(player, self.bot.content), ephemeral=True)

    @commands.hybrid_command(
        description="Advance to the next age for more production and new units"
    )
    async def nextage(self, ctx: Ctx) -> None:
        player = await self.bot.services.nation.get(ctx.author.id)
        nxt = economy.next_age(player, self.bot.content)
        missing = economy.shortfall(player.resources, nxt.advance_cost)
        e = discord.Embed(
            title=f"Advance to the {nxt.name} Age?",
            description=(
                f"Costs {fmt.cost(nxt.advance_cost, player.resources)}\n\n"
                f"Production ×{nxt.production_multiplier:g}, new units, buildings and research. "
                "Your army is retrained into the new age's units, keeping its value: "
                "e.g. 100 Clubmen become 20 Knights. Defense buildings from older ages keep "
                "fighting, but you can only build those of your current age."
            ),
            colour=fmt.GOLD,
        )
        if missing:
            e.add_field(name="You're short", value=fmt.cost(missing))
            await ctx.send(embed=e, ephemeral=True)
            return

        async def confirm(_: discord.Interaction) -> discord.Embed:
            age, _p, retrained = await self.bot.services.economy.advance(ctx.author.id)
            e = discord.Embed(
                title=f"Welcome to the {age.name} Age!",
                description="New units, buildings and research are waiting. Try `/build` and "
                "`/train`.",
                colour=fmt.GREEN,
            )
            if retrained:
                e.add_field(
                    name="Your army was retrained",
                    value=embeds.retrained(retrained, self.bot.content),
                    inline=False,
                )
            return e

        view = ConfirmView(ctx.author.id, confirm, confirm_label=f"Enter the {nxt.name} Age")
        view.message = await ctx.send(embed=e, view=view, ephemeral=True)


async def setup(bot: ChongaBot) -> None:
    await bot.add_cog(Economy(bot))

import time
from typing import Any, Literal

import discord
from discord import app_commands
from discord.ext import commands

from chongabot.bot import ChongaBot, Ctx
from chongabot.domain.models import Player
from chongabot.menus.base import OwnedView
from chongabot.menus.founding import FoundingView
from chongabot.views import embeds, fmt

PER_PAGE = 10

# /help is generated from the registered commands, so it can't fall out of date.
# Cogs appear in this order; owner-only cogs are shown to owners only.
HELP_SECTIONS: dict[str, tuple[str, bool]] = {
    "Nation": ("Nation", False),
    "Economy": ("Economy", False),
    "Military": ("Military", False),
    "Alliances": ("Alliance", False),
    "Meta": ("General", False),
    "Admin": ("Owner", True),
    "Dev": ("Dev tools (owner, dev mode only)", True),
}


def usage(command: commands.Command[Any, Any, Any]) -> str:
    """e.g. `/build [building] [amount]`."""
    params = " ".join(
        f"<{name}>" if param.required else f"[{name}]"
        for name, param in command.clean_params.items()
    )
    return f"/{command.qualified_name}{' ' + params if params else ''}"


def help_lines(cog: commands.Cog) -> list[str]:
    lines = []
    for command in cog.get_commands():  # definition order
        if command.hidden:
            continue
        children = (
            sorted(command.commands, key=lambda c: c.name)
            if isinstance(command, commands.Group)
            else [command]
        )
        for c in children:
            lines.append(f"`{usage(c)}` · {c.description or c.short_doc}")
    return lines


def help_embed(bot: commands.Bot, owner: bool) -> discord.Embed:
    e = discord.Embed(title="ChongaBot commands", colour=fmt.GOLD)
    e.description = (
        "Use them as slash commands (`/claim`) or by mentioning me (`@ChongaBot claim`). "
        "`<this>` is required, `[this]` is optional."
    )
    for cog_name, (title, owner_only) in HELP_SECTIONS.items():
        cog = bot.get_cog(cog_name)
        if cog is None or (owner_only and not owner):
            continue
        lines = help_lines(cog)
        if lines:
            e.add_field(name=title, value="\n".join(lines)[:1024], inline=False)
    e.set_footer(text="New here? Start with /createnation, then /lore for the story.")
    return e


PATCH_NOTES = """**ChongaBot 2.0: Welcome to the Land of Chonga.** A complete rebuild.
• A whole new world: read its story with `/lore`. Every nation, wonder and hero is now \
from the Land of Chonga.
• Heroes no longer fight. Find them by luck while exploring, then appoint one as your \
**Second in Command** with `/hero` to gain their bonus. Swap them out any time \
(with a short wait between appointments).
• Slash commands everywhere, with private buy menus for building, training and research.
• Faster, fairer combat in volley rounds. Units counter each other in a cycle: \
melee › ranged › cavalry › siege › defense › melee.
• 10 bot nations per age to attack for loot, however many players share your age.
• One `/alliance` menu for everything, and your alliance army defends you when attacked.
• Alliance bosses with `/boss`: send the alliance army against a giant foe for big loot, \
split by how much of the army each member contributed.
• The leaderboard ranks alliances too, by their members' combined battle rating.
• Rebalanced economy: claims store up to 24 hours, and every age is reachable in weeks.
• Advancing an age retrains your army into the new age's units, keeping its value.
• Stock investing has been retired."""


Board = Literal["nations", "alliances"]


class LeaderboardView(OwnedView):
    def __init__(self, bot: ChongaBot, owner_id: int, board: Board, page: int) -> None:
        super().__init__(owner_id)
        self.bot, self.board, self.page, self.pages = bot, board, page, 1

    async def embed(self) -> discord.Embed:
        """Fetch the current page, re-render the buttons, and return the embed."""
        if self.board == "nations":
            rows, total = await self.bot.services.nation.leaderboard(self.page, PER_PAGE)
            e = embeds.leaderboard(rows, self.page, total, PER_PAGE)
        else:
            groups, total = await self.bot.services.alliance.leaderboard(self.page, PER_PAGE)
            e = embeds.alliance_leaderboard(groups, self.page, total, PER_PAGE)
        self.pages = max(1, -(-total // PER_PAGE))
        if self.page >= self.pages:  # e.g. switching to a board with fewer pages
            self.page = self.pages - 1
            return await self.embed()
        self._render()
        return e

    def _render(self) -> None:
        self.clear_items()
        self.button("◀", self._move(-1), disabled=self.page == 0)
        self.button("▶", self._move(1), disabled=self.page >= self.pages - 1)
        for board, label in (("nations", "Nations"), ("alliances", "Alliances")):
            self.button(
                label,
                self._switch(board),
                style=discord.ButtonStyle.primary
                if self.board == board
                else discord.ButtonStyle.secondary,
            )

    def _move(self, delta: int):  # type: ignore[no-untyped-def]
        async def callback(interaction: discord.Interaction) -> None:
            self.page = max(0, min(self.pages - 1, self.page + delta))
            await interaction.response.edit_message(embed=await self.embed(), view=self)

        return callback

    def _switch(self, board: Board):  # type: ignore[no-untyped-def]
        async def callback(interaction: discord.Interaction) -> None:
            self.board, self.page = board, 0
            await interaction.response.edit_message(embed=await self.embed(), view=self)

        return callback


class Nation(commands.Cog):
    """Founding and inspecting nations."""

    def __init__(self, bot: ChongaBot) -> None:
        self.bot = bot

    @property
    def svc(self):  # type: ignore[no-untyped-def]
        return self.bot.services.nation

    @commands.hybrid_command(description="Found your nation")
    async def createnation(self, ctx: Ctx, *, name: str) -> None:
        cleaned = await self.svc.check_new(ctx.author.id, name)
        view = FoundingView(
            self.bot.services, ctx.author, cleaned, ctx.guild.id if ctx.guild else None
        )
        view.message = await ctx.send(embed=view.embed(), view=view, ephemeral=True)

    @commands.hybrid_command(description="View your nation, or another one")
    async def stats(self, ctx: Ctx, *, nation: str | None = None) -> None:
        user_id = ctx.author.id
        if nation:
            user_id = (await self.svc.find(nation)).id
        profile = await self.svc.profile(user_id)
        await ctx.send(embed=embeds.stats(profile, self.bot.content, time.time()))

    @stats.autocomplete("nation")
    async def _stats_nation(
        self, interaction: discord.Interaction, current: str
    ) -> list[discord.app_commands.Choice[str]]:
        return await nation_choices(self.bot, current)

    @commands.hybrid_command(description="Set a motto for your enemies to read")
    async def motto(self, ctx: Ctx, *, text: str) -> None:
        motto = await self.svc.set_motto(ctx.author.id, text)
        await ctx.send(embed=embeds.success(f"Your motto is now *{motto}*"), ephemeral=True)

    @commands.hybrid_command(description="Top nations and alliances by battle rating")
    @app_commands.describe(board="Nations or alliances", page="Page number")
    async def leaderboard(self, ctx: Ctx, board: Board = "nations", page: int = 1) -> None:
        view = LeaderboardView(self.bot, ctx.author.id, board, max(0, page - 1))
        view.message = await ctx.send(embed=await view.embed(), view=view)

    @commands.hybrid_command(name="help", description="Every command and what it does")
    async def help_(self, ctx: Ctx) -> None:
        owner = await self.bot.is_owner(ctx.author)
        await ctx.send(embed=help_embed(self.bot, owner), ephemeral=True)

    @commands.hybrid_command(description="The story of the Land of Chonga")
    async def lore(self, ctx: Ctx) -> None:
        await ctx.send(embed=embeds.lore(self.bot.content), ephemeral=True)

    @commands.hybrid_command(description="What changed in the latest update")
    async def patch(self, ctx: Ctx) -> None:
        await ctx.send(
            embed=discord.Embed(title="Patch notes", description=PATCH_NOTES, colour=fmt.BLUE),
            ephemeral=True,
        )


async def nation_choices(bot: ChongaBot, current: str) -> list[discord.app_commands.Choice[str]]:
    rows = await bot.services.nation.search(current) if current else []
    if not current:
        rows, _ = await bot.services.nation.leaderboard(0, 25)
    return [
        discord.app_commands.Choice(name=f"{t.name} · {t.battle_rating} BR", value=t.name)
        for t in rows[:25]
    ]


async def me(bot: ChongaBot, ctx: Ctx) -> Player:
    return await bot.services.nation.get(ctx.author.id)


async def setup(bot: ChongaBot) -> None:
    await bot.add_cog(Nation(bot))

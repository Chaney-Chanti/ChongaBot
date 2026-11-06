from typing import Literal

from discord.ext import commands

from chongabot.bot import ChongaBot


class Meta(commands.Cog):
    """Bot health and owner-only maintenance commands."""

    def __init__(self, bot: ChongaBot) -> None:
        self.bot = bot

    @commands.hybrid_command(description="Check that the bot is alive")
    async def ping(self, ctx: commands.Context[ChongaBot]) -> None:
        await ctx.send(f"Pong! {round(self.bot.latency * 1000)} ms", ephemeral=True)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sync(
        self, ctx: commands.Context[ChongaBot], scope: Literal["guild", "global"] = "guild"
    ) -> None:
        """Push slash commands to Discord: this server (instant) or everywhere (up to 1 h)."""
        if scope == "global":
            synced = await self.bot.tree.sync()
        else:
            if ctx.guild is None:
                raise commands.UserInputError("Run this in a server, or use `c!sync global`.")
            self.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await self.bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"Synced {len(synced)} commands ({scope}).")


async def setup(bot: ChongaBot) -> None:
    await bot.add_cog(Meta(bot))

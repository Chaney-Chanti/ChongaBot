from discord.ext import commands

from chongabot.bot import ChongaBot, Ctx
from chongabot.menus.alliance import AllianceMenu
from chongabot.menus.bosses import BossMenu


class Alliances(commands.Cog):
    """Everything alliance-related lives in one private menu."""

    def __init__(self, bot: ChongaBot) -> None:
        self.bot = bot

    @commands.hybrid_command(description="Found, join or manage your alliance")
    async def alliance(self, ctx: Ctx) -> None:
        menu = await AllianceMenu.open(
            self.bot.services, ctx.author.id, ctx.guild.id if ctx.guild else None
        )
        menu.message = await ctx.send(embed=menu.embed(), view=menu, ephemeral=True)

    @commands.hybrid_command(description="Alliance bosses: fight them with the alliance army")
    async def boss(self, ctx: Ctx) -> None:
        menu = await BossMenu.open(self.bot.services, ctx.author.id)
        menu.message = await ctx.send(embed=menu.embed(), view=menu, ephemeral=True)


async def setup(bot: ChongaBot) -> None:
    await bot.add_cog(Alliances(bot))

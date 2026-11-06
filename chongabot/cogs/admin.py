import asyncio
import contextlib

import discord
import structlog
from discord.ext import commands

from chongabot.bot import ChongaBot, Ctx
from chongabot.content import ContentError, load_content
from chongabot.views import embeds, fmt

log = structlog.get_logger(__name__)


class Admin(commands.Cog):
    """Owner-only commands."""

    def __init__(self, bot: ChongaBot) -> None:
        self.bot = bot
        self._tasks: set[asyncio.Task[None]] = set()

    async def cog_check(self, ctx: Ctx) -> bool:  # type: ignore[override]
        if not await self.bot.is_owner(ctx.author):
            raise commands.CheckFailure("Only the bot owner can do that.")
        return True

    @commands.hybrid_command(description="DM a message to every player (owner only)")
    async def announce(self, ctx: Ctx, *, message: str) -> None:
        ids = await self.bot.services.nation.all_ids()
        await ctx.send(
            embed=embeds.success(f"Sending to {len(ids)} players in the background…"),
            ephemeral=True,
        )
        embed = discord.Embed(title="ChongaBot", description=message, colour=fmt.GOLD)

        async def send_all() -> None:
            sent = failed = 0
            for user_id in ids:
                try:
                    user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                    await user.send(embed=embed)
                    sent += 1
                except discord.HTTPException:
                    failed += 1
                await asyncio.sleep(0.5)  # stay well under DM rate limits
            log.info("announce_done", sent=sent, failed=failed)
            with contextlib.suppress(discord.HTTPException):
                await ctx.author.send(f"Announcement delivered to {sent}, failed for {failed}.")

        task = asyncio.create_task(send_all())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @commands.hybrid_command(description="Reload game content from YAML (owner only)")
    async def reload(self, ctx: Ctx) -> None:
        try:
            content = await asyncio.to_thread(load_content)
        except ContentError as e:
            await ctx.send(f"Content has errors, nothing changed:\n```\n{e}\n```"[:1990])
            return
        self.bot.services.ctx.content = content
        log.info("content_reloaded", units=len(content.units))
        await ctx.send(embed=embeds.success("Content reloaded."), ephemeral=True)


async def setup(bot: ChongaBot) -> None:
    await bot.add_cog(Admin(bot))

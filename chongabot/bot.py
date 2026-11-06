import time

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from chongabot.config import Settings
from chongabot.content import Content
from chongabot.domain.errors import GameError
from chongabot.services import Services

log = structlog.get_logger(__name__)

EXTENSIONS = (
    "chongabot.cogs.meta",
    "chongabot.cogs.nation",
    "chongabot.cogs.economy",
    "chongabot.cogs.military",
    "chongabot.cogs.alliance",
    "chongabot.cogs.admin",
)

DEV_EXTENSION = "chongabot.cogs.dev"

GENERIC_ERROR = "Something went wrong on our side. It's been logged."


def unwrap_error(error: BaseException) -> BaseException:
    """Peel off discord.py's wrapper exceptions to reach the one that was raised."""
    wrappers = (
        commands.CommandInvokeError,
        commands.HybridCommandError,
        app_commands.CommandInvokeError,
    )
    while isinstance(error, wrappers):
        error = error.original
    return error


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(description=message, colour=discord.Colour.red())


async def reply_error(interaction: discord.Interaction, message: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(embed=error_embed(message), ephemeral=True)
    else:
        await interaction.response.send_message(embed=error_embed(message), ephemeral=True)


class ChongaTree(app_commands.CommandTree):
    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Errors from pure slash commands (hybrid ones go through on_command_error)."""
        original = unwrap_error(error)
        if isinstance(original, GameError):
            message = original.message
        elif isinstance(original, app_commands.CheckFailure):
            message = str(original)
        else:
            log.error("app_command_crashed", exc_info=original)
            message = GENERIC_ERROR
        await reply_error(interaction, message)


class ChongaBot(commands.Bot):
    def __init__(self, settings: Settings, services: Services) -> None:
        intents = discord.Intents.default()
        # Needed for c! prefix commands. Without it, prefix commands still work when
        # they mention the bot ("@ChongaBot ping"), and slash commands are unaffected.
        intents.message_content = settings.message_content_intent
        prefix = settings.command_prefix
        super().__init__(
            command_prefix=commands.when_mentioned_or(prefix, prefix.upper()),
            intents=intents,
            case_insensitive=True,
            owner_ids=settings.owner_ids or None,
            tree_cls=ChongaTree,
            help_command=None,  # replaced by the /help command in the nation cog
        )
        self.settings = settings
        self.services = services
        self._started: dict[int, float] = {}

    @property
    def content(self) -> Content:
        return self.services.ctx.content  # swapped in place by /reload

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        if self.settings.dev_mode:
            await self.load_extension(DEV_EXTENSION)
            log.warning("dev_mode_enabled", hint="owner-only /dev commands are loaded")

        if self.settings.dev_guild_id:
            guild = discord.Object(id=self.settings.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("slash_commands_synced", scope="dev_guild", count=len(synced))

    async def on_ready(self) -> None:
        assert self.user is not None
        log.info("ready", user=str(self.user), guilds=len(self.guilds))

    # --- per-command logging -------------------------------------------------

    async def on_command(self, ctx: commands.Context["ChongaBot"]) -> None:
        self._started[id(ctx)] = time.perf_counter()

    async def on_command_completion(self, ctx: commands.Context["ChongaBot"]) -> None:
        self._log_command(ctx, outcome="ok")

    def _log_command(self, ctx: commands.Context["ChongaBot"], outcome: str) -> None:
        started = self._started.pop(id(ctx), None)
        log.info(
            "command",
            command=ctx.command.qualified_name if ctx.command else None,
            via="slash" if ctx.interaction else "prefix",
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else None,
            latency_ms=round((time.perf_counter() - started) * 1000, 1) if started else None,
            outcome=outcome,
        )

    # --- error handling ------------------------------------------------------

    async def on_command_error(  # type: ignore[override]  # discord.py types ctx as Context[BotT]
        self, ctx: commands.Context["ChongaBot"], exception: commands.CommandError
    ) -> None:
        if isinstance(exception, commands.CommandNotFound):
            return
        error = unwrap_error(exception)

        if isinstance(error, GameError):
            self._log_command(ctx, outcome="game_error")
            message = error.message
        elif isinstance(error, commands.UserInputError | commands.CheckFailure):
            self._log_command(ctx, outcome="user_error")
            message = str(error)
        else:
            self._log_command(ctx, outcome="crash")
            log.error("command_crashed", exc_info=error)
            message = GENERIC_ERROR

        await ctx.send(embed=error_embed(message), ephemeral=True)


Ctx = commands.Context[ChongaBot]

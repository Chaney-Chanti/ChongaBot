import asyncio
import contextlib

import discord
import structlog

from chongabot.bot import ChongaBot
from chongabot.config import Settings, get_settings
from chongabot.content import load_content
from chongabot.log import configure_logging
from chongabot.services import GameContext, Services
from chongabot.storage.db import Database

log = structlog.get_logger(__name__)


async def run(settings: Settings) -> None:
    # The Activity's web API will join this loop later via asyncio.gather,
    # so the bot and the API share one process and one SQLite writer.
    content = load_content()  # raises ContentError listing every problem in the YAML
    log.info(
        "content_loaded",
        ages=len(content.ages),
        units=len(content.units),
        buildings=len(content.buildings),
        research=len(content.research),
        wonders=len(content.wonders),
    )
    db = Database(settings.database_path)
    await db.migrate()
    log.info("database_ready", path=str(settings.database_path))
    services = Services(GameContext(db, content))
    async with ChongaBot(settings, services) as bot:
        try:
            await bot.start(settings.discord_token.get_secret_value())
        except discord.PrivilegedIntentsRequired:
            log.error(
                "message_content_intent_not_enabled",
                fix="Developer Portal > your app > Bot > Privileged Gateway Intents > "
                "turn on Message Content Intent and save. Or set MESSAGE_CONTENT_INTENT=false "
                "in .env to run without c! prefix commands.",
            )
            raise SystemExit(1) from None
        finally:
            await db.close()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json=settings.log_json)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run(settings))

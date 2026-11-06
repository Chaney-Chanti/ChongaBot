"""The /dev commands only exist in dev mode, and register as a valid slash command group."""

from pathlib import Path

from chongabot.bot import DEV_EXTENSION, EXTENSIONS, ChongaBot
from chongabot.config import Settings
from chongabot.content import load_content
from chongabot.services import GameContext, Services
from chongabot.storage.db import Database


async def make_bot(tmp_path: Path, dev_mode: bool) -> ChongaBot:
    settings = Settings(discord_token="x", dev_mode=dev_mode, dev_guild_id=None)  # type: ignore[arg-type]
    services = Services(GameContext(Database(tmp_path / "x.db"), load_content()))
    bot = ChongaBot(settings, services)
    for ext in EXTENSIONS:
        await bot.load_extension(ext)
    if dev_mode:
        await bot.load_extension(DEV_EXTENSION)
    return bot


async def test_dev_group_registers_in_dev_mode(tmp_path: Path) -> None:
    bot = await make_bot(tmp_path, dev_mode=True)
    dev = bot.tree.get_command("dev")
    assert dev is not None
    subs = {c.name for c in dev.commands}  # type: ignore[union-attr]
    assert subs == {"spawn", "give", "units", "hero", "reset", "age", "rating", "attackme", "wipe"}
    for c in dev.commands:  # type: ignore[union-attr]
        c.to_dict(bot.tree)  # raises if any option or autocomplete is malformed
    give = next(c for c in dev.commands if c.name == "give")  # type: ignore[union-attr]
    assert {p.name for p in give.parameters if p.autocomplete} == {"resource", "nation"}


async def test_no_dev_commands_in_production(tmp_path: Path) -> None:
    bot = await make_bot(tmp_path, dev_mode=False)
    assert bot.tree.get_command("dev") is None
    assert bot.get_command("dev") is None


async def test_help_lists_every_visible_command(tmp_path: Path) -> None:
    from chongabot.cogs.nation import help_embed

    bot = await make_bot(tmp_path, dev_mode=True)
    owner = help_embed(bot, owner=True)
    player = help_embed(bot, owner=False)
    owner_text = "\n".join(f.value or "" for f in owner.fields)
    player_text = "\n".join(f.value or "" for f in player.fields)
    for command in bot.walk_commands():
        if command.hidden or command.name == "dev":
            continue
        assert f"/{command.qualified_name}" in owner_text, command.qualified_name
    assert "/dev spawn" in owner_text and "/announce" in owner_text
    assert "/dev" not in player_text and "/announce" not in player_text
    assert "/claim" in player_text and "/ping" in player_text and "/patch" in player_text
    assert len(owner) <= 6000 and all(len(f.value or "") <= 1024 for f in owner.fields)

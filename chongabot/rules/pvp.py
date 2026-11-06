"""Who can attack whom, battle rating and tribute."""

import math
from datetime import datetime, timedelta

from chongabot.content import Content
from chongabot.content.models import RESOURCES, BotNation, Resource
from chongabot.domain.errors import GameError, OnCooldown
from chongabot.domain.models import Player
from chongabot.rules.effects import Modifiers


def in_range(a: int, b: int, content: Content) -> bool:
    return abs(a - b) <= content.settings.battle_rating_range


def check_can_attack(attacker: Player, defender: Player, content: Content, now: datetime) -> None:
    s = content.settings
    if attacker.id == defender.id:
        raise GameError("You can't attack yourself.")
    if not any(c > 0 for c in attacker.units.values()):
        raise GameError("You have no army. Train some units with `/train` first.")
    if attacker.last_attack and now < attacker.last_attack + timedelta(
        minutes=s.attack_cooldown_minutes
    ):
        ready = attacker.last_attack + timedelta(minutes=s.attack_cooldown_minutes)
        raise OnCooldown(f"Your army is regrouping. Attack again <t:{int(ready.timestamp())}:R>.")
    if defender.shield_until and now < defender.shield_until:
        raise GameError(
            f"{defender.name} is shielded until <t:{int(defender.shield_until.timestamp())}:R>."
        )
    if not in_range(attacker.battle_rating, defender.battle_rating, content):
        raise GameError(
            f"{defender.name} is out of range. You can attack nations within "
            f"{s.battle_rating_range} battle rating of yours."
        )
    if attacker.alliance_id is not None and attacker.alliance_id == defender.alliance_id:
        raise GameError(f"{defender.name} is in your alliance.")


def rating_change(winner_rating: int, loser_rating: int, content: Content) -> int:
    """Beating a stronger nation earns more; beating a weaker one earns less."""
    s = content.settings
    raw = s.battle_rating_base_change + (loser_rating - winner_rating) / 10
    return int(max(s.battle_rating_min_change, min(s.battle_rating_max_change, round(raw))))


def tribute(
    loser_resources: dict[Resource, int], content: Content, winner_mods: Modifiers
) -> tuple[dict[Resource, int], dict[Resource, int]]:
    """Returns (taken from the loser, given to the winner)."""
    s = content.settings
    taken = {r: math.floor(loser_resources.get(r, 0) * s.tribute_share) for r in RESOURCES}
    taken = {r: v for r, v in taken.items() if v > 0}
    given = {
        r: math.floor(v * (1 + s.tribute_bonus) * winner_mods.tribute) for r, v in taken.items()
    }
    return taken, given


# --- bot nations -------------------------------------------------------------------


def bot_ready_at(last_attacked: datetime | None, content: Content) -> datetime | None:
    """When the player may attack this bot again, or None if they can now."""
    if last_attacked is None:
        return None
    return last_attacked + timedelta(hours=content.settings.bot_cooldown_hours)


def check_can_attack_bot(
    attacker: Player,
    bot: BotNation,
    content: Content,
    now: datetime,
    last_attacked: datetime | None,
) -> None:
    """Bots are fought by players of the same age, once per bot per cooldown.

    They ignore battle rating range and your PvP attack cooldown: they're there so a
    player is never without something to fight.
    """
    if not any(c > 0 for c in attacker.units.values()):
        raise GameError("You have no army. Train some units with `/train` first.")
    if bot.age != attacker.age:
        raise GameError(
            f"{bot.name} is a {content.age(bot.age).name} Age nation. "
            f"You can only attack bot nations of your own age."
        )
    ready = bot_ready_at(last_attacked, content)
    if ready and now < ready:
        raise OnCooldown(
            f"{bot.name} is still recovering. Attack again <t:{int(ready.timestamp())}:R>."
        )

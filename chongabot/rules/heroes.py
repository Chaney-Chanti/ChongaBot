"""Second in Command: which hero serves you, and how often you can swap."""

from datetime import datetime, timedelta

from chongabot.content import Content
from chongabot.content.models import Hero
from chongabot.domain.errors import GameError, OnCooldown
from chongabot.domain.models import Player


def swap_ready_at(player: Player, content: Content) -> datetime | None:
    """When the player may appoint a different hero, or None if they can now."""
    if player.hero_appointed_at is None:
        return None
    return player.hero_appointed_at + timedelta(hours=content.settings.hero_swap_cooldown_hours)


def check_can_appoint(player: Player, hero: Hero, content: Content, now: datetime) -> None:
    if hero.id not in player.heroes:
        raise GameError(f"You haven't found {hero.name} yet. Heroes turn up while exploring.")
    if player.hero == hero.id:
        raise GameError(f"{hero.name} is already your Second in Command.")
    ready = swap_ready_at(player, content)
    if ready and now < ready:
        raise OnCooldown(
            f"Your court needs time to adjust. You can appoint a new Second in Command "
            f"<t:{int(ready.timestamp())}:R>."
        )

"""Alliance bosses: who may start a fight, when, and how the loot is split.

An alliance fights a boss with its shared army. Each member's share of the loot is their
stake: the resource value of the units they put into that army (shrunk by the army's
losses since). So joining a strong alliance and chipping in one spearman earns one
spearman's worth of the pot, not an equal cut.
"""

from collections.abc import Mapping
from datetime import datetime, timedelta

from chongabot.content import Content
from chongabot.content.models import RESOURCES, Boss, Resource
from chongabot.domain.errors import GameError, OnCooldown
from chongabot.domain.models import ROLE_RANK, AllianceRole


def army_value(content: Content, units: Mapping[str, int]) -> int:
    """Total resource cost of an army. Units no longer in content count as nothing."""
    return sum(
        sum(content.units[u].cost.values()) * n
        for u, n in units.items()
        if n > 0 and u in content.units
    )


def ready_at(last_fought: datetime | None, content: Content) -> datetime | None:
    """When the alliance may fight this boss again, or None if it never has."""
    if last_fought is None:
        return None
    return last_fought + timedelta(hours=content.settings.boss_cooldown_hours)


def check_can_challenge(
    role: AllianceRole | None,
    army: Mapping[str, int],
    boss: Boss,
    content: Content,
    now: datetime,
    last_fought: datetime | None,
) -> None:
    if role is None:
        raise GameError("You're not in an alliance.")
    if ROLE_RANK[role] < ROLE_RANK["officer"]:
        raise GameError("Only officers and the owner can lead the alliance against a boss.")
    if army_value(content, army) == 0:
        raise GameError(
            "Your alliance army is empty. Members add units with **Contribute units** "
            "in `/alliance`."
        )
    ready = ready_at(last_fought, content)
    if ready is not None and ready > now:
        raise OnCooldown(
            f"Your alliance fought {boss.name} recently. Try again <t:{int(ready.timestamp())}:R>."
        )


def split_loot(
    loot: Mapping[Resource, int], stakes: Mapping[int, int]
) -> dict[int, dict[Resource, int]]:
    """Each player's cut, in proportion to their stake.

    Amounts are rounded down; leftover units of each resource go to the biggest stake.
    With no stakes at all (an army from before stakes were tracked), it splits evenly.
    """
    holders = {p: s for p, s in stakes.items() if s > 0} or dict.fromkeys(stakes, 1)
    if not holders:
        return {}
    total = sum(holders.values())
    top = max(holders, key=lambda p: (holders[p], -p))
    payouts: dict[int, dict[Resource, int]] = {p: {} for p in holders}
    for r in RESOURCES:
        pot = loot.get(r, 0)
        if pot <= 0:
            continue
        given = 0
        for p, s in holders.items():
            cut = pot * s // total
            payouts[p][r] = cut
            given += cut
        payouts[top][r] += pot - given
    return {p: {r: v for r, v in cut.items() if v > 0} for p, cut in payouts.items()}

"""Use cases. Cogs and the Activity API call these; these call rules and storage."""

from chongabot.services.alliance import AllianceService
from chongabot.services.bosses import BossService
from chongabot.services.common import GameContext
from chongabot.services.dev import DevService
from chongabot.services.economy import EconomyService
from chongabot.services.heroes import HeroService
from chongabot.services.military import MilitaryService
from chongabot.services.nation import NationService


class Services:
    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self.nation = NationService(ctx)
        self.economy = EconomyService(ctx)
        self.military = MilitaryService(ctx)
        self.alliance = AllianceService(ctx)
        self.heroes = HeroService(ctx)
        self.bosses = BossService(ctx)
        self.dev = DevService(ctx, self.military)  # only reachable when DEV_MODE is on


__all__ = ["GameContext", "Services"]

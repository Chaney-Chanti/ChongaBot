"""The /boss menu: see the alliance's bosses, and (officers) send the army against one."""

import contextlib

import discord

from chongabot.domain.models import ROLE_RANK, Alliance, Player
from chongabot.menus.base import OwnedView
from chongabot.services import Services
from chongabot.services.bosses import BossStatus
from chongabot.views import embeds, fmt


class BossMenu(OwnedView):
    def __init__(
        self,
        services: Services,
        player: Player,
        alliance: Alliance | None,
        statuses: list[BossStatus],
    ) -> None:
        super().__init__(player.id)
        self.services = services
        self.player, self.alliance, self.statuses = player, alliance, statuses
        self.pick: str | None = None
        self.armed = False
        self.render()

    @classmethod
    async def open(cls, services: Services, user_id: int) -> "BossMenu":
        return cls(services, *await services.bosses.overview(user_id))

    @property
    def is_officer(self) -> bool:
        role = self.player.alliance_role
        return role is not None and ROLE_RANK[role] >= ROLE_RANK["officer"]

    def embed(self) -> discord.Embed:
        return embeds.bosses(self.alliance, self.player, self.statuses, self.services.ctx.content)

    def render(self) -> None:
        self.clear_items()
        if self.alliance is None or not self.is_officer:
            return  # anyone can look; officers lead
        ready = [s for s in self.statuses if s.ready_at is None]
        if not ready:
            return
        self.select(
            "Pick a boss to fight",
            [
                discord.SelectOption(
                    label=s.boss.name[:100],
                    value=s.boss.id,
                    description=f"{self.services.ctx.content.age(s.boss.age).name} Age · "
                    f"{embeds.difficulty(s.ratio)} · loot {fmt.num(sum(s.boss.loot.values()))}",
                    default=s.boss.id == self.pick,
                )
                for s in ready
            ],
            self._pick,
            row=0,
        )
        self.button(
            "Click again to send the whole army" if self.armed else "Fight",
            self._fight,
            row=1,
            style=discord.ButtonStyle.danger,
            disabled=self.pick is None,
        )

    async def reload(self) -> None:
        self.player, self.alliance, self.statuses = await self.services.bosses.overview(
            self.player.id
        )

    async def _pick(self, interaction: discord.Interaction, boss_id: str) -> None:
        self.pick, self.armed = boss_id, False
        self.render()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def _fight(self, interaction: discord.Interaction) -> None:
        if not self.armed:
            self.armed = True
            self.render()
            await interaction.response.edit_message(embed=self.embed(), view=self)
            return
        assert self.pick
        self.armed = False
        report = await self.services.bosses.challenge(self.player.id, self.pick)
        self.pick = None
        await self.reload()
        self.render()
        await interaction.response.edit_message(embed=self.embed(), view=self)
        # The result is news for the whole alliance: post it in the channel.
        await interaction.followup.send(embed=embeds.boss_fight(report, self.services.ctx.content))

    async def after_error(self, interaction: discord.Interaction) -> None:
        self.armed = False
        with contextlib.suppress(Exception):
            await self.reload()
        self.render()
        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(embed=self.embed(), view=self)

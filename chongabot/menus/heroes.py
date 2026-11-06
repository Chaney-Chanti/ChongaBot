"""The private /hero menu: see the heroes you've found and pick your Second in Command."""

import contextlib
import time

import discord

from chongabot.domain.models import Player
from chongabot.menus.base import OwnedView
from chongabot.rules import heroes as hero_rules
from chongabot.services import Services
from chongabot.views import fmt


class HeroMenu(OwnedView):
    def __init__(self, services: Services, player: Player) -> None:
        super().__init__(player.id)
        self.services = services
        self.player = player
        self.notice: str | None = None
        self.render()

    def embed(self) -> discord.Embed:
        content, p = self.services.ctx.content, self.player
        e = discord.Embed(title="Your Heroes", colour=fmt.GOLD)
        current = content.heroes.get(p.hero or "")
        if current:
            e.add_field(
                name=f"Second in Command: {current.name}",
                value=f"*{current.desc}*\n**{fmt.effects_text(current.effects, content)}**",
                inline=False,
            )
        else:
            e.add_field(
                name="Second in Command: vacant",
                value="Appoint one of your heroes below to gain their passive bonus.",
                inline=False,
            )

        found = [h for h in content.heroes.values() if h.id in p.heroes]
        others = [h for h in found if h.id != p.hero]
        if others:
            lines = [f"**{h.name}** · {fmt.effects_text(h.effects, content)}" for h in others]
            e.add_field(name="In your court", value="\n".join(lines)[:1024], inline=False)

        here = content.age_index(p.age)
        reachable = [h for h in content.heroes.values() if content.age_index(h.age) <= here]
        e.description = (
            f"You've found **{len(found)}** of the {len(reachable)} heroes known in your age. "
            "More turn up while exploring with `/explore`. Heroes never fight: only your "
            "Second in Command's bonus applies."
        )
        ready = hero_rules.swap_ready_at(p, content)
        if ready and ready.timestamp() > time.time():
            e.add_field(name="Next appointment", value=fmt.ts(ready), inline=False)
        if self.notice:
            e.add_field(name="​", value=self.notice, inline=False)
        return e

    def render(self) -> None:
        self.clear_items()
        content, p = self.services.ctx.content, self.player
        options = [
            discord.SelectOption(
                label=h.name[:100],
                value=h.id,
                description=fmt.effects_text(h.effects, content)[:100],
            )
            for h in content.heroes.values()
            if h.id in p.heroes and h.id != p.hero
        ]
        if options:
            self.select("Appoint as Second in Command…", options, self._appoint, row=0)
        if p.hero:
            self.button("Dismiss", self._dismiss, row=1, style=discord.ButtonStyle.danger)

    async def refresh(self, interaction: discord.Interaction) -> None:
        self.render()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def _appoint(self, interaction: discord.Interaction, hero_id: str) -> None:
        self.player = await self.services.heroes.appoint(self.player.id, hero_id)
        hero = self.services.ctx.content.heroes[hero_id]
        self.notice = f"**{hero.name}** is now your Second in Command."
        await self.refresh(interaction)

    async def _dismiss(self, interaction: discord.Interaction) -> None:
        self.player = await self.services.heroes.dismiss(self.player.id)
        self.notice = "Your Second in Command has been dismissed."
        await self.refresh(interaction)

    async def after_error(self, interaction: discord.Interaction) -> None:
        self.player = await self.services.nation.get(self.player.id)
        self.render()
        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(embed=self.embed(), view=self)

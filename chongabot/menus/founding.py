"""The /createnation setup: choose King, Queen or Ruler and an epithet, then found."""

import discord

from chongabot.domain.models import EPITHETS, RULER_TITLES, RulerTitle
from chongabot.menus.base import OwnedView
from chongabot.services import Services
from chongabot.views import fmt


class FoundingView(OwnedView):
    def __init__(
        self, services: Services, user: discord.abc.User, nation: str, guild_id: int | None
    ) -> None:
        super().__init__(user.id, timeout=600)
        self.services = services
        self.username = user.display_name
        self.handle = user.name
        self.nation = nation
        self.guild_id = guild_id
        self.title: RulerTitle | None = None
        self.epithet: str | None = None
        self.render()

    def ruler(self) -> str:
        parts = [
            RULER_TITLES[self.title] if self.title else "…",
            f"<@{self.owner_id}>",
            self.epithet or "the …",
        ]
        return " ".join(parts)

    def embed(self) -> discord.Embed:
        e = discord.Embed(
            title=f"Founding {self.nation}",
            description=(f"Who rules this land?\n\n## {self.ruler()}\nof **{self.nation}**"),
            colour=fmt.GOLD,
        )
        e.set_footer(text="Choose a title and an epithet, then found your nation.")
        return e

    def render(self) -> None:
        self.clear_items()
        for key, label in RULER_TITLES.items():
            self.button(
                label,
                self._pick_title(key),
                row=0,
                style=discord.ButtonStyle.primary
                if self.title == key
                else discord.ButtonStyle.secondary,
            )
        self.select(
            "Choose your epithet",
            [
                discord.SelectOption(label=ep, value=ep, default=ep == self.epithet)
                for ep in EPITHETS
            ],
            self._pick_epithet,
            row=1,
        )
        self.button(
            f"Found {self.nation}"[:80],
            self._found,
            row=2,
            style=discord.ButtonStyle.success,
            disabled=self.title is None or self.epithet is None,
        )

    async def refresh(self, interaction: discord.Interaction) -> None:
        self.render()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    def _pick_title(self, key: RulerTitle):  # type: ignore[no-untyped-def]
        async def callback(interaction: discord.Interaction) -> None:
            self.title = key
            await self.refresh(interaction)

        return callback

    async def _pick_epithet(self, interaction: discord.Interaction, value: str) -> None:
        self.epithet = value
        await self.refresh(interaction)

    async def _found(self, interaction: discord.Interaction) -> None:
        assert self.title and self.epithet
        player = await self.services.nation.create(
            self.owner_id,
            self.username,
            self.nation,
            self.guild_id,
            ruler_title=self.title,
            epithet=self.epithet,
        )
        self.stop()
        content = self.services.ctx.content
        announcement = discord.Embed(
            title=f"{player.name} is founded!",
            description=(
                f"All hail {player.ruler_mention}!\n\n"
                f"A new nation rises in the Land of Chonga. It is the "
                f"**{content.age(player.age).tagline or content.age(player.age).name}**, "
                "and it is defended by a small band of slingers.\n\n"
                "**Next steps**\n"
                "• `/claim` collects what your land produces\n"
                "• `/build` adds farms, mills and more\n"
                "• `/train` grows your army, then `/attack` someone\n"
                "• `/help` lists everything"
            ),
            colour=fmt.GREEN,
        )
        message = interaction.message
        if message is not None and message.flags.ephemeral:
            # The setup was private; announce the founding to the channel.
            await interaction.response.edit_message(
                embed=discord.Embed(description=f"{player.name} is founded.", colour=fmt.GREEN),
                view=None,
            )
            await interaction.followup.send(embed=announcement)
        else:
            await interaction.response.edit_message(embed=announcement, view=None)

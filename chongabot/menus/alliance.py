"""The private /alliance menu. It shows only what your role allows.

Not in an alliance: browse and request to join, or found one.
Member: overview, contribute units, leave.
Officer: also handle join requests and kick members.
Owner: also promote, demote, hand over ownership and disband.

Destructive buttons (Leave, Kick, Disband, Make owner) need a second click to confirm.
"""

import contextlib

import discord

from chongabot.domain.errors import GameError
from chongabot.domain.models import ROLE_RANK, Alliance, AllianceRole, Player
from chongabot.menus.base import OwnedView, TextModal
from chongabot.services import Services
from chongabot.views import embeds, fmt

DANGER = discord.ButtonStyle.danger
GREY = discord.ButtonStyle.secondary
GREEN = discord.ButtonStyle.success
BLUE = discord.ButtonStyle.primary


class AllianceMenu(OwnedView):
    def __init__(
        self,
        services: Services,
        player: Player,
        alliance: Alliance | None,
        pending: int | None,
        guild_id: int | None,
    ) -> None:
        super().__init__(player.id)
        self.services = services
        self.guild_id = guild_id
        self.player = player
        self.alliance = alliance
        self.pending = pending  # alliance id of our pending join request
        self.browse_pick: int | None = None
        self.member_pick: int | None = None
        self.request_pick: int | None = None
        self.armed: str | None = None  # destructive action awaiting its second click
        self.notice: str | None = None
        self.browse_cache: list[tuple[int, str, int, int]] = []

    @classmethod
    async def open(cls, services: Services, user_id: int, guild_id: int | None) -> "AllianceMenu":
        player, alliance, pending = await services.alliance.mine(user_id)
        menu = cls(services, player, alliance, pending, guild_id)
        await menu.load_browse()
        menu.render()
        return menu

    async def load_browse(self) -> None:
        if self.alliance is None:
            self.browse_cache = [
                (a.id, a.name, a.members, a.battle_rating)
                for a in await self.services.alliance.browse()
            ]

    async def reload(self) -> None:
        self.player, self.alliance, self.pending = await self.services.alliance.mine(self.player.id)
        if self.alliance is None or self.alliance.member(self.member_pick or 0) is None:
            self.member_pick = None
        if self.alliance is None or all(
            r.player_id != self.request_pick for r in self.alliance.requests
        ):
            self.request_pick = None
        await self.load_browse()

    @property
    def role(self) -> AllianceRole | None:
        return self.player.alliance_role

    def at_least(self, role: AllianceRole) -> bool:
        return self.role is not None and ROLE_RANK[self.role] >= ROLE_RANK[role]

    # --- rendering ------------------------------------------------------------------

    def embed(self) -> discord.Embed:
        content = self.services.ctx.content
        if self.alliance is not None:
            e = embeds.alliance(self.alliance, content)
            e.set_footer(text=f"Your role: {self.role}")
        else:
            lines = [
                f"**{name}** · {members} members · {br:,} BR"
                for _, name, members, br in self.browse_cache[:15]
            ]
            e = discord.Embed(
                title="Alliances",
                description="You're not in an alliance. Ask to join one below, or found your own."
                + ("\n\n" + "\n".join(lines) if lines else "\n\nNo alliances exist yet."),
                colour=fmt.BLUE,
            )
            if self.pending is not None:
                name = next(
                    (n for i, n, *_ in self.browse_cache if i == self.pending), "an alliance"
                )
                e.add_field(name="Pending request", value=f"Waiting for **{name}** to answer.")
        if self.notice:
            e.add_field(name="​", value=self.notice, inline=False)
        return e

    def render(self) -> None:
        self.clear_items()
        if self.alliance is None:
            self._render_outside()
        else:
            self._render_inside(self.alliance)

    def _render_outside(self) -> None:
        if self.browse_cache:
            self.select(
                "Pick an alliance to join",
                [
                    discord.SelectOption(
                        label=name,
                        value=str(aid),
                        description=f"{members} members · {br:,} BR",
                        default=aid == self.browse_pick,
                    )
                    for aid, name, members, br in self.browse_cache
                ],
                self._pick_browse,
                row=0,
            )
        self.button(
            "Request to join", self._request, style=GREEN, row=1, disabled=self.browse_pick is None
        )
        self.button("Found an alliance", self._create, style=BLUE, row=1)
        if self.pending is not None:
            self.button("Cancel my request", self._cancel_request, row=1)
        self.button("Refresh", self._on_refresh, row=1)

    def _render_inside(self, a: Alliance) -> None:
        me = self.player
        if self.at_least("officer"):
            others = [m for m in a.members if m.id != me.id]
            if others:
                self.select(
                    "Pick a member",
                    [
                        discord.SelectOption(
                            label=m.name,
                            value=str(m.id),
                            description=f"{m.role} · {m.battle_rating} BR",
                            default=m.id == self.member_pick,
                        )
                        for m in others
                    ],
                    self._pick_member,
                    row=0,
                )
                picked = a.member(self.member_pick or 0)
                none = picked is None
                assert self.role
                if self.role == "owner":
                    self.button(
                        "Promote",
                        self._role_action("officer"),
                        row=1,
                        disabled=none or picked is None or picked.role != "member",
                    )
                    self.button(
                        "Demote",
                        self._role_action("member"),
                        row=1,
                        disabled=none or picked is None or picked.role != "officer",
                    )
                    self.button(
                        self._armed_label("transfer", "Make owner"),
                        self._role_action("owner"),
                        row=1,
                        style=DANGER if self.armed == "transfer" else GREY,
                        disabled=none,
                    )
                can_kick = picked is not None and ROLE_RANK[picked.role] < ROLE_RANK[self.role]
                self.button(
                    self._armed_label("kick", "Kick"),
                    self._kick,
                    row=1,
                    style=DANGER,
                    disabled=not can_kick,
                )

            if a.requests:
                self.select(
                    f"Join requests ({len(a.requests)})",
                    [
                        discord.SelectOption(
                            label=r.name,
                            value=str(r.player_id),
                            description=f"{r.battle_rating} BR",
                            default=r.player_id == self.request_pick,
                        )
                        for r in a.requests
                    ],
                    self._pick_request,
                    row=2,
                )
                no_pick = self.request_pick is None
                self.button("Accept", self._answer(True), row=3, style=GREEN, disabled=no_pick)
                self.button("Reject", self._answer(False), row=3, style=DANGER, disabled=no_pick)

        self.button("Contribute units", self._contribute, row=4, style=BLUE)
        self.button("Refresh", self._on_refresh, row=4)
        if self.role == "owner":
            self.button(self._armed_label("disband", "Disband"), self._disband, row=4, style=DANGER)
        else:
            self.button(self._armed_label("leave", "Leave"), self._leave, row=4, style=DANGER)

    def _armed_label(self, key: str, label: str) -> str:
        return "Click again to confirm" if self.armed == key else label

    def _arm(self, key: str) -> bool:
        """First click arms the action, second click runs it. True when it should run."""
        if self.armed == key:
            self.armed = None
            return True
        self.armed = key
        return False

    async def refresh(self, interaction: discord.Interaction, reload: bool = True) -> None:
        if reload:
            await self.reload()
        self.render()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def after_error(self, interaction: discord.Interaction) -> None:
        self.armed = None
        await self.reload()
        self.render()
        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(embed=self.embed(), view=self)

    # --- outside callbacks --------------------------------------------------------------

    async def _pick_browse(self, interaction: discord.Interaction, value: str) -> None:
        self.browse_pick, self.notice = int(value), None
        await self.refresh(interaction, reload=False)

    async def _request(self, interaction: discord.Interaction) -> None:
        assert self.browse_pick is not None
        a = await self.services.alliance.request_join(self.player.id, self.browse_pick)
        self.notice = f"Asked to join **{a.name}**. Its officers will see your request."
        await self.refresh(interaction)

    async def _cancel_request(self, interaction: discord.Interaction) -> None:
        await self.services.alliance.cancel_request(self.player.id)
        self.notice = "Request cancelled."
        await self.refresh(interaction)

    async def _create(self, interaction: discord.Interaction) -> None:
        async def submitted(modal_interaction: discord.Interaction, name: str) -> None:
            a = await self.services.alliance.create(self.player.id, name, self.guild_id)
            self.notice = f"You founded **{a.name}**."
            await self.refresh(modal_interaction)

        await interaction.response.send_modal(
            TextModal("Found an alliance", "Alliance name", submitted, max_length=24)
        )

    async def _on_refresh(self, interaction: discord.Interaction) -> None:
        self.notice, self.armed = None, None
        await self.refresh(interaction)

    # --- inside callbacks -----------------------------------------------------------------

    async def _pick_member(self, interaction: discord.Interaction, value: str) -> None:
        self.member_pick, self.armed, self.notice = int(value), None, None
        await self.refresh(interaction, reload=False)

    async def _pick_request(self, interaction: discord.Interaction, value: str) -> None:
        self.request_pick, self.notice = int(value), None
        await self.refresh(interaction, reload=False)

    def _picked_name(self) -> str:
        m = self.alliance.member(self.member_pick or 0) if self.alliance else None
        return m.name if m else "them"

    def _role_action(self, role: AllianceRole):  # type: ignore[no-untyped-def]
        async def callback(interaction: discord.Interaction) -> None:
            assert self.member_pick is not None
            if role == "owner" and not self._arm("transfer"):
                await self.refresh(interaction, reload=False)
                return
            name = self._picked_name()
            await self.services.alliance.set_role(self.player.id, self.member_pick, role)
            self.notice = {
                "officer": f"{name} is now an officer.",
                "member": f"{name} is now a member.",
                "owner": f"{name} now owns the alliance. You're an officer.",
            }[role]
            await self.refresh(interaction)

        return callback

    async def _kick(self, interaction: discord.Interaction) -> None:
        assert self.member_pick is not None
        if not self._arm("kick"):
            await self.refresh(interaction, reload=False)
            return
        name = self._picked_name()
        await self.services.alliance.kick(self.player.id, self.member_pick)
        self.notice, self.member_pick = f"Kicked {name}.", None
        await self.refresh(interaction)

    def _answer(self, accept: bool):  # type: ignore[no-untyped-def]
        async def callback(interaction: discord.Interaction) -> None:
            assert self.request_pick is not None
            applicant = await self.services.alliance.answer_request(
                self.player.id, self.request_pick, accept
            )
            self.notice = (
                f"Welcome, **{applicant.name}**." if accept else f"Rejected {applicant.name}."
            )
            self.request_pick = None
            await self.refresh(interaction)

        return callback

    async def _contribute(self, interaction: discord.Interaction) -> None:
        content = self.services.ctx.content
        army = ", ".join(
            content.units[u].name for u, n in self.player.units.items() if n and u in content.units
        )
        if not army:
            raise GameError("You have no units to contribute. Train some with `/train`.")

        async def submitted(modal_interaction: discord.Interaction, text: str) -> None:
            unit, _, amount = text.rpartition(" ")
            amount = amount.replace(",", "").lower()
            if not unit or not (amount == "max" or amount.isdigit()):
                raise GameError("Type a unit and an amount, like `Spearman 50` or `Archer max`.")
            count: int | str = "max" if amount == "max" else int(amount)
            name, n = await self.services.alliance.contribute(
                self.player.id,
                unit,
                count,  # type: ignore[arg-type]
            )
            self.notice = (
                f"Sent **{fmt.num(n)} × {name}** to the alliance army. "
                "Your share of boss loot grows with what you contribute."
            )
            await self.refresh(modal_interaction)

        await interaction.response.send_modal(
            TextModal(
                "Contribute units",
                "Unit and amount",
                submitted,
                placeholder=f"e.g. {army.split(', ')[0]} 50, or max"[:100],
                max_length=48,
            )
        )

    async def _leave(self, interaction: discord.Interaction) -> None:
        if not self._arm("leave"):
            await self.refresh(interaction, reload=False)
            return
        name = await self.services.alliance.leave(self.player.id)
        self.notice = f"You left **{name}**."
        await self.refresh(interaction)

    async def _disband(self, interaction: discord.Interaction) -> None:
        if not self._arm("disband"):
            await self.refresh(interaction, reload=False)
            return
        name = await self.services.alliance.disband(self.player.id)
        self.notice = f"**{name}** has been disbanded."
        await self.refresh(interaction)

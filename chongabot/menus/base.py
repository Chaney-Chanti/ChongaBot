"""Shared pieces for interactive menus."""

import contextlib
from collections.abc import Awaitable, Callable
from typing import Any

import discord
import structlog

from chongabot.domain.errors import GameError

log = structlog.get_logger(__name__)

Callback = Callable[[discord.Interaction], Awaitable[None]]


async def send_error(interaction: discord.Interaction, message: str) -> None:
    embed = discord.Embed(description=message, colour=discord.Colour.red())
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


class OwnedView(discord.ui.View):
    """A view only its owner may click. Slash menus are ephemeral anyway, but menus
    opened with a c! prefix command are public, so this check matters there."""

    def __init__(self, owner_id: int, timeout: float | None = 300) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.message: discord.Message | discord.InteractionMessage | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await send_error(interaction, "This menu isn't yours. Open your own with the command.")
            return False
        return True

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any]
    ) -> None:
        if isinstance(error, GameError):
            await send_error(interaction, error.message)
            await self.after_error(interaction)
            return
        log.error("menu_crashed", view=type(self).__name__, exc_info=error)
        await send_error(interaction, "Something went wrong on our side. It's been logged.")

    async def after_error(self, interaction: discord.Interaction) -> None:
        """Hook to refresh the menu after a GameError (e.g. you can no longer afford it)."""

    async def on_timeout(self) -> None:
        if self.message is not None:
            for child in self.children:
                if isinstance(child, discord.ui.Button | discord.ui.Select):
                    child.disabled = True
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)

    # --- helpers for views that rebuild their components on every render ---

    def button(
        self,
        label: str,
        callback: Callback,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        row: int = 0,
        disabled: bool = False,
        emoji: str | None = None,
    ) -> discord.ui.Button["OwnedView"]:
        b: discord.ui.Button[OwnedView] = discord.ui.Button(
            label=label, style=style, row=row, disabled=disabled, emoji=emoji
        )
        b.callback = callback  # type: ignore[method-assign,assignment]
        self.add_item(b)
        return b

    def select(
        self,
        placeholder: str,
        options: list[discord.SelectOption],
        callback: Callable[[discord.Interaction, str], Awaitable[None]],
        *,
        row: int = 0,
    ) -> discord.ui.Select["OwnedView"]:
        s: discord.ui.Select[OwnedView] = discord.ui.Select(
            placeholder=placeholder, options=options[:25], row=row
        )

        async def on_select(interaction: discord.Interaction) -> None:
            await callback(interaction, s.values[0])

        s.callback = on_select  # type: ignore[method-assign]
        self.add_item(s)
        return s


class ConfirmView(OwnedView):
    """Confirm / Cancel. `on_confirm` returns the embed to show afterwards."""

    def __init__(
        self,
        owner_id: int,
        on_confirm: Callable[[discord.Interaction], Awaitable[discord.Embed]],
        confirm_label: str = "Confirm",
    ) -> None:
        super().__init__(owner_id, timeout=120)
        self.on_confirm = on_confirm
        self.button(confirm_label, self._confirm, style=discord.ButtonStyle.success)
        self.button("Cancel", self._cancel)

    async def _confirm(self, interaction: discord.Interaction) -> None:
        embed = await self.on_confirm(interaction)
        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)

    async def _cancel(self, interaction: discord.Interaction) -> None:
        self.stop()
        await interaction.response.edit_message(
            embed=discord.Embed(description="Cancelled."), view=None
        )


class TextModal(discord.ui.Modal):
    """A one-field modal that hands the submitted text to a callback."""

    def __init__(
        self,
        title: str,
        label: str,
        on_submit: Callable[[discord.Interaction, str], Awaitable[None]],
        *,
        placeholder: str = "",
        max_length: int = 32,
        default: str = "",
    ) -> None:
        super().__init__(title=title)
        self.field: discord.ui.TextInput[TextModal] = discord.ui.TextInput(
            label=label, placeholder=placeholder, max_length=max_length, default=default
        )
        self.add_item(self.field)
        self._on_submit = on_submit

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._on_submit(interaction, self.field.value.strip())

    async def on_error(  # type: ignore[override]
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, GameError):
            await send_error(interaction, error.message)
        else:
            log.error("modal_crashed", exc_info=error)
            await send_error(interaction, "Something went wrong on our side. It's been logged.")

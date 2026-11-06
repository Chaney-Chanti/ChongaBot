"""The private buy menu behind /build, /train and /research.

Pick an item, adjust the amount (−10 −1 +1 +10, Max, or type one), and Confirm. The
cost line marks anything you're short of, and Confirm stays disabled until you can pay.
The menu stays open after a purchase so you can keep shopping.
"""

import contextlib
from typing import Literal

import discord

from chongabot.content.models import Building, Research, Unit
from chongabot.domain.errors import GameError
from chongabot.domain.models import Player
from chongabot.menus.base import OwnedView, TextModal
from chongabot.rules import economy
from chongabot.rules.economy import Cost
from chongabot.services import Services
from chongabot.views import fmt

Kind = Literal["building", "unit", "research"]
Item = Building | Unit | Research

TITLES: dict[Kind, str] = {
    "building": "Build",
    "unit": "Train",
    "research": "Research",
}
VERBS: dict[Kind, str] = {"building": "Built", "unit": "Trained", "research": "Researched"}


class BuyMenu(OwnedView):
    def __init__(
        self, services: Services, player: Player, kind: Kind, selected: str | None = None
    ) -> None:
        super().__init__(player.id)
        self.services = services
        self.player = player
        self.kind = kind
        self.qty = 1
        self.notice: str | None = None
        items = self.items()
        self.selected: str | None = selected if selected in {i.id for i in items} else None
        if self.selected is None and items:
            self.selected = items[0].id
        self.render()

    # --- state --------------------------------------------------------------------

    @property
    def content(self):  # type: ignore[no-untyped-def]
        return self.services.ctx.content

    def items(self) -> list[Item]:
        c, p = self.content, self.player
        found: list[Item]
        if self.kind == "building":
            found = list(economy.buildable(p, c))
        elif self.kind == "unit":
            found = list(economy.trainable(p, c))
        else:
            found = list(economy.researchable(p, c))
        return found[:25]

    def item(self) -> Item | None:
        return next((i for i in self.items() if i.id == self.selected), None)

    def cost_for(self, item: Item, n: int) -> Cost:
        c, p = self.content, self.player
        if isinstance(item, Building):
            return economy.building_cost(p, c, item, n)
        if isinstance(item, Unit):
            return economy.unit_cost(p, c, item, n)
        return economy.research_cost(p, c, item)

    def max_for(self, item: Item) -> int:
        c, p = self.content, self.player
        if isinstance(item, Building):
            return economy.max_buildings(p, c, item)
        if isinstance(item, Unit):
            return economy.max_units(p, c, item)
        return int(economy.affordable(p.resources, self.cost_for(item, 1)))

    # --- rendering ----------------------------------------------------------------

    def embed(self) -> discord.Embed:
        e = discord.Embed(title=TITLES[self.kind], colour=fmt.GOLD)
        item = self.item()
        if item is None:
            e.description = {
                "building": "Nothing to build right now.",
                "unit": "No units to train in this age.",
                "research": "You've researched everything available. Advance with `/nextage`.",
            }[self.kind]
            return e

        p = self.player
        lines = [f"## {item.name}"]
        if isinstance(item, Building):
            owned = p.buildings.get(item.id, 0)
            if item.kind == "production" and item.produces:
                lines.append(
                    f"+{item.yield_per_hour} {fmt.EMOJI[item.produces]} per hour each, "
                    "before bonuses"
                )
            else:
                lines.append(f"Defends your nation · {item.attack} attack · {item.hp} hp each")
            lines.append(f"You own **{owned}**. Each one makes the next pricier.")
        elif isinstance(item, Unit):
            lines.append(fmt.unit_line(item))
            lines.append(fmt.counters_line(item, self.content))
            lines.append(f"You have **{fmt.num(p.units.get(item.id, 0))}**.")
        else:
            lines.append(item.desc or "")

        cost = self.cost_for(item, self.qty)
        amount = "" if self.kind == "research" else f"**{fmt.num(self.qty)}** for "
        lines.append(f"\n{amount}{fmt.cost(cost, p.resources)}")
        missing = economy.shortfall(p.resources, cost)
        if missing:
            lines.append(f"You're short {fmt.cost(missing)}.")
        e.description = "\n".join(lines)

        e.add_field(
            name="Your resources",
            value=" · ".join(f"{fmt.EMOJI[r]} {fmt.num(v)}" for r, v in p.resources.items() if v)
            or "None",
            inline=False,
        )
        if self.notice:
            e.add_field(name="​", value=self.notice, inline=False)
        return e

    def render(self) -> None:
        self.clear_items()
        items = self.items()
        if not items:
            return
        options = [
            discord.SelectOption(
                label=i.name,
                value=i.id,
                description=fmt.plain_cost(self.cost_for(i, 1))[:100],
                default=i.id == self.selected,
            )
            for i in items
        ]
        self.select(f"Choose a {self.kind}", options, self._on_select, row=0)

        item = self.item()
        if item is None:
            return
        if self.kind != "research":
            for label, delta in (("−10", -10), ("−1", -1), ("+1", 1), ("+10", 10)):
                self.button(label, self._delta(delta), row=1)
            self.button("Max", self._max, row=2, style=discord.ButtonStyle.primary)
            self.button("Custom…", self._custom, row=2)

        affordable = economy.affordable(self.player.resources, self.cost_for(item, self.qty))
        self.button(
            "Confirm",
            self._confirm,
            row=2,
            style=discord.ButtonStyle.success,
            disabled=not affordable,
        )

    async def refresh(self, interaction: discord.Interaction) -> None:
        self.render()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    # --- callbacks ----------------------------------------------------------------

    async def _on_select(self, interaction: discord.Interaction, value: str) -> None:
        self.selected, self.qty, self.notice = value, 1, None
        await self.refresh(interaction)

    def _delta(self, delta: int):  # type: ignore[no-untyped-def]
        async def callback(interaction: discord.Interaction) -> None:
            self.qty = max(1, self.qty + delta)
            self.notice = None
            await self.refresh(interaction)

        return callback

    async def _max(self, interaction: discord.Interaction) -> None:
        item = self.item()
        if item:
            self.qty = max(1, self.max_for(item))
        self.notice = None
        await self.refresh(interaction)

    async def _custom(self, interaction: discord.Interaction) -> None:
        async def submitted(modal_interaction: discord.Interaction, text: str) -> None:
            cleaned = text.replace(",", "").replace("_", "").strip().lower()
            if cleaned == "max":
                item = self.item()
                self.qty = max(1, self.max_for(item)) if item else 1
            elif cleaned.isdigit() and int(cleaned) > 0:
                self.qty = min(int(cleaned), 1_000_000)
            else:
                raise GameError("Type a whole number like `25`, or `max`.")
            self.notice = None
            await self.refresh(modal_interaction)

        await interaction.response.send_modal(
            TextModal(
                "How many?",
                "Amount",
                submitted,
                placeholder="e.g. 25, or max",
                max_length=9,
                default=str(self.qty),
            )
        )

    async def _confirm(self, interaction: discord.Interaction) -> None:
        item = self.item()
        if item is None:
            return
        uid, econ = self.player.id, self.services.economy
        if self.kind == "building":
            bought = await econ.build(uid, item.id, self.qty)
        elif self.kind == "unit":
            bought = await econ.train(uid, item.id, self.qty)
        else:
            bought = await econ.research(uid, item.id)
        self.player = bought.player
        what = bought.item if bought.count == 1 else f"{fmt.num(bought.count)} × {bought.item}"
        self.notice = f"{VERBS[self.kind]} **{what}** for {fmt.cost(bought.cost)}."
        if self.kind == "research":
            remaining = self.items()
            self.selected = remaining[0].id if remaining else None
        self.qty = 1
        await self.refresh(interaction)

    async def after_error(self, interaction: discord.Interaction) -> None:
        # Resources may have changed elsewhere (a claim, an attack). Show the real state.
        self.player = await self.services.nation.get(self.player.id)
        self.render()
        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(embed=self.embed(), view=self)

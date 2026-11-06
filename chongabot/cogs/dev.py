"""Owner-only testing commands. Loaded only when DEV_MODE=true."""

import discord
from discord import app_commands
from discord.ext import commands

from chongabot.bot import ChongaBot, Ctx
from chongabot.cogs.nation import nation_choices
from chongabot.domain.errors import GameError
from chongabot.services.dev import DevService, is_fake
from chongabot.views import embeds, fmt

USAGE = """`/dev spawn <name> [age] [army]` · a fake nation to fight
  army like `spearman:100, archer:50`, or a copy of yours
`/dev give <resource|all> <amount> [nation]` · free resources
`/dev units <unit> <count> [nation]` · add units (negative removes)
`/dev hero <hero> [nation]` · grant a hero, as if found exploring
`/dev reset [nation]` · clear cooldowns (incl. hero swap) and shield
`/dev age <age> [nation]` · jump to an age
`/dev rating <br> [nation]` · set battle rating
`/dev attackme <nation>` · a fake nation attacks you
`/dev wipe` · delete every fake nation"""


class Dev(commands.Cog):
    """Testing tools for the bot owner."""

    def __init__(self, bot: ChongaBot) -> None:
        self.bot = bot

    async def cog_check(self, ctx: Ctx) -> bool:  # type: ignore[override]
        if not await self.bot.is_owner(ctx.author):
            raise commands.CheckFailure("Only the bot owner can use dev commands.")
        return True

    @property
    def svc(self) -> DevService:
        return self.bot.services.dev

    async def target(self, ctx: Ctx, nation: str | None) -> int:
        if nation is None:
            return ctx.author.id
        return (await self.bot.services.nation.find(nation)).id

    async def done(self, ctx: Ctx, message: str) -> None:
        await ctx.send(embed=embeds.success(message), ephemeral=True)

    @commands.hybrid_group(invoke_without_command=True, description="Owner testing tools")
    async def dev(self, ctx: Ctx) -> None:
        await ctx.send(
            embed=discord.Embed(title="Dev commands", description=USAGE, colour=fmt.BLUE),
            ephemeral=True,
        )

    @dev.command(description="Create a fake nation to fight")
    @app_commands.describe(
        age="Defaults to your age",
        army="e.g. spearman:100, archer:50. Defaults to a copy of your army",
    )
    async def spawn(
        self, ctx: Ctx, name: str, age: str | None = None, *, army: str | None = None
    ) -> None:
        p = await self.svc.spawn(ctx.author.id, name, age, army)
        await ctx.send(
            embed=embeds.success(
                f"Spawned **{p.name}** (id {p.id}), ruled by {p.ruler}.\n"
                f"{self.bot.content.age(p.age).name} Age · {p.battle_rating} BR\n"
                f"{fmt.army(p.units, self.bot.content)}"
            ),
            ephemeral=True,
        )

    @dev.command(description="Give free resources")
    async def give(
        self, ctx: Ctx, resource: str, amount: int, *, nation: str | None = None
    ) -> None:
        p = await self.svc.give(await self.target(ctx, nation), resource, amount)
        await self.done(ctx, f"Gave {fmt.num(amount)} {resource} to **{p.name}**.")

    @dev.command(description="Grant a hero, as if found while exploring")
    async def hero(self, ctx: Ctx, hero: str, *, nation: str | None = None) -> None:
        name, p = await self.svc.hero(await self.target(ctx, nation), hero)
        await self.done(ctx, f"**{p.name}** found **{name}**. Appoint them with `/hero`.")

    @dev.command(description="Add or remove units")
    async def units(self, ctx: Ctx, unit: str, count: int, *, nation: str | None = None) -> None:
        name, p = await self.svc.units(await self.target(ctx, nation), unit, count)
        await self.done(ctx, f"**{p.name}** now has:\n{fmt.army(p.units, self.bot.content)}")
        del name

    @dev.command(description="Clear cooldowns and shield")
    async def reset(self, ctx: Ctx, *, nation: str | None = None) -> None:
        await self.svc.reset(await self.target(ctx, nation))
        await self.done(ctx, "Cooldowns and shield cleared.")

    @dev.command(name="age", description="Jump to an age")
    async def age_(self, ctx: Ctx, age: str, *, nation: str | None = None) -> None:
        name = await self.svc.set_age(await self.target(ctx, nation), age)
        await self.done(ctx, f"Now in the **{name} Age**.")

    @dev.command(description="Set battle rating")
    async def rating(self, ctx: Ctx, rating: int, *, nation: str | None = None) -> None:
        await self.svc.set_rating(await self.target(ctx, nation), rating)
        await self.done(ctx, f"Battle rating set to **{rating}**.")

    @dev.command(description="Make a fake nation attack you")
    async def attackme(self, ctx: Ctx, *, nation: str) -> None:
        attacker = await self.bot.services.nation.find(nation)
        if not is_fake(attacker.id):
            raise GameError("Only fake nations (made with `/dev spawn`) can be made to attack.")
        report = await self.svc.attack_me(ctx.author.id, attacker.id)
        await ctx.send(embed=embeds.attack(report, self.bot.content))

    @dev.command(description="Delete every fake nation")
    async def wipe(self, ctx: Ctx) -> None:
        n = await self.svc.wipe()
        await self.done(ctx, f"Deleted {n} fake nation{'s' if n != 1 else ''}.")

    @hero.autocomplete("hero")
    async def _hero_ac(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        c = current.lower()
        return [
            app_commands.Choice(name=f"{h.name} ({self.bot.content.age(h.age).name})", value=h.id)
            for h in self.bot.content.heroes.values()
            if c in h.name.lower()
        ][:25]

    @hero.autocomplete("nation")
    @give.autocomplete("nation")
    @units.autocomplete("nation")
    @reset.autocomplete("nation")
    @age_.autocomplete("nation")
    @rating.autocomplete("nation")
    @attackme.autocomplete("nation")
    async def _nation_ac(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await nation_choices(self.bot, current)

    @age_.autocomplete("age")
    @spawn.autocomplete("age")
    async def _age_ac(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=a.name, value=a.id)
            for a in self.bot.content.ages
            if current.lower() in a.name.lower()
        ]

    @units.autocomplete("unit")
    async def _unit_ac(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        c = current.lower()
        return [
            app_commands.Choice(name=f"{u.name} ({self.bot.content.age(u.age).name})", value=u.id)
            for u in self.bot.content.units.values()
            if c in u.name.lower()
        ][:25]

    @give.autocomplete("resource")
    async def _res_ac(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=r, value=r)
            for r in ("all", "food", "timber", "metal", "wealth", "knowledge", "oil")
            if current.lower() in r
        ]


async def setup(bot: ChongaBot) -> None:
    await bot.add_cog(Dev(bot))

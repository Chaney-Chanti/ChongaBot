"""Small text formatting helpers shared by embeds and menus."""

from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import datetime

from chongabot.content import Content
from chongabot.content.models import (
    RESOURCES,
    ROLES,
    AttackMultiplier,
    ClaimMultiplier,
    CostMultiplier,
    Effect,
    RateMultiplier,
    Resource,
    Unit,
    UnlockUnit,
    ValueMultiplier,
)

EMOJI: dict[Resource, str] = {
    "food": "🌾",
    "timber": "🪵",
    "metal": "⛏️",
    "wealth": "💰",
    "knowledge": "📜",
    "oil": "🛢️",
}

GOLD = 0xE8B04B
GREEN = 0x3BA55C
RED = 0xED4245
BLUE = 0x5865F2


def num(n: float) -> str:
    """1234 -> 1,234; 1_234_567 -> 1.23M."""
    n = int(n)
    for size, suffix in ((1_000_000_000, "B"), (1_000_000, "M")):
        if abs(n) >= size:
            return f"{n / size:.2f}".rstrip("0").rstrip(".") + suffix
    return f"{n:,}"


def cost(c: Mapping[Resource, int], have: Mapping[Resource, int] | None = None) -> str:
    """`150 🪵, 50 ⛏️`, noting how much of each `have` can't cover."""
    if not c:
        return "free"
    parts = []
    for r in RESOURCES:
        if v := c.get(r, 0):
            short = v - have.get(r, 0) if have is not None else 0
            parts.append(f"{num(v)} {EMOJI[r]}" + (f" ({num(short)} short)" if short > 0 else ""))
    return ", ".join(parts)


def plain_cost(c: Mapping[Resource, int]) -> str:
    """Cost for select-menu descriptions, which can't render custom formatting."""
    return ", ".join(f"{num(v)} {r}" for r in RESOURCES if (v := c.get(r, 0))) or "free"


def width(text: str) -> int:
    """Columns `text` takes in a monospace block: emoji are two wide, variation selectors zero."""
    return sum(
        0 if c == "\ufe0f" else 2 if ord(c) >= 0x1F000 or 0x2600 <= ord(c) <= 0x27BF else 1
        for c in text
    )


def resource(r: Resource) -> str:
    return f"{EMOJI[r]} {r.capitalize()}"


def clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def table(
    rows: Sequence[Sequence[str]],
    header: Sequence[str] | None = None,
    right: Collection[int] = (),
) -> str:
    """Rows as a monospace code block with padded columns, so they line up in Discord.

    Code blocks don't render mentions, bold or timestamps, so cells are plain text.
    """
    every = ([list(header)] if header else []) + [list(r) for r in rows]
    if not every:
        return ""
    widths = [max(width(r[i]) for r in every) for i in range(len(every[0]))]

    def line(r: list[str]) -> str:
        cells = (
            " " * (w - width(c)) + c if i in right else c + " " * (w - width(c))
            for i, (c, w) in enumerate(zip(r, widths, strict=True))
        )
        return "  ".join(cells).rstrip()

    lines = [line(r) for r in every]
    if header:
        lines.insert(1, "  ".join("-" * w for w in widths))
    return "```\n" + "\n".join(lines) + "\n```"


def ts(when: datetime, style: str = "R") -> str:
    return f"<t:{int(when.timestamp())}:{style}>"


def counters_line(unit: Unit, content: Content) -> str:
    beats = content.counters[unit.role]
    beaten_by = next(r for r, t in content.counters.items() if t == unit.role)
    return f"Strong vs {beats}, weak vs {beaten_by}"


def unit_line(unit: Unit) -> str:
    return f"{unit.role.capitalize()} · {num(unit.attack)} attack · {num(unit.hp)} hp"


def army(units: Mapping[str, int], content: Content, limit: int = 12) -> str:
    rows = [(content.units[u], n) for u, n in units.items() if n > 0 and u in content.units]
    rows.sort(key=lambda r: (-content.age_index(r[0].age), -r[1]))
    if not rows:
        return "No units"
    cells = [[clip(u.name, 22), num(n), u.role] for u, n in rows[:limit]]
    if len(rows) > limit:
        cells.append([f"and {len(rows) - limit} more", "", ""])
    return table(cells, right={1})


def _pct(value: float) -> str:
    return f"{round(abs(value - 1) * 100):g}%"


def _roles(roles: tuple[str, ...]) -> str:
    if set(roles) == set(ROLES):
        return "All units"
    if set(ROLES) - set(roles) == {"defense"}:
        return "All units except defenses"
    names = {"defense": "Defenses"}
    return " and ".join(names.get(r, r.capitalize()) for r in roles)


def effect_text(effect: Effect, content: Content) -> str:
    """A bonus in plain words, e.g. "Cavalry +10% attack"."""
    match effect:
        case RateMultiplier(resources=res):
            parts = []
            for r, v in res.items():
                label = "every resource" if r == "all" else f"{EMOJI[r]} {r}"
                parts.append(f"{'+' if v >= 1 else '−'}{_pct(v)} {label}")
            return ", ".join(parts)
        case ClaimMultiplier(value=v):
            return f"Every claim gives {_pct(v)} more"
        case CostMultiplier(kind=kind, value=v):
            what = {
                "building_cost_multiplier": "Buildings cost",
                "unit_cost_multiplier": "Units cost",
                "research_cost_multiplier": "Research costs",
            }[kind]
            return f"{what} {_pct(v)} {'less' if v < 1 else 'more'}"
        case AttackMultiplier(kind="attack_multiplier", value=v, roles=roles):
            return f"{_roles(roles)} +{_pct(v)} attack"
        case AttackMultiplier(kind="enemy_attack_multiplier", value=v, roles=roles):
            if set(roles) == set(content.counters):
                return f"Enemies deal {_pct(v)} less damage"
            verb = "deals" if len(roles) == 1 else "deal"
            return f"Enemy {_roles(roles).lower()} {verb} {_pct(v)} less damage"
        case ValueMultiplier(kind="tribute_multiplier", value=v):
            return f"+{_pct(v)} tribute from victories"
        case ValueMultiplier(kind="exploration_reward_multiplier", value=v):
            return f"Exploration rewards +{_pct(v)}"
        case UnlockUnit(unit=unit_id):
            unit = content.units.get(unit_id)
            return f"Unlocks the {unit.name if unit else unit_id}"
    return "A mysterious bonus"


def effects_text(effects: Iterable[Effect], content: Content) -> str:
    return "; ".join(effect_text(e, content) for e in effects)

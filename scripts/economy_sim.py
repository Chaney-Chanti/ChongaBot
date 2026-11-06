"""Pacing check: how long an active player takes to reach each age.

Reads the real content YAML. The simulated player claims every N hours, puts
ARMY_SHARE of income into the army (modelled as spent), and greedily buys the
age-up, then research, then the production building with the best payback.

    uv run python scripts/economy_sim.py            # claim every 2, 4, 12 and 24 h
    uv run python scripts/economy_sim.py 6          # claim every 6 h
"""

import sys

from chongabot.content import Content, load_content
from chongabot.content.models import RESOURCES, RateMultiplier

ARMY_SHARE = 0.35


def afford(have: dict[str, float], cost: dict[str, float]) -> bool:
    return all(have.get(r, 0) >= c for r, c in cost.items())


def pay(have: dict[str, float], cost: dict[str, float]) -> None:
    for r, c in cost.items():
        have[r] -= c


def simulate(
    c: Content, claim_every: float, days: int = 45
) -> tuple[dict[str, float], dict[str, int]]:
    s = c.settings
    production = {b.id: b for b in c.buildings.values() if b.kind == "production"}
    age = c.ages[0].id
    have: dict[str, float] = {r: float(s.starting_resources.get(r, 0)) for r in RESOURCES}
    counts = dict.fromkeys(production, 0)
    bonus = dict.fromkeys(RESOURCES, 1.0)
    researched: set[str] = set()
    reached = {age: 0.0}

    def rates() -> dict[str, float]:
        mult = c.age(age).production_multiplier
        out = {}
        for r in RESOURCES:
            base = s.base_rates.get(r, 0)
            base += sum(
                (b.yield_per_hour or 0) * counts[b.id]
                for b in production.values()
                if b.produces == r
            )
            out[r] = base * mult * bonus[r]
        return out

    for step in range(int(days * 24 / claim_every)):
        for r, v in rates().items():
            have[r] += v * claim_every * (1 - ARMY_SHARE)
        bought = True
        while bought:
            bought = False
            nxt = c.next_age(age)
            if nxt and afford(have, dict(nxt.advance_cost)):
                pay(have, dict(nxt.advance_cost))
                age = nxt.id
                reached[age] = (step + 1) * claim_every / 24
                bought = True
                continue
            for res in c.research.values():
                if res.id in researched or res.age != age or not afford(have, dict(res.cost)):
                    continue
                pay(have, dict(res.cost))
                researched.add(res.id)
                for e in res.effects:
                    if isinstance(e, RateMultiplier):
                        for r, m in e.resources.items():
                            bonus[r] = bonus.get(r, 1.0) * m
                bought = True
            options = []
            for b in production.values():
                if c.age_index(b.age) > c.age_index(age):
                    continue
                cost = {r: v * s.building_cost_growth ** counts[b.id] for r, v in b.cost.items()}
                score = sum(cost.values()) / (b.yield_per_hour or 1)
                if b.produces == "knowledge":
                    score *= 0.6  # knowledge gates the age-ups, so value it more
                options.append((score, b.id, cost))
            if options:
                _, best, cost = min(options)
                if afford(have, cost):
                    pay(have, cost)
                    counts[best] += 1
                    bought = True
    return reached, counts


def main() -> None:
    content = load_content()
    habits = [float(sys.argv[1])] if len(sys.argv) > 1 else [2, 4, 12, 24]
    print(
        f"{'claims every':>13}  "
        + "  ".join(f"{a.name:>13}" for a in content.ages[1:])
        + "  most of one building"
    )
    for every in habits:
        reached, counts = simulate(content, every)
        days = [
            f"day {reached[a.id]:5.1f}" if a.id in reached else "    -    "
            for a in content.ages[1:]
        ]
        print(
            f"{every:>11g} h  "
            + "  ".join(f"{d:>13}" for d in days)
            + f"  {max(counts.values()):>5}"
        )


if __name__ == "__main__":
    main()

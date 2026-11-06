"""Derive attack/hp from cost so every unit in an age is equally cost-efficient.

Lanchester-style strength of a budget B spent on a unit with cost c is
(B/c)^2 * attack * hp, so we fix attack*hp = k_age * c^2 and split it by role:
hp = ratio * attack.
"""

import math

K = {"ancient": 0.03, "medieval": 0.045, "enlightenment": 0.0675, "modern": 0.10, "space": 0.15}
RATIO = {"melee": 3.0, "ranged": 1.2, "cavalry": 2.0, "siege": 0.6, "defense": 5.0}

UNITS = {
    "ancient": [
        ("slinger", "ranged", {"food": 35}),
        ("clubman", "melee", {"food": 30, "timber": 10}),
        ("spearman", "melee", {"food": 40, "metal": 25}),
        ("archer", "ranged", {"food": 40, "timber": 25}),
        ("horseman", "cavalry", {"food": 50, "wealth": 30}),
        ("catapult", "siege", {"timber": 60, "metal": 40}),
    ],
    "medieval": [
        ("knight", "melee", {"food": 100, "metal": 80, "wealth": 20}),
        ("crossbowman", "ranged", {"food": 80, "timber": 50, "metal": 30}),
        ("lancer", "cavalry", {"food": 120, "metal": 60, "wealth": 40}),
        ("trebuchet", "siege", {"timber": 160, "metal": 100}),
    ],
    "enlightenment": [
        ("grenadier", "melee", {"food": 250, "metal": 200, "wealth": 50}),
        ("minuteman", "ranged", {"food": 220, "metal": 130, "wealth": 50}),
        ("hussar", "cavalry", {"food": 300, "metal": 150, "wealth": 100}),
        ("cannon", "siege", {"timber": 250, "metal": 300, "wealth": 50}),
    ],
    "modern": [
        ("commando", "melee", {"food": 600, "metal": 400, "wealth": 300, "oil": 100}),
        ("infantry", "ranged", {"food": 500, "metal": 400, "wealth": 200, "oil": 100}),
        ("tank", "cavalry", {"metal": 900, "wealth": 300, "oil": 400}),
        ("fighter", "cavalry", {"metal": 1200, "wealth": 600, "oil": 700}),
        ("bomber", "siege", {"metal": 1000, "wealth": 500, "oil": 600}),
        ("battleship", "siege", {"timber": 800, "metal": 2000, "wealth": 800, "oil": 900}),
        ("icbm", "siege", {"metal": 3000, "wealth": 3000, "oil": 3000}),
    ],
    "space": [
        ("shocktrooper", "melee", {"food": 1500, "metal": 1500, "wealth": 1000, "oil": 500}),
        ("lasercannon", "ranged", {"metal": 2000, "wealth": 1500, "oil": 1000}),
        ("thor", "melee", {"metal": 4000, "wealth": 2500, "oil": 1500}),
        ("starfighter", "cavalry", {"metal": 3000, "wealth": 2000, "oil": 2000}),
        ("battlecruiser", "siege", {"metal": 6000, "wealth": 4000, "oil": 4000}),
        ("deathstar", "siege", {"metal": 15000, "wealth": 15000, "oil": 10000}),
    ],
}

DEFENSE = {
    "ancient": ("keep", {"timber": 400, "metal": 300}),
    "medieval": ("castle", {"timber": 1000, "metal": 1000, "wealth": 300}),
    "enlightenment": ("fortress", {"timber": 2500, "metal": 3000, "wealth": 1000}),
    "modern": ("bunker", {"metal": 8000, "wealth": 3000, "oil": 2000}),
    "space": ("planetary_fortress", {"metal": 20000, "wealth": 10000, "oil": 8000}),
}

# Heroes are worth this many average units of their age (by budget).
HERO_BUDGET = 25
HEROES = {
    "ancient": [
        ("cleopatra", "ranged"),
        ("alexander_the_great", "cavalry"),
        ("ramesses_ii", "melee"),
        ("attila_the_hun", "cavalry"),
        ("caesar", "melee"),
        ("war_elephant", "melee"),
    ],
    "medieval": [
        ("genghis_khan", "cavalry"),
        ("william_the_conqueror", "melee"),
        ("marco_polo", "ranged"),
        ("robin_hood", "ranged"),
        ("leonardo_da_vinci", "siege"),
    ],
    "enlightenment": [
        ("napoleon", "siege"),
        ("king_henry_viii", "melee"),
        ("george_washington", "ranged"),
        ("louis_xiv", "melee"),
        ("armada", "siege"),
    ],
    "modern": [
        ("albert_einstein", "siege"),
        ("mao_zedong", "melee"),
        ("winston_churchill", "ranged"),
        ("oppenheimer", "siege"),
        ("warren_buffett", "ranged"),
    ],
    "space": [
        ("cad_bane", "ranged"),
        ("the_malevolence", "siege"),
        ("space_battleship_yamato", "siege"),
    ],
}


def stats(age, role, cost_value):
    attack = cost_value * math.sqrt(K[age] / RATIO[role])
    return max(1, round(attack)), max(1, round(attack * RATIO[role]))


def avg_cost(age):
    units = UNITS[age]
    return sum(sum(c.values()) for _, _, c in units) / len(units)


if __name__ == "__main__":
    for age, units in UNITS.items():
        print(age)
        for name, role, cost in units:
            a, h = stats(age, role, sum(cost.values()))
            print(f"  {name:14s} {role:8s} cost {sum(cost.values()):6d}  atk {a:6d}  hp {h:6d}")
        name, cost = DEFENSE[age]
        a, h = stats(age, "defense", sum(cost.values()))
        print(f"  {name:14s} defense  cost {sum(cost.values()):6d}  atk {a:6d}  hp {h:6d}")
        for name, role in HEROES[age]:
            a, h = stats(age, role, avg_cost(age) * HERO_BUDGET)
            print(f"  {name:22s} HERO {role:8s} atk {a:6d}  hp {h:6d}")

import random

import pytest

from chongabot.content import Content
from chongabot.rules.combat import army_from_units, player_army, resolve
from chongabot.rules.effects import Modifiers
from tests.conftest import make_player


def fight(content: Content, a: dict[str, int], d: dict[str, int], seed: int = 1, **kw):  # type: ignore[no-untyped-def]
    return resolve(
        army_from_units(content, "attacker", a),
        army_from_units(content, "defender", d),
        content,
        random.Random(seed),
        **kw,
    )


def test_same_seed_same_battle(content: Content) -> None:
    a = fight(content, {"archer": 50, "spearman": 50}, {"horseman": 60}, seed=7)
    b = fight(content, {"archer": 50, "spearman": 50}, {"horseman": 60}, seed=7)
    assert a.log == b.log and a.winner == b.winner


@pytest.mark.parametrize("seed", range(30))
def test_counts_never_go_negative_and_one_winner(content: Content, seed: int) -> None:
    rng = random.Random(seed)
    pool = ["slinger", "clubman", "spearman", "archer", "horseman", "catapult"]
    a = {u: rng.randint(0, 200) for u in rng.sample(pool, 3)}
    d = {u: rng.randint(0, 200) for u in rng.sample(pool, 3)}
    result = fight(content, a, d, seed=seed)
    assert result.winner in ("attacker", "defender")
    for unit, lost in result.attacker_losses.items():
        assert 0 < lost <= a[unit]
    for unit, lost in result.defender_losses.items():
        assert 0 < lost <= d[unit]


def test_bigger_army_of_same_unit_wins(content: Content) -> None:
    wins = sum(
        fight(content, {"spearman": 200}, {"spearman": 100}, seed=s).winner == "attacker"
        for s in range(20)
    )
    assert wins == 20


def test_mirror_match_is_close_to_even(content: Content) -> None:
    wins = sum(
        fight(
            content, {"archer": 100, "spearman": 100}, {"archer": 100, "spearman": 100}, seed=s
        ).winner
        == "attacker"
        for s in range(200)
    )
    assert 70 <= wins <= 130  # ties go to the defender, so slightly below half is expected


def test_counter_beats_equal_spend(content: Content) -> None:
    """Melee counters ranged: equal resources in each should favour melee clearly."""
    spearman, archer = content.units["spearman"], content.units["archer"]
    budget = 10_000
    a = {"spearman": budget // sum(spearman.cost.values())}
    d = {"archer": budget // sum(archer.cost.values())}
    wins = sum(fight(content, a, d, seed=s).winner == "attacker" for s in range(50))
    assert wins >= 45


def test_later_age_wins_equal_spend(content: Content) -> None:
    knight, spearman = content.units["knight"], content.units["spearman"]
    budget = 20_000
    a = {"knight": budget // sum(knight.cost.values())}
    d = {"spearman": budget // sum(spearman.cost.values())}
    wins = sum(fight(content, a, d, seed=s).winner == "attacker" for s in range(50))
    assert wins >= 45


def test_empty_defender_loses(content: Content) -> None:
    assert fight(content, {"slinger": 1}, {}).winner == "attacker"


def test_defense_buildings_fight_but_are_not_lost(content: Content) -> None:
    defender = make_player(content, units={}, buildings={"keep": 3})
    result = resolve(
        army_from_units(content, "attacker", {"catapult": 400}),
        player_army(content, defender, "defender"),
        content,
        random.Random(3),
    )
    assert "keep" not in result.defender_losses
    assert any(h["from"] == "defender.keep" for r in result.log["rounds"] for h in r["hits"])


def test_attack_modifier_helps(content: Content) -> None:
    buffed = Modifiers()
    buffed.attack = {k: 1.5 for k in buffed.attack}
    plain = sum(
        fight(content, {"spearman": 100}, {"spearman": 110}, seed=s).winner == "attacker"
        for s in range(30)
    )
    boosted = sum(
        fight(content, {"spearman": 100}, {"spearman": 110}, seed=s, attacker_mods=buffed).winner
        == "attacker"
        for s in range(30)
    )
    assert boosted > plain


def test_log_has_rounds_and_winner(content: Content) -> None:
    result = fight(content, {"archer": 30}, {"clubman": 30})
    assert 1 <= len(result.log["rounds"]) <= content.settings.combat_rounds
    assert result.log["winner"] == result.winner
    assert result.log["sides"]["attacker"]["squads"] == {"attacker.archer": 30}


def test_big_battle_is_fast(content: Content) -> None:
    import time

    start = time.perf_counter()
    fight(content, {"icbm": 50_000, "tank": 200_000}, {"bomber": 100_000, "infantry": 300_000})
    assert time.perf_counter() - start < 0.05


def test_alliance_army_defends_and_takes_its_own_losses(content: Content) -> None:
    defender = make_player(content, units={"spearman": 20})
    result = resolve(
        army_from_units(content, "attacker", {"spearman": 100}),
        player_army(content, defender, "defender", allies={"spearman": 200}),
        content,
        random.Random(2),
    )
    assert result.winner == "defender"
    assert result.ally_losses and set(result.ally_losses) == {"spearman"}
    assert result.defender_losses.get("spearman", 0) <= 20


def test_heroes_never_fight(content: Content) -> None:
    p = make_player(
        content, units={"spearman": 10}, heroes=frozenset({"chief_bonk"}), hero="chief_bonk"
    )
    squads = player_army(content, p, "attacker")
    assert [s.unit_id for s in squads] == ["spearman"]

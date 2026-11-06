import random
from datetime import timedelta

import pytest

from chongabot.content import Content
from chongabot.domain.errors import GameError, OnCooldown
from chongabot.rules import exploration, pvp
from chongabot.rules.effects import Modifiers
from tests.conftest import NOW, make_player


def test_cannot_attack_self_or_without_army(content: Content) -> None:
    p = make_player(content)
    with pytest.raises(GameError, match="yourself"):
        pvp.check_can_attack(p, p, content, NOW)
    with pytest.raises(GameError, match="no army"):
        pvp.check_can_attack(
            make_player(content, units={}), make_player(content, id=2), content, NOW
        )


def test_shield_range_cooldown_and_alliance(content: Content) -> None:
    a = make_player(content)
    with pytest.raises(GameError, match="shielded"):
        pvp.check_can_attack(
            a, make_player(content, id=2, shield_until=NOW + timedelta(hours=1)), content, NOW
        )
    with pytest.raises(GameError, match="out of range"):
        pvp.check_can_attack(a, make_player(content, id=2, battle_rating=500), content, NOW)
    with pytest.raises(OnCooldown):
        pvp.check_can_attack(
            make_player(content, last_attack=NOW), make_player(content, id=2), content, NOW
        )
    with pytest.raises(GameError, match="alliance"):
        pvp.check_can_attack(
            make_player(content, alliance_id=9),
            make_player(content, id=2, alliance_id=9),
            content,
            NOW,
        )
    pvp.check_can_attack(a, make_player(content, id=2), content, NOW)


def test_rating_change_rewards_upsets(content: Content) -> None:
    even = pvp.rating_change(500, 500, content)
    upset = pvp.rating_change(400, 600, content)
    stomp = pvp.rating_change(600, 400, content)
    assert stomp < even < upset
    assert content.settings.battle_rating_min_change <= stomp
    assert upset <= content.settings.battle_rating_max_change


def test_tribute_takes_share_and_adds_bonus(content: Content) -> None:
    taken, given = pvp.tribute({"food": 1000, "metal": 5}, content, Modifiers())
    assert taken == {"food": 100}
    assert given == {"food": 150}


def test_exploration_cooldown(content: Content) -> None:
    with pytest.raises(OnCooldown):
        exploration.check_ready(
            make_player(content, last_explore=NOW), content, NOW + timedelta(hours=1)
        )
    exploration.check_ready(
        make_player(content, last_explore=NOW), content, NOW + timedelta(hours=6)
    )


def test_exploration_outcomes_are_valid(content: Content) -> None:
    rng = random.Random(4)
    p = make_player(content)
    kinds = set()
    for _ in range(300):
        o = exploration.roll(p, content, rng)
        kinds.add(o.kind)
        if o.kind == "hero":
            assert o.hero in content.heroes
        if o.kind == "units":
            assert all(content.units[u].age == "ancient" for u in o.units)
        if o.kind == "pirates":
            assert o.pirate_units and o.resources
    assert kinds == {"resources", "units", "building", "hero", "wonder", "pirates"}


def test_owned_heroes_and_wonders_are_not_repeated(content: Content) -> None:
    ancient_heroes = frozenset(h.id for h in content.heroes.values() if h.age == "ancient")
    ancient_wonders = frozenset(w.id for w in content.wonders.values() if w.age == "ancient")
    p = make_player(content, heroes=ancient_heroes, wonders=ancient_wonders)
    rng = random.Random(1)
    for _ in range(200):
        assert exploration.roll(p, content, rng).kind not in ("hero", "wonder")


def test_explorers_can_find_heroes_from_earlier_ages(content: Content) -> None:
    ancient = frozenset(h.id for h in content.heroes.values() if h.age == "ancient")
    p = make_player(content, age="medieval", heroes=frozenset())
    rng = random.Random(9)
    found = {o.hero for o in (exploration.roll(p, content, rng) for _ in range(800)) if o.hero}
    assert found & ancient and all(content.heroes[h].age in ("ancient", "medieval") for h in found)

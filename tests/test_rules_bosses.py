from datetime import timedelta

import pytest

from chongabot.content import Content
from chongabot.domain.errors import GameError, OnCooldown
from chongabot.rules import bosses
from tests.conftest import NOW


def test_split_is_proportional_and_exact() -> None:
    out = bosses.split_loot({"food": 1000, "metal": 7}, {1: 900, 2: 100, 3: 0})
    assert out == {1: {"food": 900, "metal": 7}, 2: {"food": 100}}
    assert sum(c.get("metal", 0) for c in out.values()) == 7  # leftovers go to the top stake


def test_tiny_stake_gets_a_tiny_share() -> None:
    out = bosses.split_loot({"oil": 1_000_000}, {1: 5_000_000, 2: 50})
    assert out[2] == {"oil": 9}


def test_no_stakes_splits_evenly() -> None:
    out = bosses.split_loot({"food": 90}, {1: 0, 2: 0, 3: 0})
    assert [c["food"] for c in out.values()] == [30, 30, 30]


def test_challenge_checks(content: Content) -> None:
    boss = content.bosses["the_mud_golem"]
    army = {"spearman": 10}
    with pytest.raises(GameError, match="Only officers"):
        bosses.check_can_challenge("member", army, boss, content, NOW, None)
    with pytest.raises(GameError, match="empty"):
        bosses.check_can_challenge("owner", {}, boss, content, NOW, None)
    with pytest.raises(OnCooldown):
        bosses.check_can_challenge("officer", army, boss, content, NOW, NOW - timedelta(hours=1))
    bosses.check_can_challenge("officer", army, boss, content, NOW, NOW - timedelta(days=2))


def test_every_age_has_bosses_worth_more_than_bots(content: Content) -> None:
    for age in content.ages:
        ours = [b for b in content.bosses.values() if b.age == age.id]
        assert ours, age.id
        strongest_bot = max(b.value for b in content.bots.values() if b.age == age.id)
        assert min(b.value for b in ours) > strongest_bot
        assert all(sum(b.loot.values()) >= b.value for b in ours)  # loot beats expected losses

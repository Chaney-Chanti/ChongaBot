from datetime import timedelta

import pytest

from chongabot.content import Content
from chongabot.domain.errors import GameError, NotEnough, OnCooldown, WrongAge
from chongabot.domain.models import Player
from chongabot.rules import economy
from chongabot.rules.effects import modifiers
from tests.conftest import NOW, make_player


def test_base_rates_with_no_buildings(content: Content, player: Player) -> None:
    rates = economy.production_rates(player, content)
    assert rates["food"] == content.settings.base_rates["food"]
    assert rates["oil"] == 0


def test_buildings_add_yield_and_age_multiplies(content: Content) -> None:
    p = make_player(content, age="medieval", buildings={"granary": 4})
    rates = economy.production_rates(p, content)
    expected = (content.settings.base_rates["food"] + 4 * 25) * 1.6
    assert rates["food"] == pytest.approx(expected)


def test_research_multiplies_its_resource(content: Content) -> None:
    p = make_player(content, research=frozenset({"pastures"}))
    base = economy.production_rates(make_player(content), content)["food"]
    assert economy.production_rates(p, content)["food"] == pytest.approx(base * 1.2)


def test_dyson_chonga_boosts_every_resource(content: Content) -> None:
    mods = modifiers(make_player(content, wonders=frozenset({"the_dyson_chonga"})), content)
    assert all(v == pytest.approx(1.1) for v in mods.rate.values())


def test_claim_needs_an_hour(content: Content, player: Player) -> None:
    with pytest.raises(OnCooldown):
        economy.claim(player, content, NOW + timedelta(minutes=59))


def test_claim_is_capped_at_24_hours(content: Content, player: Player) -> None:
    day = economy.claim(player, content, NOW + timedelta(hours=24))
    week = economy.claim(player, content, NOW + timedelta(days=7))
    assert week.gained == day.gained
    assert day.gained["food"] == 50 * 24


def test_building_cost_grows_with_each_copy(content: Content) -> None:
    granary = content.buildings["granary"]
    first = economy.building_cost(make_player(content), content, granary, 1)
    tenth = economy.building_cost(
        make_player(content, buildings={"granary": 9}), content, granary, 1
    )
    assert first == {"timber": 150, "metal": 50}
    assert tenth["timber"] == pytest.approx(150 * 1.16**9, abs=1)


def test_buying_n_at_once_costs_the_same_as_one_by_one(content: Content) -> None:
    granary = content.buildings["granary"]
    batch = economy.building_cost(make_player(content), content, granary, 3)
    singles = [
        economy.building_cost(make_player(content, buildings={"granary": i}), content, granary, 1)
        for i in range(3)
    ]
    for r in batch:
        assert batch[r] == pytest.approx(sum(s[r] for s in singles), abs=3)


def test_max_buildings_is_exactly_the_most_you_can_afford(content: Content) -> None:
    p = make_player(content, resources={"timber": 2000, "metal": 2000})
    granary = content.buildings["granary"]
    n = economy.max_buildings(p, content, granary)
    assert economy.affordable(p.resources, economy.building_cost(p, content, granary, n))
    assert not economy.affordable(p.resources, economy.building_cost(p, content, granary, n + 1))


def test_great_chonga_mound_makes_buildings_cheaper(content: Content) -> None:
    granary = content.buildings["granary"]
    p = make_player(content, wonders=frozenset({"the_great_chonga_mound"}))
    assert economy.building_cost(p, content, granary, 1)["timber"] == round(150 * 0.85)


def test_defense_buildings_only_in_their_own_age(content: Content) -> None:
    medieval = make_player(content, age="medieval")
    with pytest.raises(WrongAge):
        economy.check_buildable(medieval, content, content.buildings["keep"])
    economy.check_buildable(medieval, content, content.buildings["castle"])
    economy.check_buildable(medieval, content, content.buildings["granary"])


def test_oil_rig_locked_until_enlightenment(content: Content, player: Player) -> None:
    with pytest.raises(WrongAge):
        economy.check_buildable(player, content, content.buildings["oil_rig"])


def test_units_only_from_your_age(content: Content, player: Player) -> None:
    economy.check_trainable(player, content, content.units["archer"])
    with pytest.raises(WrongAge):
        economy.check_trainable(player, content, content.units["knight"])
    assert "chief_bonk" not in content.units  # heroes aren't units


def test_icbm_needs_dr_kaboom_as_second_in_command(content: Content) -> None:
    modern = make_player(content, age="modern")
    assert "icbm" not in {u.id for u in economy.trainable(modern, content)}
    found = make_player(content, age="modern", heroes=frozenset({"dr_kaboom"}))
    assert "icbm" not in {u.id for u in economy.trainable(found, content)}  # found, not appointed
    appointed = make_player(
        content, age="modern", heroes=frozenset({"dr_kaboom"}), hero="dr_kaboom"
    )
    assert "icbm" in {u.id for u in economy.trainable(appointed, content)}


def test_only_the_second_in_command_passive_applies(content: Content) -> None:
    court = frozenset({"chief_bonk", "grubnar"})
    none = modifiers(make_player(content, heroes=court), content)
    bonk = modifiers(make_player(content, heroes=court, hero="chief_bonk"), content)
    assert none.attack["melee"] == 1.0
    assert bonk.attack["melee"] == pytest.approx(1.05) and bonk.attack["cavalry"] == pytest.approx(
        1.05
    )
    fake = modifiers(make_player(content, heroes=frozenset(), hero="chief_bonk"), content)
    assert fake.attack["melee"] == 1.0  # appointed but never found: ignored


def test_max_units(content: Content) -> None:
    p = make_player(content, resources={"food": 350})
    assert economy.max_units(p, content, content.units["slinger"]) == 10


def test_research_once_only(content: Content) -> None:
    p = make_player(content, research=frozenset({"pastures"}))
    with pytest.raises(GameError):
        economy.check_researchable(p, content, content.research["pastures"])
    assert "pastures" not in {r.id for r in economy.researchable(p, content)}


def test_fizzlewick_makes_research_cheaper(content: Content) -> None:
    p = make_player(content, heroes=frozenset({"maestro_fizzlewick"}), hero="maestro_fizzlewick")
    assert economy.research_cost(p, content, content.research["pastures"]) == {"knowledge": 240}


def test_require_names_the_shortfall(content: Content) -> None:
    with pytest.raises(NotEnough, match="1,900 metal"):
        economy.require({"metal": 3100}, {"metal": 5000})


def test_no_age_after_space(content: Content) -> None:
    with pytest.raises(GameError):
        economy.next_age(make_player(content, age="space"), content)


def test_retrain_keeps_value_and_merges_roles(content: Content) -> None:
    from chongabot.rules.economy import retrain_army

    # clubman (40) and spearman (65) are both melee: 100*40 + 40*65 = 6,600 -> 33 knights (200)
    out = {r.into: r for r in retrain_army({"clubman": 100, "spearman": 40}, "medieval", content)}
    assert out["knight"].count == 33
    assert out["knight"].old == {"clubman": 100, "spearman": 40}


def test_retrain_skips_current_age_and_hero_units(content: Content) -> None:
    from chongabot.rules.economy import retrain_army

    special = next(u.id for u in content.units.values() if u.requires_unlock)
    out = retrain_army({"knight": 5, special: 3}, "medieval", content)
    assert out == []
    # units two ages behind still retrain into the newest age
    [r] = retrain_army({"archer": 50}, "enlightenment", content)
    assert content.units[r.into].age == "enlightenment" and content.units[r.into].role == "ranged"

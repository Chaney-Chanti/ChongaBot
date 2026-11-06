import shutil
from pathlib import Path

import pytest
import yaml

from chongabot.content import Content, ContentError, load_content
from chongabot.content.loader import CONTENT_DIR
from chongabot.content.models import ROLES


@pytest.fixture(scope="module")
def content():  # type: ignore[no-untyped-def]
    return load_content()


def test_shipped_content_loads(content) -> None:  # type: ignore[no-untyped-def]
    assert [a.id for a in content.ages] == [
        "ancient",
        "medieval",
        "enlightenment",
        "modern",
        "space",
    ]
    assert len(content.units) > 25
    assert len(content.heroes) > 20 and len(content.wonders) > 10
    assert content.lore.title == "The Land of Chonga" and content.lore.regions
    assert all(a.tagline for a in content.ages)
    assert content.next_age("space") is None


def test_counters_form_one_cycle(content) -> None:  # type: ignore[no-untyped-def]
    role, seen = "melee", []
    for _ in ROLES:
        seen.append(role)
        role = content.counters[role]
    assert role == "melee" and sorted(seen) == sorted(ROLES)


def test_every_regular_unit_in_an_age_is_about_equally_efficient(content) -> None:  # type: ignore[no-untyped-def]
    """attack * hp / cost^2 is the Lanchester strength per resource spent."""
    for age in content.ages:
        scores = [
            u.attack * u.hp / sum(u.cost.values()) ** 2
            for u in content.units.values()
            if u.age == age.id and not u.requires_unlock
        ]
        assert max(scores) / min(scores) < 1.25, age.id


def test_later_ages_are_stronger_per_resource(content) -> None:  # type: ignore[no-untyped-def]
    def efficiency(age_id: str) -> float:
        units = [u for u in content.units.values() if u.age == age_id and not u.requires_unlock]
        return sum(u.attack * u.hp / sum(u.cost.values()) ** 2 for u in units) / len(units)

    values = [efficiency(a.id) for a in content.ages]
    assert values == sorted(values)


def test_exploration_weights_sum_to_100(content) -> None:  # type: ignore[no-untyped-def]
    assert sum(e.weight for e in content.exploration) == 100


# --- the loader rejects broken content ---------------------------------------


@pytest.fixture
def content_copy(tmp_path: Path) -> Path:
    for f in CONTENT_DIR.glob("*.yaml"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


def edit(directory: Path, name: str, change) -> None:  # type: ignore[no-untyped-def]
    path = directory / name
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data))


def test_rejects_unknown_resource(content_copy: Path) -> None:
    edit(content_copy, "units.yaml", lambda d: d["ancient"]["slinger"]["cost"].update(gold=5))
    with pytest.raises(ValueError, match="gold"):
        load_content(content_copy)


def test_rejects_oil_cost_before_oil_exists(content_copy: Path) -> None:
    edit(content_copy, "units.yaml", lambda d: d["ancient"]["slinger"]["cost"].update(oil=5))
    with pytest.raises(ContentError, match="nobody can produce"):
        load_content(content_copy)


def test_rejects_duplicate_ids_across_ages(content_copy: Path) -> None:
    def dup(d):  # type: ignore[no-untyped-def]
        d["medieval"]["slinger"] = d["ancient"]["slinger"]

    edit(content_copy, "units.yaml", dup)
    with pytest.raises(ContentError, match="duplicate"):
        load_content(content_copy)


def test_rejects_broken_counter_cycle(content_copy: Path) -> None:
    edit(content_copy, "counters.yaml", lambda d: d.update(defense="ranged"))
    with pytest.raises(ContentError, match="counters"):
        load_content(content_copy)


def test_rejects_unlock_of_unknown_unit(content_copy: Path) -> None:
    def bad(d):  # type: ignore[no-untyped-def]
        d["modern"]["dr_kaboom"]["effects"] = [{"kind": "unlock_unit", "unit": "nuke"}]

    edit(content_copy, "heroes.yaml", bad)
    with pytest.raises(ContentError, match="nuke"):
        load_content(content_copy)


def test_rejects_hero_without_a_passive(content_copy: Path) -> None:
    edit(content_copy, "heroes.yaml", lambda d: d["ancient"]["chief_bonk"].update(effects=[]))
    with pytest.raises(ValueError, match="effects"):
        load_content(content_copy)


def test_rejects_hero_id_clashing_with_a_unit(content_copy: Path) -> None:
    edit(
        content_copy, "heroes.yaml", lambda d: d["ancient"].update(spearman=d["ancient"]["gerald"])
    )
    with pytest.raises(ContentError, match="spearman"):
        load_content(content_copy)


def test_every_hero_and_wonder_describes_its_bonus(content: Content) -> None:
    from chongabot.views.fmt import effects_text

    for item in (*content.heroes.values(), *content.wonders.values()):
        text = effects_text(item.effects, content)
        assert text and "mysterious" not in text, item.id


def test_rejects_unknown_effect_kind(content_copy: Path) -> None:
    def bad(d):  # type: ignore[no-untyped-def]
        d["space"]["the_chongularity"]["effects"] = [{"kind": "free_win"}]

    edit(content_copy, "wonders.yaml", bad)
    with pytest.raises(ValueError):
        load_content(content_copy)


def test_ten_bots_per_age_getting_stronger(content: Content) -> None:
    for age in content.ages:
        bots = sorted((b for b in content.bots.values() if b.age == age.id), key=lambda b: b.tier)
        assert [b.tier for b in bots] == list(range(1, 11)), age.id
        values = [b.value for b in bots]
        assert values == sorted(values) and values[-1] > 8 * values[0]
        for b in bots:
            assert all(
                content.units[u].age == age.id and not content.units[u].requires_unlock
                for u in b.units
            )
            assert b.loot and all(v > 0 for v in b.loot.values())


def test_weakest_bot_is_a_fair_first_fight(content: Content) -> None:
    starting_value = sum(
        sum(content.units[u].cost.values()) * n for u, n in content.settings.starting_units.items()
    )
    assert 0.5 * starting_value <= content.bots["ancient_1"].value <= 2 * starting_value

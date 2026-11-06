from datetime import UTC, datetime
from typing import Any

import pytest

from chongabot.content import Content, load_content
from chongabot.domain.models import Player

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="session")
def content() -> Content:
    return load_content()


def make_player(content: Content, **overrides: Any) -> Player:
    s = content.settings
    fields: dict[str, Any] = {
        "id": 1,
        "name": "Chongaland",
        "username": "chaney",
        "age": "ancient",
        "resources": dict(s.starting_resources),
        "units": dict(s.starting_units),
        "last_claim": NOW,
        "created_at": NOW,
    }
    fields.update(overrides)
    return Player(**fields)


@pytest.fixture
def player(content: Content) -> Player:
    return make_player(content)

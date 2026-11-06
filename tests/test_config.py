import pytest

from chongabot.config import Settings


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("DISCORDTOKEN", raising=False)


def settings(**env: str) -> Settings:
    return Settings(_env_file=None, **env)  # type: ignore[call-arg]


def test_reads_new_token_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "abc")
    assert settings().discord_token.get_secret_value() == "abc"


def test_accepts_legacy_token_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORDTOKEN", "legacy")
    assert settings().discord_token.get_secret_value() == "legacy"


def test_token_is_hidden_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "super-secret")
    assert "super-secret" not in repr(settings())


def test_owner_ids_parse_from_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "abc")
    monkeypatch.setenv("OWNER_IDS", "[217413468410609664]")
    assert settings().owner_ids == {217413468410609664}


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "abc")
    s = settings()
    assert s.command_prefix == "c!"
    assert s.dev_guild_id is None
    assert s.owner_ids == set()

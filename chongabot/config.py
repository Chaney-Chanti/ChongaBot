from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, read from the environment or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # DISCORDTOKEN is accepted so the old .env keeps working.
    discord_token: SecretStr = Field(
        validation_alias=AliasChoices("DISCORD_TOKEN", "DISCORDTOKEN"),
    )
    command_prefix: str = "c!"
    # Privileged intent; must also be switched on in the Developer Portal (Bot page).
    message_content_intent: bool = True
    owner_ids: set[int] = Field(default_factory=set)
    # When set, slash commands sync to this guild on startup (instant, for development).
    dev_guild_id: int | None = None
    # Loads the owner-only /dev commands (fake nations, free resources). Never in production.
    dev_mode: bool = False
    database_path: Path = Path("chonga.db")
    log_level: str = "INFO"
    log_json: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()

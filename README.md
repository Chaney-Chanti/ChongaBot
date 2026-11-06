# ChongaBot

A nation-building game for Discord: gather resources, build, research, raise an army,
form alliances and attack other players.

## Run locally

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env      # then fill in DISCORD_TOKEN, OWNER_IDS, DEV_GUILD_ID
uv sync
uv run python -m chongabot
```

With `DEV_GUILD_ID` set, slash commands appear in that server right away.
To publish them everywhere, run `c!sync global` as an owner (takes up to an hour).

## Checks

```bash
uv run ruff check && uv run ruff format --check
uv run mypy
uv run pytest
```

## Deploy

Runs on any Ubuntu server, including a free Oracle Cloud VM: see
[`deploy/ORACLE.md`](deploy/ORACLE.md) for the step-by-step guide.

- `deploy/setup.sh`: one-time server setup (user, code, `.env`, systemd services, backups).
- `deploy/deploy.sh`: update to the latest code and restart.
- `deploy/backup.sh`: nightly database backup, run by `chongabot-backup.timer`.

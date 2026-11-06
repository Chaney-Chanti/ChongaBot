"""Engine setup, transactions and migrations.

Every transaction starts with BEGIN IMMEDIATE, which takes SQLite's write lock up front.
That makes read-check-write sequences atomic: two `/build` clicks at the same moment run
one after the other, so the second one sees the first one's spend. Reads are cheap with
WAL, and at ~100 players the single writer is never the bottleneck.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",
    "PRAGMA synchronous=NORMAL",
)


def _install_hooks(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_connection: Any, _record: Any) -> None:
        # Let us issue BEGIN ourselves instead of the driver's deferred BEGIN.
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        for pragma in PRAGMAS:
            cursor.execute(pragma)
        cursor.close()

    @event.listens_for(engine.sync_engine, "begin")
    def on_begin(conn: Any) -> None:
        conn.exec_driver_sql("BEGIN IMMEDIATE")


def alembic_config(database_path: Path) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    return cfg


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.path}")
        _install_hooks(self.engine)

    async def migrate(self) -> None:
        """Bring the schema up to date. Runs Alembic in a thread (it is synchronous)."""
        await asyncio.to_thread(command.upgrade, alembic_config(self.path), "head")

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncConnection]:
        """One atomic unit of work. Commits on success, rolls back on any exception."""
        async with self.engine.begin() as conn:
            yield conn

    async def close(self) -> None:
        await self.engine.dispose()

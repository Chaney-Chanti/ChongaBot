"""Alembic environment. Migrations run synchronously against the same SQLite file."""

from alembic import context
from sqlalchemy import create_engine

from chongabot.storage.schema import metadata

config = context.config


def run_migrations() -> None:
    url = config.get_main_option("sqlalchemy.url")
    assert url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=metadata,
            render_as_batch=True,  # SQLite can't ALTER most things; batch mode rebuilds tables
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()

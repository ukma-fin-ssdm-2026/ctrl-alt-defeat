import os

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import declarative_base, sessionmaker


def normalize_database_url(url: str) -> str:
    """Hosting providers (e.g. Render, Heroku) give `postgres://...`; SQLAlchemy needs `postgresql+psycopg2://`."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


# An empty value (e.g. `DATABASE_URL=` in .env) also means the local SQLite file
DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL") or "sqlite:///./app.db")

# Reliability (finding 10): time limits for PostgreSQL (Neon)
CONNECT_TIMEOUT_SECONDS = 5  # opening a connection
POOL_TIMEOUT_SECONDS = 10  # waiting for a free connection of the pool
STATEMENT_TIMEOUT_MS = 10000  # one SQL statement


def set_statement_timeout(connection) -> None:
    """
    Limit every SQL statement of the transaction. `SET LOCAL` instead of the startup parameter
    `options=-c statement_timeout=...`: the pooled Neon connection string (PgBouncer) rejects such startup
    options with "unsupported startup parameter", while `SET LOCAL` works with and without the pooler.
    """
    connection.exec_driver_sql(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")


def build_engine(url: str):
    """SQLite for local runs and tests; PostgreSQL with connect, pool and statement time limits."""
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False}, pool_pre_ping=True)
    postgres = create_engine(
        url,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
        pool_pre_ping=True,
        pool_timeout=POOL_TIMEOUT_SECONDS,
    )
    event.listen(postgres, "begin", set_statement_timeout)
    return postgres


engine = build_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# Old databases were created with UNIQUE(tmdb_id) on the content table (PostgreSQL names it content_tmdb_id_key).
# TMDB numbers movies and TV series separately, so a series could not be saved when a movie had its number.
OLD_TMDB_CONSTRAINT = "content_tmdb_id_key"


def upgrade_content_tmdb_uniqueness(bind) -> bool:
    """
    One-time upgrade of an existing PostgreSQL database: UNIQUE(tmdb_id) -> UNIQUE(category, tmdb_id).
    Idempotent (IF EXISTS / IF NOT EXISTS). SQLite (local development, tests) is left as created:
    there the import skips a title whose number is taken instead of failing. Returns True if it ran.
    """
    if bind.dialect.name != "postgresql":
        return False
    with bind.begin() as connection:
        connection.exec_driver_sql(f"ALTER TABLE content DROP CONSTRAINT IF EXISTS {OLD_TMDB_CONSTRAINT}")
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_content_category_tmdb ON content (category, tmdb_id)"
        )
    return True


# Columns added to the users table after the first release: create_all() does not add columns to an existing
# table, so they are added on startup. Types per database: (PostgreSQL, SQLite).
USER_COLUMNS = {
    "verification_sent_at": ("TIMESTAMP WITH TIME ZONE", "DATETIME"),
    "token_version": ("INTEGER NOT NULL DEFAULT 0", "INTEGER NOT NULL DEFAULT 0"),
}


def upgrade_user_columns(bind) -> list:
    """Add the missing USER_COLUMNS to an existing users table. Returns the names of the added columns."""
    existing = {column["name"] for column in inspect(bind).get_columns("users")}
    missing = [name for name in USER_COLUMNS if name not in existing]
    if not missing:
        return []
    postgres = bind.dialect.name == "postgresql"
    with bind.begin() as connection:
        for name in missing:
            column_type = USER_COLUMNS[name][0 if postgres else 1]
            # Names and types come from USER_COLUMNS above, never from input
            connection.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {name} {column_type}")
    return missing


def upgrade_schema(bind) -> None:
    """One-time upgrades of an existing database, run on every startup (each step is idempotent)."""
    upgrade_content_tmdb_uniqueness(bind)
    upgrade_user_columns(bind)

import os
from sqlalchemy import create_engine
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

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
else:
    connect_args = {
        "connect_timeout": 5,
        "options": "-c statement_timeout=10000",
    }

    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_timeout=10,
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

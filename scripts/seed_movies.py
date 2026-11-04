#!/usr/bin/env python3
"""
Seed script to populate initial movie and series catalog into database (FR-002, FR-012).
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

# Read .env (the same file as `uvicorn --env-file .env`) before the app modules read the environment
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from sqlalchemy import text  # noqa: E402

from src.api.db.database import Base, SessionLocal, engine  # noqa: E402
from src.api.services.demo_accounts import seed_default_users  # noqa: E402
from src.api.services.tmdb import fetch_tmdb_movies, seed_movies_to_database  # noqa: E402


def ensure_schema_compatibility():
    """Ensure older SQLite databases receive newly introduced columns."""
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE content ADD COLUMN runtime INTEGER"))
            conn.commit()
        except Exception:
            pass


def main():
    print("🛠️ Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()

    print("📥 Fetching movie catalog metadata (TMDB / Fallback)...")
    movies = fetch_tmdb_movies()

    db = SessionLocal()
    try:
        added = seed_movies_to_database(db, movies)
        from src.api.db.models import Content

        total_count = db.query(Content).count()
        print(f"✅ Successfully seeded {added} new titles into database. Total in catalog: {total_count}")

        # Same seed accounts as on API startup (SEED_* variables, see .env.example)
        seed_default_users(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()

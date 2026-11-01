#!/usr/bin/env python3
"""
Seed script to populate initial movie and series catalog into database (FR-002, FR-012).
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.db.database import Base, SessionLocal, engine
from src.api.services.tmdb import fetch_tmdb_movies, seed_movies_to_database


def main():
    print("🛠️ Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    print("📥 Fetching movie catalog metadata (TMDB / Fallback)...")
    movies = fetch_tmdb_movies()

    db = SessionLocal()
    try:
        added = seed_movies_to_database(db, movies)
        from src.api.db.models import Content
        total_count = db.query(Content).count()
        print(f"✅ Successfully seeded {added} new titles into database. Total in catalog: {total_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Seed script to populate initial movie and series catalog into database (FR-002, FR-012).
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from src.api.db.database import Base, SessionLocal, engine
from src.api.services.auth import hash_password
from src.api.services.tmdb import fetch_tmdb_movies, seed_movies_to_database


def ensure_schema_compatibility():
    """Ensure older SQLite databases receive newly introduced columns."""
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE content ADD COLUMN runtime INTEGER"))
            conn.commit()
        except Exception:
            pass


def seed_demo_users(db):
    """Create initial verified admin and user accounts for evaluation and testing."""
    from src.api.db.models import User

    demo_users = [
        {
            "email": "admin@platform.local",
            "nickname": "admin_demo",
            "password": "Admin123!",
            "role": "admin",
        },
        {
            "email": "user@platform.local",
            "nickname": "user_demo",
            "password": "User123!",
            "role": "user",
        },
    ]

    for item in demo_users:
        existing = db.query(User).filter(User.email == item["email"]).first()
        if not existing:
            user = User(
                email=item["email"],
                nickname=item["nickname"],
                password_hash=hash_password(item["password"]),
                role=item["role"],
                email_verified=True,
                status="active",
            )
            db.add(user)
            print(f"👤 Created demo {item['role']}: {item['email']} (password: {item['password']})")
    db.commit()


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

        seed_demo_users(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()

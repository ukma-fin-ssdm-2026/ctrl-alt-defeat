import uuid

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content, User, WatchedItem
from src.api.routers.watched import get_watched_list


def test_watched_list_50_movies_uses_at_most_two_queries():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)

    try:
        with SessionLocal() as db:
            user_id = uuid.uuid4()

            user = User(
                user_id=user_id,
                email="performance@example.com",
                nickname="performance_user",
                password_hash="test-hash",
                email_verified=True,
                status="active",
            )
            db.add(user)

            for i in range(50):
                content_id = uuid.uuid4()

                db.add(
                    Content(
                        content_id=content_id,
                        title=f"Movie {i}",
                        category="Movie",
                        genre="Drama",
                        year=2020,
                        rating=8.0,
                    )
                )

                db.add(
                    WatchedItem(
                        user_id=user_id,
                        content_id=content_id,
                    )
                )

            db.commit()

            # Використовуємо окремий об'єкт користувача,
            # щоб не викликати додаткові SQL-запити.
            class TestUser:
                def __init__(self, user_id):
                    self.user_id = user_id

            current_user = TestUser(user_id)

            queries = []

            def count_queries(conn, cursor, statement, parameters, context, executemany):
                queries.append(statement)

            # Починаємо рахувати тільки після створення тестових даних.
            event.listen(engine, "before_cursor_execute", count_queries)

            try:
                result = get_watched_list(
                    db=db,
                    current_user=current_user,
                )
            finally:
                event.remove(engine, "before_cursor_execute", count_queries)

            assert result.total == 50
            assert len(result.items) == 50

            # Перевіряємо, що назви фільмів отримано правильно.
            titles = {item.title for item in result.items}
            assert titles == {f"Movie {i}" for i in range(50)}

            # Головна перевірка продуктивності.
            assert len(queries) <= 2, (
                f"Expected at most 2 SQL queries, "
                f"but executed {len(queries)}"
            )
    finally:
        engine.dispose()
        
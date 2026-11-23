"""
Names of titles and film series in the Ukrainian interface (issue #276): titles without a Ukrainian
translation came in Japanese, Chinese or Korean, and film series names ended with "| Колекція".
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content
from src.api.main import app
from src.api.routers import movies as movies_router
from src.api.services.tmdb import (
    build_catalog_item,
    clean_collection_name,
    collection_names,
    fix_unreadable_titles,
    is_readable_title,
    ukrainian_title,
)

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.mark.parametrize(
    "text, readable",
    [
        ("Сутінки", True),
        ("Ґуфі фільм", True),
        ("Pokémon: Lucario and the Mystery of Mew", True),
        ("Ngọc Trinh", True),
        ("Final Fantasy VII: Advent Children (2005)", True),
        ("名探偵コナン 緋色の弾丸", False),
        ("소원", False),
        ("ドラゴンボールＺ 極限バトル！", False),
        ("Dragon Ball ＺＺ", False),
        ("", False),
        (None, False),
    ],
)
def test_readable_scripts(text, readable):
    # Trace: T-033
    assert is_readable_title(text) is readable


def test_ukrainian_title_falls_back_to_english_for_another_script():
    # Trace: T-033
    assert ukrainian_title(
        "名探偵コナン 緋色の弾丸", "Detective Conan: The Scarlet Bullet", "名探偵コナン 緋色の弾丸"
    ) == ("Detective Conan: The Scarlet Bullet")
    assert ukrainian_title("Сутінки", "Twilight", "Twilight") == "Сутінки"
    # No readable English title either: the original stays rather than an empty card
    assert ukrainian_title("소원", None, "소원") == "소원"
    assert ukrainian_title(None, None, None) == "Без назви"


def test_import_uses_the_english_title_when_tmdb_has_no_ukrainian_one():
    # Trace: T-033
    details = {
        "id": 1768,
        "title": "名探偵コナン 緋色の弾丸",
        "original_title": "名探偵コナン 緋色の弾丸",
        "original_language": "ja",
        "release_date": "2021-04-16",
        "poster_path": "/conan.jpg",
        "overview": "Конан розслідує викрадення.",
        "translations": {
            "translations": [
                {"iso_639_1": "en", "iso_3166_1": "US", "data": {"title": "Detective Conan: The Scarlet Bullet"}}
            ]
        },
    }

    item = build_catalog_item("Cartoons", "movie", {"id": 1768}, details)

    assert item["title"] == "Detective Conan: The Scarlet Bullet"
    assert item["title_en"] == "Detective Conan: The Scarlet Bullet"


@pytest.mark.parametrize(
    "name, cleaned",
    [
        ("Сутінки | Колекція", "Сутінки"),
        ("Практична магія |Колекція", "Практична магія"),
        ("Тарзан | Анімаційна колекція", "Тарзан"),
        ("Дзвінок | Оригінальна колекція", "Дзвінок"),
        ("Ліга справедливості (2013) | Анімаційна колекція", "Ліга справедливості (2013)"),
        ("Смертельна битва. Легенди (Колекція)", "Смертельна битва. Легенди"),
        ("Привид у латах (анімаційна колекція)", "Привид у латах"),
        ("Володар перснів (Колекція)", "Володар перснів"),
        ("Twilight Collection", "Twilight"),
        ("Tarzan (Animation) Collection", "Tarzan (Animation)"),
        ("ドラゴンボールZシリーズ", "ドラゴンボールZ"),
        ("白蛇（系列）", "白蛇"),
        ("Doraemon Movies", "Doraemon Movies"),
        ("Дівчинка-чарівниця Мадока Маґіка: Фільми", "Дівчинка-чарівниця Мадока Маґіка: Фільми"),
        ("Collection", "Collection"),
        (None, None),
    ],
)
def test_collection_suffix_is_removed(name, cleaned):
    # Trace: T-049
    assert clean_collection_name(name) == cleaned


def test_collection_name_in_another_script_is_replaced_with_english():
    # Trace: T-049
    assert collection_names("ソードアート・オンライン プログレッシブ", "Sword Art Online Progressive Collection") == (
        "Sword Art Online Progressive",
        "Sword Art Online Progressive",
    )
    assert collection_names("Сутінки | Колекція", "Twilight Collection") == ("Сутінки", "Twilight")
    assert collection_names("ドラゴンボールZシリーズ", None) == ("ドラゴンボールZ", None)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine_test)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_test)


def add(db, title, title_en=None, **fields):
    content = Content(
        content_id=uuid.uuid4(), title=title, title_en=title_en, category="Movie", genre="Пригоди", year=2020, **fields
    )
    db.add(content)
    db.commit()
    return content


def test_startup_fixes_titles_stored_in_another_script(db_session):
    # Trace: T-033
    conan = add(db_session, "名探偵コナン 緋色の弾丸", "Detective Conan: The Scarlet Bullet")
    hope = add(db_session, "소원", "Hope")
    no_english = add(db_session, "大鱼海棠", "大鱼海棠")
    twilight = add(db_session, "Сутінки", "Twilight")

    assert fix_unreadable_titles(db_session) == 2
    assert fix_unreadable_titles(db_session) == 0  # idempotent

    for content in (conan, hope, no_english, twilight):
        db_session.refresh(content)
    assert conan.title == "Detective Conan: The Scarlet Bullet"
    assert hope.title == "Hope"
    assert no_english.title == "大鱼海棠"
    assert twilight.title == "Сутінки"


def test_related_titles_show_the_clean_series_name(db_session):
    # Trace: T-049
    def override_get_db():
        yield db_session

    first = add(
        db_session,
        "Сутінки",
        "Twilight",
        tmdb_id=8966,
        collection_id=33514,
        collection_name="Сутінки | Колекція",
        collection_name_en="The Twilight Collection",
    )
    add(
        db_session,
        "Молодий місяць",
        "New Moon",
        tmdb_id=18239,
        collection_id=33514,
        collection_name="Сутінки | Колекція",
        collection_name_en="The Twilight Collection",
    )

    app.dependency_overrides[movies_router.get_db] = override_get_db
    try:
        with TestClient(app) as client:
            related = client.get(f"/api/v1/movies/{first.content_id}/related").json()
    finally:
        app.dependency_overrides.clear()

    assert related["collection"] == {"id": 33514, "name": "Сутінки", "name_en": "The Twilight"}

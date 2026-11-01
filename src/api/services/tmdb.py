import json
import logging
import os
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from src.api.db.models import Content

logger = logging.getLogger(__name__)

# Fallback catalog metadata (FR-012 Graceful Degradation)
FALLBACK_MOVIES = [
    {
        "id": 1,
        "title": "Дюна: Частина друга",
        "title_en": "Dune: Part Two",
        "category": "Movie",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Бойовик", "Пригоди"],
        "year": 2024,
        "rating": 8.8,
        "rotten_rating": "93%",
        "img": "https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2TGpiom05.jpg",
        "description": (
            "Пол Атрід об'єднується з Чані та фременами, вирушаючи на шлях помсти "
            "проти змовників, які знищили його родину."
        ),
        "description_en": (
            "Paul Atreides unites with Chani and the Fremen while seeking revenge "
            "against the conspirators who destroyed his family."
        ),
        "tmdb_id": 693134,
    },
    {
        "id": 2,
        "title": "Оппенгеймер",
        "title_en": "Oppenheimer",
        "category": "Movie",
        "genre": "Драма",
        "genres": ["Драма", "Біографія", "Історія"],
        "year": 2023,
        "rating": 8.4,
        "rotten_rating": "93%",
        "img": "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
        "description": (
            "Історія життя американського фізика Роберта Оппенгеймера, який очолював «Проєкт Манхеттен»."
        ),
        "description_en": (
            "The story of American physicist J. Robert Oppenheimer and his role in the development of the atomic bomb."
        ),
        "tmdb_id": 872585,
    },
    {
        "id": 3,
        "title": "Інтерстеллар",
        "title_en": "Interstellar",
        "category": "Movie",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Драма", "Пригоди"],
        "year": 2014,
        "rating": 8.6,
        "rotten_rating": "87%",
        "img": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
        "description": (
            "Група дослідників вирушає крізь червоточину в космосі, щоб забезпечити нове майбутнє для людства."
        ),
        "description_en": (
            "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival."
        ),
        "tmdb_id": 157336,
    },
    {
        "id": 4,
        "title": "Темний лицар",
        "title_en": "The Dark Knight",
        "category": "Movie",
        "genre": "Бойовик",
        "genres": ["Бойовик", "Кримінал", "Драма"],
        "year": 2008,
        "rating": 9.0,
        "rotten_rating": "94%",
        "img": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "description": (
            "Бетмен піднімає ставки у війні з криміналом за допомогою "
            "лейтенанта Джима Ґордона та прокурора Гарві Дента."
        ),
        "description_en": (
            "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, "
            "Batman must accept one of the greatest psychological and physical tests."
        ),
        "tmdb_id": 155,
    },
    {
        "id": 5,
        "title": "Початок",
        "title_en": "Inception",
        "category": "Movie",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Бойовик", "Пригоди"],
        "year": 2010,
        "rating": 8.8,
        "rotten_rating": "87%",
        "img": "https://image.tmdb.org/t/p/w500/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg",
        "description": (
            "Злодій, який краде корпоративні секрети через технологію спільного сновидіння, "
            "отримує завдання закарбувати ідею в підсвідомість директора."
        ),
        "description_en": (
            "A thief who steals corporate secrets through the use of dream-sharing technology "
            "is given the inverse task of planting an idea into the mind of a C.E.O."
        ),
        "tmdb_id": 27205,
    },
    {
        "id": 6,
        "title": "Дивні дива",
        "title_en": "Stranger Things",
        "category": "Series",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Драма", "Містика"],
        "year": 2016,
        "rating": 8.7,
        "rotten_rating": "92%",
        "img": "https://image.tmdb.org/t/p/w500/49WJfeN0moxb9IPfGn8AIqMGskD.jpg",
        "description": (
            "У маленькому містечку зникає хлопчик, і його друзі починають власні пошуки, "
            "стикаючись із таємними експериментами та надприродними силами."
        ),
        "description_en": (
            "When a young boy vanishes, a small town uncovers a mystery involving secret experiments, "
            "terrifying supernatural forces and one strange little girl."
        ),
        "tmdb_id": 66732,
    },
    {
        "id": 7,
        "title": "Пуститися берега",
        "title_en": "Breaking Bad",
        "category": "Series",
        "genre": "Кримінал",
        "genres": ["Кримінал", "Драма", "Трилер"],
        "year": 2008,
        "rating": 9.5,
        "rotten_rating": "96%",
        "img": "https://image.tmdb.org/t/p/w500/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
        "description": (
            "Вчитель хімії Волтер Вайт, дізнавшись про невиліковний рак легенів, "
            "починає виробляти метамфетамін разом зі своїм колишнім учнем."
        ),
        "description_en": (
            "A chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing "
            "and selling methamphetamine with a former student."
        ),
        "tmdb_id": 1396,
    },
    {
        "id": 8,
        "title": "Гра престолів",
        "title_en": "Game of Thrones",
        "category": "Series",
        "genre": "Фентезі",
        "genres": ["Фентезі", "Драма", "Пригоди"],
        "year": 2011,
        "rating": 9.2,
        "rotten_rating": "89%",
        "img": "https://image.tmdb.org/t/p/w500/1XS1oqL89opfnbLl8WnZY1O1uJx.jpg",
        "description": (
            "Дев'ять шляхетних родин ведуть жорстоку війну за контроль над Залізним троном Вестеросу, "
            "поки з півночі насувається давній ворог."
        ),
        "description_en": (
            "Nine noble families fight for control over the lands of Westeros, "
            "while an ancient enemy returns after being dormant for millennia."
        ),
        "tmdb_id": 1399,
    },
]


def fetch_tmdb_movies(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch popular movies from TMDB API with graceful degradation to local metadata fallback.
    Trace: T-033, T-034 (FR-012).
    """
    key = api_key or os.getenv("TMDB_API_KEY")
    if not key:
        logger.info("TMDB_API_KEY not configured. Using verified cached fallback metadata.")
        return FALLBACK_MOVIES

    url = f"https://api.themoviedb.org/3/movie/popular?api_key={key}&language=uk-UA&page=1"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MoviePlatform/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:  # nosec B310
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                results = payload.get("results", [])
                movies = []
                for idx, item in enumerate(results, start=1):
                    release_date = item.get("release_date")
                    year = int(release_date.split("-")[0]) if release_date else 2024
                    poster_path = item.get("poster_path")
                    img_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

                    movies.append({
                        "id": idx,
                        "title": item.get("title") or item.get("original_title", "Без назви"),
                        "title_en": item.get("original_title"),
                        "category": "Movie",
                        "genre": "Фантастика",
                        "genres": ["Фантастика", "Драма"],
                        "year": year,
                        "rating": round(float(item.get("vote_average", 0.0)), 1),
                        "rotten_rating": f"{int(item.get('vote_average', 0) * 10)}%",
                        "img": img_url,
                        "description": item.get("overview") or "Опис оновлюється.",
                        "description_en": item.get("overview"),
                        "tmdb_id": item.get("id"),
                    })
                return movies
    except Exception as e:
        logger.warning(f"Error fetching from TMDB API: {e}. Falling back to cached catalog.")

    return FALLBACK_MOVIES


def seed_movies_to_database(db: Session, movies_data: Optional[List[Dict[str, Any]]] = None) -> int:
    """
    Seed or update movies in database.
    """
    data = movies_data or FALLBACK_MOVIES
    count = 0
    for item in data:
        existing = db.query(Content).filter(
            (Content.id == item["id"]) | (Content.title == item["title"])
        ).first()

        if not existing:
            content_item = Content(
                id=item["id"],
                content_id=uuid.uuid4(),
                title=item["title"],
                title_en=item.get("title_en"),
                category=item.get("category", "Movie"),
                genre=item.get("genre", "Драма"),
                genres=item.get("genres", []),
                year=item.get("year", 2024),
                rating=item.get("rating", 0.0),
                rotten_rating=item.get("rotten_rating"),
                img=item.get("img"),
                description=item.get("description"),
                description_en=item.get("description_en"),
                tmdb_id=item.get("tmdb_id"),
            )
            db.add(content_item)
            count += 1
        else:
            # Update fields if needed
            existing.rating = item.get("rating", existing.rating)
            existing.rotten_rating = item.get("rotten_rating", existing.rotten_rating)
            if item.get("img"):
                existing.img = item.get("img")

    db.commit()
    return count


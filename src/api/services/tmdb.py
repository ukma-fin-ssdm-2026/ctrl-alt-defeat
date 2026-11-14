import json
import logging
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.db.models import Content
from src.api.services.genres import DEFAULT_GENRE, genres_from_tmdb, set_content_genres
from src.api.settings import env_int

logger = logging.getLogger(__name__)

# Fallback catalog metadata (FR-012 Graceful Degradation): used only while TMDB is not available.
# The titles have no TMDB ids; the first TMDB update adopts them by title and year or removes them
# (services/catalog_cleanup.py).
FALLBACK_MOVIES = [
    {
        "id": 1,
        "title": "Дюна: Частина друга",
        "title_en": "Dune: Part Two",
        "category": "Movie",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Бойовик", "Пригоди"],
        "year": 2024,
        "runtime": 166,
        "rating": 8.8,
        "rotten_rating": "93%",
        "img": "https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2TGpiom05.jpg",
        "description": (
            "Пол Атрід об'єднується з Чані та фременами, вирушаючи на шлях помсти проти змовників, які"
            "знищили його родину."
        ),
        "description_en": (
            "Paul Atreides unites with Chani and the Fremen while seeking revenge against the"
            "conspirators who destroyed his family."
        ),
    },
    {
        "id": 2,
        "title": "Оппенгеймер",
        "title_en": "Oppenheimer",
        "category": "Movie",
        "genre": "Драма",
        "genres": ["Драма", "Біографія", "Історія"],
        "year": 2023,
        "runtime": 180,
        "rating": 8.4,
        "rotten_rating": "93%",
        "img": "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
        "description": (
            "Історія життя американського фізика Роберта Оппенгеймера, який очолював «Проєкт" "Манхеттен»."
        ),
        "description_en": (
            "The story of American physicist J. Robert Oppenheimer and his role in the development of"
            "the atomic bomb."
        ),
    },
    {
        "id": 3,
        "title": "Інтерстеллар",
        "title_en": "Interstellar",
        "category": "Movie",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Драма", "Пригоди"],
        "year": 2014,
        "runtime": 169,
        "rating": 8.6,
        "rotten_rating": "87%",
        "img": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
        "description": (
            "Група дослідників вирушає крізь червоточину в космосі, щоб забезпечити нове майбутнє для" "людства."
        ),
        "description_en": (
            "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's" "survival."
        ),
    },
    {
        "id": 4,
        "title": "Темний лицар",
        "title_en": "The Dark Knight",
        "category": "Movie",
        "genre": "Бойовик",
        "genres": ["Бойовик", "Кримінал", "Драма"],
        "year": 2008,
        "runtime": 152,
        "rating": 9,
        "rotten_rating": "94%",
        "img": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "description": (
            "Бетмен стикається з хаотичним генієм — злочинцем на ім'я Джокер, який занурює Ґотем у" "хаос."
        ),
        "description_en": (
            "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman"
            "must accept one of the greatest psychological and physical tests."
        ),
    },
    {
        "id": 5,
        "title": "Початок",
        "title_en": "Inception",
        "category": "Movie",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Бойовик", "Трилер"],
        "year": 2010,
        "runtime": 148,
        "rating": 8.8,
        "rotten_rating": "87%",
        "img": "https://image.tmdb.org/t/p/w500/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg",
        "description": (
            "Злодій, який краде секрети через підсвідомість під час сну, отримує завдання впровадити"
            "ідею в голову мільярдера."
        ),
        "description_en": (
            "A thief who steals corporate secrets through the use of dream-sharing technology is given"
            "the inverse task of planting an idea."
        ),
    },
    {
        "id": 6,
        "title": "Втеча з Шоушенка",
        "title_en": "The Shawshank Redemption",
        "category": "Movie",
        "genre": "Драма",
        "genres": ["Драма"],
        "year": 1994,
        "runtime": 142,
        "rating": 9.3,
        "rotten_rating": "91%",
        "img": "https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",
        "description": (
            "Банкір Енді Дюфрейн потрапляє до в'язниці Шоушенк за вбивство, якого не скоював, де" "знаходить надію."
        ),
        "description_en": (
            "Over the course of several years, two convicts form a friendship, seeking consolation and,"
            "eventually, redemption."
        ),
    },
    {
        "id": 7,
        "title": "Форест Ґамп",
        "title_en": "Forrest Gump",
        "category": "Movie",
        "genre": "Драма",
        "genres": ["Драма", "Мелодрама"],
        "year": 1994,
        "runtime": 142,
        "rating": 8.8,
        "rotten_rating": "75%",
        "img": "https://image.tmdb.org/t/p/w500/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg",
        "description": (
            "Історія життя добродушного та простого чоловіка з Алабами, який ненавмисно стає учасником"
            "ключових подій епохи."
        ),
        "description_en": (
            "The presidencies of Kennedy and Johnson, the Vietnam War, and other historical events"
            "unfold from the perspective of an Alabama man."
        ),
    },
    {
        "id": 8,
        "title": "Той, хто біжить по лезу 2049",
        "title_en": "Blade Runner 2049",
        "category": "Movie",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Детектив", "Трилер"],
        "year": 2017,
        "runtime": 164,
        "rating": 8,
        "rotten_rating": "88%",
        "img": "https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg",
        "description": (
            "Офіцер поліції Лос-Анджелеса розкриває давню таємницю, яка може занурити залишки" "суспільства у хаос."
        ),
        "description_en": (
            "Young Blade Runner K's discovery of a long-buried secret leads him to track down former"
            "Blade Runner Rick Deckard."
        ),
    },
    {
        "id": 9,
        "title": "Паразити",
        "title_en": "Parasite",
        "category": "Movie",
        "genre": "Драма",
        "genres": ["Драма", "Трилер", "Комедія"],
        "year": 2019,
        "runtime": 132,
        "rating": 8.5,
        "rotten_rating": "99%",
        "img": "https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg",
        "description": (
            "Бідна родина хитрощами влаштовується працювати до будинку заможних людей, але ситуація"
            "виходить з-під контролю."
        ),
        "description_en": (
            "Greed and class discrimination threaten the newly formed symbiotic relationship between"
            "the wealthy Park family and the destitute Kim clan."
        ),
    },
    {
        "id": 10,
        "title": "Спасенний",
        "title_en": "Saved",
        "category": "Movie",
        "genre": "Драма",
        "genres": ["Драма", "Фантастика"],
        "year": 2026,
        "runtime": None,
        "rating": 8.4,
        "rotten_rating": "88%",
        "img": "https://picsum.photos/300/450?random=1",
        "description": "Драматична історія про виживання та моральний вибір у критичних умовах майбутнього.",
        "description_en": "A dramatic story about survival and moral choice in critical conditions of the future.",
    },
    {
        "id": 11,
        "title": "Дивні Дива",
        "title_en": "Stranger Things",
        "category": "Series",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Жахи", "Драма"],
        "year": 2016,
        "runtime": 51,
        "rating": 8.7,
        "rotten_rating": "92%",
        "img": "https://picsum.photos/300/450?random=5",
        "description": (
            "Зникнення хлопчика в містечку Гокінс розкриває таємницю секретних експериментів і" "надприродних сил."
        ),
        "description_en": (
            "When a young boy vanishes, a small town uncovers a mystery involving secret experiments,"
            "terrifying supernatural forces."
        ),
    },
    {
        "id": 12,
        "title": "Чорнобиль",
        "title_en": "Chernobyl",
        "category": "Series",
        "genre": "Драма",
        "genres": ["Драма", "Історія", "Трилер"],
        "year": 2019,
        "runtime": 65,
        "rating": 9.3,
        "rotten_rating": "95%",
        "img": "https://image.tmdb.org/t/p/w500/hlLXt2Stj6R38NT9PNtt8G4GBZo.jpg",
        "description": (
            "Хроніка катастрофи на Чорнобильській АЕС 1986 року та героїчні зусилля ліквідаторів" "наслідків."
        ),
        "description_en": (
            "In 1986, a Soviet nuclear plant, suffers a massive explosion which releases radioactive"
            "material across Europe."
        ),
    },
    {
        "id": 13,
        "title": "Гра престолів",
        "title_en": "Game of Thrones",
        "category": "Series",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Драма", "Пригоди"],
        "year": 2011,
        "runtime": 57,
        "rating": 9.2,
        "rotten_rating": "89%",
        "img": "https://image.tmdb.org/t/p/w500/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg",
        "description": (
            "Дев'ять шляхетних родин борються за контроль над землями Вестероса, тоді як стародавній"
            "ворог повертається."
        ),
        "description_en": (
            "Nine noble families fight for control over the lands of Westeros, while an ancient enemy"
            "returns after being dormant."
        ),
    },
    {
        "id": 14,
        "title": "Пуститися берега",
        "title_en": "Breaking Bad",
        "category": "Series",
        "genre": "Драма",
        "genres": ["Драма", "Кримінал", "Трилер"],
        "year": 2008,
        "runtime": 47,
        "rating": 9.5,
        "rotten_rating": "96%",
        "img": "https://image.tmdb.org/t/p/w500/ztkUQFLlC19CCMYHW9o1zWhJRNq.jpg",
        "description": (
            "Хворий на рак вчитель хімії об'єднується з колишнім учнем заради виробництва та продажу" "метамфетаміну."
        ),
        "description_en": (
            "A chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and"
            "selling methamphetamine with a former student."
        ),
    },
    {
        "id": 15,
        "title": "Справжній детектив",
        "title_en": "True Detective",
        "category": "Series",
        "genre": "Детектив",
        "genres": ["Детектив", "Кримінал", "Драма"],
        "year": 2014,
        "runtime": 58,
        "rating": 8.9,
        "rotten_rating": "83%",
        "img": "https://image.tmdb.org/t/p/w500/aVnwbDe7K0Xv7d3cE4yX0V7mY7Y.jpg",
        "description": (
            "Детективи розслідують складні та містичні злочини протягом багатьох років, занурюючись у" "власні демони."
        ),
        "description_en": (
            "Seasonal anthology series in which police investigations unearth the personal and"
            "professional secrets of those involved."
        ),
    },
    {
        "id": 16,
        "title": "Пацани",
        "title_en": "The Boys",
        "category": "Series",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Бойовик", "Комедія"],
        "year": 2019,
        "runtime": 60,
        "rating": 8.7,
        "rotten_rating": "93%",
        "img": "https://image.tmdb.org/t/p/w500/stTEycfG9928HYGEISBFaG1ngjM.jpg",
        "description": (
            "Загін пильних візионерів намагається викрити корумпованих супергероїв, які зловживають"
            "своїми суперсилами."
        ),
        "description_en": (
            "A group of vigilantes set out to take down corrupt superheroes who abuse their" "superpowers."
        ),
    },
    {
        "id": 17,
        "title": "Останні з нас",
        "title_en": "The Last of Us",
        "category": "Series",
        "genre": "Драма",
        "genres": ["Драма", "Жахи", "Пригоди"],
        "year": 2023,
        "runtime": 56,
        "rating": 8.8,
        "rotten_rating": "96%",
        "img": "https://image.tmdb.org/t/p/w500/uKvVjHNqB5VmOrdxqAt2F7J78ED.jpg",
        "description": "Контрабандист Джоел має супроводжувати дівчинку Еллі крізь зруйновані США після пандемії.",
        "description_en": (
            "After a global pandemic destroys civilization, a hardened survivor takes charge of a"
            "14-year-old girl who may be humanity's last hope."
        ),
    },
    {
        "id": 18,
        "title": "Ужас з могили",
        "title_en": "Grave Horror",
        "category": "Series",
        "genre": "Жахи",
        "genres": ["Жахи", "Детектив"],
        "year": 2021,
        "runtime": None,
        "rating": 7.2,
        "rotten_rating": "65%",
        "img": "https://picsum.photos/300/450?random=3",
        "description": "Антологія моторошних міських легенд з темного минулого.",
        "description_en": "An anthology of creepy urban legends from the dark past.",
    },
    {
        "id": 19,
        "title": "Корона",
        "title_en": "The Crown",
        "category": "Series",
        "genre": "Драма",
        "genres": ["Драма", "Історія", "Біографія"],
        "year": 2016,
        "runtime": 58,
        "rating": 8.6,
        "rotten_rating": "89%",
        "img": "https://image.tmdb.org/t/p/w500/1MvuU91VjH3pM91sK7iW2Y9R55m.jpg",
        "description": "Хроніка життя королеви Єлизавети II від її весілля до сьогодення.",
        "description_en": (
            "Follows the political rivalries and romance of Queen Elizabeth II's reign and the events"
            "that shaped the second half of the twentieth century."
        ),
    },
    {
        "id": 20,
        "title": "Фарґо",
        "title_en": "Fargo",
        "category": "Series",
        "genre": "Драма",
        "genres": ["Драма", "Кримінал", "Трилер"],
        "year": 2014,
        "runtime": 53,
        "rating": 8.9,
        "rotten_rating": "93%",
        "img": "https://image.tmdb.org/t/p/w500/5Wk0N0hGz0o2C0X0G7W5t6v1n5h.jpg",
        "description": "Антологія історій про кримінальний світ провінційної Америки з чорним гумором.",
        "description_en": (
            "Various chronological stories involving disparate characters all connected in some way"
            "around snowy Midwestern towns."
        ),
    },
    {
        "id": 21,
        "title": "Шрек",
        "title_en": "Shrek",
        "category": "Cartoons",
        "genre": "Комедія",
        "genres": ["Комедія", "Пригоди", "Фантастика"],
        "year": 2001,
        "runtime": 90,
        "rating": 7.9,
        "rotten_rating": "90%",
        "img": "https://picsum.photos/300/450?random=6",
        "description": "Огр на ім'я Шрек вирушає рятувати принцесу, щоб повернути своє болото.",
        "description_en": "A grumpy ogre goes on a quest to rescue a princess and get his swamp back.",
    },
    {
        "id": 22,
        "title": "Павутина всесвітів",
        "title_en": "Spider-Man: Across the Spider-Verse",
        "category": "Cartoons",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Бойовик", "Пригоди"],
        "year": 2023,
        "runtime": 140,
        "rating": 8.7,
        "rotten_rating": "95%",
        "img": "https://image.tmdb.org/t/p/w500/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg",
        "description": "Майлз Моралес вирушає у подорож мультивсесвітом разом із новими супергероями.",
        "description_en": (
            "Miles Morales catapults across the Multiverse, where he encounters a team of Spider-People"
            "charged with protecting its very existence."
        ),
    },
    {
        "id": 23,
        "title": "Віднесена примарами",
        "title_en": "Spirited Away",
        "category": "Cartoons",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Пригоди", "Драма"],
        "year": 2001,
        "runtime": 125,
        "rating": 8.6,
        "rotten_rating": "97%",
        "img": "https://image.tmdb.org/t/p/w500/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg",
        "description": (
            "Маленька дівчинка Тіхіро потрапляє до загадкового світу богів та духів, де її батьків"
            "перетворюють на свиней."
        ),
        "description_en": (
            "During her family's move to the suburbs, a sullen 10-year-old girl wanders into a world"
            "ruled by gods, witches, and spirits."
        ),
    },
    {
        "id": 24,
        "title": "Думками навиворіт",
        "title_en": "Inside Out",
        "category": "Cartoons",
        "genre": "Комедія",
        "genres": ["Комедія", "Драма", "Пригоди"],
        "year": 2015,
        "runtime": 95,
        "rating": 8.1,
        "rotten_rating": "98%",
        "img": "https://image.tmdb.org/t/p/w500/2H1TmgdfNtsKlU9jKdeNyYL5y8T.jpg",
        "description": "Емоції Радість, Сум, Гнів, Страх та Відраза керують внутрішнім світом дівчинки Райлі.",
        "description_en": (
            "After young Riley is uprooted from her Midwest life and moved to San Francisco, her"
            "emotions - Joy, Fear, Anger, Disgust and Sadness - conflict on how best to navigate a new"
            "city, house, and school."
        ),
    },
    {
        "id": 25,
        "title": "Волл-і",
        "title_en": "WALL·E",
        "category": "Cartoons",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Пригоди", "Мелодрама"],
        "year": 2008,
        "runtime": 98,
        "rating": 8.4,
        "rotten_rating": "95%",
        "img": "https://image.tmdb.org/t/p/w500/hBGRgrjkjuoY2yV56A9eA890T5t.jpg",
        "description": (
            "Маленький робот-прибиральник залишається на покинутій Землі та випадково вирушає у" "космічну пригоду."
        ),
        "description_en": (
            "In the distant future, a small waste-collecting robot inadvertently embarks on a space"
            "journey that will ultimately decide the fate of mankind."
        ),
    },
    {
        "id": 26,
        "title": "Коко",
        "title_en": "Coco",
        "category": "Cartoons",
        "genre": "Драма",
        "genres": ["Драма", "Музика", "Пригоди"],
        "year": 2017,
        "runtime": 105,
        "rating": 8.4,
        "rotten_rating": "97%",
        "img": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
        "description": "Хлопчик Мігель мріє стати музикантом і випадково потрапляє до Країни Мертвих.",
        "description_en": (
            "Aspiring musician Miguel, confronted with his family's ancestral ban on music, enters the"
            "Land of the Dead to find his great-great-grandfather."
        ),
    },
    {
        "id": 27,
        "title": "Король Лев",
        "title_en": "The Lion King",
        "category": "Cartoons",
        "genre": "Драма",
        "genres": ["Драма", "Пригоди"],
        "year": 1994,
        "runtime": 88,
        "rating": 8.5,
        "rotten_rating": "93%",
        "img": "https://image.tmdb.org/t/p/w500/sKCr78MXSLixwmZ8DyJLrpMsd15.jpg",
        "description": (
            "Історія маленького левеняти Сімби, яке проходить через зраду та вигнання, щоб зайняти своє"
            "законне місце."
        ),
        "description_en": (
            "Lion prince Simba and his father are targeted by his bitter uncle, who wants to ascend the"
            "throne himself."
        ),
    },
    {
        "id": 28,
        "title": "Як приборкати дракона",
        "title_en": "How to Train Your Dragon",
        "category": "Cartoons",
        "genre": "Пригоди",
        "genres": ["Пригоди", "Фантастика", "Комедія"],
        "year": 2010,
        "runtime": 98,
        "rating": 8.1,
        "rotten_rating": "99%",
        "img": "https://image.tmdb.org/t/p/w500/ygGgaVfY6bBvM6WjXq8vXqT1pZ2.jpg",
        "description": "Незграбний вікінг Гіккі дружить з рідкісним драконом і назавжди змінює життя свого селища.",
        "description_en": (
            "A hapless young Viking who aspires to hunt dragons becomes the unlikely friend of a young"
            "dragon of a certain species."
        ),
    },
    {
        "id": 29,
        "title": "Душа",
        "title_en": "Soul",
        "category": "Cartoons",
        "genre": "Драма",
        "genres": ["Драма", "Комедія", "Фантастика"],
        "year": 2020,
        "runtime": 100,
        "rating": 8,
        "rotten_rating": "95%",
        "img": "https://image.tmdb.org/t/p/w500/hm58Jw4Lw8OIeECIq5qyPYhAeRJ.jpg",
        "description": "Шкільний вчитель музики випадково потрапляє у світ душ до того, як його мрія здійснитися.",
        "description_en": (
            "After a pianist lands a gig at a jazz club, he is suddenly separated from his soul and"
            "must find his way back with the help of an infant soul."
        ),
    },
    {
        "id": 30,
        "title": "Джейн Доу проти Корнелла",
        "title_en": "Jane Doe vs Cornell",
        "category": "Cartoons",
        "genre": "Документальний",
        "genres": ["Документальний", "Драма"],
        "year": 2026,
        "runtime": None,
        "rating": 9,
        "rotten_rating": "95%",
        "img": "https://picsum.photos/300/450?random=4",
        "description": "Глибоке документальне анімаційне розслідування юридичних баталій у галузі технологій.",
        "description_en": "An animated documentary investigation of legal battles in technology.",
    },
]


TMDB_API = "https://api.themoviedb.org/3"
TMDB_IMAGES = "https://image.tmdb.org/t/p/w500"
# Small pictures: photos of actors, posters of seasons
TMDB_THUMBS = "https://image.tmdb.org/t/p/w185"
TMDB_PAGE_SIZE = 20
# TMDB serves at most 500 pages of a list
TMDB_MAX_PAGE = 500
# How many titles of each section the catalog keeps (movies, series, cartoons)
TITLES_PER_SECTION = env_int("TMDB_TITLES_PER_SECTION", 500, minimum=1, maximum=500)
# Selection rules: titles with fewer votes are obscure and often have no texts, posters or a stable rating
MIN_VOTE_COUNT = 100
# Some candidates are dropped (no poster, release year or description), so a little more is requested
CANDIDATE_RESERVE = 1.2
# Parallel detail requests: ~40 requests per second, below the TMDB limit (~50 per second)
DETAIL_WORKERS = 8
# HTTP 429 (rate limit): wait as TMDB asks (Retry-After, at most MAX_RETRY_AFTER s) and retry
RATE_LIMIT_RETRIES = 3
MAX_RETRY_AFTER = 10
NO_DESCRIPTION = "Опис оновлюється."

# Catalog sections: category in the catalog, TMDB media type and discover filters.
# Cartoons are animated movies (TMDB genre 16), so "Movie" excludes them; news, reality and talk shows
# are not offered as series.
SECTIONS = [
    ("Movie", "movie", {"without_genres": "16"}),
    ("Series", "tv", {"without_genres": "10763,10764,10767"}),
    ("Cartoons", "movie", {"with_genres": "16"}),
]


class TmdbError(Exception):
    """TMDB is not configured or did not answer."""


def tmdb_kind(category: Optional[str]) -> str:
    """TMDB media type of a catalog title: movie and TV ids are separate sequences."""
    return "tv" if category == "Series" else "movie"


def _retry_after(error: urllib.error.HTTPError) -> float:
    """Seconds to wait after HTTP 429: the Retry-After header (1 s if missing), at most MAX_RETRY_AFTER."""
    try:
        seconds = float((error.headers or {}).get("Retry-After") or 1)
    except (TypeError, ValueError):
        seconds = 1.0
    return min(max(seconds, 0.0), MAX_RETRY_AFTER)


def _tmdb_get(path: str, params: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    GET a TMDB v3 endpoint. Accepts both the v3 API key and the v4 read access token.
    HTTP 429 (too many requests) is retried up to RATE_LIMIT_RETRIES times after the time TMDB asks for.
    """
    query = dict(params)
    headers = {"User-Agent": "PislyaTytriv/1.0", "Accept": "application/json"}
    if api_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        query["api_key"] = api_key
    url = f"{TMDB_API}{path}?{urllib.parse.urlencode(query)}"
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        request = urllib.request.Request(url, headers=headers)
        try:
            # Only the fixed https://api.themoviedb.org address is requested
            with urllib.request.urlopen(request, timeout=10) as response:  # nosec B310
                if response.status != 200:
                    raise TmdbError(f"TMDB answered {response.status}")
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == RATE_LIMIT_RETRIES:
                raise
            time.sleep(_retry_after(error))
    raise TmdbError("TMDB rate limit")  # pragma: no cover - the loop always returns or raises


def _year(date: Optional[str]) -> Optional[int]:
    try:
        return int(date[:4]) if date else None
    except ValueError:
        return None


def _english(details: Dict[str, Any]) -> Dict[str, Any]:
    """English title and overview from `append_to_response=translations` (US English first)."""
    translations = (details.get("translations") or {}).get("translations") or []
    english = [t for t in translations if t.get("iso_639_1") == "en"]
    english.sort(key=lambda t: t.get("iso_3166_1") != "US")
    return (english[0].get("data") or {}) if english else {}


def _runtime(kind: str, details: Dict[str, Any]) -> Optional[int]:
    if kind == "tv":
        runtimes = details.get("episode_run_time") or []
        return runtimes[0] if runtimes else None
    return details.get("runtime") or None


# Details of the page of a title (US-013)
CAST_LIMIT = 10
CREW_LIMIT = 3
SIMILAR_LIMIT = 20
# A YouTube video id: only these characters end up in the embedded player address
YOUTUBE_KEY = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
WRITER_JOBS = ("Screenplay", "Writer", "Story", "Novel")


def _thumb(path: Optional[str]) -> Optional[str]:
    return f"{TMDB_THUMBS}{path}" if path else None


def pick_trailer(videos: Dict[str, Any], language: str) -> Optional[str]:
    """
    YouTube key of the best trailer in `language` (uk/en): a trailer before a teaser, an official one first,
    then the newest. None if TMDB has no YouTube video in that language.
    """
    candidates = [
        video
        for video in (videos or {}).get("results") or []
        if video.get("site") == "YouTube"
        and video.get("iso_639_1") == language
        and video.get("type") in ("Trailer", "Teaser")
        and YOUTUBE_KEY.match(str(video.get("key") or ""))
    ]
    # Stable sorts: newest first, then trailers before teasers and official videos first
    candidates.sort(key=lambda video: video.get("published_at") or "", reverse=True)
    candidates.sort(key=lambda video: (video.get("type") != "Trailer", not video.get("official")))
    return candidates[0]["key"] if candidates else None


def pick_english_poster(images: Dict[str, Any]) -> Optional[str]:
    """
    Poster for the English interface: the best rated English one, otherwise the best one without text
    (`iso_639_1` null). None if TMDB has neither: the interface then shows the main poster.
    """
    posters = [poster for poster in (images or {}).get("posters") or [] if poster.get("file_path")]
    for language in ("en", None):
        candidates = [poster for poster in posters if poster.get("iso_639_1") == language]
        if candidates:
            best = max(candidates, key=lambda poster: (poster.get("vote_average") or 0, poster.get("vote_count") or 0))
            return f"{TMDB_IMAGES}{best['file_path']}"
    return None


def cast_from_credits(credits: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The first CAST_LIMIT actors in billing order: name, role and photo."""
    cast = sorted((credits or {}).get("cast") or [], key=lambda person: person.get("order", 999))
    return [
        {
            "name": person.get("name"),
            "character": person.get("character") or None,
            "photo": _thumb(person.get("profile_path")),
        }
        for person in cast[:CAST_LIMIT]
        if person.get("name")
    ]


def _unique_names(people: List[Dict[str, Any]]) -> List[str]:
    names: List[str] = []
    for person in people:
        name = person.get("name")
        if name and name not in names:
            names.append(name)
    return names[:CREW_LIMIT]


def crew_from_details(kind: str, details: Dict[str, Any]) -> Dict[str, List[str]]:
    """Directors and writers (movies), creators (series)."""
    crew = (details.get("credits") or {}).get("crew") or []
    return {
        "directors": _unique_names([person for person in crew if person.get("job") == "Director"]),
        "writers": _unique_names([person for person in crew if person.get("job") in WRITER_JOBS]),
        "creators": _unique_names(details.get("created_by") or []) if kind == "tv" else [],
    }


def series_from_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Seasons and episodes of a series, its status and the next episode."""
    next_episode = details.get("next_episode_to_air") or None
    seasons = sorted(details.get("seasons") or [], key=lambda season: season.get("season_number", 0))
    return {
        "status": details.get("status"),
        "number_of_seasons": details.get("number_of_seasons"),
        "number_of_episodes": details.get("number_of_episodes"),
        "last_air_date": details.get("last_air_date"),
        "next_episode": (
            {
                "air_date": next_episode.get("air_date"),
                "season_number": next_episode.get("season_number"),
                "episode_number": next_episode.get("episode_number"),
                "name": next_episode.get("name") or None,
            }
            if next_episode
            else None
        ),
        "seasons": [
            {
                "season_number": season.get("season_number"),
                "name": season.get("name"),
                "episode_count": season.get("episode_count"),
                "air_date": season.get("air_date") or None,
                "poster": _thumb(season.get("poster_path")),
            }
            for season in seasons
        ],
    }


def page_details(kind: str, details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fields for the page of a title (US-013): trailers, cast and crew, series details, film series and
    similar titles. Empty when the details request failed, so an update never erases stored data.
    """
    if not details:
        return {}
    collection = details.get("belongs_to_collection") or None
    similar = [title.get("id") for title in ((details.get("recommendations") or {}).get("results") or [])]
    return {
        "img_en": pick_english_poster(details.get("images")),
        "trailer_uk": pick_trailer(details.get("videos"), "uk"),
        "trailer_en": pick_trailer(details.get("videos"), "en"),
        "cast_members": cast_from_credits(details.get("credits")),
        "crew_members": crew_from_details(kind, details),
        "series_details": series_from_details(details) if kind == "tv" else None,
        "similar_tmdb_ids": [tmdb_id for tmdb_id in similar if isinstance(tmdb_id, int)][:SIMILAR_LIMIT],
        "collection_id": collection.get("id") if collection else None,
        "collection_name": collection.get("name") if collection else None,
    }


def build_catalog_item(category: str, kind: str, item: Dict[str, Any], details: Dict[str, Any]) -> Optional[Dict]:
    """
    Catalog fields of one TMDB title (list entry + details in Ukrainian with English translations).
    Titles without a poster, a release year or a description (Ukrainian or English) are skipped (None).
    """
    data = {**item, **details}
    poster = data.get("poster_path")
    year = _year(data.get("release_date") if kind == "movie" else data.get("first_air_date"))
    english = _english(details)
    description = (data.get("overview") or english.get("overview") or "").strip()
    if not poster or year is None or not description:
        return None

    title_key = "title" if kind == "movie" else "name"
    original = data.get("original_title" if kind == "movie" else "original_name")
    title_en = english.get(title_key) or (original if data.get("original_language") == "en" else None)
    genre_ids = [genre["id"] for genre in details.get("genres") or []] or item.get("genre_ids") or []
    genres = genres_from_tmdb(genre_ids, kind) or [DEFAULT_GENRE]
    if category == "Cartoons" and "Мультфільм" not in genres:
        genres = ["Мультфільм", *genres]
    vote = float(data.get("vote_average") or 0.0)

    return {
        "tmdb_id": data["id"],
        "category": category,
        "title": data.get(title_key) or title_en or original or "Без назви",
        "title_en": title_en or original,
        "genre": genres[0],
        "genres": genres,
        "year": year,
        "runtime": _runtime(kind, details),
        "rating": round(vote, 1),
        "rotten_rating": f"{int(vote * 10)}%",
        "img": f"{TMDB_IMAGES}{poster}",
        "description": description,
        "description_en": english.get("overview") or None,
        **page_details(kind, details),
    }


def _details(kind: str, tmdb_id: int, api_key: str) -> Dict[str, Any]:
    """Details with translations; a failure leaves the list data only (no runtime, no English texts)."""
    try:
        return _tmdb_get(
            f"/{kind}/{int(tmdb_id)}",
            {
                "language": "uk-UA",
                # One request: English texts and posters, trailers, cast and crew, similar titles (US-013)
                "append_to_response": "translations,videos,credits,recommendations,images",
                "include_video_language": "uk,en",
                # Posters for the English interface: English ones and ones without text
                "include_image_language": "en,null",
            },
            api_key,
        )
    except Exception as error:  # one title must not stop the whole import
        logger.warning("TMDB details of %s %s failed: %s", kind, tmdb_id, error)
        return {}


def _discover_page(kind: str, filters: Dict[str, Any], page: int, api_key: str) -> List[Dict[str, Any]]:
    """One page of a section list: popular, not adult, with at least MIN_VOTE_COUNT votes."""
    params = {
        "language": "uk-UA",
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "vote_count.gte": MIN_VOTE_COUNT,
        "page": page,
        **filters,
    }
    try:
        return _tmdb_get(f"/discover/{kind}", params, api_key).get("results") or []
    except TmdbError:
        raise
    except Exception as error:
        raise TmdbError(f"TMDB list request failed: {error}") from error


def _fetch_section(
    pool: ThreadPoolExecutor,
    section: Tuple[str, str, Dict[str, Any]],
    per_section: int,
    api_key: str,
    seen: set,
) -> List[Dict[str, Any]]:
    """
    `per_section` titles of one section in popularity order. Candidates are built in batches (details in
    parallel, each turned into a small catalog item right away, so the large detail answers are not kept);
    when some are dropped by the selection rules, the next candidates from the list replace them.
    """
    category, kind, filters = section
    kept: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    page, exhausted = 1, False
    while len(kept) < per_section:
        wanted = math.ceil((per_section - len(kept)) * CANDIDATE_RESERVE)
        while len(pending) < wanted and not exhausted:
            results = _discover_page(kind, filters, page, api_key)
            for item in results:
                key = (kind, item.get("id"))
                if item.get("id") is None or key in seen:
                    continue
                seen.add(key)
                pending.append(item)
            exhausted = len(results) < TMDB_PAGE_SIZE or page >= TMDB_MAX_PAGE
            page += 1
        if not pending:
            break
        batch, pending = pending[:wanted], pending[wanted:]
        built = pool.map(
            lambda item: build_catalog_item(category, kind, item, _details(kind, item["id"], api_key)), batch
        )
        kept.extend(item for item in built if item is not None)
    return kept[:per_section]


def fetch_tmdb_catalog(api_key: str, per_section: int = TITLES_PER_SECTION) -> List[Dict[str, Any]]:
    """
    Popular movies, series and cartoons from TMDB (FR-012): `per_section` titles of each section
    (500 by default), Ukrainian texts with English fallback, real genres, runtime and posters.

    Selection rules: sorted by popularity, no adult titles, at least MIN_VOTE_COUNT votes; cartoons are
    animated movies, movies exclude animation, series exclude news, reality and talk shows; a title needs
    a poster, a release year and a description. Raises TmdbError if a list request fails.
    """
    if not api_key:
        raise TmdbError("TMDB_API_KEY is not configured")

    catalog: List[Dict[str, Any]] = []
    seen: set = set()
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
        for section in SECTIONS:
            catalog.extend(_fetch_section(pool, section, per_section, api_key, seen))
    return catalog


def fetch_tmdb_movies(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Catalog from TMDB with graceful degradation to the built-in metadata.
    Trace: T-033, T-034 (FR-012).
    """
    key = api_key or os.getenv("TMDB_API_KEY")
    if not key:
        logger.info("TMDB_API_KEY not configured. Using verified cached fallback metadata.")
        return FALLBACK_MOVIES
    try:
        catalog = fetch_tmdb_catalog(key)
    except Exception as error:  # any TMDB problem falls back to the built-in catalog
        logger.warning("Error fetching from TMDB API: %s. Falling back to cached catalog.", error)
        return FALLBACK_MOVIES
    return catalog or FALLBACK_MOVIES


@dataclass
class SyncResult:
    added: int = 0
    updated: int = 0
    skipped: int = 0


def _find_existing(db: Session, item: Dict[str, Any]) -> Optional[Content]:
    """
    The catalog row of an item, if the catalog already has it.
    Titles are matched by TMDB id of the same media type, never by the internal numeric id
    (the internal id of an imported title has nothing to do with the existing rows).
    A row without tmdb_id (old data, built-in titles) is adopted by an exact title and release year.
    """
    tmdb_id = item.get("tmdb_id")
    if tmdb_id is not None:
        # Movies and series are numbered separately by TMDB: the same number of the other media type
        # is a different title, so only rows of the same type match
        kind = tmdb_kind(item.get("category"))
        for existing in db.query(Content).filter(Content.tmdb_id == tmdb_id).order_by(Content.id):
            if tmdb_kind(existing.category) == kind:
                return existing
    legacy = db.query(Content).filter(Content.title == item["title"])
    if item.get("year") is not None:
        # Same name, different film (e.g. a remake): the release year must match too
        legacy = legacy.filter(Content.year.between(item["year"] - 1, item["year"] + 1))
    if tmdb_id is not None:
        legacy = legacy.filter(Content.tmdb_id.is_(None))
    return legacy.first()


UPDATED_FIELDS = ("title", "title_en", "category", "year", "runtime", "rating", "rotten_rating", "img")
# Details of the page of a title: replaced as a whole whenever the details request succeeded
PAGE_FIELDS = (
    "img_en",
    "trailer_uk",
    "trailer_en",
    "cast_members",
    "crew_members",
    "series_details",
    "similar_tmdb_ids",
    "collection_id",
    "collection_name",
)


def _update(db: Session, content: Content, item: Dict[str, Any]) -> None:
    for field in UPDATED_FIELDS:
        value = item.get(field)
        if value is not None and value != "":
            setattr(content, field, value)
    # Keep a real description instead of the placeholder
    for field in ("description", "description_en"):
        value = item.get(field)
        if value and value != NO_DESCRIPTION:
            setattr(content, field, value)
    # No details (the request failed): the stored page data stays; otherwise it is replaced, a removed
    # trailer or a title that left a film series included
    if "cast_members" in item:
        for field in PAGE_FIELDS:
            setattr(content, field, item.get(field))
    if item.get("tmdb_id") is not None and content.tmdb_id is None:
        content.tmdb_id = item["tmdb_id"]
    if item.get("genres") and content.content_id is not None:
        set_content_genres(db, content, item["genres"])


def sync_catalog(db: Session, items: List[Dict[str, Any]]) -> SyncResult:
    """
    Add new titles and update existing ones (FR-012). Titles are never deleted:
    reviews, ratings and lists of users keep pointing to them.
    """
    result = SyncResult()
    next_id = (db.query(func.max(Content.id)).scalar() or 0) + 1
    for item in items:
        existing = _find_existing(db, item)
        if existing is not None:
            _update(db, existing, item)
            result.updated += 1
            continue

        # The built-in catalog keeps its numbers on an empty database; imported titles get the next free one
        wanted = item.get("id")
        if wanted is None or db.get(Content, wanted) is not None:
            wanted = next_id
        next_id = max(next_id, wanted + 1)
        content = Content(
            id=wanted,
            content_id=uuid.uuid4(),
            title=item["title"],
            title_en=item.get("title_en"),
            category=item.get("category", "Movie"),
            genre=item.get("genre") or DEFAULT_GENRE,
            genres=item.get("genres", []),
            year=item.get("year", 2024),
            runtime=item.get("runtime"),
            rating=item.get("rating", 0.0),
            rotten_rating=item.get("rotten_rating"),
            img=item.get("img"),
            description=item.get("description"),
            description_en=item.get("description_en"),
            tmdb_id=item.get("tmdb_id"),
            **{field: item.get(field) for field in PAGE_FIELDS},
        )
        try:
            # Savepoint: an old local SQLite database still has UNIQUE(tmdb_id) (see upgrade_content_tmdb_uniqueness);
            # there a series with the number of a movie is skipped instead of failing the whole import
            with db.begin_nested():
                db.add(content)
                db.flush()
        except IntegrityError:
            logger.info(
                "Skipped TMDB %s (%s): the number is taken in this database.", item.get("tmdb_id"), item["title"]
            )
            result.skipped += 1
            continue
        set_content_genres(db, content, [item.get("genre"), *item.get("genres", [])])
        result.added += 1

    db.commit()
    return result


def seed_movies_to_database(db: Session, movies_data: Optional[List[Dict[str, Any]]] = None) -> int:
    """Seed or update the catalog; returns the number of added titles."""
    return sync_catalog(db, movies_data or FALLBACK_MOVIES).added


def seed_catalog_if_empty(db: Session) -> int:
    """
    Fill an empty catalog on application startup (FR-012), so a fresh database is usable
    without running scripts/seed_movies.py manually. Returns the number of titles added.
    Disabled with AUTO_SEED_CATALOG=false.

    Reliability (finding 13): only the built-in titles, without any network call. The startup used to
    import the whole TMDB catalog here (about 300 requests); while it ran, the service answered nothing
    and the hosting health check could fail the deploy. The TMDB import now runs in the background
    (services/catalog_sync.start_in_background) and replaces the built-in titles when it finishes.
    """
    if os.getenv("AUTO_SEED_CATALOG", "true").lower() in ("false", "0", "no"):
        return 0
    try:
        if db.query(Content.id).first() is not None:
            return 0
        added = seed_movies_to_database(db, FALLBACK_MOVIES)
    except SQLAlchemyError as error:
        # Never block the API startup: e.g. an old local database without newer columns
        db.rollback()
        logger.warning(
            "Catalog auto-seed skipped (%s). If the database schema is outdated, recreate app.db.",
            error.__class__.__name__,
        )
        return 0
    logger.info("Catalog was empty: seeded %s titles.", added)
    return added

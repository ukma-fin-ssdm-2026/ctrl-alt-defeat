# Звіт про надійність (Лабораторна робота 9)

**Проєкт:** «Після титрів» (`ctrl-alt-defeat`)  
**Джерело знахідок:** [`scavenger-hunt.md`](scavenger-hunt.md) — 17 ризиків, класифікованих за ланцюгом «несправність → помилка → відмова».  
**Тести надійності:** [`tests/reliability/`](../../tests/reliability) (бекенд) і [`frontend/src/reliability/`](../../frontend/src/reliability) (фронтенд); запускаються окремим job `reliability` у CI.

Кожен учасник заповнює свій розділ у пункті 2: до/після, застосовані патерни, режим відмови й відновлення, тести.

---

## 1. Усі знайдені проблеми

| № | Кат. | Проблема | Критичність | Хто відповідає | Статус |
|---|---|---|---|---|---|
| 1 | A, D | Автор коментаря з тіла запиту: гість без токена коментує від імені іншого користувача | Висока | Учасник 1 | Відкрито |
| 2 | A | Гонитва при додаванні до «До перегляду»: `500` замість `409` | Середня | Іван Ліфєнцєв | **Виправлено** (PR #205) |
| 3 | A | Немає глобального обробника непередбачених винятків | Середня | Учасник 1 | Відкрито |
| 4 | B | Запис OpenAPI під час старту без обробки `OSError` | Середня | Іван Ліфєнцєв | **Виправлено** (PR #205) |
| 5 | C | Пошук без `max_length`, рік без меж (`500` на завеликому році) | Середня | Учасник 1 | Відкрито |
| 6 | D, C | Зведення відгуків падає на оцінці `None` | Низька | Іван Ліфєнцєв | **Виправлено** (PR #205) |
| 7 | D, A | Перевірка пароля: широкий `except` без логування; пошкоджений хеш давав `500` | Низька → **Середня** (див. 2.4) | Михайло Крилов | **Виправлено** (PR #206) |
| 8 | E | N+1 запитів у списку «Переглянуте» | Середня | Юлія Галка | **Виправлено** (PR #218) |
| 9 | C | Числовий `id` фільму без меж: `500` замість `404` | Середня | Учасник 1 | Відкрито |
| 10 | B | БД без тайм-аутів з'єднання й запиту | Висока | Юлія Галка | **Виправлено** (PR #218) |
| 11 | B | Старт не переживає недоступну БД | Висока | Юлія Галка | **Виправлено** (PR #218) |
| 12 | A | Гонитва при реєстрації та в «Переглянутому» | Середня | Юлія Галка | **Виправлено** (PR #218) |
| 13 | E | Повний імпорт TMDB синхронно під час старту | Середня | Михайло Крилов | **Виправлено** (PR #206) |
| 14 | B | HTTP-клієнт фронтенду без тайм-ауту | Середня | Михайло Крилов | **Виправлено** (PR #206) |
| 15 | C | `int(os.getenv(...))` під час імпорту модулів | Низька | Михайло Крилов | **Виправлено** (PR #206) |
| 16 | D | Стан оновлення каталогу лише в пам'яті процесу | Низька | Михайло Крилов | **Виправлено** (PR #206) |
| 17 | A | `user_id` / `author_name` коментаря з тіла запиту | Середня | Учасник 1 (разом із 1) | Відкрито |

---

## 2. Виправлення, патерни, режими відмов і відновлення

### 2.1. Іван Ліфєнцєв — знахідки 2, 4, 6 (PR #205)

_Заповнює Іван Ліфєнцєв: до/після, патерн, швидка чи безпечна відмова, що бачить користувач, як система відновлюється, тести._

### 2.2. Учасник 1 — знахідки 1, 3, 5, 9, 17

_Заповнює учасник 1._

### 2.3. Юлія Галка — знахідки 8, 10, 11, 12

#### Знахідка 10. Відсутність тайм-аутів бази даних (B, висока)

**До:** у `src/api/db/database.py` підключення до PostgreSQL не мало явно заданих тайм-аутів. Якщо база даних не відповідала, операції могли тривалий час очікувати завершення.

```python
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
```

**Після:** додано обмеження часу підключення, виконання SQL-запитів та очікування з'єднання з пулу.

```python
CONNECT_TIMEOUT_SECONDS = 5  # opening a connection
POOL_TIMEOUT_SECONDS = 10  # waiting for a free connection of the pool
STATEMENT_TIMEOUT_MS = 10000  # one SQL statement


def set_statement_timeout(connection) -> None:
    connection.exec_driver_sql(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")


def build_engine(url: str):
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
```

Тайм-аут запиту задається через `SET LOCAL` на початку кожної транзакції, а не стартовим параметром `options=-c statement_timeout=...`. Пул-рядок підключення Neon (PgBouncer) відхиляє такі стартові параметри з помилкою «unsupported startup parameter», тож сайт лишився б без бази; `SET LOCAL` працює і з пулом, і без нього.

Також у `src/api/main.py` додано глобальний обробник `OperationalError`, який повертає HTTP 503 замість внутрішньої помилки сервера.

```python
@app.exception_handler(OperationalError)
async def database_error_handler(request: Request, exc: OperationalError):
    logger.error("Database operation failed: %s", exc)

    error_content = ErrorResponse(
        error=ErrorPayload(
            code="DATABASE_UNAVAILABLE",
            message="Database is temporarily unavailable",
            request_id=str(uuid.uuid4()),
            documentation="https://api.our-movie-platform.com/docs/errors#database-unavailable",
        )
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_content.model_dump(),
    )
```

- **Патерни:** Fail Fast, тайм-аути, централізована обробка помилок.
- **Режим відмови:** швидка відмова.
- **Що бачить користувач:** HTTP 503 із кодом `DATABASE_UNAVAILABLE`.
- **Відновлення:** після відновлення доступності БД наступні запити можуть виконуватися нормально.
- **Тести:** `tests/reliability/test_database_failures.py` — ін'єкція `OperationalError` та перевірка HTTP 503; `tests/reliability/test_database_timeouts.py` — тайм-аут запиту через `SET LOCAL`, для PostgreSQL лише параметри, які приймає пул Neon.

#### Знахідка 11. Недоступність БД під час запуску (B, висока)

**До:** у `src/api/main.py` застосунок одразу виконував ініціалізацію таблиць.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
```

Якщо PostgreSQL була недоступна, виникала помилка, яка переривала запуск застосунку.

**Після:** реалізовано функцію `initialize_database_with_retry()`, яка виконує до п'яти спроб підключення з експоненційним відступом і повним джитером.

```python
def initialize_database_with_retry(
    max_attempts: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
) -> bool:
    for attempt in range(max_attempts):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully")
            return True

        except OperationalError as exc:
            logger.warning(
                "Database initialization failed (attempt %d/%d): %s",
                attempt + 1,
                max_attempts,
                exc,
            )

            if attempt == max_attempts - 1:
                logger.error("Database unavailable after %d attempts", max_attempts)
                return False

            delay = random.uniform(
                0,
                min(max_delay, base_delay * (2 ** attempt)),
            )
            time.sleep(delay)

    return False
```

Якщо всі спроби завершуються невдало, застосунок запускається в деградованому режимі.

```python
database_available = initialize_database_with_retry()
app.state.database_available = database_available

if database_available:
    # Початкова ініціалізація БД
    ...
else:
    logger.warning(
        "Starting application in degraded mode: database unavailable"
    )
```

- **Патерни:** Retry, Exponential Backoff, Full Jitter, Graceful Degradation.
- **Режим відмови:** безпечна відмова.
- **Що бачить користувач:** `/health/live` повертає 200, а `/health` — 503.
- **Відновлення:** автоматичне для запитів: кожен запит відкриває нове з'єднання, тож щойно БД повертається, сайт працює, а `/health` знову відповідає `200` і знімає позначку деградованого режиму. Початкові дані (демо-акаунти, каталог) створюються лише під час старту, тож якщо БД була порожня — після перезапуску сервісу.
- **Тести:** `tests/reliability/test_startup_retries.py` — перевірка кількості спроб, затримок, деградованого режиму та повернення `/health` до `200`, коли БД знову доступна.

#### Знахідка 12. Конкурентні записи (A, середня)

**До:** у `src/api/routers/auth.py` та `src/api/routers/watched.py` перед створенням запису перевірялася його наявність.

Однак два одночасні запити могли пройти перевірку та спробувати створити однаковий запис. Це призводило до `IntegrityError`.

**Після:** додано обробку `IntegrityError` із викликом `rollback()`.

У `auth.py` конфлікт реєстрації повертає HTTP 409.

```python
db.add(user)

try:
    db.commit()
except IntegrityError:
    db.rollback()
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "USER_ALREADY_EXISTS",
            "message": "An account with this email or nickname already exists",
        },
    )

db.refresh(user)
```

У `watched.py` після конфлікту повторно перевіряється наявність запису.

```python
db.add(new_item)

try:
    db.commit()
except IntegrityError:
    db.rollback()

    existing = (
        db.query(models.WatchedItem)
        .filter(
            models.WatchedItem.user_id == current_user.user_id,
            models.WatchedItem.content_id == payload.content_id,
        )
        .first()
    )

    if existing:
        response.status_code = status.HTTP_200_OK
        return _build_watched_response(existing, db)

    raise

db.refresh(new_item)
```

Якщо інший запит уже додав фільм до переглянутого, повертається наявний запис зі статусом HTTP 200.

- **Патерни:** Race Condition Handling, Rollback, ідемпотентна поведінка.
- **Режим відмови:** контрольована обробка конфлікту.
- **Що бачить користувач:** HTTP 409 при конфлікті реєстрації або HTTP 200 при повторному додаванні переглянутого.
- **Відновлення:** після `rollback()` сесія повертається до коректного стану.
- **Тести:** `tests/reliability/test_concurrent_writes.py` — перевірка `IntegrityError`, HTTP 409, HTTP 200 та `rollback()`.

#### Знахідка 8. N+1 SQL-запитів у списку «Переглянуте» (E, середня)

**До:** у `src/api/routers/watched.py` спочатку отримувався список переглянутих фільмів, після чого для кожного фільму виконувався окремий SQL-запит.

```python
watched_items = (
    db.query(models.WatchedItem)
    .filter(models.WatchedItem.user_id == current_user.user_id)
    .order_by(models.WatchedItem.created_at.desc())
    .all()
)

items = [_build_watched_response(item, db) for item in watched_items]
```

У `_build_watched_response()` виконувався додатковий запит:

```python
content = (
    db.query(models.Content)
    .filter(models.Content.content_id == watched.content_id)
    .first()
)
```

Для 50 переглянутих фільмів це означало приблизно 51 SQL-запит.

**Після:** реалізовано отримання даних одним запитом через `OUTER JOIN`.

```python
results = (
    db.query(models.WatchedItem, models.Content)
    .outerjoin(
        models.Content,
        models.WatchedItem.content_id == models.Content.content_id,
    )
    .filter(models.WatchedItem.user_id == current_user.user_id)
    .order_by(models.WatchedItem.created_at.desc())
    .all()
)
```

Тепер інформація про всі переглянуті фільми отримується одним SQL-запитом.

`OUTER JOIN` дозволяє зберегти записи переглянутого, навіть якщо відповідний фільм відсутній у таблиці `Content`.

- **Патерни:** усунення N+1, оптимізація SQL-запитів, JOIN.
- **Режим відмови:** запобігання деградації продуктивності.
- **Що бачить користувач:** той самий список фільмів із меншою кількістю звернень до БД.
- **Відновлення:** окремий механізм не потрібен, оскільки усунуто причину надмірних запитів.
- **Тест:** `tests/reliability/test_watched_query_performance.py` — 50 фільмів, підрахунок SQL-запитів через `event.listen()`, перевірка обмеження не більше 2 запитів.

### 2.4. Михайло Крилов — знахідки 7, 13, 14, 15, 16

#### Знахідка 13. Імпорт TMDB під час старту (E, середня)

**До** (`src/api/services/tmdb.py`, `seed_catalog_if_empty`): на порожній БД із ключем TMDB старт виконував близько 300 HTTP-запитів, і поки вони йшли, сервіс не відповідав нічому.

```python
if db.query(Content.id).first() is not None:
    return 0
added = seed_movies_to_database(db, fetch_tmdb_movies())  # ~300 запитів до TMDB у lifespan
```

**Після:** старт заповнює каталог лише вбудованими тайтлами, без мережі; імпорт із TMDB іде у фоновому потоці й замінює їх, коли завершиться (`src/api/main.py`, `src/api/services/catalog_sync.py`).

```python
# tmdb.py — жодного мережевого виклику під час старту
added = seed_movies_to_database(db, FALLBACK_MOVIES)

# main.py, lifespan
seeded = seed_catalog_if_empty(db)
...
catalog_sync.mark_interrupted_runs(db)
api_key = catalog_sync.tmdb_api_key()
if seeded and api_key:
    catalog_sync.start_in_background(db, api_key)  # daemon-потік "tmdb-catalog-sync"
```

- **Патерни:** резервна логіка (вбудований каталог), винесення довгої операції з критичного шляху (фоновий потік), тайм-аут 10 с на кожен запит до TMDB (був і раніше).
- **Режим відмови:** безпечна відмова. Сайт працює одразу; якщо TMDB не відповідає, користувачі бачать вбудований каталог.
- **Що бачить користувач під час збою:** звичайний сайт з 30 вбудованими тайтлами; адміністратор — у картці «Каталог TMDB» стан «Оновлення не вдалося» з причиною.
- **Відновлення:** автоматичне при наступному старті на порожній БД або вручну кнопкою «Оновити каталог з TMDB»; після успішного імпорту вбудовані тайтли перебираються справжніми.

#### Знахідка 16. Стан оновлення каталогу лише в пам'яті (D, низька)

**До** (`src/api/services/catalog_sync.py`): словник `_status` у пам'яті процесу. Перезапуск посеред імпорту мовчки повертав стан `idle`.

```python
_status: Dict[str, Any] = {"state": "idle", ...}
```

**Після:** кожне оновлення — рядок таблиці `catalog_sync_runs` (`CatalogSyncRun`); під час старту оновлення, що лишилося «running», позначається як перерване.

```python
def mark_interrupted_runs(db: Session) -> int:
    """On startup nothing can be importing yet: a "running" run was cut off by a restart."""
    runs = db.query(CatalogSyncRun).filter(CatalogSyncRun.state == "running").all()
    for run in runs:
        run.state = "failed"
        run.finished_at = datetime.now(UTC)
        run.error = INTERRUPTED_MESSAGE
    db.commit()
```

- **Патерни:** збереження стану поза процесом, відновлення після збою під час старту, логування, захист від двох одночасних запусків (блокування + перевірка останнього запуску).
- **Режим відмови:** швидка відмова: неправильний стан («нічого не відбувалося») гірший за чесне «не вдалося», тож перерване оновлення явно позначається невдалим і не продовжується саме (частковий імпорт при цьому безпечний — фільми лише додаються й оновлюються).
- **Що бачить користувач під час збою:** адміністратор бачить «Оновлення не вдалося: Оновлення перервано: сервер перезапустився під час імпорту. Запустіть оновлення ще раз.»
- **Відновлення:** ручне — кнопкою «Оновити каталог з TMDB» (повторний імпорт ідемпотентний: тайтли зіставляються за `tmdb_id`).

#### Знахідка 14. HTTP-клієнт фронтенду без тайм-ауту (B, середня)

**До** (`frontend/src/api/client.js`):

```javascript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  withCredentials: true,
  ...
});
```

**Після:**

```javascript
export const REQUEST_TIMEOUT_MS = 30000;

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: REQUEST_TIMEOUT_MS,
  withCredentials: true,
  ...
});
```

Плюс один автоматичний повтор читаючих запитів (`GET`/`HEAD`) після тайм-ауту, обриву мережі або `502`/`503`/`504`, з паузою 1 с:

```javascript
export function shouldRetry(error) {
  const config = error?.config;
  if (!config || config.retried) return false;
  if (!RETRY_METHODS.includes((config.method || 'get').toLowerCase())) return false;
  if (error.response) return RETRY_STATUSES.includes(error.response.status);
  return RETRY_CODES.includes(error.code);
}

apiClient.interceptors.response.use((response) => response, async (error) => {
  if (shouldRetry(error)) {
    const { config } = error;
    config.retried = true;
    await wait(config.retryDelayMs ?? RETRY_DELAY_MS);
    return apiClient(config);
  }
  ...
});
```

- **Патерни:** тайм-аут на зовнішню операцію, обмежений повтор (одна спроба) лише для ідемпотентних запитів, складені в порядку «тайм-аут → повтор → повідомлення користувачу». 30 с — з запасом на «пробудження» Neon і безкоштовного плану Render (keep-alive тримає сайт активним, тож зазвичай відповідь за долі секунди). Запити, що змінюють дані (`POST`/`PUT`/`PATCH`/`DELETE`), не повторюються: повтор міг би створити другу рецензію чи голос.
- **Режим відмови:** швидка відмова: підставлені чи застарілі дані були б гіршими за чесну помилку (тому тестових фільмів на фронтенді більше й немає), тож запит обривається з `ECONNABORTED`; для читання — після однієї повторної спроби (найдовше очікування ~61 с).
- **Що бачить користувач під час збою:** замість нескінченного «Завантаження…» — «Каталог тимчасово недоступний: сервер не відповідає. Спробуйте оновити сторінку.» (головна сторінка) або повідомлення про помилку конкретної дії.
- **Відновлення:** автоматичне для читання (один повтор: перший запит до «заснулого» сайту чи бази зазвичай вдається з другої спроби); якщо й повтор не вдався — користувач оновлює сторінку або повторює дію.

#### Знахідка 15. Числові змінні середовища (C, низька)

**До:** `int(os.getenv(...))` під час імпорту модулів (`auth.py`, `tmdb.py`, у `email.py` — під час відправлення листа).

```python
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
TITLES_PER_SECTION = int(os.getenv("TMDB_TITLES_PER_SECTION", "100"))
port = int(os.getenv("SMTP_PORT") or (465 if security == "ssl" else 587))
```

**Після:** одна функція `env_int` (`src/api/settings.py`) з межами для кожного параметра.

```python
def env_int(name, default, minimum=None, maximum=None) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        logger.warning("%s=%r is not a whole number; using the default %s.", name, raw, default)
        return default
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        logger.warning("%s=%s is outside %s..%s; using the default %s.", name, value, minimum, maximum, default)
        return default
    return value

ACCESS_TOKEN_EXPIRE_MINUTES = env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 1440, minimum=1, maximum=60 * 24 * 30)
TITLES_PER_SECTION = env_int("TMDB_TITLES_PER_SECTION", 100, minimum=1, maximum=500)
port = env_int("SMTP_PORT", 465 if security == "ssl" else 587, minimum=1, maximum=65535)
```

- **Патерни:** перевірка входу (межі), безпечне значення за замовчуванням, логування з назвою змінної.
- **Режим відмови:** безпечна відмова — ці налаштування некритичні, тож краще працювати зі значенням за замовчуванням, ніж не стартувати. (Для критичних налаштувань, як-от `DATABASE_URL`, правильна була б швидка відмова.)
- **Що бачить користувач під час збою:** нічого — сайт працює; у лозі Render: `ACCESS_TOKEN_EXPIRE_MINUTES='24h' is not a whole number; using the default 1440.`
- **Відновлення:** ручне — виправити змінну в Render → Environment.

#### Знахідка 7. Перевірка пароля (D, A; критичність підвищено до середньої)

Під час написання тестів з'ясувалося, що ризик серйозніший за опис на парі: на обрізаному хеші (`$2b$12$short`) ядро `bcrypt` (написане на Rust) не кидає `ValueError`, а аварійно завершується з `PanicException`. Цей виняток успадковується від `BaseException`, а не від `Exception`, тож старий `except Exception` його не ловив, і **логін відповідав `500`**.

**До** (`src/api/services/auth.py`):

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False
```

**Після:**

```python
BCRYPT_HASH = re.compile(r"\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password:
        return False
    if not hashed_password:
        logger.error("Password check failed: the account has no stored password hash.")
        return False
    # Guard clause: a damaged hash makes the Rust core of bcrypt panic
    if not isinstance(hashed_password, str) or not BCRYPT_HASH.fullmatch(hashed_password):
        logger.error("Password check failed: the stored password hash is invalid (not a bcrypt hash).")
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError) as error:
        logger.error("Password check failed: the stored password hash is invalid (%s).", type(error).__name__)
        return False
```

- **Патерни:** захисні перевірки (guard clauses) замість широкого `catch`, вузький `except`, логування без чутливих даних (ні хешу, ні пароля в лозі).
- **Режим відмови:** швидка «закрита» відмова (fail closed): неправильна відповідь (впустити без справжньої перевірки чи віддати `500` з деталями) тут найгірша, тож вхід заборонено чітким `401 INVALID_CREDENTIALS` без внутрішніх деталей, а помилка йде в лог для розробників.
- **Що бачить користувач під час збою:** «Невірний email або пароль», як при звичайній помилці входу.
- **Відновлення:** ручне втручання — адміністратор бачить помилку в лозі й скидає пароль акаунта.

---

## 3. Тести надійності

| Файл | Тип | Знахідка | Що перевіряє |
|---|---|---|---|
| [`tests/reliability/test_startup_without_tmdb.py`](../../tests/reliability/test_startup_without_tmdb.py) | Зовнішня відмова (ін'єкція збою) | 13 | Кожен запит до TMDB падає з тайм-аутом → сервіс стартує менш ніж за 5 с, жоден запит до TMDB не йде в потоці старту, каталог — вбудовані тайтли, фонове оновлення збережено як `failed` з причиною; на непорожньому каталозі імпорт не запускається |
| [`tests/reliability/test_interrupted_catalog_update.py`](../../tests/reliability/test_interrupted_catalog_update.py) | Зовнішня відмова (ін'єкція збою) | 16 | «Перезапуск» посеред оновлення → після старту стан `failed` з поясненням і можна запустити нове; збій імпорту видно з іншої сесії (іншого процесу); два одночасні запуски неможливі |
| [`tests/reliability/test_env_settings.py`](../../tests/reliability/test_env_settings.py) | Граничний | 15 | Порожнє значення, пробіли, межі `1` і `43200`, `0`, `43201`, від'ємне, `"24h"`, `"1.5"`, величезне число; попередження з назвою змінної, валідне значення без попереджень |
| [`tests/reliability/test_password_check.py`](../../tests/reliability/test_password_check.py) | Обробка помилки | 7 | Логін із пошкодженим і обрізаним хешем → `401`, хеш і пароль не потрапляють ні у відповідь, ні в лог; `None`, порожні, обрізані й неправильного типу хеші не кидають винятків |
| [`frontend/src/reliability/apiTimeout.test.js`](../../frontend/src/reliability/apiTimeout.test.js) | Зовнішня відмова (ін'єкція збою) | 14 | Сервер, який приймає з'єднання й ніколи не відповідає → запит обривається з `ECONNABORTED` менш ніж за 2 с; клієнт має тайм-аут 30 с |
| [`frontend/src/reliability/apiRetry.test.js`](../../frontend/src/reliability/apiRetry.test.js) | Зовнішня відмова (ін'єкція збою) | 14 | Перший `GET` «висне» або отримує `503`, другий успішний → сторінка отримує дані; сервер падає завжди → рівно 2 спроби, далі помилка; `POST` не повторюється ніколи; які збої повторюються, а які ні (`404`, `500`, `DELETE`, уже повторений запит) |
| [`tests/reliability/test_database_failures.py`](../../tests/reliability/test_database_failures.py) | Ін'єкція збою | 10 | Недоступність БД (`OperationalError`) → HTTP 503 `DATABASE_UNAVAILABLE` замість 500 |
| [`tests/reliability/test_startup_retries.py`](../../tests/reliability/test_startup_retries.py) | Ін'єкція збою | 11 | Дві невдалі спроби та успіх на третій; 5 невдалих спроб → деградований режим; затримки в межах експоненційного відступу з повним джитером; у деградованому режимі `/health/live` → `200`, `/health` → `503`; коли БД повертається, `/health` → `200` |
| [`tests/reliability/test_database_timeouts.py`](../../tests/reliability/test_database_timeouts.py) | Граничний (конфігурація) | 10 | Тайм-аут запиту — `SET LOCAL statement_timeout = 10000` на кожну транзакцію; для PostgreSQL лише `connect_timeout`, `pool_timeout` і `pool_pre_ping`, без стартових `options`, які відхиляє пул Neon |
| [`tests/reliability/test_concurrent_writes.py`](../../tests/reliability/test_concurrent_writes.py) | Обробка помилки | 12 | `IntegrityError` під час реєстрації → 409; під час додавання переглянутого → 200; перевірка `rollback()` |
| [`tests/reliability/test_watched_query_performance.py`](../../tests/reliability/test_watched_query_performance.py) | Граничний | 8 | Список із 50 фільмів → не більше 2 SQL-запитів, підрахунок через `event.listen()` |

Запуск локально: `pytest tests/reliability -v` і `cd frontend && npm run test:reliability`.

---

## 4. Відкриті проблеми

- **Знахідка 11, початкові дані після деградованого старту:** якщо БД була недоступна під час старту, сервіс працює, щойно вона повертається, але створення таблиць, демо-акаунтів і каталогу відбувається лише під час старту. Для наявної бази це не важливо, а для нової порожньої потрібен перезапуск сервісу.
- **Знахідка 16, кілька процесів:** позначка «перервано» під час старту розрахована на один процес Uvicorn (так налаштовано в `Dockerfile`). Якщо колись запустити кілька воркерів, старт одного позначить як перерване оновлення, яке ще йде в іншому; тоді потрібен «пульс» (heartbeat) запуску в БД.
- **Знахідка 13, повтори:** фоновий імпорт не повторюється автоматично після збою TMDB; повтор — вручну кнопкою. Повтори з експоненційним відступом і джитером можна додати для запитів деталей тайтлів.
- **Знахідка 14, повтор запитів, що змінюють дані:** вони свідомо не повторюються автоматично. Якщо такий запит обірвався за тайм-аутом, а сервер уже встиг зберегти зміну, користувач повторює дію сам. Для рецензій, голосів, списків і реєстрації це безпечно (унікальність у БД або ідемпотентний PUT), але коментар при цьому може задублюватися. Усунути можна ключем ідемпотентності в запиті на створення коментаря.

---

## Бонуси

### Тести надійності як обов'язкова перевірка PR (Михайло Крилов)

- **Окремий крок у CI.** У [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) додано job `reliability`, що на кожен PR і push у `main` запускає:
  - `pytest tests/reliability -v` — крок «Reliability tests (tests/reliability)»;
  - `npm run test:reliability` (`vitest run src/reliability`) — крок «Reliability tests (frontend/src/reliability)». Саме через `npm run`, а не `npx`: `npx` може сам завантажити й запустити пакет, на що вказав SonarCloud.
- **Обов'язкова перевірка гілки `main`.** Перевірку `reliability` додано до Settings → Branches → `main` → *Require status checks to pass before merging* (поруч із `build`, `frontend`, `docker` і `secrets`).
- **Захист від випадкового видалення:** тест `tests/test_workflows_security.py::test_reliability_tests_run_as_a_separate_ci_job` падає, якщо job або його кроки зникнуть з `ci.yml`.
- **Прогін, де крок пройшов:** [CI Test → job `reliability`, PR #206](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43012171808/job/130494249315) — обидва кроки («Reliability tests (tests/reliability)» і «Reliability tests (frontend/src/reliability)») зелені.
- **Доказ обов'язковості:** у правилі захисту гілки `main` (Settings → Branches → *Require status checks to pass before merging*) обов'язкові перевірки `build`, `reliability`, `frontend`, `docker` і `secrets`; у PR біля `reliability` показано позначку **Required**, без неї PR не можна змерджити. Показано у відео.

### Повтори з відступом і джитером (Юлія Галка)

- **Що зроблено.** Ідемпотентний зовнішній виклик — створення таблиць БД під час старту (`Base.metadata.create_all`) — виконується з обмеженими повторами з експоненційним відступом і повним джитером: функція `initialize_database_with_retry()` у [`src/api/main.py`](../../src/api/main.py).
- **Як працює.** До 5 спроб; перед кожною наступною — пауза `random.uniform(0, min(5.0, 0.5 * 2 ** attempt))`, тобто не більше 0,5 → 1 → 2 → 4 с. Повний джитер розносить повтори кількох екземплярів у часі, щоб вони не «добивали» базу одночасно.
- **Порядок патернів (§3.5).** Тайм-аут → повтор → резервна реакція: кожна спроба обмежена `connect_timeout = 5` с, повторів не більше 5, після останньої — деградований режим (сервіс стартує, `/health/live` → `200`, `/health` → `503`) замість падіння.
- **Тест:** [`tests/reliability/test_startup_retries.py`](../../tests/reliability/test_startup_retries.py) — БД падає двічі й відповідає на третій спробі → рівно 3 спроби й 2 паузи; БД недоступна завжди → рівно 5 спроб, 4 паузи й деградований режим; кожна пауза в межах свого ліміту.

### Перевірка здоров'я сервісу (Юлія Галка)

- **Що зроблено.** Два ендпоінти в [`src/api/routers/health.py`](../../src/api/routers/health.py): `/health/live` (процес живий, БД не чіпає — її використовує Render) і `/health` (перевіряє критичну залежність — БД — запитом `SELECT 1`).
- **Як працює.** `/health` повертає `200 {"status": "ok", "database": "ok"}` або `503 {"status": "degraded", "database": "unavailable"}`. Стан перевіряється на кожен виклик, тож після деградованого старту `/health` знову стає `200`, щойно БД повертається.
- **Тест з ін'єкцією збою:** [`tests/reliability/test_startup_retries.py`](../../tests/reliability/test_startup_retries.py) — сесія БД, кожен запит якої падає з `OperationalError`: `/health/live` → `200`, `/health` → `503` зі статусом «degraded»; після «повернення» БД `/health` → `200`.

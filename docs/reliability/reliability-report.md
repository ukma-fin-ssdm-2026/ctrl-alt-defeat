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
| 2 | A | Гонитва при додаванні до «До перегляду»: `500` замість `409` | Середня | Іван Ліфєнцєв | Виправлено (PR #205) |
| 3 | A | Немає глобального обробника непередбачених винятків | Середня | Учасник 1 | Відкрито |
| 4 | B | Запис OpenAPI під час старту без обробки `OSError` | Середня | Іван Ліфєнцєв | Виправлено (PR #205) |
| 5 | C | Пошук без `max_length`, рік без меж (`500` на завеликому році) | Середня | Учасник 1 | Відкрито |
| 6 | D, C | Зведення відгуків падає на оцінці `None` | Низька | Іван Ліфєнцєв | Виправлено (PR #205) |
| 7 | D, A | Перевірка пароля: широкий `except` без логування; пошкоджений хеш давав `500` | Низька → **Середня** (див. 2.4) | Михайло Крилов | **Виправлено** |
| 8 | E | N+1 запитів у списку «Переглянуте» | Середня | Учасник 2 | Відкрито |
| 9 | C | Числовий `id` фільму без меж: `500` замість `404` | Середня | Учасник 1 | Відкрито |
| 10 | B | БД без тайм-аутів з'єднання й запиту | Висока | Учасник 2 | Відкрито |
| 11 | B | Старт не переживає недоступну БД | Висока | Учасник 2 | Відкрито |
| 12 | A | Гонитва при реєстрації та в «Переглянутому» | Середня | Учасник 2 | Відкрито |
| 13 | E | Повний імпорт TMDB синхронно під час старту | Середня | Михайло Крилов | **Виправлено** |
| 14 | B | HTTP-клієнт фронтенду без тайм-ауту | Середня | Михайло Крилов | **Виправлено** |
| 15 | C | `int(os.getenv(...))` під час імпорту модулів | Низька | Михайло Крилов | **Виправлено** |
| 16 | D | Стан оновлення каталогу лише в пам'яті процесу | Низька | Михайло Крилов | **Виправлено** |
| 17 | A | `user_id` / `author_name` коментаря з тіла запиту | Середня | Учасник 1 (разом із 1) | Відкрито |

---

## 2. Виправлення, патерни, режими відмов і відновлення

### 2.1. Іван Ліфєнцєв — знахідки 2, 4, 6 (PR #205)

_Заповнює Іван Ліфєнцєв: до/після, патерн, швидка чи безпечна відмова, що бачить користувач, як система відновлюється, тести._

### 2.2. Учасник 1 — знахідки 1, 3, 5, 9, 17

_Заповнює учасник 1._

### 2.3. Учасник 2 — знахідки 8, 10, 11, 12

_Заповнює учасник 2._

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
- **Режим відмови:** безпечна відмова з явним сигналом: імпорт не продовжується сам (частковий імпорт безпечний — фільми лише додаються й оновлюються), але стан не губиться.
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

- **Патерн:** тайм-аут на зовнішню операцію. 30 с — з запасом на «пробудження» Neon і безкоштовного плану Render (keep-alive тримає сайт активним, тож зазвичай відповідь за долі секунди).
- **Режим відмови:** швидка відмова: запит обривається з `ECONNABORTED`.
- **Що бачить користувач під час збою:** замість нескінченного «Завантаження…» — «Каталог тимчасово недоступний: сервер не відповідає. Спробуйте оновити сторінку.» (головна сторінка) або повідомлення про помилку конкретної дії.
- **Відновлення:** користувач повторює дію або оновлює сторінку.

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
- **Режим відмови:** безпечна відмова для користувача (`401 INVALID_CREDENTIALS`, без внутрішніх деталей) + помилка в лозі для розробників.
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

Запуск локально: `pytest tests/reliability -v` і `cd frontend && npm run test:reliability`.

---

## 4. Відкриті проблеми

- **Знахідки 1, 3, 5, 8, 9, 10, 11, 12, 17** — у роботі учасників 1 і 2 (див. таблицю в пункті 1).
- **Знахідка 16, кілька процесів:** позначка «перервано» під час старту розрахована на один процес Uvicorn (так налаштовано в `Dockerfile`). Якщо колись запустити кілька воркерів, старт одного позначить як перерване оновлення, яке ще йде в іншому; тоді потрібен «пульс» (heartbeat) запуску в БД.
- **Знахідка 13, повтори:** фоновий імпорт не повторюється автоматично після збою TMDB; повтор — вручну кнопкою. Повтори з експоненційним відступом і джитером можна додати для запитів деталей тайтлів.
- **Знахідка 14, тривалий «пробуджувальний» старт:** якщо безкоштовний сервіс Render прокидається довше за 30 с (буває після тривалої тиші, хоча keep-alive це майже виключає), перший запит обірветься, і користувачу доведеться оновити сторінку.

---

## Бонуси

### Тести надійності як обов'язкова перевірка PR (Михайло Крилов)

- **Окремий крок у CI.** У [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) додано job `reliability`, що на кожен PR і push у `main` запускає:
  - `pytest tests/reliability -v` — крок «Reliability tests (tests/reliability)»;
  - `npm run test:reliability` (`vitest run src/reliability`) — крок «Reliability tests (frontend/src/reliability)». Саме через `npm run`, а не `npx`: `npx` може сам завантажити й запустити пакет, на що вказав SonarCloud.
- **Обов'язкова перевірка гілки `main`.** Перевірку `reliability` додано до Settings → Branches → `main` → *Require status checks to pass before merging* (поруч із `build`).
- **Захист від випадкового видалення:** тест `tests/test_workflows_security.py::test_reliability_tests_run_as_a_separate_ci_job` падає, якщо job або його кроки зникнуть з `ci.yml`.
- **Прогін, де крок пройшов:** [CI Test → job `reliability`, PR #206](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/runs/43012171808/job/130494249315) — обидва кроки («Reliability tests (tests/reliability)» і «Reliability tests (frontend/src/reliability)») зелені.
- **Доказ обов'язковості:** у правилі захисту гілки `main` (Settings → Branches → *Require status checks to pass before merging*) обов'язкові перевірки `build` і `reliability`; у PR біля `reliability` показано позначку **Required**, без неї PR не можна змерджити. Показано у відео.

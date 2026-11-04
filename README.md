# Сайт рецензій та рекомендацій фільмів і серіалів «Після титрів» 

[![CI Test](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/workflows/ci.yml/badge.svg)](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/workflows/ci.yml)

<p align="center">
  <img src="images/banner.png" width="100%"/>
</p>

Проєкт являє собою веб-платформу для кіноманів та любителів серіалів, яка дозволяє відкривати для себе новий контент, вести облік переглянутого та ділитися враженнями. Зважаючи на величезну кількість доступних шоу в жанрах наукової фантастики, містики та драми, користувачам часто важко знайти щось якісне для перегляду. 

Система розв'яже цю проблему, надаючи можливість оцінювати контент, писати рецензії та отримувати персоналізовані рекомендації. Платформа об'єднає функціонал бази даних та соціального трекера (аналог Letterboxd або міні-IMDb).

## Команда Ctrl-Alt-Defeat
- Михайло Крилов 
- Юлія Галка
- Іван Ліфєнцєв 
- Владислав Виговський 
- Максим Годік

## Артефакти та документація (Лабораторні роботи 1–7)

Повний індекс документації доступний у [docs/README.md](./docs/README.md).

### Лабораторна робота 1: Управління проєктом та команда
- [Опис проєкту (Project-Description.md)](Project-Description.md)
- [Командний статут та правила використання ШІ (TeamCharter.md)](TeamCharter.md)
- [Конфігурація CI/CD конвеєра (.github/workflows/ci.yml)](.github/workflows/ci.yml)
- [Відеопрезентація команди](./Labs/Lab01/)

### Артефакти вимог (Лабораторна робота 2)
- [Вимоги до системи (FR та NFR за ISO 25010)](./docs/requirements/requirements.md)
- [Користувацькі історії з INVEST-аналізом (User Stories)](./docs/requirements/user-stories.md)
- [Матриця простежуваності вимог (RTM)](./docs/requirements/rtm.md)
- [Сценарії використання (Use Cases)](./docs/requirements/use-cases.md)
- [Міні-ТЗ проєкту (Project-Description.md)](./Project-Description.md#4-міні-тз)
- [Індекс артефактів вимог](./docs/requirements/README.md)
- [Відеопрезентація Лаб 2](./Labs/Lab02/)

### Лабораторна робота 3: Архітектурне проектування та дизайн
- [Високорівнева архітектура системи (High-Level Design)](./docs/architecture/high-level-design.md)
- [Матриця простежуваності архітектури](./docs/architecture/traceability-matrix.md)
- [Модель загроз безпеки за методологією STRIDE](./docs/architecture/threat-model.md)
- [Доменна модель даних (Data Model)](./docs/architecture/data-model.md)
- [Архітектурні рішення (ADR-001, ADR-002)](./docs/architecture/decisions/)
- [Діаграми UML та модель сутностей](./docs/architecture/uml/)
- [Індекс артефактів архітектури](./docs/architecture/README.md)
- [Відеопрезентація Лаб 3](./Labs/Lab03/)

### Лабораторна робота 4: Проектування та документування API
- [Дизайн REST API (API Design)](./docs/api/api-design.md)
- [Атрибути якості API та аналіз компромісів](./docs/api/quality-attributes.md)
- [Автоматично згенерована специфікація OpenAPI](./docs/api/openapi-generated.yaml)
- [Онлайн-документація Swagger UI (GitHub Pages)](https://ukma-fin-ssdm-2026.github.io/ctrl-alt-defeat/)
- [Індекс артефактів API](./docs/api/README.md)
- [Відеопрезентація Лаб 4](./Labs/Lab04/)

### Лабораторна робота 5: Стандарти кодування, безпека та Code Review
- [Звіт про перехресне рецензування коду (Code Review Report)](./docs/code-quality/review-report.md)
- [Звіт зі статичного аналізу безпеки (SAST / Bandit / Ruff)](./docs/code-quality/static-analysis.md)
- [Звіт про модульну декомпозицію та прогрес](./docs/code-quality/progress.md)
- [Індекс артефактів якості коду](./docs/code-quality/README.md)
- [Відеопрезентація Лаб 5](./Labs/Lab05/)

### Лабораторна робота 6: Модульне тестування та перевірка коду
- [Стратегія тестування та Quality Gates](./docs/testing/testing-strategy.md)
- [Журнал налагодження виявлених дефектів (Debugging Log)](./docs/testing/debugging-log.md)
- [Інтерактивний звіт покриття коду (htmlcov)](./htmlcov/index.html)
- [Індекс артефактів тестування](./docs/testing/README.md)
- [Відеопрезентація Лаб 6](./Labs/Lab06/)

### Лабораторна робота 7: Валідація, верифікація та простежуваність
- [План тестування та звіт навантажувального тесту k6](./docs/validation/test-plan.md)
- [Журнал верифікації та рев'ю ШІ-коду (AI Code Review Log)](./docs/validation/review-log.md)
- [Індекс артефактів валідації](./docs/validation/README.md)
- [Відеопрезентація Лаб 7](./Labs/Lab07/)

### Рефакторинг та додаткові звіти
- [Звіт якості коду SonarCloud](./docs/refactoring/sonarcloud-report.md)
- [Демонстрація проміжного етапу (Midterm Presentation)](./Labs/midterm-presentation.txt)

---

## Інструкція із запуску системи

### 1. Вимоги до середовища
- **Python:** 3.11+
- **Node.js:** 18+ (та npm)
- **PostgreSQL:** 14+ (або локальний інстанс SQLite/Docker)
- **Git**

### 2. Клонування репозиторію
```bash
git clone https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat.git
cd ctrl-alt-defeat
```

### 3. Запуск Backend API (FastAPI)

1. Створіть та активуйте віртуальне середовище Python:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Налаштування бази даних:
   - **Швидкий локальний запуск (Zero-Config SQLite):**  
     За замовчуванням (якщо змінна `DATABASE_URL` не задана) бекенд автоматично ініціалізує локальну SQLite базу даних (`app.db`), тому додаткових кроків налаштування СКБД не потрібно.
   - **Запуск із PostgreSQL (опціонально для production):**
     ```bash
     export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/reviews_db"
     ```

3. Запустіть сервер розробки Uvicorn на порту **8000**:
   ```bash
   uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
   ```
   Після запуску бекенд доступний за адресою: `http://127.0.0.1:8000`
   - **Swagger UI:** [http://127.0.0.1:8000/api-docs](http://127.0.0.1:8000/api-docs)
   - **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

   **Окремих кроків ініціалізації не потрібно.** Під час першого старту сервер сам створює таблиці, тестові акаунти (див. розділ 5) і, якщо каталог порожній, імпортує 30 тайтлів фільмів/серіалів (з TMDB за наявності `TMDB_API_KEY`, інакше — вбудований набір). Автозаповнення каталогу вимикається змінною `AUTO_SEED_CATALOG=false`.

   *Необов'язково:* `python3 scripts/seed_movies.py` — оновлює метадані каталогу, додає колонку `runtime` у старі локальні бази та створює додаткові акаунти `*@platform.local` (розділ 5).

### 4. Запуск Frontend клієнта (React + Vite)

У новому вікні термінала перейдіть до директорії фронтенду:
```bash
cd frontend
npm install
npm run dev
```
Клієнтський застосунок відкриється за адресою: [http://localhost:5173](http://localhost:5173).  
Фронтенд звертається до API за відносною адресою `/api/v1`, а dev-сервер Vite проксіює ці запити на бекенд `http://127.0.0.1:8000` (`frontend/vite.config.js`). Тому сесія зберігається після перезавантаження сторінки, а порт фронтенду може бути будь-яким. Для бекенда на іншій адресі задайте `VITE_API_URL`.

### 5. Тестові облікові записи (Demo Accounts)

Під час старту сервер автоматично створює попередньо активовані демо-акаунти (ті самі, що підказує вікно входу):

| Роль | Електронна пошта | Пароль | Доступний функціонал |
|---|---|---|---|
| **Адміністратор** | `admin@gmail.com` | `password12345` | Модерація та видалення будь-яких відгуків (FR-008), повний доступ |
| **Користувач** | `user@example.com` | `password123` | Watchlist (FR-005), Watched list (FR-006), оцінювання переглянутого (FR-003/004), рекомендації (FR-007), коментарі (FR-011) |

Додаткові акаунти `admin@platform.local` / `Admin123!` та `user@platform.local` / `User123!` створює необов'язковий скрипт `scripts/seed_movies.py`.

> ⚠️ Демо-акаунти мають загальновідомі паролі й призначені лише для локальної перевірки — не використовуйте їх у публічному розгортанні.

*Також можна зареєструвати новий обліковий запис безпосередньо у веб-інтерфейсі.*

### 6. Запуск автотестів та перевірка якості

Для запуску модульних тестів бекенду із перевіркою покриття (поріг $\ge 80\%$):
```bash
pytest --cov=src.api --cov-report=term tests/
```

Для запуску тестів фронтенду (Vitest):
```bash
npm --prefix frontend test
```

Для перевірки простежуваності тестів до матриці RTM:
```bash
python3 scripts/verify_traceability.py
```

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

3. Створіть файл налаштувань `.env` і впишіть у нього свої значення (файл не потрапляє в git):
   ```bash
   cp .env.example .env
   ```
   Для локальної роботи достатньо `JWT_SECRET_KEY`, `SEED_ADMIN_PASSWORD`, `SEED_USER_PASSWORD` і, за бажанням, `DEMO_MODE=true` (див. розділ 5).

4. Запустіть сервер розробки Uvicorn на порту **8000**:
   ```bash
   uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000 --env-file .env
   ```
   Після запуску бекенд доступний за адресою: `http://127.0.0.1:8000`
   - **Swagger UI:** [http://127.0.0.1:8000/api-docs](http://127.0.0.1:8000/api-docs)
   - **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

   **Окремих кроків ініціалізації не потрібно.** Під час першого старту сервер сам створює таблиці, акаунти з `.env` (див. розділ 5) і, якщо каталог порожній, імпортує 30 тайтлів фільмів/серіалів (з TMDB за наявності `TMDB_API_KEY`, інакше — вбудований набір). Автозаповнення каталогу вимикається змінною `AUTO_SEED_CATALOG=false`.

   *Необов'язково:* `python3 scripts/seed_movies.py` — оновлює метадані каталогу, додає колонку `runtime` у старі локальні бази та створює ті самі акаунти з `.env` (розділ 5).

### 4. Запуск Frontend клієнта (React + Vite)

У новому вікні термінала перейдіть до директорії фронтенду:
```bash
cd frontend
npm install
npm run dev
```
Клієнтський застосунок відкриється за адресою: [http://localhost:5173](http://localhost:5173).  
Фронтенд звертається до API за відносною адресою `/api/v1`, а dev-сервер Vite проксіює ці запити на бекенд `http://127.0.0.1:8000` (`frontend/vite.config.js`). Тому сесія зберігається після перезавантаження сторінки, а порт фронтенду може бути будь-яким. Для бекенда на іншій адресі задайте `VITE_API_URL`.

### 4a. Запуск у Docker (альтернатива пунктам 3–4)

Один Docker-образ містить бекенд і зібраний фронтенд, тому сайт і API доступні з однієї адреси:
```bash
cp .env.example .env    # впишіть свої значення, зокрема POSTGRES_PASSWORD і JWT_SECRET_KEY
docker compose up --build
```
Сайт відкриється за адресою [http://localhost:8000](http://localhost:8000), стан сервісу — [http://localhost:8000/health](http://localhost:8000/health). `docker-compose.yml` також піднімає PostgreSQL 16; обидва контейнери мають політику перезапуску `restart: unless-stopped`. Образ встановлює залежності з `requirements-lock.txt` (фіксовані версії з sha256-хешами); після зміни `requirements.txt` lock-файл оновлюється командою з `scripts/check_requirements_lock.py`, а CI перевіряє їх відповідність.

### 5. Тестові облікові записи (Demo Accounts)

Паролів у коді немає: демо-акаунти мають одне джерело, змінні оточення з `.env` (або налаштувань хостингу). Під час старту сервер створює попередньо активовані акаунти, для яких задано пароль:

| Роль | Змінні | Email за замовчуванням | Доступний функціонал |
|---|---|---|---|
| **Адміністратор** | `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD` | `admin@gmail.com` | Модерація та видалення будь-яких відгуків, повний доступ |
| **Користувач** | `SEED_USER_EMAIL`, `SEED_USER_PASSWORD` | `user@example.com` | Watchlist, Watched list, оцінювання переглянутого, рекомендації, коментарі |

Під час кожного старту пароль і роль наявного акаунта синхронізуються з `.env`, тож вписаний пароль завжди дійсний.

**Підказка у вікні входу.** Якщо `DEMO_MODE=true`, вікно входу показує ці акаунти разом із паролями (ендпоінт `GET /api/v1/auth/demo-accounts`), а кнопка «Підставити» заповнює форму. `DEMO_ROLES` обмежує, які саме акаунти показуються (за замовчуванням `admin,user`). На публічному сайті це `user`, щоб пароль адміністратора не бачили всі (розділ 7). Це ті самі значення, з якими створено акаунти, тому підказка й README не можуть розійтися. Для реальних користувачів `DEMO_MODE` не вмикається.

*Також можна зареєструвати новий обліковий запис безпосередньо у веб-інтерфейсі.*

### 6. Запуск автотестів та перевірка якості

Для запуску модульних тестів бекенду із перевіркою покриття (поріг $\ge 80\%$):
```bash
pytest --cov=src.api --cov-report=term tests/
```

Перевірка форматування та статичний аналіз (ті самі кроки, що в CI):
```bash
black --check .
ruff check .
bandit -r src/api -ll
```

Для запуску тестів фронтенду (Vitest):
```bash
npm --prefix frontend test
```

Для перевірки простежуваності тестів до матриці RTM:
```bash
python3 scripts/verify_traceability.py
```

### 7. Онлайн-розгортання (Render + Neon)

Сайт розгортається на [Render](https://render.com) з файлу `render.yaml` (Blueprint) як один веб-сервіс із Docker-образу: бекенд і фронтенд працюють на одній адресі, регіон Frankfurt. База даних — безкоштовна PostgreSQL від [Neon](https://neon.tech). На відміну від безкоштовної бази Render, вона не видаляється через 30 днів, тому зареєстровані користувачі й відгуки зберігаються.

1. **Neon:** створити проєкт (регіон *AWS Europe Central (Frankfurt)*, PostgreSQL 16) і скопіювати рядок підключення (**Connect** → `postgresql://...?sslmode=require`).
2. **Render:** Dashboard → **New → Blueprint** → обрати репозиторій `ctrl-alt-defeat` (гілка `main`). На запит `DATABASE_URL` вставити рядок із Neon; `TMDB_API_KEY` можна залишити порожнім. `JWT_SECRET_KEY`, `SEED_ADMIN_PASSWORD` і `SEED_USER_PASSWORD` Render згенерує сам.
3. Після першого деплою сайт доступний за адресою `https://<назва-сервісу>.onrender.com`; `/health` показує стан сервісу й бази.
4. **Щоб сайт не засинав:** у GitHub → Settings → Secrets and variables → Actions → **Variables** додати `SITE_URL` з адресою сайту. Тоді workflow `keep-alive.yml` кожні 10 хвилин звертається до `/health/live`, а невдалий запуск сигналізує, що сайт не відповідає.

**Демо-акаунти на публічному сайті:** вікно входу показує тільки звичайного користувача (`DEMO_ROLES=user`). Пароль адміністратора (`SEED_ADMIN_PASSWORD`) видно в Render → сервіс → **Environment**, і він передається викладачу окремо, щоб відвідувачі сайту не отримували прав адміністратора.

Подальші деплої запускаються автоматично після злиття в `main`, але тільки коли CI пройшов (`autoDeployTrigger: checksPass`). Трафік перемикається на нову версію лише після успішної перевірки `/health/live`.

**Обмеження безкоштовних тарифів:**
- Render дає 750 годин роботи на місяць, і цього вистачає, щоб один сервіс працював цілодобово. Без `SITE_URL` сервіс засинає після 15 хвилин без запитів, і перше відкриття триває близько хвилини.
- Neon «присипляє» базу після 5 хвилин без запитів. Пробудження займає менше секунди, а `/health/live` базу не будить, тому ліміт обчислень Neon витрачається лише на реальні запити.

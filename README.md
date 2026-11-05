# Сайт рецензій та рекомендацій фільмів і серіалів «Після титрів» 

[![CI Test](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/workflows/ci.yml/badge.svg)](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/actions/workflows/ci.yml)

### [Відкрити онлайн-версію «Після титрів»](https://pislya-tytriv.onrender.com/)

Демо-акаунт користувача підказує вікно входу.

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

## Артефакти та документація (Лабораторні роботи 1–8)

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

### Лабораторна робота 8: Рефакторинг та управління релізами
- [Звіт SonarQube Cloud: метрики до/після, рефакторинги, використання ШІ, регресія](./docs/refactoring/sonarcloud-report.md)
- [Журнал змін (CHANGELOG.md)](./CHANGELOG.md), реліз `v0.1.1`
- [Відеопрезентація Лаб 8](./Labs/Lab08/)

### Додаткові звіти
- [Демонстрація проміжного етапу (Midterm Presentation)](./Labs/midterm-presentation.txt)

---

## Інструкція із запуску системи

### 1. Вимоги до середовища
- **Python** 3.11+
- **Node.js** 22 LTS (Vite 8 потребує щонайменше 20.19) та npm
- **Git**
- *Необов'язково:* Docker (розділ 5) або PostgreSQL. Без них використовується SQLite.

### 2. Клонування та налаштування
```bash
git clone https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat.git
cd ctrl-alt-defeat
cp .env.example .env
```
У `.env` (не потрапляє в git) впишіть щонайменше `JWT_SECRET_KEY`, `SEED_ADMIN_PASSWORD` і `SEED_USER_PASSWORD`; усі змінні описані в самому `.env.example`. Без `DATABASE_URL` бекенд створює локальну SQLite-базу `app.db`; для PostgreSQL задайте, наприклад, `DATABASE_URL=postgresql://user:password@localhost:5432/reviews_db`.

### 3. Запуск Backend API (FastAPI)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000 --env-file .env
```
- API: `http://127.0.0.1:8000`, Swagger UI: [/api-docs](http://127.0.0.1:8000/api-docs), ReDoc: [/redoc](http://127.0.0.1:8000/redoc)
- Під час старту сервер сам створює таблиці, акаунти з `.env` (розділ 6) і, якщо каталог порожній, імпортує 30 тайтлів: з TMDB за наявності `TMDB_API_KEY`, інакше з вбудованого набору.
- Для старої локальної бази без колонки `runtime` один раз виконайте `python3 scripts/seed_movies.py` (або просто видаліть `app.db`).

### 4. Запуск Frontend (React + Vite)
У новому вікні термінала:
```bash
cd frontend
npm install
npm run dev
```
Сайт відкриється на [http://localhost:5173](http://localhost:5173). Dev-сервер Vite проксіює запити `/api/v1` на бекенд `http://127.0.0.1:8000`, тому окремих налаштувань не потрібно.

### 5. Запуск у Docker (альтернатива пунктам 3–4)
```bash
docker compose up --build
```
Потрібен той самий `.env`, у якому для Docker також задано `POSTGRES_PASSWORD`. Сайт і API доступні на [http://localhost:8000](http://localhost:8000), стан сервісу — на [/health](http://localhost:8000/health). Разом із застосунком піднімається PostgreSQL 16; обидва контейнери мають `restart: unless-stopped`.

### 6. Демо-акаунти

Паролів у коді немає. Акаунти створюються під час старту з `.env` (або з налаштувань хостингу), якщо задано пароль; при кожному старті пароль і роль синхронізуються з цими значеннями.

| Роль | Змінні | Email за замовчуванням | Можливості |
|---|---|---|---|
| **Адміністратор** | `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD` | `admin@gmail.com` | Видалення будь-яких відгуків, сторінка «Користувачі»: тимчасове або постійне блокування (FR-009) і видалення акаунтів |
| **Користувач** | `SEED_USER_EMAIL`, `SEED_USER_PASSWORD` | `user@example.com` | Watchlist, переглянуте, оцінки, рецензії, рекомендації, коментарі |

З `DEMO_MODE=true` вікно входу показує ці акаунти з паролями й кнопкою «Підставити». `DEMO_ROLES` обмежує, які саме акаунти показуються: за замовчуванням `admin,user`, на публічному сайті `user`. Новий акаунт можна також зареєструвати через інтерфейс.

**Підтвердження пошти (FR-001).** Після реєстрації на вказану адресу надходить лист із посиланням `…/verify-email?token=…`; акаунт активується після переходу за ним. Лист надсилається через Google Apps Script з Gmail-акаунта (`GOOGLE_SCRIPT_URL`, `GOOGLE_SCRIPT_SECRET`), через HTTP API [Brevo](https://www.brevo.com) (потрібен власний домен) або через SMTP (`SMTP_HOST` та інші, наприклад Gmail з паролем застосунку; див. `.env.example`). Якщо нічого не налаштовано, посилання друкується в лог сервера: так зручно працювати локально. API ніколи не повертає токен підтвердження: він потрапляє до користувача лише в листі.

### 7. Тести та перевірка якості
```bash
pytest --cov=src.api --cov-report=term tests/     # бекенд, поріг покриття 80%
npm --prefix frontend test                        # фронтенд (Vitest)
black --check . && ruff check . && bandit -r src/api -ll
python3 scripts/verify_traceability.py            # простежуваність тестів до RTM
```
CI (`.github/workflows/ci.yml`) запускає ці самі перевірки, а також сканування секретів `gitleaks` і збирання Docker-образу зі smoke-тестом.

### 8. Онлайн-розгортання (Render + Neon)

Сайт працює на [Render](https://render.com) як один Docker-сервіс (бекенд і фронтенд на одній адресі) за файлом `render.yaml`. База — безкоштовна PostgreSQL від [Neon](https://neon.tech), яка, на відміну від безкоштовної бази Render, не видаляється через 30 днів. Обидва сервіси в регіоні Frankfurt.

- **Деплой:** автоматично після злиття в `main`, але тільки коли CI пройшов; трафік перемикається на нову версію після успішної перевірки `/health/live`.
- **Секрети:** `DATABASE_URL` (рядок підключення з Neon) задано в Render; `JWT_SECRET_KEY` і паролі демо-акаунтів Render згенерував сам. Пароль адміністратора — у Render → сервіс `pislya-tytriv` → **Environment** → `SEED_ADMIN_PASSWORD`; він передається викладачу окремо.
- **Листи:** безкоштовні сервіси Render блокують SMTP-порти, а сервіси розсилки вимагають власного домену. Тому сайт надсилає листи через невеликий веб-застосунок Google Apps Script (`scripts/google-apps-script/mailer.gs`). Він приймає лист по HTTPS із секретним ключем і відправляє його з Gmail команди (близько 100 листів на день). Налаштування:
  1. [script.google.com](https://script.google.com) → **New project** → вставити вміст `mailer.gs` → зберегти.
  2. **Project Settings → Script Properties → Add script property**: `MAILER_SECRET` = довгий випадковий рядок (`python -c "import secrets; print(secrets.token_urlsafe(32))"`).
  3. **Deploy → New deployment → Web app**: *Execute as* — **Me**, *Who has access* — **Anyone** → **Deploy** → дозволити доступ до Gmail → скопіювати **Web app URL** (`https://script.google.com/macros/s/…/exec`).
  4. Render → сервіс → **Environment**: `GOOGLE_SCRIPT_URL` = Web app URL, `GOOGLE_SCRIPT_SECRET` = той самий секрет → **Save Changes**.

  Посилання в листах ведуть на адресу сервісу (`RENDER_EXTERNAL_URL`). Сервер надсилає секрет лише на `https://script.google.com/macros/…`, будь-яку іншу адресу він відхиляє.
- **Keep-alive:** безкоштовний сервіс Render засинає після 15 хвилин без запитів. Workflow `keep-alive.yml` кожні 10 хвилин звертається до `/health/live` (адреса задана змінною репозиторію `SITE_URL`). Невдалий запуск означає, що сайт не відповідав.
- **Повторне розгортання з нуля:** створити проєкт у Neon (Frankfurt, PostgreSQL 16), потім Render → **New → Blueprint** → цей репозиторій, і на запит `DATABASE_URL` вставити рядок із Neon.

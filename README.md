# Сайт рецензій та рекомендацій фільмів і серіалів 

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

## Артефакти вимог
- [Вимоги до системи](./docs/requirements/requirements.md)
- [Користувацькі історії](./docs/requirements/user-stories.md)
- [Матриця простежуваності](./docs/requirements/rtm.md)
- [Cценарій користування](./docs/requirements/use-cases.md)
- [Архітектура](./docs/architecture/high-level-design.md)

## Документація
- [Опис проєкту](Project-Description.md)
- [Командний статут](TeamCharter.md)
- [Атрибути якості API](./docs/api/quality-attributes.md)
- [Специфікація API (OpenAPI)](./docs/api/openapi-generated.yaml)

## Інструкція із запуску API

### 1. Вимоги до оточення
- **Python:** (версія 3.11+)
- **Git**

### 2. Клонування та встановлення залежностей
Створіть та активуйте віртуальне середовище Python:
```bash
git clone https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat.git
cd ctrl-alt-defeat

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Запуск сервера розробки
Запустіть ASGI-сервер Uvicorn:
```bash
uvicorn src.api.main:app --reload --port 8000
```
Після запуску сервер доступний за адресою `http://127.0.0.1:8000`.

### 4. Документація API
Після запуску локального сервера документація доступна за посиланнями:
- **Swagger UI:** [http://127.0.0.1:8000/api-docs](http://127.0.0.1:8000/api-docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **GitHub Pages (онлайн-специфікація):** [https://ukma-fin-ssdm-2026.github.io/ctrl-alt-defeat/](https://ukma-fin-ssdm-2026.github.io/ctrl-alt-defeat/)

### 5. Запуск тестів та перевірок
Для запуску модульних тестів та перевірки покриття коду:
```bash
pytest --cov=src.api tests/
```

# Звіт про прогрес проєкту (Лабораторна робота 5)

Цей документ фіксує стан архітектури прототипу, готовність компонентів, інструкцію із запуску та статус автоматизованого тестування кодової бази **ctrl-alt-defeat**.

---

## 1. Поточний стан архітектури

Згідно з вимогами до базової структури коду та за результатами зворотного зв'язку Code Review, монолітний файл API було успішно декомпозовано на логічні модулі:
- **`src/api/db/`**: Містить налаштування підключення до бази даних ([database.py](../../src/api/db/database.py)) з підтримкою пулу з'єднань через SQLAlchemy та ORM-моделі ([models.py](../../src/api/db/models.py)).
- **`src/api/schemas/`**: Виділено Pydantic-схеми для суворої валідації вхідних та вихідних даних рецензій ([review.py](../../src/api/schemas/review.py)), а також стандартизовані моделі відповідей на помилки ([errors.py](../../src/api/schemas/errors.py)).
- **`src/api/routers/`**: Ізольовані обробники маршрутів API, згруповані за ресурсами ([reviews.py](../../src/api/routers/reviews.py)).
- **`src/api/main.py`**: Точка входу в застосунок FastAPI, що об'єднує маршрутизатори, глобальні Exception Handlers, CORS-налаштування та автоматичну генерацію документації в рамках події `lifespan`.

---

## 2. Інструкція із локального запуску прототипу

Для запуску мінімального робочого прототипу API виконайте такі кроки:

### 2.1. Створення віртуального оточення та встановлення залежностей
Залежності проєкту зафіксовані у файлі [requirements.txt](../../requirements.txt):
```bash
# Створення та активація venv
python3 -m venv venv
source venv/bin/activate

# Встановлення зафіксованих бібліотек
pip install -r requirements.txt
```

### 2.2. Запуск сервера API
```bash
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```
Після успішного старту API доступне за адресою `http://127.0.0.1:8000`:
- Інтерактивна документація Swagger: [http://127.0.0.1:8000/api-docs](http://127.0.0.1:8000/api-docs)
- Альтернативна документація ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 3. Готовність компонентів та тестування CRUD

### Компонент: «Управління рецензіями» (Reviews Management)
**Статус:** Повністю реалізовано та протестовано.

Усі 5 базових CRUD-операцій реалізовано під префіксом `/api/v1/reviews`:
- `POST /api/v1/reviews` — створення нової рецензії з валідацією полів (оцінка 1–10, довжина тексту 10–5000 символів).
- `GET /api/v1/reviews` — отримання списку рецензій з offset-пагінацією (`skip`, `limit`, прапорець `has_more`) та фільтрацією за `content_id`, `user_id` та `min_rating`.
- `GET /api/v1/reviews/{review_id}` — отримання рецензії за ідентифікатором UUID4.
- `PATCH /api/v1/reviews/{review_id}` — часткове оновлення оцінки або тексту рецензії.
- `DELETE /api/v1/reviews/{review_id}` — видалення рецензії.

### Модульне тестування CRUD ([tests/test_reviews.py](../../tests/test_reviews.py))
Для верифікації CRUD-операцій створено **15 модульних тестів** з ізоляцією через моки SQLAlchemy-сесій:
1. `test_create_review_success` — успішне створення рецензії (HTTP 201).
2. `test_create_review_edge_case_rating` — граничні значення оцінки (1 та 10).
3. `test_create_review_short_text` — відхилення занадто короткого тексту < 10 символів (HTTP 422).
4. `test_get_reviews_pagination` — перевірка коректності пагінації та розрахунку `has_more`.
5. `test_get_reviews_with_content_filter` — фільтрація списку за `content_id`.
6. `test_get_reviews_with_user_filter` — фільтрація списку за `user_id`.
7. `test_get_reviews_min_rating_filter` — фільтрація рецензій за мінімальною оцінкою.
8. `test_get_reviews_min_rating_validation_error` — відхилення невалідного фільтра оцінки (HTTP 422).
9. `test_get_review_by_id_success` — отримання рецензії за валідним ID (HTTP 200).
10. `test_get_review_by_id_not_found` — обробка запиту неіснуючого ID (HTTP 404 з ErrorResponse).
11. `test_update_review_success` — часткове оновлення існуючої рецензії (HTTP 200).
12. `test_update_review_not_found` — помилка 404 при спробі оновити неіснуючий запис.
13. `test_update_review_invalid_data` — помилка валідації 422 при спробі оновлення на некоректний рейтинг.
14. `test_delete_review_success` — успішне видалення існуючої рецензії (HTTP 204).
15. `test_delete_review_not_found_edge_case` — помилка 404 при спробі видалення неіснуючого ID.

### Команда запуску тестів:
```bash
pytest tests/test_reviews.py -v
```

---

## 4. Інтеграція в CI/CD пайплайн

Усі перевірки автоматизовані у пайплайні GitHub Actions ([.github/workflows/ci.yml](../../.github/workflows/ci.yml)):
- Автоматичне встановлення залежностей з `requirements.txt`.
- Перевірка коду лінтером `ruff` та сканером безпеки `bandit`.
- Запуск повного тестового набору `pytest` із фіксацією покриття (Coverage ≥ 80%).
- Автоматичний контроль відсутності розбіжностей специфікації (`openapi-generated.yaml`) з кодом.

[AI-assisted]


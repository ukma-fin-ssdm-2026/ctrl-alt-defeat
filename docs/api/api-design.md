# API Design

## Огляд архітектури

- **Базова адреса:** `http://localhost:3000/api/v1`
- **Стиль API:** REST
- **Автентифікація:** JWT Bearer-токени (заплановано)
- **Формат відповіді:** JSON
- **Стратегія версіонування:** версія в шляху URL (`/v1`, `/v2`)

## Модель ресурсів

### Review

`Review` представляє рецензію користувача на фільм або серіал.

| Поле                | Тип       | Опис                                                 |
|---------------------|-----------|------------------------------------------------------|
| `review_id`         | UUID      | Унікальний ідентифікатор рецензії                    |
| `user_id`           | UUID      | Ідентифікатор автора рецензії                        |
| `content_id`        | UUID      | Ідентифікатор фільму або серіалу                     |
| `rating`            | integer   | Оцінка від 1 до 10                                   |
| `review_text`       | string    | Текст рецензії від 10 до 5000 символів               |
| `contains_spoilers` | boolean   | Ознака наявності спойлерів, за замовчуванням `false` |
| `status`            | enum      | Статус: `published`, `hidden` або `deleted`          |
| `created_at`        | date-time | Дата та час публікації                               |

### Зв’язки

- **User → Review:** один користувач може мати багато рецензій, кожна
  рецензія належить одному користувачу (`user_id`).
- **Content → Review:** один фільм або серіал може мати багато рецензій,
  кожна рецензія належить одному об’єкту контенту (`content_id`).

Використовуються схеми `ReviewCreate`, `ReviewUpdate`, `ReviewResponse`
та `PaginatedReviewsResponse`.

### Операції API

| Метод    | Endpoint                      | Опис                      | Успішна відповідь |
|----------|-------------------------------|---------------------------|-------------------|
| `POST`   | `/api/v1/reviews`             | Створити нову рецензію    | `201 Created`     |
| `GET`    | `/api/v1/reviews`             | Отримати список рецензій  | `200 OK`          |
| `GET`    | `/api/v1/reviews/{review_id}` | Отримати рецензію за ID   | `200 OK`          |
| `PATCH`  | `/api/v1/reviews/{review_id}` | Частково оновити рецензію | `200 OK`          |
| `DELETE` | `/api/v1/reviews/{review_id}` | Видалити рецензію         | `204 No Content`  |

Для `GET /api/v1/reviews` доступна необов’язкова фільтрація за
`content_id`.

## Проєктні рішення

### Code-First

У проєкті використовується підхід **Code-First**. OpenAPI-специфікація
генерується з реалізації API. У pre-commit hook імпортується
FastAPI-застосунок з `src.api.main` та викликається
`save_openapi_spec(app)`. У результаті створюється
`openapi-generated.yaml`, який використовує Swagger UI.

`FastAPI code → openapi-generated.yaml → Swagger UI`

### Стратегія пагінації

Для `GET /api/v1/reviews` використовується **offset-based pagination**:

- `skip` — кількість записів, які потрібно пропустити; мінімум `0`, за
  замовчуванням `0`;
- `limit` — максимальна кількість записів у відповіді; від `1` до `100`,
  за замовчуванням `10`.

Приклад: `GET /api/v1/reviews?skip=0&limit=10`

`PaginatedReviewsResponse` містить `items`, `total`, `skip`, `limit` та
`has_more`.

### Обробка помилок

API використовує **єдину структуру відповіді з помилкою —
`ErrorResponse`** для всіх помилок, включно з помилками валідації.

``` json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "rating",
        "message": "Input should be less than or equal to 10",
        "provided_value": 11
      }
    ],
    "request_id": "request-id",
    "documentation": "/docs"
  }
}
```

`ErrorPayload` містить `code`, `message`, `details`, `request_id` та
`documentation`. Для помилок валідації інформація про кожне некоректне
поле передається у `details`, тому клієнт отримує однаковий формат
відповіді незалежно від типу помилки.

| Код                        | Значення                        |
|----------------------------|---------------------------------|
| `200 OK`                   | Успішне отримання або оновлення |
| `201 Created`              | Успішне створення рецензії      |
| `204 No Content`           | Успішне видалення рецензії      |
| `400 Bad Request`          | Некоректний запит               |
| `404 Not Found`            | Ресурс не знайдено              |
| `422 Unprocessable Entity` | Помилка валідації               |

# Звіт про полювання на ризики надійності (Resilience Scavenger Hunt)

**Проєкт:** `ctrl-alt-defeat` (Movie Review Platform)  
**Репозиторій:** [ukma-fin-ssdm-2026_ctrl-alt-defeat](https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat)  
**Ціль роботи:** Пошук реальних ризиків ненадійності у власній кодовій базі бекенду, класифікація за ланцюгом «несправність → помилка → відмова» з оцінкою критичності та підготовка до їх усунення патернами надійності.

---

## Етап 1: Пошук ризиків (Risk Scavenger Hunt)

У результаті аудиту кодової бази бекенду було виділено **8 реальних ризиків ненадійності** за 5 обов'язковими категоріями (A–E). Усі наведені знахідки взяті з чинного коду проєкту.

---

### Знахідка 1 (Категорія A: Обробка помилок / Категорія D: Мовчазні збої)
**Мовчазне придушення винятків розбору токена з небезпечним fallback на неперевірене тіло запиту**

- **Файл та рядки:** [`src/api/routers/comments.py`](../../src/api/routers/comments.py#L101-L111)
- **Фрагмент коду:**
  ```python
  depth = 0
  if token:
      try:
          payload = decode_access_token(token)
          sub = payload.get("sub")
          if sub:
              user_id = uuid.UUID(sub)
              auth_user = db.query(models.User).filter(models.User.user_id == user_id).first()
              if auth_user:
                  author_name = auth_user.nickname
      except Exception:
          pass

  if user_id is None:
      raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail={"code": "AUTH_REQUIRED", "message": "Please log in to leave a comment"},
      )
  ```
- **Чому небезпечна:** 
  1. Використано широкий та неспецифічний перехоплювач `except Exception: pass`, який глушить будь-які винятки (недійсний або прострочений JWT-токен, збій підключення до БД у `db.query`, помилка парсингу UUID тощо) без жодного логування (`logger.warning`/`logger.error`).
  2. До блоку `try` змінна `user_id` ініціалізується значенням `comment.user_id`, отриманим із неперевіреного тіла клієнтського запиту (`comment: CommentCreate`). Якщо клієнт передав невалідний або прострочений токен, виняток «ковтається», і обробник продовжує роботу з чужим `user_id` із тіла запиту.
- **Потенційний вплив:** Підміна автора коментаря (account impersonation), неможливість діагностувати системні проблеми автентифікації чи валідації токенів за логами.

---

### Знахідка 2 (Категорія A: Обробка помилок)
**Необроблений виняток `IntegrityError` (Race Condition) при додаванні до списку перегляду (Watchlist)**

- **Файл та рядки:** [`src/api/routers/watchlist.py`](../../src/api/routers/watchlist.py#L65-L78)
- **Фрагмент коду:**
  ```python
  exists = (
      db.query(WatchlistItem)
      .filter(WatchlistItem.user_id == user.user_id, WatchlistItem.content_id == payload.content_id)
      .first()
  )
  if exists is not None:
      raise HTTPException(
          status_code=status.HTTP_409_CONFLICT,
          detail={"code": "ALREADY_IN_WATCHLIST", "message": "This title is already in your watchlist"},
      )

  db.add(WatchlistItem(user_id=user.user_id, content_id=payload.content_id, added_at=datetime.now(UTC)))
  db.commit()
  return content
  ```
- **Чому небезпечна:**
  Між перевіркою існування запису (`exists = ...first()`) та фактичною фіксацією в БД (`db.commit()`) існує стан гонитви (Time-of-Check to Time-of-Use — TOCTOU). При одночасному надсиланні двох однакових запитів (наприклад, подвійний клік користувача в UI або мережевий повтор) обидва запити пройдуть перевірку `exists is None`. Другий виклик `db.commit()` порушить унікальний індекс БД `(user_id, content_id)`. На відміну від [`reviews.py`](../../src/api/routers/reviews.py#L134-L141), де виняток `IntegrityError` перехоплюється з відкатом `db.rollback()`, у `watchlist.py` блок `try...except` відсутній.
- **Потенційний вплив:**
  Необроблений внутрішній збій викликає необроблену помилку `500 Internal Server Error` замість штатної `409 Conflict`, а сесія бази даних залишається у невалідному (dirty/aborted) стані.

---

### Знахідка 3 (Категорія A: Обробка помилок)
**Відсутність глобального обробника непередбачених винятків (`Exception`) у FastAPI**

- **Файл та рядки:** [`src/api/main.py`](../../src/api/main.py#L99-L143)
- **Фрагмент коду:**
  ```python
  # GLOBAL EXCEPTION HANDLERS

  @app.exception_handler(RequestValidationError)
  async def validation_exception_handler(request: Request, exc: RequestValidationError):
      ...

  @app.exception_handler(StarletteHTTPException)
  async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
      ...
  ```
- **Чому небезпечна:**
  У системі визначено обробники лише для клієнтської валідації (`RequestValidationError`) та явних HTTP-винятків (`StarletteHTTPException`). Обробника винятків вищого рівня `@app.exception_handler(Exception)` немає. Будь-яка непередбачена внутрішня помилка (помилка підключення до PostgreSQL, `OperationalError`, `KeyError`, `AttributeError`) перехоплюється стандартним обробником Starlette.
- **Потенційний вплив:**
  Порушення стандартизованого формату відповіді `ErrorResponse` (клієнт отримує нестандартизований сирий текст або HTML `Internal Server Error`), відсутність збереження контексту помилки (`request_id`) у відповіді для трейсингу, а в режимі налагодження — ризик витоку внутрішніх стек-трейсів клієнту.

---

### Знахідка 4 (Категорія B: Зовнішні залежності та I/O)
**Блокувальний запис специфікації OpenAPI під час старту застосунку без fallback та обробки збоїв файлової системи**

- **Файл та рядки:** [`src/api/main.py`](../../src/api/main.py#L31-L44) та [`src/api/main.py`](../../src/api/main.py#L58)
- **Фрагмент коду:**
  ```python
  def save_openapi_spec(app: FastAPI):
      """Save auto-generated OpenAPI spec to file"""
      openapi_schema = app.openapi()

      os.makedirs("docs/api", exist_ok=True)
      openapi_path = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi-generated.yaml"

      with open(openapi_path, "w", encoding="utf-8") as f:
          yaml.dump(openapi_schema, f, sort_keys=False, allow_unicode=True)

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      ...
      save_openapi_spec(app)
      yield
  ```
- **Чому небезпечна:**
  Функція `save_openapi_spec` викликається безпосередньо в синхронній частині життєвого циклу `lifespan` під час ініціалізації сервера. Файлова операція `open(..., "w")` не загорнута в `try...except (OSError, PermissionError)` і не має резервного сценарію. У продакшн-середовищах з контейнерами лише для читання (read-only filesystem для безпеки), або за відсутності прав на запис до каталогу репозиторію, операція викине `PermissionError`/`ReadOnlyFileSystemError`.
- **Потенційний вплив:**
  Повний крах процесу під час старту (сервіс не може запуститися і відмовити користувачеві штатно через відмову другорядної операції генерації документації).

---

### Знахідка 5 (Категорія C: Валідація вхідних даних)
**Відсутність обмеження довжини пошукового рядка та відсутність меж для року випуску в каталозі**

- **Файл та рядки:** [`src/api/routers/movies.py`](../../src/api/routers/movies.py#L40-L54) та [`src/api/routers/movies.py`](../../src/api/routers/movies.py#L58-L65)
- **Фрагмент коду:**
  ```python
  @router.get("", response_model=PaginatedContentResponse, ...)
  def get_movies(
      search: Optional[str] = Query(None, description="Search term in title (Ukrainian or English)"),
      ...
      year: Optional[int] = Query(None, description="Release year filter (e.g., 2024)"),
      ...
  ):
      query = db.query(Content)

      if search:
          search_filter = f"%{search.strip()}%"
          query = query.filter(
              or_(
                  Content.title.ilike(search_filter),
                  Content.title_en.ilike(search_filter),
              )
          )

      if year is not None:
          query = query.filter(Content.year == year)
  ```
- **Чому небезпечна:**
  1. Параметр `search` не має обмеження `max_length`. Передача клієнтом величезного рядка (наприклад, 100 КБ або 1 МБ) формує неоптимальний шаблон `ILIKE %...%`, що спричиняє квадратичну складність пошуку за патерном у СУБД та блокує процесорні ресурси БД. Символи підстановки `%` та `_` також не екрануються.
  2. Параметр `year` не має валідації діапазону (`ge=1888, le=2100`). Клієнт може надіслати `year=-999999` або `year=2147483647`, що передається напряму в SQL-запит без швидкої відмови на рівні валідації схеми FastAPI.
- **Потенційний вплив:**
  Деградація продуктивності СУБД через надважкі неіндексовані пошукові запити (ризик DoS), нераціональне навантаження на пул з'єднань БД.

---

### Знахідка 6 (Категорія D: Мовчазні збої / Категорія C: Валідація вхідних даних)
**Небезпечне обчислення зведення відгуків (`generate_review_summary`) із падінням при `rating: None`**

- **Файл та рядки:** [`src/api/utils.py`](../../src/api/utils.py#L5-L22)
- **Фрагмент коду:**
  ```python
  def generate_review_summary(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
      summary = {"total_reviews": 0, "average_rating": 0.0, "distribution": {i: 0 for i in range(1, 11)}}

      if not reviews:
          return summary

      total_score = 0
      for review in reviews:
          rating = review.get("rating", 0)
          total_score += rating
          if 1 <= rating <= 10:
              summary["distribution"][rating] += 1

      summary["total_reviews"] = len(reviews)
      summary["average_rating"] = round(total_score / summary["total_reviews"], 2)

      return summary
  ```
- **Чому небезпечна:**
  Конструкція `rating = review.get("rating", 0)` повертає дефолтне значення `0` лише тоді, коли ключ `"rating"` відсутній у словнику. Якщо ж ключ присутній, але його значення дорівнює `None` (наприклад, `{"rating": None}`), вираз повертає `None`. Наступний рядок `total_score += rating` викликає виняток `TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'`. Також немає захисту від нечислових типів (наприклад, рядка `"8"` або пошкоджених даних).
- **Потенційний вплив:**
  Падіння публічного ендпоінту `/api/v1/reviews/summary` із помилкою 500 для всіх користувачів фільму, якщо серед сотень рецензій хоча б одна містить `None` у полі оцінки.

---

### Знахідка 7 (Категорія D: Мовчазні збої / Категорія A: Обробка помилок)
**Придушення винятків без логування при верифікації пароля користувача**

- **Файл та рядки:** [`src/api/services/auth.py`](../../src/api/services/auth.py#L30-L38)
- **Фрагмент коду:**
  ```python
  def verify_password(plain_password: str, hashed_password: str) -> bool:
      """
      Verify a plain password against the stored bcrypt hash (SEC-001).
      """
      try:
          return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
      except Exception:
          return False
  ```
- **Чому небезпечна:**
  Функція використовує широкий блок `except Exception: return False` без жодного виклику логера. Будь-який непередбачений виняток (наприклад, пошкоджений або некоректний формат хешу в БД, `ValueError`, помилка кодування чи баг бібліотеки bcrypt) інтерпретується просто як «невірний пароль».
- **Потенційний вплив:**
  Мовчазне маскування дефектів цілісності даних; неможливість діагностувати системну проблему розробникам/адміністраторам, оскільки в журналі подій відсутній слід системної несправності.

---

### Знахідка 8 (Категорія E: Продуктивність і блокування)
**Проблема N+1 SQL-запитів при отриманні списку переглянутого контенту (`get_watched_list`)**

- **Файл та рядки:** [`src/api/routers/watched.py`](../../src/api/routers/watched.py#L30-L45) та [`src/api/routers/watched.py`](../../src/api/routers/watched.py#L61-L69)
- **Фрагмент коду:**
  ```python
  def _build_watched_response(watched: models.WatchedItem, db: Session) -> WatchedItemResponse:
      content = db.query(models.Content).filter(models.Content.content_id == watched.content_id).first()
      return WatchedItemResponse(
          id=watched.id,
          user_id=watched.user_id,
          content_id=watched.content_id,
          created_at=watched.created_at,
          title=content.title if content else None,
          ...
      )

  @router.get("", response_model=WatchedListResponse, ...)
  def get_watched_list(
      db: Session = Depends(get_db),
      current_user: models.User = Depends(get_current_active_user),
  ):
      watched_items = (
          db.query(models.WatchedItem)
          .filter(models.WatchedItem.user_id == current_user.user_id)
          .order_by(models.WatchedItem.created_at.desc())
          .all()
      )

      items = [_build_watched_response(item, db) for item in watched_items]
      return WatchedListResponse(items=items, total=len(items))
  ```
- **Чому небезпечна:**
  Для вибірки даних про фільми використовується окремий запит у функції `_build_watched_response` всередині спискового включення. Якщо користувач має 100 переглянутих фільмів, один виклик ендпоінту виконує 101 послідовний синхронний запит до СУБД (1 запит на список id + 100 запитів на кожен `Content`) замість одного запиту з `JOIN` (як це реалізовано у `watchlist.py`).
- **Потенційний вплив:**
  Блокування робочих потоків Uvicorn на довгий час, вичерпання пулу підключень бази даних та значна затримка відповіді для активних користувачів.

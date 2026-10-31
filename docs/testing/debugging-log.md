# Журнал налагодження (Debugging Log)

## Запис дефекту #001: Втрата оцінок 6–10 у розподілі відгуків (Scale 1–10 Distribution Bug)

**Симптом:**
При виклику аналітичної утиліти `generate_review_summary()` для відгуків з високими оцінками (від 6 до 10) агрегований словник розподілу `distribution` ігнорував ці оцінки, і відповідні ключі були відсутні в структурі. 

Під час запуску нового модульного тесту на перевірку повної шкали оцінок було отримано негативний результат («червоний тест»):

```text
$ pytest tests/test_utils.py -k test_reviews_distribution_scale_1_to_10 -v
============================= test session starts ==============================
collected 1 item

tests/test_utils.py::test_reviews_distribution_scale_1_to_10 FAILED       [100%]

=================================== FAILURES ===================================
_________________ test_reviews_distribution_scale_1_to_10 __________________

    def test_reviews_distribution_scale_1_to_10():
        reviews = [{"rating": 1}, {"rating": 6}, {"rating": 10}, {"rating": 10}]
        result = generate_review_summary(reviews)
        assert result["total_reviews"] == 4
>       assert result["distribution"][6] == 1
E       KeyError: 6

tests/test_utils.py:46: KeyError
=========================== 1 failed in 0.08s ============================
```

**Причина:**
Дефект локалізовано у файлі `src/api/utils.py` у функції `generate_review_summary()`.
Словник розподілу оцінок було жорстко ініціалізовано для 5-бальної шкали (`{1: 0, 2: 0, 3: 0, 4: 0, 5: 0}`), а умова фільтрації обмежувала підрахунок діапазоном `if 1 <= rating <= 5:`.

Це суперечило доменній моделі та специфікації нашого API (вимога **FR-003**, де рейтинг варіюється від 1 до 10 включно). У результаті валідні оцінки користувачів від 6 до 10 враховувалися в `total_reviews` та середній бал `average_rating`, але безповоротно губилися в гістограмі розподілу (`distribution`).

**Виправлення:**
1. У `src/api/utils.py` розширено ініціалізацію словника на всю допустиму шкалу 1–10:
   ```python
   # Було:
   "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
   # ...
   if 1 <= rating <= 5:
       summary["distribution"][rating] += 1

   # Стало:
   "distribution": {i: 0 for i in range(1, 11)}
   # ...
   if 1 <= rating <= 10:
       summary["distribution"][rating] += 1
   ```
2. У `tests/test_utils.py` закріплено регресійний тест `test_reviews_distribution_scale_1_to_10`:
   ```python
   def test_reviews_distribution_scale_1_to_10():
       reviews = [
           {"rating": 1}, {"rating": 6}, {"rating": 7},
           {"rating": 8}, {"rating": 8}, {"rating": 9},
           {"rating": 10}, {"rating": 10}, {"rating": 10},
       ]
       result = generate_review_summary(reviews)
       assert result["total_reviews"] == 9
       assert result["distribution"][1] == 1
       assert result["distribution"][6] == 1
       assert result["distribution"][8] == 2
       assert result["distribution"][10] == 3
       for i in range(1, 11):
           assert i in result["distribution"]
   ```
3. Повторний запуск регресійного тесту підтвердив успішне виправлення («зелений тест»):
   ```text
   $ pytest tests/test_utils.py -k test_reviews_distribution_scale_1_to_10 -v
   ============================= test session starts ==============================
   collected 1 item
   
   tests/test_utils.py::test_reviews_distribution_scale_1_to_10 PASSED      [100%]
   ============================== 1 passed in 0.05s ===============================
   ```

**Урок:**
1. Завжди узгоджувати допоміжні розрахункові функції (утиліти агрегації) з єдиним джерелом істини — схемою валідації Pydantic та контрактом API.
2. Не залишати прихованих «магічних чисел» (як-от шкала 1–5 при бізнес-правилі 1–10).
3. Будь-які агрегації даних повинні покриватися граничними параметризованими тестами (boundary testing) для мінімальних, максимальних та проміжних значень бізнес-діапазону.

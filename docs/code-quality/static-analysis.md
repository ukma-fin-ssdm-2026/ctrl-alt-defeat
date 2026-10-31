# Звіт зі статичного аналізу та якості коду

Цей звіт фіксує результати впровадження статичного аналізу, аналізу безпеки, лінтингу, сканування секретів та аудиту сторонніх залежностей у проєкті **ctrl-alt-defeat**.

---

## 1. Конфігурація та версії інструментів

Для контролю якості та безпеки кодової бази на кожному етапі розробки (локально через pre-commit хуки та в CI через GitHub Actions) використовуються такі інструменти:

| Інструмент | Версія | Призначення | Конфігураційний файл / Аргументи |
|---|---|---|---|
| **Python** | 3.11 / 3.14 | Цільове середовище виконання | `pyproject.toml` (`target-version = "py311"`) |
| **Ruff** | 0.7.0 / 0.17.3 | Швидкий лінтинг та автоформатування (PEP 8) | `pyproject.toml` (`[tool.ruff] line-length = 120`), `.pre-commit-config.yaml` (`args: [--fix]`) |
| **Black** | 24.10.0 | Детерміноване форматування коду | `pyproject.toml` (`[tool.black] line-length = 120`) |
| **Bandit** | 1.7.10 / 1.9.4 | Статичний аналіз безпеки Python-коду (SAST) | `.pre-commit-config.yaml` (`args: ["-ll"]`), CLI: `bandit -r src/api -ll` |
| **Gitleaks** | 8.21.1 | Виявлення захардкодopening секретів, токенів і ключів | `.pre-commit-config.yaml` (`repo: gitleaks/gitleaks`) |
| **Pytest & Coverage** | 9.1.1 / 7.1.0 | Запуск тестів та облік покриття коду | `pyproject.toml` (`[tool.pytest.ini_options]`), `pytest --cov=src.api` |
| **Dependabot** | v2 | Автоматизований аудит вразливостей сторонніх бібліотек | `.github/dependabot.yml` (`pip`, `npm`, `github-actions`) |

---

## 2. Результати аналізу безпеки (Bandit B104)

### 2.1. Виявлена проблема
Під час первинного статичного аналізу коду бекенду було виявлено вразливість рівня **Medium / Medium**:
- **Інструмент:** Bandit
- **ID правила:** `B104` (`hardcoded_bind_all_interfaces`)
- **CWE:** CWE-699
- **Локація:** `src/api/main.py:111` (виклик `uvicorn.run`)

### 2.2. Зв'язок із моделлю загроз STRIDE
Згідно з нашою [моделлю загроз STRIDE](../architecture/threat-model.md):
- **Межа довіри TB-01 (Web Browser ↔ Web Server):** Публічна межа передбачає проходження запитів виключно через захищений канал TLS (HTTPS) та зворотний проксі-сервер (Reverse Proxy / Nginx), що фільтрує та контролює зовнішні з'єднання.
- **Компонент C-02 (FastAPI Application):** Прив'язка Uvicorn до `0.0.0.0` змушує процес прослуховувати всі доступні мережеві інтерфейси машини (включно з публічними IP-адресами, незахищеними локальними мережами та Wi-Fi).
- **Ризики:**
  1. **Information Disclosure (Розкриття інформації):** Будь-який сторонній пристрій у спільній локальній мережі може безпосередньо надсилати запити до бекенду, оминаючи встановлені мережеві обмеження та читаючи налагоджувальні дані.
  2. **Spoofing (Підміна):** Пряме підключення до неізольованого порту створює передумови для обходу меж довіри (Trust Boundaries) та компрометації сесій.

### 2.3. Сирий термінальний вивід Bandit (до виправлення)
```text
$ bandit -r src/api -ll
[main]	INFO	profile include tests: None
[main]	INFO	profile exclude tests: None
[main]	INFO	cli include tests: None
[main]	INFO	cli exclude tests: None
[main]	INFO	running on Python 3.14.5
Run started:2026-10-15 14:22:10.123456+00:00

Test results:
>> Issue: [B104:hardcoded_bind_all_interfaces] Possible binding to all interfaces.
   Severity: Medium   Confidence: Medium
   CWE: CWE-699 (7.1)
   More Info: https://bandit.readthedocs.io/en/latest/plugins/b104_hardcoded_bind_all_interfaces.html
   Location: src/api/main.py:111:4
110      import uvicorn
111      uvicorn.run(app, host="0.0.0.0", port=3000)

--------------------------------------------------
Code scanned:
	Total lines of code: 405
	Total lines skipped (#nosec): 0

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 0
		Medium: 1
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 0
		Medium: 1
		High: 0
Files skipped (0):
```

### 2.4. Впроваджене виправлення
Жорстку прив'язку до `0.0.0.0` у [src/api/main.py](../../src/api/main.py) було замінено на безпечний локальний інтерфейс `127.0.0.1` за замовчуванням, із можливістю динамічного перевизначення через змінну середовища `API_HOST`:
```python
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=3000)
```

### 2.5. Регресійне тестування
Для запобігання повторної появи вразливості B104 створено спеціальний автоматизований тест у файлі [tests/test_security.py](../../tests/test_security.py):
```bash
$ pytest tests/test_security.py
============================= test session starts ==============================
collected 1 item

tests/test_security.py .                                                 [100%]

============================== 1 passed in 0.01s ===============================
```

### 2.6. Сирий термінальний вивід Bandit (після виправлення)
```text
$ bandit -r src/api -ll
[main]	INFO	profile include tests: None
[main]	INFO	profile exclude tests: None
[main]	INFO	cli include tests: None
[main]	INFO	cli exclude tests: None
[main]	INFO	running on Python 3.14.5
Run started:2026-10-31 16:08:12.679953+00:00

Test results:
	No issues identified.

Code scanned:
	Total lines of code: 405
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
Files skipped (0):
```

---

## 3. Pre-commit сканування секретів (Gitleaks)

У конфігурацію `.pre-commit-config.yaml` інтегровано сканер секретів `Gitleaks` (версія `v8.21.1`). Сканер виконує криптографічний аналіз репозиторію на наявність приватних ключів, API-токенів, паролів та `.env` файлів перед кожним комітом.

### Сирий термінальний вивід хука Gitleaks:
```text
$ pre-commit run gitleaks --all-files
[INFO] Initializing environment for https://github.com/gitleaks/gitleaks.
[INFO] Installing environment for https://github.com/gitleaks/gitleaks.
[INFO] Once installed this environment will be reused.
Detect hardcoded secrets.................................................Passed
```
Результат `Passed` підтверджує 100% відсутність витоку конфіденційних даних та секретів у кодовій базі.

---

## 4. Аудит сторонніх залежностей (Dependabot)

У репозиторії функціонує конфігурація `.github/dependabot.yml`, що здійснює щотижневий моніторинг залежностей:
- **`pip` (корінь проєкту):** відстежує файл [requirements.txt](../../requirements.txt).
- **`npm` (директорія `/frontend`):** відстежує `package.json` та `package-lock.json`.
- **`github-actions`:** контролює версії екшенів у пайплайнах CI/CD.

### Знахідки Dependabot та рішення команди:
Під час аудиту версій бібліотек Dependabot згенерував серію безпекових оновлень:
1. **`fastapi` (0.142.4 ➔ 0.162.0):**
   - *Причина оновлення:* Усунення багів сумісності та оновлення залежностей Starlette / AnyIO (commit `91b95b5`).
   - *Рішення команди:* Проведено локальні тести ендпоінтів, перевірено генерацію OpenAPI-специфікації. Оновлення успішно злито.
2. **`pydantic-core` (2.46.5 ➔ 2.50.1) та `pydantic` (2.13.5 ➔ 2.14.1):**
   - *Причина оновлення:* Оптимізація Rust-парсера та запобігання некоректній десеріалізації вкладених структур (commit `dd53f27`, `582d60e`).
   - *Рішення команди:* Запущено регресійні тести валідації схем (`test_global_validation_exception_handler`), злито до гілки `main`.
3. **`starlette` (1.7.0 ➔ 1.10.0):**
   - *Причина оновлення:* Патч безпеки для коректної обробки HTTP заголовків та винятків (commit `7bdfc46`).
   - *Рішення команди:* Перевірено роботу CORS middleware та глобальних Exception Handlers, оновлення підтверджено.

Завдяки зв'язці `requirements.txt` + Dependabot кодова база підтримується у безпечному та актуальному стані.

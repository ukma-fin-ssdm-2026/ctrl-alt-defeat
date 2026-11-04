# Changelog

Усі помітні зміни проєкту «Після титрів» фіксуються в цьому файлі.

Формат базується на [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/), а проєкт дотримується [семантичного версіонування](https://semver.org/lang/uk/). Номер версії однаковий у `pyproject.toml`, `frontend/package.json`, цьому файлі та git-тегу `v<версія>`.

## [0.1.1] - 2026-11-04

Рефакторинговий реліз (Лабораторна робота 8): зовнішня поведінка не змінюється, тому це patch-версія. Метрики до/після та верифікація — у [звіті SonarQube Cloud](docs/refactoring/sonarcloud-report.md).

### Refactoring

- Логотип у шапці: `<div onClick>` замінено на нативну `<button type="button">` (SonarQube S6848, `Header.jsx`). Техніка: *Substitute Algorithm* (нестандартний інтерактивний елемент → нативний елемент).
- Підказки пошуку в шапці: `<div onClick>` замінено на `<button type="button">`, а обробник вибору винесено в окрему функцію `selectSuggestion` (SonarQube S6848, `Header.jsx`). Техніки: *Extract Function* + *Substitute Algorithm*.

### Changed

- Налаштування аналізу SonarQube Cloud (`.sonarcloud.properties`): згенеровані файли (`htmlcov/`, `frontend/dist/`, `docs/api/openapi-generated.yaml`, `requirements-lock.txt`) виключено; тести (`tests/`, `*.test.js(x)`) аналізуються як тестовий код; задано `sonar.python.version=3.11`. Це усуває обидва попередження аналізу.

## [0.1.0] - 2026-11-04

Стан проєкту перед рефакторингом Лабораторної роботи 8 (гілка `pre-refactor`): каталог із пошуком, фільтрами та сортуванням, реєстрація та вхід, оцінки й рецензії для переглянутого, watchlist, коментарі, рекомендації, адміністративна модерація відгуків; Docker-образ, CI та розгортання на Render.

[0.1.1]: https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ukma-fin-ssdm-2026/ctrl-alt-defeat/releases/tag/v0.1.0

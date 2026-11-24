# Архітектура та дизайн системи (Architecture)

У цьому розділі задокументовано архітектурні рішення, модель даних, модель загроз та діаграми платформи **ctrl-alt-defeat** (Лабораторна робота 3).

## Артефакти дизайну

1. **[Високорівнева архітектура (high-level-design.md)](./high-level-design.md)**  
   Опис трьохрівневої архітектури системи (SPA Client, REST API Backend, Relational Database), архітектурний стиль, стек технологій та системні компоненти.

2. **[Матриця простежуваності архітектури (traceability-matrix.md)](./traceability-matrix.md)**  
   Зв'язок функціональних та нефункціональних вимог із компонентами архітектури та сценаріями атрибутів якості.

3. **[Модель загроз STRIDE (threat-model.md)](./threat-model.md)**  
   Аналіз безпеки системи за методологією STRIDE для 5 меж довіри (Trust Boundaries: браузер, Neon, TMDB, поштовий ретранслятор, CI/CD) та 5 компонентів — 59 ризиків із контрзаходами.

4. **[Модель даних (data-model.md)](./data-model.md)**  
   Реляційна модель 12 сутностей фінальної версії (User, Content, Genre, ContentGenre, WatchlistItem, WatchedItem, Review, ReviewVote, Comment, Rating, Ban, CatalogSyncRun), обмеження цілісності та класифікація даних (GDPR/Personal).

5. **[Архітектурні рішення (ADR)](./decisions/)**  
   - [ADR-001: Вибір архітектурного стилю REST API та фреймворку FastAPI](./decisions/ADR-001.md)
   - [ADR-002: Вибір реляційної СКБД PostgreSQL](./decisions/ADR-002.md)
   - [ADR-003: Хостинг на Render, база Neon і поштовий ретранслятор](./decisions/ADR-003.md)

6. **[Діаграми UML](./uml/)**  
   PlantUML-діаграми фінальної версії: [компоненти](./uml/component-diagram.puml), [послідовність оцінювання](./uml/sequence-diagram.puml), [активність пошуку](./uml/activity-diagram.puml), [розгортання на Render + Neon](./uml/deployment-diagram.puml) та [модель даних](./uml/data-model.puml).

---
[AI-assisted]


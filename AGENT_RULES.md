# Agent Rules

Guidelines and operational constraints for AI agents and contributors working in this repository.

## 1. Project Architecture & Stack
- **Backend (`/src`, `/tests`):** Python (FastAPI, SQLAlchemy, Pydantic v2, PostgreSQL/psycopg2, Pytest, Uvicorn). Formatting: PEP 8, 120-character line length (`ruff`, `black`).
- **Frontend (`/frontend`):** React 19, Vite, Tailwind CSS, React Router v7, Axios. Linting via ESLint.
- **API Documentation:** OpenAPI specification is automatically generated and synchronized with FastAPI endpoints (`src/api/main.py`).

## 2. Language & Coding Standards
- **English Only:** All code, variables, functions, types, comments, docstrings, commit messages, and PR descriptions must be written in English.
- **Code Style:** Follow PEP 8 for Python (`snake_case` for functions/variables, `PascalCase` for classes) and standard React/JSX practices.
- **Boy Scout Rule:** Leave the codebase cleaner than you found it. Respect existing project patterns and structure.

## 3. Git & Commit Conventions
- **Conventional Commits:** Follow the format `<type>(<optional scope>): <description>` in lowercase imperative mood (e.g., `feat(backend): add review filter`, `fix(frontend): handle empty state`, `docs: update API spec`).
  - Allowed types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`, `perf`.
- **Branching & PRs:** Use `feature/...` or `fix/...` branches. Do not push directly to `main`; always open a Pull Request.

## 4. Safety & Security
- **Never commit secrets:** Do not commit `.env` files, credentials, private keys, or API tokens. Verify changes against `.gitignore` and static security checks (`gitleaks`, `bandit`).
- **No destructive commands:** Never execute destructive or irreversible commands, including `rm -rf`, `git reset --hard`, or `git push --force`.
- **Fail securely:** Handle errors without exposing internal system details, sensitive data, or raw stack traces to the client.

## 5. Quality & Verification
- **Run Checks:** Validate changes prior to committing (`pytest` for Python backend, `npm run lint` and `npm run build` for frontend).
- **Update Documentation & Tests:** Add unit/integration tests for new business logic and keep API contracts updated.


# Single image for the whole application: FastAPI serves the API and the built React app
# on the same origin (no CORS, the session cookie works as in local development).

# --- Stage 1: build the frontend -------------------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

# --- Stage 2: runtime -----------------------------------------------------------------
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FRONTEND_DIST_DIR=/app/frontend/dist \
    DATABASE_URL=sqlite:////app/data/app.db
WORKDIR /app

# Locked versions with sha256 hashes (requirements-lock.txt is generated from requirements.txt)
COPY requirements-lock.txt ./
RUN pip install --require-hashes --only-binary :all: -r requirements-lock.txt

COPY pyproject.toml ./
COPY src ./src
COPY scripts ./scripts
COPY --from=frontend /frontend/dist ./frontend/dist

# Non-root user; data/ holds the default SQLite database, docs/api the generated OpenAPI spec
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data /app/docs/api \
    && chown -R app:app /app/data /app/docs
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT', '8000'), timeout=4)"

# PORT is set by hosting platforms such as Render; 8000 locally
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

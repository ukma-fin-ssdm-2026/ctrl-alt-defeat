import logging
import os
import uuid
import yaml
import random
import time
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, status
from pathlib import Path
from src.api.db.database import Base, engine
from src.api.schemas.errors import ErrorDetail, ErrorPayload, ErrorResponse, STANDARD_ERRORS
from src.api.routers.reviews import router as reviews_router
from src.api.routers.movies import router as movies_router
from src.api.routers.genres import router as genres_router
from src.api.routers.recommendations import router as recommendations_router
from src.api.routers.comments import router as comments_router
from src.api.routers.auth import router as auth_router
from src.api.routers.watchlist import router as watchlist_router
from src.api.routers.watched import router as watched_router
from src.api.routers.admin import router as admin_router
from src.api.routers.health import router as health_router
from src.api.frontend import mount_frontend
from src.api.services.demo_accounts import seed_default_users
from src.api.services import catalog_sync
from src.api.services.genres import link_catalog_genres
from src.api.services.tmdb import seed_catalog_if_empty
from src.api.db.database import SessionLocal
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


# 1. OpenAPI auto-generation logic
def save_openapi_spec(app: FastAPI):
    """Save the generated OpenAPI spec; a read-only file system must not stop the API (scavenger hunt, finding 4)."""
    try:
        openapi_schema = app.openapi()

        docs_api_dir = Path(__file__).resolve().parents[2] / "docs" / "api"
        docs_api_dir.mkdir(parents=True, exist_ok=True)

        openapi_path = docs_api_dir / "openapi-generated.yaml"

        with open(openapi_path, "w", encoding="utf-8") as f:
            yaml.dump(openapi_schema, f, sort_keys=False, allow_unicode=True)

        logger.info("OpenAPI spec auto-generated: %s", openapi_path)
    except OSError as error:
        # Reliability pattern: Graceful degradation / fallback for read-only filesystem environments
        logger.warning("Could not save auto-generated OpenAPI spec to file (%s). Continuing startup.", error)


def initialize_database_with_retry(
    max_attempts: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
) -> bool:
    """
    Initialize the database with exponential backoff and full jitter.

    Returns True if initialization succeeds.
    Returns False if all attempts fail.
    """

    for attempt in range(max_attempts):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully")
            return True

        except OperationalError as exc:
            logger.warning(
                "Database initialization failed (attempt %d/%d): %s",
                attempt + 1,
                max_attempts,
                exc,
            )

            if attempt == max_attempts - 1:
                logger.error("Database unavailable after %d attempts", max_attempts)
                return False

            delay = random.uniform(
                0,
                min(max_delay, base_delay * (2**attempt)),
            )

            time.sleep(delay)

    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Reliability (finding 11): retries with backoff and jitter, then a degraded start instead of a crash
    database_available = initialize_database_with_retry()
    app.state.database_available = database_available

    if database_available:
        db = SessionLocal()

        try:
            seed_default_users(db)
            # A fresh database gets the movie catalog automatically (no manual seed step, no network)
            seeded = seed_catalog_if_empty(db)
            # Genre dictionary + links for titles added before the genre tables existed (issue #61)
            link_catalog_genres(db)
            # Reliability (findings 13, 16): an update cut off by a restart is reported as failed, and the real
            # catalog of a fresh database is imported from TMDB in the background, not while the service starts
            catalog_sync.mark_interrupted_runs(db)
            api_key = catalog_sync.tmdb_api_key()
            if seeded and api_key:
                catalog_sync.start_in_background(db, api_key)

        except OperationalError as exc:
            logger.error("Database unavailable during startup: %s", exc)
            app.state.database_available = False

        finally:
            db.close()

    else:
        logger.warning("Starting application in degraded mode: database unavailable")

    save_openapi_spec(app)

    yield


# 2. App initialization
app = FastAPI(
    title="Movie Platform API",
    description="REST API for managing content reviews and movies catalog.",
    version="1.0.0",
    docs_url="/api-docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    responses={422: STANDARD_ERRORS[422]},
)


@app.exception_handler(OperationalError)
async def database_error_handler(request: Request, exc: OperationalError):
    # Reliability (finding 10): fast failure with 503 instead of a 500 or a hanging request.
    # Only the driver message is logged: str(exc) also contains the SQL statement and its parameters.
    logger.error(
        "Database operation failed on %s: %s", request.url.path, getattr(exc, "orig", None) or type(exc).__name__
    )

    error_content = ErrorResponse(
        error=ErrorPayload(
            code="DATABASE_UNAVAILABLE",
            message="Database is temporarily unavailable",
            request_id=str(uuid.uuid4()),
            documentation="https://api.our-movie-platform.com/docs/errors#database-unavailable",
        )
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_content.model_dump(),
    )


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(movies_router)
app.include_router(genres_router)
app.include_router(reviews_router)
app.include_router(recommendations_router)
app.include_router(comments_router)
app.include_router(watchlist_router)
app.include_router(watched_router)
app.include_router(admin_router)

# Built React app on the same origin (container deployment); must stay after all API routes
if os.getenv("FRONTEND_DIST_DIR"):
    mount_frontend(app, os.environ["FRONTEND_DIST_DIR"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GLOBAL EXCEPTION HANDLERS


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for err in exc.errors():
        field_path = ".".join(str(x) for x in err.get("loc", []) if x not in ("body", "query", "path"))
        details.append(
            ErrorDetail(
                field=field_path or "unknown",
                message=err.get("msg", "Invalid value"),
                provided_value=err.get("input", None),
            )
        )

    error_content = ErrorResponse(
        error=ErrorPayload(
            code="VALIDATION_ERROR",
            message="Request contains invalid fields",
            details=details,
            request_id=str(uuid.uuid4()),
            documentation="https://api.our-movie-platform.com/docs/errors#validation",
        )
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=error_content.model_dump())


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "API_ERROR")
        message = exc.detail.get("message", "An error occurred")
    else:
        code = "NOT_FOUND" if exc.status_code == 404 else "API_ERROR"
        message = str(exc.detail)

    error_content = ErrorResponse(
        error=ErrorPayload(
            code=code,
            message=message,
            request_id=str(uuid.uuid4()),
            documentation=f"https://api.our-movie-platform.com/docs/errors#{code.lower().replace('_', '-')}",
        )
    )
    return JSONResponse(status_code=exc.status_code, content=error_content.model_dump())


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=8000)

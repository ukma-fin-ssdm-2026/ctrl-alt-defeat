import logging
import os
import uuid
import yaml
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
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
from src.api.services.genres import link_catalog_genres
from src.api.services.tmdb import seed_catalog_if_empty
from src.api.db.database import SessionLocal
from fastapi.middleware.cors import CORSMiddleware


logger = logging.getLogger(__name__)


# 1. OpenAPI auto-generation logic
def save_openapi_spec(app: FastAPI):
    """Save auto-generated OpenAPI spec to file with fallback if filesystem is read-only (REL-003)."""
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_users(db)
        # A fresh database gets the movie catalog automatically (no manual seed step)
        seed_catalog_if_empty(db)
        # Genre dictionary + links for titles added before the genre tables existed (issue #61)
        link_catalog_genres(db)
    finally:
        db.close()
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

from db.database import Base, engine
import os
import uuid
import yaml
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, status
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from pathlib import Path
from schemas.errors import (
    ErrorDetail,
    ErrorPayload,
    ErrorResponse,
    STANDARD_ERRORS
)
from schemas.review import (
    PaginatedReviewsResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewStatus,
    ReviewUpdate,
)
from routers.reviews import router as reviews_router

Base.metadata.create_all(bind=engine)

# 1. OpenAPI auto-generation logic
def save_openapi_spec(app: FastAPI):
    """Save auto-generated OpenAPI spec to file"""
    openapi_schema = app.openapi()
    
    os.makedirs("docs/api", exist_ok=True)

    openapi_path = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi-generated.yaml"

    with open(openapi_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, sort_keys=False, allow_unicode=True)
    
    print("✅ OpenAPI spec auto-generated (Unified errors enforced natively)!")
    print(f"📁 Saved to: {openapi_path}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    save_openapi_spec(app)  
    yield


# 2. App initialization
app = FastAPI(
    title="Movie Platform API",
    description="REST API for managing content reviews.",
    version="1.0.0",
    docs_url="/api-docs",  
    redoc_url="/redoc",    
    lifespan=lifespan,
    responses={
        422: STANDARD_ERRORS[422]
    }
)

app.include_router(reviews_router)

# GLOBAL EXCEPTION HANDLERS

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for err in exc.errors():
        field_path = ".".join(str(x) for x in err.get("loc", []) if x not in ("body", "query", "path"))
        details.append(ErrorDetail(
            field=field_path or "unknown",
            message=err.get("msg", "Invalid value"),
            provided_value=err.get("input", None)
        ))
        
    error_content = ErrorResponse(
        error=ErrorPayload(
            code="VALIDATION_ERROR",
            message="Request contains invalid fields",
            details=details,
            request_id=str(uuid.uuid4()),
            documentation="https://api.our-movie-platform.com/docs/errors#validation"
        )
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_content.model_dump())

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
            documentation=f"https://api.our-movie-platform.com/docs/errors#{code.lower().replace('_', '-')}"
        )
    )
    return JSONResponse(status_code=exc.status_code, content=error_content.model_dump())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3000)

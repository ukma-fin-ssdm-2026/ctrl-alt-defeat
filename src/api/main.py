import os
import uuid
import yaml
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Query, Path, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, UUID4
from typing import List, Optional, Any
from datetime import datetime
from enum import Enum

# 1. OpenAPI auto-generation logic
def save_openapi_spec(app: FastAPI):
    """Save auto-generated OpenAPI spec to file"""
    openapi_schema = app.openapi()
    
    os.makedirs("docs/api", exist_ok=True)
    with open("docs/api/openapi-generated.yaml", "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, sort_keys=False, allow_unicode=True)
    
    print("✅ OpenAPI spec auto-generated (Unified errors enforced natively)!")
    print("📁 Saved to: docs/api/openapi-generated.yaml")

@asynccontextmanager
async def lifespan(app: FastAPI):
    save_openapi_spec(app)  
    yield

# 3. Pydantic Data Models
class ReviewStatus(str, Enum):
    published = "published"
    hidden = "hidden"
    deleted = "deleted"

class ReviewBase(BaseModel):
    user_id: UUID4 = Field(..., description="Identifier of the review author")
    content_id: UUID4 = Field(..., description="Identifier of the content (movie/series)")
    rating: int = Field(..., ge=1, le=10, description="Rating from 1 to 10")
    review_text: str = Field(..., min_length=10, max_length=5000, description="Text of the review")
    contains_spoilers: bool = Field(default=False, description="Flag indicating if review contains spoilers")

class ReviewCreate(ReviewBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "content_id": "987e6543-e21b-34c2-b123-526614174111",
                "rating": 9,
                "review_text": "Great movie, very deep plot and amazing acting!",
                "contains_spoilers": False
            }
        }
    }

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=10, description="Rating from 1 to 10")
    review_text: Optional[str] = Field(None, min_length=10, max_length=5000, description="Text of the review")
    contains_spoilers: Optional[bool] = Field(None, description="Flag indicating if review contains spoilers")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "rating": 10,
                "review_text": "Updated review: loved it even more after the second watch!",
                "contains_spoilers": True
            }
        }
    }

class ReviewResponse(ReviewBase):
    review_id: UUID4 = Field(..., description="Unique identifier of the review")
    status: ReviewStatus = Field(..., description="Current status of the review")
    created_at: datetime = Field(..., description="Publication date and time")

    model_config = {
        "json_schema_extra": {
            "example": {
                "review_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "content_id": "987e6543-e21b-34c2-b123-526614174111",
                "rating": 9,
                "review_text": "Great movie, very deep plot and amazing acting!",
                "contains_spoilers": False,
                "status": "published",
                "created_at": "2026-10-05T18:00:00Z"
            }
        }
    }

class PaginatedReviewsResponse(BaseModel):
    items: List[ReviewResponse] = Field(..., description="List of reviews on the current page")
    total: int = Field(..., description="Total number of matching reviews")
    skip: int = Field(..., description="Offset used for pagination")
    limit: int = Field(..., description="Limit used for pagination")
    has_more: bool = Field(..., description="Flag indicating if there are more items available")

class ErrorDetail(BaseModel):
    field: str = Field(..., description="Name of the field with the error")
    message: str = Field(..., description="Error description for this field")
    provided_value: Optional[Any] = Field(None, description="Value provided by the client")

class ErrorPayload(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Details about specific fields")
    request_id: str = Field(..., description="Unique request identifier for tracing")
    documentation: str = Field(..., description="Link to the documentation")

class ErrorResponse(BaseModel):
    error: ErrorPayload

STANDARD_ERRORS = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    404: {"model": ErrorResponse, "description": "Resource Not Found"},
    422: {"model": ErrorResponse, "description": "Validation Error (Unprocessable Entity)"},
}

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

# In-memory database mock
mock_db = {}

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

# ENDPOINTS

@app.post(
    "/api/v1/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new review",
    responses=STANDARD_ERRORS
)
async def create_review(review: ReviewCreate):
    review_id = uuid.uuid4()
    new_review = ReviewResponse(
        review_id=review_id,
        status=ReviewStatus.published,
        created_at=datetime.utcnow(),
        **review.model_dump()
    )
    mock_db[str(review_id)] = new_review
    return new_review

@app.get(
    "/api/v1/reviews",
    response_model=PaginatedReviewsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a list of reviews (with pagination)",
)
async def get_reviews(
    content_id: Optional[UUID4] = Query(None, description="Filter by content ID"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items per page")
):
    results = list(mock_db.values())
    if content_id:
        results = [r for r in results if str(r.content_id) == str(content_id)]
    
    total = len(results)
    paginated_items = results[skip : skip + limit]
    has_more = (skip + limit) < total

    return PaginatedReviewsResponse(
        items=paginated_items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more
    )

@app.get(
    "/api/v1/reviews/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific review by ID",
    responses=STANDARD_ERRORS
)
async def get_review(review_id: UUID4 = Path(..., description="ID of the review")):
    if str(review_id) not in mock_db:
        raise HTTPException(
            status_code=404, 
            detail={"code": "REVIEW_NOT_FOUND", "message": "Review not found"}
        )
    return mock_db[str(review_id)]

@app.patch(
    "/api/v1/reviews/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update a review",
    responses=STANDARD_ERRORS
)
async def update_review(
    review_update: ReviewUpdate,
    review_id: UUID4 = Path(..., description="ID of the review to update")
):
    if str(review_id) not in mock_db:
        raise HTTPException(
            status_code=404, 
            detail={"code": "REVIEW_NOT_FOUND", "message": "Review not found"}
        )
    
    existing_review = mock_db[str(review_id)]
    update_data = review_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(existing_review, key, value)
        
    return existing_review

@app.delete(
    "/api/v1/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a review",
    responses=STANDARD_ERRORS
)
async def delete_review(review_id: UUID4 = Path(..., description="ID of the review to delete")):
    if str(review_id) not in mock_db:
        raise HTTPException(
            status_code=404, 
            detail={"code": "REVIEW_NOT_FOUND", "message": "Review not found"}
        )
    del mock_db[str(review_id)]
    return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)

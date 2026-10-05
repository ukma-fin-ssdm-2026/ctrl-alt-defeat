import os
import uuid
import yaml
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Query, Path
from pydantic import BaseModel, Field, UUID4
from typing import List, Optional
from datetime import datetime
from enum import Enum

# 1. Логіка автогенерації OpenAPI
def save_openapi_spec(app: FastAPI):
    """Save auto-generated OpenAPI spec to file"""
    openapi_schema = app.openapi()
    
    os.makedirs("docs/api", exist_ok=True)
    
    # Save as YAML
    with open("docs/api/openapi-generated.yaml", "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, sort_keys=False, allow_unicode=True)
    
    print("✅ OpenAPI spec auto-generated from code!")
    print("📁 Saved to: docs/api/openapi-generated.yaml")

@asynccontextmanager
async def lifespan(app: FastAPI):
    save_openapi_spec(app)  
    yield

# 2. Ініціалізація додатку
app = FastAPI(
    title="Movie Platform API",
    description="REST API для керування рецензіями.",
    version="1.0.0",
    docs_url="/api-docs",  
    redoc_url="/redoc",    
    lifespan=lifespan
)

# 3. Моделі даних (Pydantic)
class ReviewStatus(str, Enum):
    published = "published"
    hidden = "hidden"
    deleted = "deleted"

class ReviewBase(BaseModel):
    user_id: UUID4 = Field(..., description="Ідентифікатор автора (користувача)")
    content_id: UUID4 = Field(..., description="Ідентифікатор контенту (фільму/серіалу)")
    rating: int = Field(..., ge=1, le=10, description="Оцінка від 1 до 10")
    review_text: str = Field(..., min_length=10, max_length=5000, description="Текст рецензії")
    contains_spoilers: bool = Field(default=False, description="Позначка про спойлери")

class ReviewCreate(ReviewBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "content_id": "987e6543-e21b-34c2-b123-526614174111",
                "rating": 9,
                "review_text": "Чудовий фільм, дуже глибокий сюжет і неймовірна акторська гра!",
                "contains_spoilers": False
            }
        }
    }

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=10, description="Оцінка від 1 до 10")
    review_text: Optional[str] = Field(None, min_length=10, max_length=5000, description="Текст рецензії")
    contains_spoilers: Optional[bool] = Field(None, description="Позначка про спойлери")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "rating": 10,
                "review_text": "Оновлений відгук: після другого перегляду фільм сподобався ще більше!",
                "contains_spoilers": True
            }
        }
    }

class ReviewResponse(ReviewBase):
    review_id: UUID4 = Field(..., description="Унікальний ідентифікатор рецензії")
    status: ReviewStatus = Field(..., description="Статус рецензії")
    created_at: datetime = Field(..., description="Дата публікації")

    model_config = {
        "json_schema_extra": {
            "example": {
                "review_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "content_id": "987e6543-e21b-34c2-b123-526614174111",
                "rating": 9,
                "review_text": "Чудовий фільм, дуже глибокий сюжет і неймовірна акторська гра!",
                "contains_spoilers": False,
                "status": "published",
                "created_at": "2026-10-05T18:00:00Z"
            }
        }
    }

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
    request_id: str

STANDARD_ERRORS = {
    400: {"model": ErrorResponse, "description": "Помилка валідації (Bad Request)"},
    404: {"model": ErrorResponse, "description": "Ресурс не знайдено (Not Found)"},
}

# Заглушка бази даних
mock_db = {}

# 4. Кінцеві точки (Endpoints)
@app.post(
    "/api/v1/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Створити нову рецензію",
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
    mock_db[review_id] = new_review
    return new_review

@app.get(
    "/api/v1/reviews",
    response_model=List[ReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Отримати список рецензій (з пагінацією)",
)
async def get_reviews(
    content_id: Optional[UUID4] = Query(None, description="Фільтр за контентом"),
    skip: int = Query(0, ge=0, description="Зсув для пагінації (offset)"),
    limit: int = Query(10, ge=1, le=100, description="Кількість елементів на сторінку")
):
    results = list(mock_db.values())
    if content_id:
        results = [r for r in results if r.content_id == content_id]
    return results[skip : skip + limit]

@app.get(
    "/api/v1/reviews/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Отримати рецензію за ID",
    responses=STANDARD_ERRORS
)
async def get_review(review_id: UUID4 = Path(..., description="ID рецензії")):
    if review_id not in mock_db:
        raise HTTPException(
            status_code=404, 
            detail={"code": "REVIEW_NOT_FOUND", "message": "Рецензію не знайдено", "request_id": str(uuid.uuid4())}
        )
    return mock_db[review_id]

@app.put(
    "/api/v1/reviews/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Оновити рецензію",
    responses=STANDARD_ERRORS
)
async def update_review(
    review_update: ReviewUpdate,
    review_id: UUID4 = Path(..., description="ID рецензії")
):
    if review_id not in mock_db:
        raise HTTPException(
            status_code=404, 
            detail={"code": "REVIEW_NOT_FOUND", "message": "Рецензію не знайдено", "request_id": str(uuid.uuid4())}
        )
    
    existing_review = mock_db[review_id]
    update_data = review_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(existing_review, key, value)
        
    return existing_review

@app.delete(
    "/api/v1/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити рецензію",
    responses=STANDARD_ERRORS
)
async def delete_review(review_id: UUID4 = Path(..., description="ID рецензії")):
    if review_id not in mock_db:
        raise HTTPException(
            status_code=404, 
            detail={"code": "REVIEW_NOT_FOUND", "message": "Рецензію не знайдено", "request_id": str(uuid.uuid4())}
        )
    del mock_db[review_id]
    return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)


# [AI-assisted]

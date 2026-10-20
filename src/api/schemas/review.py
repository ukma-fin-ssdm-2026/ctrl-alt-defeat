from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, UUID4


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
                "contains_spoilers": False,
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
                "contains_spoilers": True,
            }
        }
    }


class ReviewResponse(ReviewBase):
    review_id: UUID4 = Field(..., description="Unique identifier of the review")
    status: ReviewStatus = Field(..., description="Current status of the review")
    created_at: datetime = Field(..., description="Publication date and time")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "review_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "content_id": "987e6543-e21b-34c2-b123-526614174111",
                "rating": 9,
                "review_text": "Great movie, very deep plot and amazing acting!",
                "contains_spoilers": False,
                "status": "published",
                "created_at": "2026-10-05T18:00:00Z",
            }
        },
    }


class PaginatedReviewsResponse(BaseModel):
    items: List[ReviewResponse] = Field(..., description="List of reviews on the current page")
    total: int = Field(..., description="Total number of matching reviews")
    skip: int = Field(..., description="Offset used for pagination")
    limit: int = Field(..., description="Limit used for pagination")
    has_more: bool = Field(..., description="Flag indicating if there are more items available")

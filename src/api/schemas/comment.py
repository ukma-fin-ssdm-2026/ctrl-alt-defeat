from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, UUID4, field_validator

MAX_COMMENT_LENGTH = 2000
MAX_AUTHOR_NAME_LENGTH = 50
EMPTY_COMMENT_MESSAGE = "Comment text cannot be empty"


class CommentCreate(BaseModel):
    review_id: UUID4 = Field(..., description="Review to comment on")
    user_id: Optional[UUID4] = Field(None, description="Author ID (defaults to authenticated user from JWT)")
    author_name: Optional[str] = Field(
        None, max_length=MAX_AUTHOR_NAME_LENGTH, description="Author nickname (defaults to authenticated user)"
    )
    text: str = Field(..., max_length=MAX_COMMENT_LENGTH, description="Comment text (1-2000 chars)")
    parent_id: Optional[UUID4] = Field(None, description="Comment to reply to; omit for a top-level comment")

    @field_validator("text", "author_name")
    @classmethod
    def strip_and_require(cls, value: Optional[str], info) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError(EMPTY_COMMENT_MESSAGE if info.field_name == "text" else "Author name cannot be empty")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "review_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "author_name": "admin",
                "text": "Totally agree about the soundtrack!",
                "parent_id": None,
            }
        }
    }


class CommentResponse(BaseModel):
    comment_id: UUID4
    review_id: UUID4
    parent_id: Optional[UUID4] = None
    user_id: UUID4
    author_name: str = Field(..., description="Author nickname")
    text: str
    depth: int = Field(..., description="Nesting level: 0 for top-level comments")
    created_at: datetime = Field(..., description="Publication date and time")
    replies: List["CommentResponse"] = Field(default_factory=list, description="Nested replies, oldest first")

    model_config = {"from_attributes": True}


class CommentThreadResponse(BaseModel):
    items: List[CommentResponse] = Field(..., description="Top-level comments with nested replies, oldest first")
    total: int = Field(..., description="Total number of comments under the review, replies included")

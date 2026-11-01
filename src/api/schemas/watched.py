import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, UUID4


class WatchedItemCreate(BaseModel):
    content_id: UUID4 = Field(..., description="ID of the movie/content to mark as watched")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )


class WatchedItemResponse(BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4, description="Watched record ID")
    user_id: UUID4 = Field(..., description="Owner user ID")
    content_id: UUID4 = Field(..., description="Content ID")
    created_at: datetime = Field(..., description="Timestamp when content was marked as watched")
    title: Optional[str] = Field(None, description="Movie Ukrainian title")
    title_en: Optional[str] = Field(None, description="Movie original title")
    category: Optional[str] = Field(None, description="Category (Movie/Series)")
    genre: Optional[str] = Field(None, description="Primary genre")
    year: Optional[int] = Field(None, description="Release year")
    rating: Optional[float] = Field(None, description="Average rating")
    img: Optional[str] = Field(None, description="Poster image URL")

    model_config = ConfigDict(from_attributes=True)


class WatchedListResponse(BaseModel):
    items: List[WatchedItemResponse] = Field(..., description="List of watched content items")
    total: int = Field(..., description="Total count of watched items")

    model_config = ConfigDict(from_attributes=True)


class WatchedStatusResponse(BaseModel):
    is_watched: bool = Field(..., description="Whether this content is in user's watched list")
    content_id: UUID4 = Field(..., description="Content identifier")
    watched_at: Optional[datetime] = Field(None, description="Timestamp when it was marked as watched")

    model_config = ConfigDict(from_attributes=True)


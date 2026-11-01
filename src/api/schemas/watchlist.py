from typing import List

from pydantic import BaseModel, Field, UUID4

from src.api.schemas.movie import ContentResponse


class WatchlistAddRequest(BaseModel):
    content_id: UUID4 = Field(..., description="Movie or series to add to the watchlist")

    model_config = {"json_schema_extra": {"example": {"content_id": "11111111-1111-4111-8111-111111111111"}}}


class WatchlistResponse(BaseModel):
    items: List[ContentResponse] = Field(..., description="Titles in the watchlist, most recently added first")
    total: int = Field(..., description="Number of titles in the watchlist")

from typing import List

from pydantic import BaseModel, Field

from src.api.schemas.movie import ContentResponse


class RecommendationsResponse(BaseModel):
    items: List[ContentResponse] = Field(..., description="Recommended movies and series, best match first")
    personalized: bool = Field(
        ...,
        description="True if based on the user's highly rated titles; False for a new user (best-rated titles)",
    )
    favorite_genres: List[str] = Field(
        default_factory=list, description="User's top genres the recommendations are based on"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "personalized": True,
                "favorite_genres": ["Фантастика", "Драма"],
            }
        }
    }

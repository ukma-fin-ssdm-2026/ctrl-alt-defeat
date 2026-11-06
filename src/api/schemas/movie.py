import uuid
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Numeric identifier for backward compatibility with frontend")
    content_id: uuid.UUID = Field(..., description="Unique UUID identifier of the movie or series")
    title: str = Field(..., description="Ukrainian title of the movie/series")
    title_en: Optional[str] = Field(None, description="Original or English title")
    category: str = Field("Movie", description="Category: 'Movie' or 'Series'")
    genre: str = Field(..., description="Primary genre")
    genres: Optional[List[str]] = Field(default_factory=list, description="List of genre tags")
    year: int = Field(..., description="Release year")
    runtime: Optional[int] = Field(None, description="Runtime in minutes (for series: average episode length)")
    rating: float = Field(0.0, description="Average user rating (0.0 - 10.0)")
    rotten_rating: Optional[str] = Field(None, description="Rotten Tomatoes / Critic score percentage")
    img: Optional[str] = Field(None, description="Poster image URL")
    description: Optional[str] = Field(None, description="Ukrainian synopsis")
    description_en: Optional[str] = Field(None, description="English synopsis")
    tmdb_id: Optional[int] = Field(None, description="External TMDB identifier")


class ContentSortField(str, Enum):
    """Sorting criteria for the catalog (FR-010)."""

    rating = "rating"
    release_date = "release_date"
    runtime = "runtime"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class PaginatedContentResponse(BaseModel):
    items: List[ContentResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


# Aliases for backward compatibility
MovieResponse = ContentResponse
PaginatedMoviesResponse = PaginatedContentResponse


class GenreResponse(BaseModel):
    """A genre of the catalog with the number of titles (FR-012, issue #61)."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"genre_id": 7, "name": "Драма", "name_en": "Drama", "titles_count": 18}}
    )

    genre_id: int = Field(..., description="Genre identifier")
    name: str = Field(..., description="Ukrainian name, used in the catalog and in the genre filter")
    name_en: Optional[str] = Field(None, description="English name")
    titles_count: int = Field(..., ge=0, description="Number of movies and series with this genre")

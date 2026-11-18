import uuid
from enum import Enum
from datetime import datetime
from typing import List, Literal, Optional
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
    img: Optional[str] = Field(None, description="Poster image URL (Ukrainian poster if TMDB has one)")
    img_en: Optional[str] = Field(
        None, description="Poster for the English interface (English or without text); null: use `img`"
    )
    description: Optional[str] = Field(None, description="Ukrainian synopsis")
    description_en: Optional[str] = Field(None, description="English synopsis")
    tmdb_id: Optional[int] = Field(None, description="External TMDB identifier")


class CastMember(BaseModel):
    name: str = Field(..., description="Actor or actress")
    name_en: Optional[str] = Field(None, description="The name in English (empty for data imported earlier)")
    character: Optional[str] = Field(None, description="Role in this title")
    photo: Optional[str] = Field(None, description="Photo URL (TMDB, 185 px wide)")


class CrewInfo(BaseModel):
    directors: List[str] = Field(default_factory=list, description="Directors (movies)")
    writers: List[str] = Field(default_factory=list, description="Screenplay and story (movies)")
    creators: List[str] = Field(default_factory=list, description="Creators (series)")
    directors_en: List[str] = Field(default_factory=list, description="Directors in English")
    writers_en: List[str] = Field(default_factory=list, description="Writers in English")
    creators_en: List[str] = Field(default_factory=list, description="Creators in English")


class NextEpisode(BaseModel):
    air_date: Optional[str] = Field(None, description="Air date, YYYY-MM-DD")
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    name: Optional[str] = None


class SeasonInfo(BaseModel):
    season_number: Optional[int] = Field(None, description="0 is specials")
    name: Optional[str] = None
    episode_count: Optional[int] = None
    air_date: Optional[str] = Field(None, description="First air date, YYYY-MM-DD")
    poster: Optional[str] = Field(None, description="Poster URL (TMDB, 185 px wide)")


class SeriesInfo(BaseModel):
    status: Optional[str] = Field(None, description="TMDB status: Returning Series, Ended, Canceled, In Production…")
    number_of_seasons: Optional[int] = None
    number_of_episodes: Optional[int] = None
    last_air_date: Optional[str] = None
    next_episode: Optional[NextEpisode] = None
    seasons: List[SeasonInfo] = Field(default_factory=list)


class CollectionInfo(BaseModel):
    id: int = Field(..., description="TMDB collection id")
    name: str = Field(..., description="Name of the film series")
    name_en: Optional[str] = Field(None, description="Name of the film series in English")


class ContentDetailsResponse(ContentResponse):
    """One title with the details of its page (US-013): trailers, cast and crew, series details, film series."""

    trailer_uk: Optional[str] = Field(None, description="YouTube video id of the Ukrainian trailer")
    trailer_en: Optional[str] = Field(None, description="YouTube video id of the English trailer")
    cast: List[CastMember] = Field(default_factory=list, description="Main cast in billing order (up to 10)")
    crew: CrewInfo = Field(default_factory=CrewInfo, description="Directors and writers or creators")
    series: Optional[SeriesInfo] = Field(None, description="Seasons and episodes (series only)")
    collection: Optional[CollectionInfo] = Field(None, description="Film series the title belongs to")


class RelatedContentResponse(BaseModel):
    """Titles of the catalog related to one title (US-013)."""

    collection: Optional[CollectionInfo] = Field(None, description="Film series of the title")
    collection_items: List[ContentResponse] = Field(
        default_factory=list, description="Other parts of the film series present in the catalog, by year"
    )
    similar: List[ContentResponse] = Field(
        default_factory=list, description="Similar titles from TMDB recommendations present in the catalog"
    )


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


class CatalogSyncStatus(BaseModel):
    """State of the catalog update from TMDB started by an administrator (FR-012)."""

    configured: bool = Field(..., description="TMDB_API_KEY is set on the server")
    state: Literal["idle", "running", "done", "failed"] = Field(..., description="State of the last update")
    started_at: Optional[datetime] = Field(None, description="When the last update started")
    finished_at: Optional[datetime] = Field(None, description="When the last update finished")
    added: int = Field(0, ge=0, description="New titles")
    updated: int = Field(0, ge=0, description="Updated titles")
    skipped: int = Field(0, ge=0, description="Titles skipped (TMDB id already used by another title)")
    placeholders_removed: int = Field(0, ge=0, description="Built-in titles merged into real ones or removed")
    placeholders_kept: int = Field(0, ge=0, description="Built-in titles kept because users reviewed or saved them")
    error: Optional[str] = Field(None, description="Why the last update failed")

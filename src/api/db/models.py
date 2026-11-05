import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    select,
)
from sqlalchemy.orm import column_property, relationship
from sqlalchemy.sql import func

from src.api.db.database import Base


class Content(Base):
    __tablename__ = "content"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_id = Column(Uuid(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    title_en = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False, default="Movie")
    genre = Column(String(100), nullable=False)
    genres = Column(JSON, nullable=True)
    year = Column(Integer, nullable=False, index=True)
    # Runtime in minutes (for series: average episode length). Nullable: not always known.
    runtime = Column(Integer, nullable=True)
    rating = Column(Float, nullable=False, default=0.0)
    rotten_rating = Column(String(10), nullable=True)
    img = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    tmdb_id = Column(Integer, unique=True, nullable=True)


# Alias for backward compatibility
Movie = Content


class Genre(Base):
    """Genre dictionary (FR-012). Names are stored in Ukrainian; tmdb_id links TMDB `genre_ids`."""

    __tablename__ = "genres"
    __table_args__ = {"extend_existing": True}

    genre_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    name_en = Column(String(100), nullable=True)
    tmdb_id = Column(Integer, unique=True, nullable=True)


class ContentGenre(Base):
    """
    Many-to-many link between Content and Genre (FR-002, FR-012).
    position keeps the order of genres of a title: 0 is the primary genre.
    """

    __tablename__ = "content_genres"
    __table_args__ = {"extend_existing": True}

    content_id = Column(Uuid(as_uuid=True), ForeignKey("content.content_id", ondelete="CASCADE"), primary_key=True)
    genre_id = Column(Integer, ForeignKey("genres.genre_id", ondelete="CASCADE"), primary_key=True)
    position = Column(Integer, nullable=False, default=0)


class ReviewVote(Base):
    """
    "Support" (+1) or "Don't support" (-1) of a review by a user. One vote per user and review;
    the author cannot vote for their own review.
    """

    __tablename__ = "review_votes"
    __table_args__ = (
        CheckConstraint("value IN (1, -1)", name="ck_review_votes_value"),
        {"extend_existing": True},
    )

    review_id = Column(Uuid(as_uuid=True), ForeignKey("reviews.review_id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    value = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _vote_count(review_id_column, value):
    return (
        select(func.count())
        .where(ReviewVote.review_id == review_id_column, ReviewVote.value == value)
        .correlate_except(ReviewVote)
        .scalar_subquery()
    )


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        # 1) One review per user per movie/series
        UniqueConstraint("user_id", "content_id", name="uq_reviews_user_content"),
        # 2) Text is optional, but if present it must be 10-5000 chars
        CheckConstraint(
            "review_text IS NULL OR length(review_text) BETWEEN 10 AND 5000",
            name="ck_reviews_text_length",
        ),
        {"extend_existing": True},
    )

    review_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    content_id = Column(Uuid(as_uuid=True), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=True)
    contains_spoilers = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="published")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Vote counters, loaded together with the review (one correlated subquery each)
    likes = column_property(_vote_count(review_id, 1))
    dislikes = column_property(_vote_count(review_id, -1))

    # Read-only links used to show who wrote the review and about which title (no DB schema change)
    author = relationship("User", primaryjoin="foreign(Review.user_id) == User.user_id", viewonly=True, lazy="selectin")
    content = relationship(
        "Content", primaryjoin="foreign(Review.content_id) == Content.content_id", viewonly=True, lazy="selectin"
    )

    @property
    def author_nickname(self):
        return self.author.nickname if self.author is not None else None

    @property
    def content_title(self):
        return self.content.title if self.content is not None else None


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = {"extend_existing": True}

    rating_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    content_id = Column(Uuid(as_uuid=True), nullable=False)
    score = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Comment(Base):
    """Threaded comment under a review (FR-011). Replies reference their parent comment."""

    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint("length(text) BETWEEN 1 AND 2000", name="ck_comments_text_length"),
        {"extend_existing": True},
    )

    comment_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(
        Uuid(as_uuid=True), ForeignKey("reviews.review_id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id = Column(
        Uuid(as_uuid=True), ForeignKey("comments.comment_id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    # Display name snapshot. TODO(FR-001): take the nickname from the authenticated user.
    author_name = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    depth = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    user_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(100), unique=True, index=True, nullable=False)
    role = Column(String(20), nullable=False, default="user")  # 'user' | 'admin'
    email_verified = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="pending")  # 'pending' | 'active' | 'banned'
    verification_token = Column(String(255), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class WatchlistItem(Base):
    """A title in the user's "Watch later" list (FR-005). One row per user and title."""

    __tablename__ = "watchlist"
    __table_args__ = {"extend_existing": True}

    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    content_id = Column(Uuid(as_uuid=True), ForeignKey("content.content_id", ondelete="CASCADE"), primary_key=True)
    added_at = Column(DateTime(timezone=True), nullable=False)


class WatchedItem(Base):
    """
    User's watched list item (FR-006, US-004).
    Stores content that the user has marked as watched.
    """

    __tablename__ = "watched_items"
    __table_args__ = (
        UniqueConstraint("user_id", "content_id", name="uq_watched_user_content"),
        {"extend_existing": True},
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    content_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Ban(Base):
    """
    Account ban set by an administrator (FR-009, US-006).
    A ban is in force while is_active is true and it is permanent or ends_at is still in the future;
    a temporary ban therefore expires on its own. Rows are kept as the user's ban history.
    """

    __tablename__ = "bans"
    __table_args__ = (
        CheckConstraint("ban_type IN ('temporary', 'permanent')", name="ck_bans_type"),
        {"extend_existing": True},
    )

    ban_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(Uuid(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    ban_type = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

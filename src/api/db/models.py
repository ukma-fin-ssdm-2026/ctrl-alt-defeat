import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text, Uuid
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
    rating = Column(Float, nullable=False, default=0.0)
    rotten_rating = Column(String(10), nullable=True)
    img = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    tmdb_id = Column(Integer, unique=True, nullable=True)


# Alias for backward compatibility
Movie = Content


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = {"extend_existing": True}

    review_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    content_id = Column(Uuid(as_uuid=True), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=False)
    contains_spoilers = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="published")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


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

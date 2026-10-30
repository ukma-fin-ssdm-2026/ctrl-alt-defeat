import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from src.api.db.database import Base


class Review(Base):
    __tablename__ = "reviews"

    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    content_id = Column(UUID(as_uuid=True), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=False)
    contains_spoilers = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="published")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

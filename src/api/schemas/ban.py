import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_TEMPORARY_BAN_DAYS = 365
MAX_BAN_REASON_LENGTH = 500


class BanType(str, Enum):
    temporary = "temporary"
    permanent = "permanent"


class BanInfo(BaseModel):
    """The ban currently in force (FR-009): type, period and the message shown to the user."""

    model_config = ConfigDict(from_attributes=True)

    ban_type: BanType = Field(..., description="'temporary' or 'permanent'")
    reason: Optional[str] = Field(None, description="Message from the administrator")
    starts_at: Optional[datetime] = Field(None, description="When the ban started")
    ends_at: Optional[datetime] = Field(None, description="When a temporary ban ends; null for a permanent ban")


class BanCreate(BaseModel):
    user_id: uuid.UUID = Field(..., description="User to ban")
    ban_type: BanType = Field(..., description="'temporary' or 'permanent'")
    duration_days: Optional[int] = Field(
        None,
        ge=1,
        le=MAX_TEMPORARY_BAN_DAYS,
        description=f"Length of a temporary ban in days (1-{MAX_TEMPORARY_BAN_DAYS}); not used for a permanent ban",
    )
    reason: Optional[str] = Field(
        None, max_length=MAX_BAN_REASON_LENGTH, description="Message shown to the banned user"
    )

    @model_validator(mode="after")
    def duration_matches_type(self):
        if self.ban_type == BanType.temporary and self.duration_days is None:
            raise ValueError("duration_days is required for a temporary ban")
        if self.ban_type == BanType.permanent and self.duration_days is not None:
            raise ValueError("duration_days must not be set for a permanent ban")
        if self.reason is not None:
            self.reason = self.reason.strip() or None
        return self


class AdminUser(BaseModel):
    user_id: uuid.UUID
    email: str
    nickname: str
    role: str
    status: str
    created_at: datetime
    ban: Optional[BanInfo] = Field(None, description="The ban in force, if any")


class AdminUserList(BaseModel):
    items: List[AdminUser]
    total: int

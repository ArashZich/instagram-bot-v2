from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

# Enums


class InteractionType(str, Enum):
    COMMENT = "comment"
    LIKE = "like"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    STORY_REACTION = "story_reaction"
    DIRECT_MESSAGE = "direct_message"


class TimeRange(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SIX_MONTHS = "six_months"
    YEARLY = "yearly"

# Base models


class UserBase(BaseModel):
    user_id: str
    username: str

# Interaction models


class InteractionCreate(BaseModel):
    user_id: str
    username: str
    interaction_type: InteractionType
    content: Optional[str] = None
    media_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class InteractionResponse(InteractionCreate):
    id: str
    timestamp: datetime
    status: str

    class Config:
        orm_mode = True

# User profile models


class UserProfileResponse(UserBase):
    full_name: Optional[str] = None
    is_following: bool = False
    is_follower: bool = False
    interaction_count: int = 0
    last_interaction: Optional[datetime] = None
    first_seen: Optional[datetime] = None

    class Config:
        orm_mode = True

# Statistics models


class InteractionCount(BaseModel):
    interaction_type: str
    count: int


class TimeSeriesPoint(BaseModel):
    date: str
    count: int


class InteractionStats(BaseModel):
    total_interactions: int
    interaction_types: List[InteractionCount]
    time_series: List[TimeSeriesPoint]


class UserStats(BaseModel):
    total_users: int
    followers_count: int
    following_count: int
    new_users_count: int
    most_interacted: List[UserProfileResponse]


class BotStats(BaseModel):
    total_runtime: str
    session_count: int
    last_session: Optional[datetime] = None
    is_active: bool


class StatsResponse(BaseModel):
    interactions: InteractionStats
    users: UserStats
    bot: BotStats

# Query parameters


class StatsQueryParams(BaseModel):
    time_range: TimeRange = TimeRange.WEEKLY
    limit: int = 10


class UserQueryParams(BaseModel):
    is_follower: Optional[bool] = None
    is_following: Optional[bool] = None
    limit: int = 20
    skip: int = 0

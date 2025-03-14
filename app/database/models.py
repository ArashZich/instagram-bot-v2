from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class InteractionType(str, Enum):
    COMMENT = "comment"
    LIKE = "like"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    STORY_REACTION = "story_reaction"
    DIRECT_MESSAGE = "direct_message"


class BotSession:
    """Model for tracking bot login sessions"""

    def __init__(
        self,
        session_id: str,
        started_at: datetime,
        user_agent: str,
        session_data: Dict = None,
        ended_at: Optional[datetime] = None,
        is_active: bool = True
    ):
        self.session_id = session_id
        self.started_at = started_at
        self.ended_at = ended_at
        self.user_agent = user_agent
        self.session_data = session_data or {}
        self.is_active = is_active

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "user_agent": self.user_agent,
            "session_data": self.session_data,
            "is_active": self.is_active,
        }


class UserInteraction:
    """Model for user interactions"""

    def __init__(
        self,
        user_id: str,
        username: str,
        interaction_type: InteractionType,
        timestamp: datetime,
        content: str = None,
        media_id: str = None,
        status: str = "success",
        error: str = None,
        metadata: Dict = None
    ):
        self.user_id = user_id
        self.username = username
        self.interaction_type = interaction_type
        self.timestamp = timestamp
        self.content = content
        self.media_id = media_id
        self.status = status
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "interaction_type": self.interaction_type,
            "timestamp": self.timestamp,
            "content": self.content,
            "media_id": self.media_id,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
        }


class UserProfile:
    """Model for storing user profiles we've interacted with"""

    def __init__(
        self,
        user_id: str,
        username: str,
        full_name: str = None,
        is_following: bool = False,
        is_follower: bool = False,
        interaction_count: int = 0,
        last_interaction: datetime = None,
        first_seen: datetime = None,
        metadata: Dict = None
    ):
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.is_following = is_following
        self.is_follower = is_follower
        self.interaction_count = interaction_count
        self.last_interaction = last_interaction
        self.first_seen = first_seen or datetime.now()
        self.metadata = metadata or {}

    @staticmethod
    def _sanitize_dict_values(d):
        """Convert complex objects to simple types for MongoDB"""
        result = {}
        for k, v in d.items():
            if isinstance(v, dict):
                v = UserProfile._sanitize_dict_values(v)
            result[k] = str(v) if hasattr(v, '__dict__') else v
        return result

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "is_following": self.is_following,
            "is_follower": self.is_follower,
            "interaction_count": self.interaction_count,
            "last_interaction": self.last_interaction,
            "first_seen": self.first_seen,
            "metadata": self._sanitize_dict_values(self.metadata) if self.metadata else {},
        }


# اطمینان از یکسان بودن نام کالکشن‌ها
COLLECTIONS = {
    "sessions": "bot_sessions",
    "interactions": "user_interactions",
    "users": "user_profiles",
    "statistics": "bot_statistics",
}


def get_collection_name(collection_key: str) -> str:
    """Get the collection name from the key"""
    return COLLECTIONS.get(collection_key, collection_key)

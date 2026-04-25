"Пакет моделей БД.

Импорт всех моделей здесь нужен, чтобы:
- relationship по строковым именам корректно резолвились;
- Alembic / Base.metadata видели все таблицы.
"

from backend.db.base import Base, TimestampMixin
from backend.db.database import engine, async_session_maker, get_db
from backend.db.enums import (
    UserRole,
    OrgType,
    PostType,
    PostStatus,
    ModuleType,
    Platform,
    EventSource,
    SystemStateEnum,
)
from backend.db.organizations import Organization
from backend.db.users import User
from backend.db.posts import Post
from backend.db.tags import Tag
from backend.db.posts_tags import post_tags
from backend.db.events import Event
from backend.db.analytics_logs import AnalyticsLog
from backend.db.system_states import SystemState

__all__ = [
    'Base',
    'TimestampMixin',
    'engine',
    'async_session_maker',
    'get_db',
    'UserRole',
    'OrgType',
    'PostType',
    'PostStatus',
    'ModuleType',
    'Platform',
    'EventSource',
    'SystemStateEnum',
    'Organization',
    'User',
    'Post',
    'Tag',
    'post_tags',
    'Event',
    'AnalyticsLog',
    'SystemState',
]

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, Integer, DateTime, ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class AnalyticsLog(Base):
    __tablename__ = "analytics_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id"))

    collected_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    likes: Mapped[int]
    comments: Mapped[int]
    views: Mapped[int]

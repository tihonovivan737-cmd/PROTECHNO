import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, Integer, DateTime, ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    event_date: Mapped[datetime]
    location: Mapped[str] = mapped_column(String(255))

    source: Mapped[EventSource] = mapped_column(Enum(EventSource))
    external_id: Mapped[str] = mapped_column(String(255), nullable=True)

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    organization = relationship("Organization", back_populates="events")

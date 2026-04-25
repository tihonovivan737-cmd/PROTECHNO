import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, Integer, DateTime, ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[OrgType] = mapped_column(Enum(OrgType))
    description: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    posts = relationship("Post", back_populates="organization")
    events = relationship("Event", back_populates="organization")
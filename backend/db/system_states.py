import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, Integer, DateTime, ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class SystemState(Base):
    __tablename__ = "system_state"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), unique=True)

    current_state: Mapped[SystemStateEnum] = mapped_column(Enum(SystemStateEnum))

    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

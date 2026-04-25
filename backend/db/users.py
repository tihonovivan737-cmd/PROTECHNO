import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, Integer, DateTime, ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    role: Mapped[UserRole] = mapped_column(Enum(UserRole))

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    posts = relationship("Post", back_populates="author")
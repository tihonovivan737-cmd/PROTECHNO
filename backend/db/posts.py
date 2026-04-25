import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, Integer, DateTime, ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(255))

    text_draft: Mapped[str] = mapped_column(Text, nullable=True)
    text_generated: Mapped[str] = mapped_column(Text, nullable=True)
    text_final: Mapped[str] = mapped_column(Text, nullable=True)

    media_urls: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)

    post_type: Mapped[PostType] = mapped_column(Enum(PostType))
    status: Mapped[PostStatus] = mapped_column(Enum(PostStatus))

    module_type: Mapped[ModuleType] = mapped_column(Enum(ModuleType))
    platform: Mapped[Platform] = mapped_column(Enum(Platform))

    scheduled_at: Mapped[datetime] = mapped_column(nullable=True)
    published_at: Mapped[datetime] = mapped_column(nullable=True)

    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)

    external_id: Mapped[str] = mapped_column(String(255), nullable=True)

    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    author = relationship("User", back_populates="posts")
    organization = relationship("Organization", back_populates="posts")
    tags = relationship("Tag", secondary="post_tags", back_populates="posts")

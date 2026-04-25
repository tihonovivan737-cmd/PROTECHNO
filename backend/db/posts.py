import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin
from backend.db.enums import PostType, PostStatus, ModuleType, Platform

if TYPE_CHECKING:
    from backend.db.users import User
    from backend.db.organizations import Organization
    from backend.db.tags import Tag


class Post(Base, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    text_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_generated: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_final: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    media_urls: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)

    post_type: Mapped[PostType] = mapped_column(Enum(PostType), nullable=False)
    status: Mapped[PostStatus] = mapped_column(Enum(PostStatus), nullable=False)

    module_type: Mapped[ModuleType] = mapped_column(Enum(ModuleType), nullable=False)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)

    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )

    author: Mapped[Optional["User"]] = relationship("User", back_populates="posts")
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="posts"
    )
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary="post_tags", back_populates="posts"
    )

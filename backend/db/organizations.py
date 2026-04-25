import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin
from backend.db.enums import OrgType

if TYPE_CHECKING:
    from backend.db.users import User
    from backend.db.posts import Post
    from backend.db.events import Event


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[OrgType] = mapped_column(Enum(OrgType), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="organization")
    events: Mapped[list["Event"]] = relationship("Event", back_populates="organization")
import enum
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base, TimestampMixin


class NotificationType(str, enum.Enum):
    NEW_MESSAGE = "new_message"
    GROUP_INVITE = "group_invite"
    ADDED_TO_GROUP = "added_to_group"
    REPLY = "reply"
    REACTION = "reaction"
    MODERATION_WARNING = "moderation_warning"
    ROLE_CHANGED = "role_changed"
    ACCOUNT_RESTRICTED = "account_restricted"
    SYSTEM = "system"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
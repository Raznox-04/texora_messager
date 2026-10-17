from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.conversation import Conversation
from app.models.message import Message, MessageRead, MessageReaction, MessageType
from app.schemas.message import MessageCreate


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_conversation_access(self, conversation_id: int, user_id: int) -> Conversation:
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.members))
            .where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise NotFoundError("گفت‌وگو یافت نشد")

        member_ids = [m.user_id for m in conv.members]
        if user_id not in member_ids:
            raise ForbiddenError("شما عضو این گفت‌وگو نیستید")
        return conv

    async def create_message(self, sender_id: int, data: MessageCreate) -> Message:
        await self.check_conversation_access(data.conversation_id, sender_id)

        if not data.content and data.message_type == MessageType.TEXT.value:
            raise ForbiddenError("محتوای پیام خالی است")

        msg = Message(
            conversation_id=data.conversation_id,
            sender_id=sender_id,
            content=data.content,
            message_type=MessageType(data.message_type),
            reply_to_id=data.reply_to_id,
            moderation_status="pending",
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_messages(
        self, conversation_id: int, user_id: int, limit: int = 50, before_id: Optional[int] = None
    ) -> List[Message]:
        await self.check_conversation_access(conversation_id, user_id)
        q = (
            select(Message)
            .options(
                selectinload(Message.attachments),
                selectinload(Message.reactions),
            )
            .where(Message.conversation_id == conversation_id, Message.is_deleted == False)  # noqa: E712
            .order_by(desc(Message.id))
            .limit(limit)
        )
        if before_id:
            q = q.where(Message.id < before_id)
        result = await self.db.execute(q)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def edit_message(self, message_id: int, user_id: int, content: str) -> Message:
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        msg = result.scalar_one_or_none()
        if not msg:
            raise NotFoundError("پیام یافت نشد")
        if msg.sender_id != user_id:
            raise ForbiddenError("فقط فرستنده می‌تواند پیام را ویرایش کند")
        if msg.is_deleted:
            raise ForbiddenError("پیام حذف شده قابل ویرایش نیست")
        msg.content = content
        msg.is_edited = True
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def delete_message(self, message_id: int, user_id: int, is_admin: bool = False) -> None:
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        msg = result.scalar_one_or_none()
        if not msg:
            raise NotFoundError("پیام یافت نشد")
        if msg.sender_id != user_id and not is_admin:
            raise ForbiddenError("اجازه حذف این پیام را ندارید")
        msg.is_deleted = True
        msg.content = None
        await self.db.commit()

    async def mark_read(self, message_id: int, user_id: int) -> None:
        result = await self.db.execute(
            select(MessageRead).where(
                MessageRead.message_id == message_id, MessageRead.user_id == user_id
            )
        )
        existing = result.scalar_one_or_none()
        if not existing:
            self.db.add(MessageRead(
                message_id=message_id, user_id=user_id, read_at=datetime.now(timezone.utc)
            ))
            await self.db.commit()

    async def add_reaction(self, message_id: int, user_id: int, emoji: str) -> MessageReaction:
        result = await self.db.execute(
            select(MessageReaction).where(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == user_id,
                MessageReaction.emoji == emoji,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        reaction = MessageReaction(message_id=message_id, user_id=user_id, emoji=emoji)
        self.db.add(reaction)
        await self.db.commit()
        await self.db.refresh(reaction)
        return reaction
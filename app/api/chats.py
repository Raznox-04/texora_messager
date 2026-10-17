from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError, ForbiddenError
from app.database.session import get_db
from app.models.conversation import Conversation, ConversationMember, ConversationType
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationOut
from app.websocket.manager import manager

router = APIRouter(prefix="/api/chats", tags=["chats"])


async def _build_conversation_out(
    conv: Conversation, current_user_id: int, db: AsyncSession
) -> ConversationOut:
    """ساخت خروجی چت خصوصی به همراه نام کاربر مقابل و آخرین پیام"""
    other_user: User | None = None
    for member in conv.members:
        if member.user_id != current_user_id and member.user:
            other_user = member.user
            break

    if other_user:
        title = other_user.display_name or other_user.username
        other_user_id = other_user.id
        other_username = other_user.username
        is_online = manager.is_online(other_user.id)
    else:
        title = conv.title or f"گفت‌وگوی خصوصی #{conv.id}"
        other_user_id = None
        other_username = None
        is_online = False

    last_msg_res = await db.execute(
        select(Message.content)
        .where(Message.conversation_id == conv.id, Message.is_deleted == False)  # noqa: E712
        .order_by(desc(Message.id))
        .limit(1)
    )
    last_message = last_msg_res.scalar_one_or_none()

    return ConversationOut(
        id=conv.id,
        type=conv.type,
        title=title,
        group_id=conv.group_id,
        other_user_id=other_user_id,
        other_username=other_username,
        is_online=is_online,
        last_message=last_message,
        created_at=conv.created_at,
    )


@router.get("", response_model=List[ConversationOut])
async def list_private_chats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    my_conv_ids = select(ConversationMember.conversation_id).where(
        ConversationMember.user_id == user.id
    )

    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.members).selectinload(ConversationMember.user))
        .where(
            Conversation.id.in_(my_conv_ids),
            Conversation.type == ConversationType.PRIVATE,
        )
        .order_by(desc(Conversation.updated_at))
    )
    conversations = result.scalars().all()

    return [await _build_conversation_out(c, user.id, db) for c in conversations]


@router.post("", response_model=ConversationOut)
async def start_private_chat(
    data: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.participant_id == user.id:
        raise ForbiddenError("امکان ایجاد گفت‌وگو با خودتان وجود ندارد")

    target_res = await db.execute(select(User).where(User.id == data.participant_id))
    target_user = target_res.scalar_one_or_none()
    if not target_user:
        raise NotFoundError("کاربر مورد نظر یافت نشد")

    my_convs = select(ConversationMember.conversation_id).where(
        ConversationMember.user_id == user.id
    )
    their_convs = select(ConversationMember.conversation_id).where(
        ConversationMember.user_id == data.participant_id
    )

    existing_res = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.members).selectinload(ConversationMember.user))
        .where(
            Conversation.type == ConversationType.PRIVATE,
            Conversation.id.in_(my_convs),
            Conversation.id.in_(their_convs),
        )
    )
    existing_conv = existing_res.scalars().first()
    if existing_conv:
        return await _build_conversation_out(existing_conv, user.id, db)

    conv = Conversation(
        type=ConversationType.PRIVATE,
        title=target_user.display_name or target_user.username,
    )
    db.add(conv)
    await db.flush()

    db.add(ConversationMember(conversation_id=conv.id, user_id=user.id))
    db.add(ConversationMember(conversation_id=conv.id, user_id=data.participant_id))
    await db.commit()

    reloaded = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.members).selectinload(ConversationMember.user))
        .where(Conversation.id == conv.id)
    )
    conv_full = reloaded.scalar_one()
    return await _build_conversation_out(conv_full, user.id, db)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.message import MessageCreate, MessageOut, MessageUpdate, ReactionCreate, ReactionOut
from app.services.message_service import MessageService

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("", response_model=MessageOut, status_code=201)
async def send_message(
    data: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    msg = await service.create_message(user.id, data)
    return MessageOut.model_validate(msg)


@router.get("/conversation/{conversation_id}", response_model=list[MessageOut])
async def get_messages(
    conversation_id: int,
    limit: int = 50,
    before_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    msgs = await service.get_messages(conversation_id, user.id, limit, before_id)
    return [MessageOut.model_validate(m) for m in msgs]


@router.patch("/{message_id}", response_model=MessageOut)
async def edit_message(
    message_id: int,
    data: MessageUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    msg = await service.edit_message(message_id, user.id, data.content)
    return MessageOut.model_validate(msg)


@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    is_admin = user.role.value in ("moderator", "super_admin")
    await service.delete_message(message_id, user.id, is_admin)
    return {"message": "پیام حذف شد"}


@router.post("/{message_id}/reactions", response_model=ReactionOut)
async def add_reaction(
    message_id: int,
    data: ReactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    r = await service.add_reaction(message_id, user.id, data.emoji)
    return ReactionOut.model_validate(r)
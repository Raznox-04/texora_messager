import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from app.core.security import decode_token
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.conversation import ConversationMember
from app.websocket.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


async def _authenticate_ws(token: str) -> User | None:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    user_id = int(payload["sub"])
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user = await _authenticate_ws(token)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(user.id, user.role.value, websocket)
    await _notify_online_status(user.id, True)

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("type")

            if event == "ping":
                await websocket.send_json({"type": "pong", "ts": datetime.now(timezone.utc).isoformat()})
            elif event == "typing":
                await _handle_typing(user, data.get("conversation_id"))
            elif event == "message:send":
                await _handle_send_message(user, data)
            elif event == "message:read":
                await _handle_read(user, data)
            else:
                await websocket.send_json({"type": "error", "message": "رویداد نامعتبر"})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        await manager.disconnect(user.id, websocket)
        if not manager.is_online(user.id):
            await _notify_online_status(user.id, False)


async def _handle_typing(user: User, conversation_id: int | None):
    if not conversation_id:
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id
            )
        )
        members = [r for r in result.scalars().all()]
        if user.id not in members:
            return
        await manager.broadcast_to_conversation(
            members,
            {"type": "typing", "conversation_id": conversation_id, "user_id": user.id},
            exclude={user.id},
        )


async def _handle_send_message(user: User, data: dict):
    from app.services.message_service import MessageService
    from app.schemas.message import MessageCreate
    conversation_id = data.get("conversation_id")
    content = data.get("content", "")
    if not conversation_id or not content:
        return
    async with AsyncSessionLocal() as db:
        service = MessageService(db)
        try:
            msg = await service.create_message(
                user.id,
                MessageCreate(conversation_id=conversation_id, content=content),
            )
        except Exception:
            await manager.send_personal(user.id, {"type": "error", "message": "ارسال پیام ناموفق"})
            return

        result = await db.execute(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id
            )
        )
        members = [r for r in result.scalars().all()]

    payload = {
        "type": "message:new",
        "message": {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "message_type": msg.message_type.value,
            "reply_to_id": msg.reply_to_id,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        },
    }
    await manager.broadcast_to_conversation(members, payload)

    from app.modules.moderation.queue import moderation_queue
    await moderation_queue.enqueue(msg.id, user.id, content or "")


async def _handle_read(user: User, data: dict):
    message_id = data.get("message_id")
    if not message_id:
        return
    from app.services.message_service import MessageService
    async with AsyncSessionLocal() as db:
        service = MessageService(db)
        try:
            await service.mark_read(message_id, user.id)
        except Exception:
            return


async def _notify_online_status(user_id: int, is_online: bool):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConversationMember.conversation_id).where(ConversationMember.user_id == user_id)
        )
        conv_ids = [r for r in result.scalars().all()]
        if not conv_ids:
            return
        result2 = await db.execute(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id.in_(conv_ids)
            ).distinct()
        )
        contacts = [r for r in result2.scalars().all() if r != user_id]
    for cid in contacts:
        await manager.send_personal(cid, {
            "type": "presence",
            "user_id": user_id,
            "is_online": is_online,
        })
import uuid
import aiofiles
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.database.session import get_db
from app.models.user import User
from app.models.message import Message, MessageAttachment, MessageType
from app.services.message_service import MessageService
from app.schemas.message import MessageOut

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_ROOT = Path(settings.UPLOAD_DIR).resolve()


def _safe_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".txt", ".zip"}
    if ext not in allowed:
        raise ForbiddenError("پسوند فایل مجاز نیست")
    return ext


def _detect_is_image(mime: str) -> bool:
    return mime in settings.allowed_image_types_list


@router.post("/message", response_model=MessageOut)
async def upload_to_message(
    conversation_id: int = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    await service.check_conversation_access(conversation_id, user.id)

    ext = _safe_extension(file.filename or "file.bin")
    mime = file.content_type or "application/octet-stream"

    is_image = _detect_is_image(mime)
    max_bytes = (settings.MAX_IMAGE_SIZE_MB if is_image else settings.MAX_FILE_SIZE_MB) * 1024 * 1024

    content = await file.read()
    if len(content) > max_bytes:
        raise ForbiddenError("حجم فایل بیش از حد مجاز است")

    if is_image and mime not in settings.allowed_image_types_list:
        raise ForbiddenError("نوع تصویر مجاز نیست")
    if not is_image and mime not in settings.allowed_file_types_list:
        raise ForbiddenError("نوع فایل مجاز نیست")

    subdir = "images" if is_image else "files"
    target_dir = UPLOAD_ROOT / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    target_path = target_dir / safe_name

    async with aiofiles.open(target_path, "wb") as f:
        await f.write(content)

    msg = Message(
        conversation_id=conversation_id,
        sender_id=user.id,
        content=file.filename,
        message_type=MessageType.IMAGE if is_image else MessageType.FILE,
        moderation_status="pending",
    )
    db.add(msg)
    await db.flush()

    attachment = MessageAttachment(
        message_id=msg.id,
        file_name=file.filename or safe_name,
        file_path=f"/uploads/{subdir}/{safe_name}",
        file_size=len(content),
        mime_type=mime,
        is_image=is_image,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(msg)
    return MessageOut.model_validate(msg)
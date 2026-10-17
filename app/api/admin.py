from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_moderator, require_super_admin
from app.database.session import get_db
from app.models.user import User
from app.models.message import Message
from app.models.group import Group
from app.models.moderation import ModerationReport
from app.models.audit import AuditLog
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def stats(user: User = Depends(require_moderator), db: AsyncSession = Depends(get_db)):
    users_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    messages_count = (await db.execute(select(func.count()).select_from(Message))).scalar() or 0
    groups_count = (await db.execute(select(func.count()).select_from(Group))).scalar() or 0
    pending_reports = (await db.execute(
        select(func.count()).select_from(ModerationReport).where(ModerationReport.status == "pending")
    )).scalar() or 0
    return {
        "users": users_count,
        "messages": messages_count,
        "groups": groups_count,
        "pending_reports": pending_reports,
    }


@router.get("/users")
async def list_users(
    q: str = "",
    limit: int = 50,
    user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).limit(limit).order_by(User.id.desc())
    if q:
        stmt = stmt.where(User.username.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    result = await db.execute(stmt)
    return [
        {
            "id": u.id, "username": u.username, "email": u.email,
            "display_name": u.display_name, "role": u.role.value,
            "is_active": u.is_active, "is_blocked": u.is_blocked,
            "created_at": u.created_at.isoformat(),
        }
        for u in result.scalars().all()
    ]


@router.post("/users/{user_id}/block")
async def block_user(
    user_id: int, reason: str = "",
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise NotFoundError("کاربر یافت نشد")
    u.is_blocked = True
    db.add(AuditLog(
        actor_id=admin.id, action="block_user",
        target_type="user", target_id=user_id, details=reason,
    ))
    await db.commit()
    return {"message": "کاربر مسدود شد"}


@router.post("/users/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise NotFoundError("کاربر یافت نشد")
    u.is_blocked = False
    db.add(AuditLog(actor_id=admin.id, action="unblock_user", target_type="user", target_id=user_id))
    await db.commit()
    return {"message": "رفع مسدودی انجام شد"}
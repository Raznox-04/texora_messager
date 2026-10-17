from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.core.security import decode_token
from app.database.session import get_db
from app.models.user import User, UserRole

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise UnauthorizedError()
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("توکن نامعتبر است")
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("کاربر یافت نشد")
    if not user.is_active or user.is_blocked:
        raise ForbiddenError("حساب کاربری مسدود است")
    return user


async def require_moderator(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.MODERATOR, UserRole.SUPER_ADMIN):
        raise ForbiddenError("دسترسی مدیر لازم است")
    return user


async def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.SUPER_ADMIN:
        raise ForbiddenError("دسترسی مدیر کل لازم است")
    return user
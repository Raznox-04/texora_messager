from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token, decode_token
)
from app.core.exceptions import ConflictError, UnauthorizedError, NotFoundError
from app.models.user import User, UserSession
from app.schemas.auth import RegisterRequest, LoginRequest


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: RegisterRequest) -> User:
        existing = await self.db.execute(
            select(User).where(
                (User.username == data.username) | (User.email == data.email)
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("نام کاربری یا ایمیل قبلاً ثبت شده است")

        user = User(
            username=data.username,
            email=data.email,
            display_name=data.display_name,
            password_hash=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, data: LoginRequest, user_agent: str = "", ip: str = "") -> tuple[User, str, str]:
        result = await self.db.execute(
            select(User).where(User.username == data.username.lower())
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("نام کاربری یا رمز عبور نادرست است")
        if not user.is_active:
            raise UnauthorizedError("حساب کاربری غیرفعال است")

        access = create_access_token(str(user.id), {"role": user.role.value})
        refresh = create_refresh_token(str(user.id))

        session = UserSession(
            user_id=user.id,
            refresh_token=refresh,
            user_agent=user_agent[:500],
            ip_address=ip[:45],
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(session)
        user.is_online = True
        user.last_seen_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(user)
        return user, access, refresh

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("توکن نامعتبر است")

        result = await self.db.execute(
            select(UserSession).where(
                UserSession.refresh_token == refresh_token,
                UserSession.revoked == False,  # noqa: E712
            )
        )
        session = result.scalar_one_or_none()
        if not session or session.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedError("نشست منقضی شده است")

        user_result = await self.db.execute(select(User).where(User.id == session.user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            raise UnauthorizedError("کاربر یافت نشد")

        session.revoked = True
        new_refresh = create_refresh_token(str(user.id))
        new_session = UserSession(
            user_id=user.id,
            refresh_token=new_refresh,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(new_session)
        await self.db.commit()

        new_access = create_access_token(str(user.id), {"role": user.role.value})
        return new_access, new_refresh

    async def logout(self, user_id: int, refresh_token: Optional[str] = None) -> None:
        if refresh_token:
            result = await self.db.execute(
                select(UserSession).where(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token == refresh_token,
                )
            )
            session = result.scalar_one_or_none()
            if session:
                session.revoked = True
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.is_online = False
            user.last_seen_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def get_user_by_id(self, user_id: int) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("کاربر یافت نشد")
        return user
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError, ForbiddenError
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import (
    UserPublic, UserPrivate, UserUpdate, UserProfileUpdate, ChangePasswordRequest
)
from app.core.security import hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserPrivate)
async def get_me(user: User = Depends(get_current_user)):
    return UserPrivate.model_validate(user)


@router.patch("/me", response_model=UserPrivate)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.display_name is not None:
        user.display_name = data.display_name
    if data.bio is not None:
        user.bio = data.bio
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    await db.commit()
    await db.refresh(user)
    return UserPrivate.model_validate(user)


@router.patch("/me/privacy", response_model=UserPrivate)
async def update_privacy(
    data: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.show_online_status is not None:
        user.show_online_status = data.show_online_status
    if data.show_last_seen is not None:
        user.show_last_seen = data.show_last_seen
    await db.commit()
    await db.refresh(user)
    return UserPrivate.model_validate(user)


@router.post("/me/password")
async def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, user.password_hash):
        raise ForbiddenError("رمز عبور فعلی نادرست است")
    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"message": "رمز عبور تغییر کرد"}


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise NotFoundError("کاربر یافت نشد")
    pub = UserPublic.model_validate(u)
    if not u.show_online_status:
        pub.is_online = False
    if not u.show_last_seen:
        pub.last_seen_at = None
    return pub


@router.get("", response_model=list[UserPublic])
async def search_users(
    q: str = "",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(User).where(User.is_active == True).limit(30)  # noqa: E712
    if q:
        stmt = stmt.where(User.username.ilike(f"%{q}%") | User.display_name.ilike(f"%{q}%"))
    result = await db.execute(stmt)
    return [UserPublic.model_validate(u) for u in result.scalars().all()]
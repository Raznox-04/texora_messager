from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from app.schemas.user import UserPrivate
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.models.user import User
from app.core.security import decode_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserPrivate, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.register(data)
    return UserPrivate.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else ""
    user, access, refresh = await service.login(data, ua, ip)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserPrivate.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    access, refresh = await service.refresh(data.refresh_token)
    payload = decode_token(access)
    user_id = int(payload["sub"])
    user = await service.get_user_by_id(user_id)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserPrivate.model_validate(user),
    )


@router.post("/logout")
async def logout(
    data: RefreshRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.logout(user.id, data.refresh_token if data else None)
    return {"message": "خروج انجام شد"}
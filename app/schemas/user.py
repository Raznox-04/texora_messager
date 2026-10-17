from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_online: bool = False
    last_seen_at: Optional[datetime] = None


class UserPrivate(UserPublic):
    email: EmailStr
    role: str
    is_active: bool
    is_blocked: bool
    show_online_status: bool
    show_last_seen: bool
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None


class UserProfileUpdate(BaseModel):
    show_online_status: Optional[bool] = None
    show_last_seen: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
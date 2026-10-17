from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_public: bool = False
    member_ids: List[int] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    rules: Optional[str] = None
    is_public: Optional[bool] = None
    allow_member_send_messages: Optional[bool] = None
    allow_member_send_files: Optional[bool] = None
    allow_member_send_links: Optional[bool] = None


class GroupMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    role: str
    is_muted: bool
    created_at: datetime


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    avatar_url: Optional[str]
    is_public: bool
    owner_id: int
    created_at: datetime


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    expires_at: Optional[datetime]
    max_uses: Optional[int]
    uses_count: int
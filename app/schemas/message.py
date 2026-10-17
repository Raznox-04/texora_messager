from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    is_image: bool


class ReactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    emoji: str


class MessageCreate(BaseModel):
    conversation_id: int
    content: Optional[str] = Field(None, max_length=5000)
    message_type: str = "text"
    reply_to_id: Optional[int] = None


class MessageUpdate(BaseModel):
    content: str = Field(..., max_length=5000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    sender_id: Optional[int]
    content: Optional[str]
    message_type: str
    reply_to_id: Optional[int]
    is_edited: bool
    is_deleted: bool
    is_pinned: bool
    moderation_status: str
    created_at: datetime
    updated_at: datetime
    attachments: List[AttachmentOut] = []
    reactions: List[ReactionOut] = []


class ReactionCreate(BaseModel):
    emoji: str = Field(..., max_length=10)
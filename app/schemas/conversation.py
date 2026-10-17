from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConversationCreate(BaseModel):
    participant_id: int


class ConversationOut(BaseModel):
    id: int
    type: str = "private"
    title: Optional[str] = None
    other_user_id: Optional[int] = None
    other_username: Optional[str] = None
    is_online: bool = False
    last_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
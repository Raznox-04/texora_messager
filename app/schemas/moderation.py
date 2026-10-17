from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ModerationVerdict(str, Enum):
    ALLOWED = "allowed"
    SUSPICIOUS = "suspicious"
    VIOLATION = "violation"


class ViolationCategory(str, Enum):
    NONE = "none"
    INSULT = "insult"
    THREAT = "threat"
    HARASSMENT = "harassment"
    SPAM = "spam"
    REPETITION = "repetition"
    PHISHING = "phishing"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"


class SeverityLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SuggestedAction(str, Enum):
    NONE = "none"
    REVIEW = "review"
    WARN = "warn"
    RESTRICT = "restrict"
    BAN = "ban"


class ModerationResult(BaseModel):
    """خروجی ساختاریافته تحلیل هوش مصنوعی"""
    verdict: ModerationVerdict = ModerationVerdict.ALLOWED
    category: ViolationCategory = ViolationCategory.NONE
    severity: SeverityLevel = SeverityLevel.NONE
    explanation: str = ""
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    suggested_action: SuggestedAction = SuggestedAction.NONE


class ModerationReportOut(BaseModel):
    id: int
    message_id: int
    user_id: int
    result: str
    category: Optional[str]
    severity: Optional[str]
    explanation: Optional[str]
    confidence: Optional[float]
    suggested_action: Optional[str]
    status: str
    created_at: str
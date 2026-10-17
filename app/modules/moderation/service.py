import json
import logging
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.modules.moderation.client import AIGatewayClient
from app.modules.moderation.rules import MODERATION_SYSTEM_PROMPT, build_user_prompt
from app.schemas.moderation import ModerationResult, ModerationVerdict
from app.models.moderation import ModerationReport
from app.models.message import Message

logger = logging.getLogger(__name__)


class ModerationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AIGatewayClient()

    async def analyze_message(
        self, message_id: int, user_id: int, content: str
    ) -> Optional[ModerationReport]:
        if not settings.MODERATION_ENABLED:
            return None
        if not content or len(content.strip()) < settings.MODERATION_MIN_LENGTH:
            return None

        existing = await self.db.execute(
            select(ModerationReport).where(ModerationReport.message_id == message_id)
        )
        if existing.scalar_one_or_none():
            return None

        recent_q = await self.db.execute(
            select(Message.content)
            .where(Message.sender_id == user_id, Message.id != message_id, Message.is_deleted == False)  # noqa: E712
            .order_by(desc(Message.id))
            .limit(5)
        )
        recent = [r for r in recent_q.scalars().all() if r]

        user_prompt = build_user_prompt(content, recent)
        raw = await self.client.chat_completion(
            MODERATION_SYSTEM_PROMPT, user_prompt, response_format_json=True
        )

        if raw is None:
            logger.warning(f"Moderation skipped for message {message_id}: AI unavailable")
            return None

        parsed = self._parse_response(raw)
        if parsed is None:
            logger.warning(f"Moderation parse failed for message {message_id}")
            return None

        is_allowed = parsed.verdict == ModerationVerdict.ALLOWED

        # بروزرسانی وضعیت نظارتی خود پیام در جدول messages
        msg_result = await self.db.execute(select(Message).where(Message.id == message_id))
        msg_obj = msg_result.scalar_one_or_none()
        if msg_obj:
            msg_obj.moderation_status = "approved" if is_allowed else "flagged"

        report = ModerationReport(
            message_id=message_id,
            user_id=user_id,
            result=parsed.verdict.value,
            category=parsed.category.value,
            severity=parsed.severity.value,
            explanation=parsed.explanation[:2000] if parsed.explanation else None,
            confidence=parsed.confidence,
            suggested_action=parsed.suggested_action.value,
            raw_response=raw[:5000],
            status="auto_approved" if is_allowed else "pending",
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    def _parse_response(self, raw: str) -> Optional[ModerationResult]:
        try:
            text = raw.strip()
            if "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                text = text[start:end]
            data = json.loads(text)
            return ModerationResult.model_validate(data)
        except Exception as e:
            logger.warning(f"Moderation response parse error: {e} | raw={raw[:200]}")
            return None
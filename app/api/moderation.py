from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_moderator
from app.database.session import get_db
from app.models.user import User
from app.models.moderation import ModerationReport, ModerationDecision
from app.schemas.moderation import ModerationReportOut
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


@router.get("/reports", response_model=list[ModerationReportOut])
async def list_reports(
    status_filter: str = "pending",
    limit: int = 50,
    user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    q = select(ModerationReport).order_by(ModerationReport.id.desc()).limit(limit)
    if status_filter:
        q = q.where(ModerationReport.status == status_filter)
    result = await db.execute(q)
    return [
        ModerationReportOut(
            id=r.id, message_id=r.message_id, user_id=r.user_id, result=r.result,
            category=r.category, severity=r.severity, explanation=r.explanation,
            confidence=r.confidence, suggested_action=r.suggested_action,
            status=r.status, created_at=r.created_at.isoformat(),
        )
        for r in result.scalars().all()
    ]


@router.post("/reports/{report_id}/decision")
async def make_decision(
    report_id: int,
    decision: str,
    reason: str = "",
    user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModerationReport).where(ModerationReport.id == report_id))
    r = result.scalar_one_or_none()
    if not r:
        raise NotFoundError("گزارش یافت نشد")
    r.status = "reviewed"
    r.reviewed_by_id = user.id
    r.reviewed_at = datetime.now(timezone.utc)
    d = ModerationDecision(report_id=report_id, admin_id=user.id, decision=decision, reason=reason)
    db.add(d)
    await db.commit()
    return {"message": "تصمیم ثبت شد"}
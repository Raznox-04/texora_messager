import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.conversation import Conversation, ConversationMember, ConversationType
from app.models.group import Group, GroupMember, GroupRole, Invitation
from app.schemas.group import GroupCreate, GroupOut, GroupUpdate, GroupMemberOut, InvitationOut
from app.core.exceptions import ForbiddenError, NotFoundError, ConflictError

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.post("", response_model=GroupOut, status_code=201)
async def create_group(
    data: GroupCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = Group(
        name=data.name,
        description=data.description,
        is_public=data.is_public,
        owner_id=user.id,
    )
    db.add(group)
    await db.flush()

    conv = Conversation(type=ConversationType.GROUP, title=data.name, group_id=group.id)
    db.add(conv)
    await db.flush()

    db.add(GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.ADMIN))
    db.add(ConversationMember(conversation_id=conv.id, user_id=user.id))

    for uid in data.member_ids:
        if uid == user.id:
            continue
        u = await db.execute(select(User).where(User.id == uid))
        if u.scalar_one_or_none():
            db.add(GroupMember(group_id=group.id, user_id=uid, role=GroupRole.MEMBER))
            db.add(ConversationMember(conversation_id=conv.id, user_id=uid))

    await db.commit()
    await db.refresh(group)
    return GroupOut.model_validate(group)


@router.get("", response_model=list[GroupOut])
async def list_my_groups(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Group).join(GroupMember).where(GroupMember.user_id == user.id)
    )
    return [GroupOut.model_validate(g) for g in result.scalars().unique().all()]


@router.get("/{group_id}", response_model=GroupOut)
async def get_group(
    group_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_member(db, group_id, user.id)
    result = await db.execute(select(Group).where(Group.id == group_id))
    g = result.scalar_one_or_none()
    if not g:
        raise NotFoundError("گروه یافت نشد")
    return GroupOut.model_validate(g)


@router.patch("/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: int,
    data: GroupUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_admin(db, group_id, user.id)
    result = await db.execute(select(Group).where(Group.id == group_id))
    g = result.scalar_one_or_none()
    if not g:
        raise NotFoundError("گروه یافت نشد")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(g, k, v)
    await db.commit()
    await db.refresh(g)
    return GroupOut.model_validate(g)


@router.get("/{group_id}/members", response_model=list[GroupMemberOut])
async def list_members(
    group_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_member(db, group_id, user.id)
    result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id))
    return [GroupMemberOut.model_validate(m) for m in result.scalars().all()]


@router.post("/{group_id}/members/{user_id}")
async def add_member(
    group_id: int, user_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_admin(db, group_id, user.id)
    exists = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )
    if exists.scalar_one_or_none():
        raise ConflictError("کاربر قبلاً عضو گروه است")
    db.add(GroupMember(group_id=group_id, user_id=user_id, role=GroupRole.MEMBER))
    conv_q = await db.execute(select(Conversation).where(Conversation.group_id == group_id))
    conv = conv_q.scalar_one_or_none()
    if conv:
        db.add(ConversationMember(conversation_id=conv.id, user_id=user_id))
    await db.commit()
    return {"message": "عضو اضافه شد"}


@router.delete("/{group_id}/members/{user_id}")
async def remove_member(
    group_id: int, user_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_admin(db, group_id, user.id)
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise NotFoundError("عضو یافت نشد")
    await db.delete(m)
    conv_q = await db.execute(select(Conversation).where(Conversation.group_id == group_id))
    conv = conv_q.scalar_one_or_none()
    if conv:
        cm_q = await db.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conv.id,
                ConversationMember.user_id == user_id,
            )
        )
        cm = cm_q.scalar_one_or_none()
        if cm:
            await db.delete(cm)
    await db.commit()
    return {"message": "عضو حذف شد"}


@router.post("/{group_id}/invitations", response_model=InvitationOut)
async def create_invitation(
    group_id: int,
    expires_hours: int = 72,
    max_uses: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_admin(db, group_id, user.id)
    inv = Invitation(
        group_id=group_id,
        code=secrets.token_urlsafe(16),
        created_by_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
        max_uses=max_uses,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return InvitationOut.model_validate(inv)


@router.post("/join/{code}")
async def join_by_invitation(
    code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Invitation).where(Invitation.code == code))
    inv = result.scalar_one_or_none()
    if not inv or inv.revoked:
        raise NotFoundError("دعوت‌نامه یافت نشد")
    if inv.expires_at and inv.expires_at < datetime.now(timezone.utc):
        raise ForbiddenError("دعوت‌نامه منقضی شده")
    if inv.max_uses and inv.uses_count >= inv.max_uses:
        raise ForbiddenError("ظرفیت دعوت‌نامه تکمیل است")

    exists = await db.execute(
        select(GroupMember).where(GroupMember.group_id == inv.group_id, GroupMember.user_id == user.id)
    )
    if exists.scalar_one_or_none():
        raise ConflictError("شما قبلاً عضو این گروه هستید")

    db.add(GroupMember(group_id=inv.group_id, user_id=user.id, role=GroupRole.MEMBER))
    inv.uses_count += 1
    conv_q = await db.execute(select(Conversation).where(Conversation.group_id == inv.group_id))
    conv = conv_q.scalar_one_or_none()
    if conv:
        db.add(ConversationMember(conversation_id=conv.id, user_id=user.id))
    await db.commit()
    return {"message": "به گروه پیوستید", "group_id": inv.group_id}


async def _check_member(db: AsyncSession, group_id: int, user_id: int) -> GroupMember:
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise ForbiddenError("شما عضو این گروه نیستید")
    return m


async def _check_admin(db: AsyncSession, group_id: int, user_id: int) -> GroupMember:
    m = await _check_member(db, group_id, user_id)
    if m.role not in (GroupRole.ADMIN, GroupRole.MODERATOR):
        raise ForbiddenError("دسترسی مدیریت گروه لازم است")
    return m
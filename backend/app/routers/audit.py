from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_cap
from app.auth.permissions import Cap
from app.db import get_session
from app.models.audit import AuditLog
from app.models.users import User
from app.schemas.audit import AuditOut

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
async def list_audit(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_cap(Cap.VIEW_AUDIT)),
    db: AsyncSession = Depends(get_session),
):
    rows = (
        await db.execute(
            select(AuditLog, User.email)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .order_by(AuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    out: list[AuditOut] = []
    for entry, actor_email in rows:
        item = AuditOut.model_validate(entry)
        item.actor_email = actor_email
        out.append(item)
    return out

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int | None
    actor_email: str | None = None
    action: str
    target_type: str | None
    target_id: int | None
    detail: dict | None
    created_at: datetime

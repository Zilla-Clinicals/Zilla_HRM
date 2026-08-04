from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documents import EmployeeDocument
from app.schemas.documents import PHOTO_KIND
from app.storage import get_storage


async def has_photo(db: AsyncSession, employee_id: int) -> bool:
    row = await db.scalar(
        select(EmployeeDocument.id)
        .where(
            EmployeeDocument.employee_id == employee_id,
            EmployeeDocument.kind == PHOTO_KIND,
        )
        .limit(1)
    )
    return row is not None


async def employees_with_photo(db: AsyncSession, employee_ids: list[int]) -> set[int]:
    if not employee_ids:
        return set()
    rows = await db.scalars(
        select(EmployeeDocument.employee_id).where(
            EmployeeDocument.kind == PHOTO_KIND,
            EmployeeDocument.employee_id.in_(employee_ids),
        )
    )
    return set(rows.all())


async def delete_documents(db: AsyncSession, docs: list[EmployeeDocument]) -> None:
    """Delete document rows and their backing blobs."""
    for doc in docs:
        await get_storage(doc.storage_backend).delete(db, doc.storage_key)
        await db.delete(doc)

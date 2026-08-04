from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documents import DocumentBlob


class DbStorage:
    """Stores blob bytes in the `document_blobs` Postgres table."""

    async def save(self, db: AsyncSession, key: str, data: bytes) -> None:
        db.add(DocumentBlob(storage_key=key, data=data))
        await db.flush()

    async def load(self, db: AsyncSession, key: str) -> bytes | None:
        blob = await db.get(DocumentBlob, key)
        return bytes(blob.data) if blob else None

    async def delete(self, db: AsyncSession, key: str) -> None:
        blob = await db.get(DocumentBlob, key)
        if blob:
            await db.delete(blob)

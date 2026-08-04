"""Swappable blob storage.

Metadata lives in the `employee_documents` table; the raw bytes go through a
`BlobStorage` backend keyed by an opaque `storage_key`. The default backend keeps
bytes in Postgres (survives Render/Neon redeploys, no external credentials).

To switch to S3/Cloudinary later: implement the BlobStorage protocol in a new
module, register it in `_BACKENDS`, and set STORAGE_BACKEND. Each document records
the backend it was saved with, so existing files keep resolving after a switch.
"""
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.storage.db import DbStorage


class BlobStorage(Protocol):
    async def save(self, db: AsyncSession, key: str, data: bytes) -> None: ...
    async def load(self, db: AsyncSession, key: str) -> bytes | None: ...
    async def delete(self, db: AsyncSession, key: str) -> None: ...


_BACKENDS: dict[str, BlobStorage] = {
    "db": DbStorage(),
    # "s3": S3Storage(),  # add here when needed
}


def get_storage(backend: str | None = None) -> BlobStorage:
    name = backend or settings.storage_backend
    if name not in _BACKENDS:
        raise ValueError(f"Unknown storage backend: {name}")
    return _BACKENDS[name]

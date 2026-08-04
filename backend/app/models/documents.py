from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EmployeeDocument(Base):
    """Metadata for a file attached to an employee (photo or a filed document)."""

    __tablename__ = "employee_documents"
    __table_args__ = (
        UniqueConstraint("storage_key", name="uq_employee_documents_storage_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # photo | degree | offer_letter | …
    title: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_backend: Mapped[str] = mapped_column(Text, nullable=False, default="db")
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DocumentBlob(Base):
    """Raw bytes for the in-DB storage backend, keyed by storage_key."""

    __tablename__ = "document_blobs"

    storage_key: Mapped[str] = mapped_column(Text, primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

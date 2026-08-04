import secrets

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_cap
from app.auth.permissions import Cap, can
from app.config import settings
from app.db import get_session
from app.models.documents import EmployeeDocument
from app.models.employees import Employee
from app.models.users import User
from app.schemas.documents import (
    ALLOWED_DOCUMENT_TYPES,
    ALLOWED_IMAGE_TYPES,
    DOCUMENT_KINDS,
    PHOTO_KIND,
    DocumentOut,
)
from app.services import audit
from app.services.documents import delete_documents
from app.storage import get_storage

router = APIRouter(prefix="/api/employees", tags=["documents"])


async def _employee_or_404(db: AsyncSession, employee_id: int) -> Employee:
    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return emp


async def _my_employee_id(db: AsyncSession, user: User) -> int | None:
    return await db.scalar(select(Employee.id).where(Employee.user_id == user.id))


async def _can_view_employee(db: AsyncSession, user: User, target: Employee) -> bool:
    """Photos: anyone who can see the person (org viewers, self, or their manager)."""
    if can(user.role, Cap.VIEW_ORG):
        return True
    me = await _my_employee_id(db, user)
    return me is not None and (me == target.id or target.manager_id == me)


async def _can_view_documents(db: AsyncSession, user: User, target: Employee) -> bool:
    """Filed documents are more sensitive: org viewers (HR/exec/admin) or the person."""
    if can(user.role, Cap.VIEW_ORG):
        return True
    me = await _my_employee_id(db, user)
    return me is not None and me == target.id


async def _read_upload(file: UploadFile, *, allowed: set[str], max_mb: int) -> bytes:
    if file.content_type not in allowed:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type: {file.content_type}",
        )
    max_bytes = max_mb * 1024 * 1024
    # Fast reject when the multipart parser already knows the size, so we never
    # even start buffering an oversized body.
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {max_mb} MB"
        )
    # Read in chunks and abort the moment we cross the cap — bounds peak memory
    # to ~max_bytes rather than reading the whole (possibly huge) body at once.
    # NOTE: a hard request-body limit must still be enforced at the reverse proxy
    # (e.g. nginx client_max_body_size) — see DEPLOYMENT.md.
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {max_mb} MB"
            )
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    return b"".join(chunks)


# --------------------------------------------------------------- Profile photo
@router.post("/{employee_id}/photo", response_model=DocumentOut, status_code=201)
async def upload_photo(
    employee_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_cap(Cap.MANAGE_PEOPLE)),
    db: AsyncSession = Depends(get_session),
):
    await _employee_or_404(db, employee_id)
    data = await _read_upload(file, allowed=ALLOWED_IMAGE_TYPES, max_mb=settings.max_photo_mb)

    # One photo per employee — replace any existing.
    existing = (
        await db.scalars(
            select(EmployeeDocument).where(
                EmployeeDocument.employee_id == employee_id,
                EmployeeDocument.kind == PHOTO_KIND,
            )
        )
    ).all()
    await delete_documents(db, list(existing))

    key = secrets.token_hex(16)
    await get_storage().save(db, key, data)
    doc = EmployeeDocument(
        employee_id=employee_id,
        kind=PHOTO_KIND,
        title="Profile photo",
        filename=file.filename or "photo",
        content_type=file.content_type,
        size_bytes=len(data),
        storage_backend=settings.storage_backend,
        storage_key=key,
        uploaded_by=user.id,
    )
    db.add(doc)
    await audit.record(
        db, actor_user_id=user.id, action="employee.photo.upload",
        target_type="employee", target_id=employee_id,
    )
    await db.commit()
    await db.refresh(doc)
    return DocumentOut.model_validate(doc)


@router.get("/{employee_id}/photo")
async def get_photo(
    employee_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    target = await _employee_or_404(db, employee_id)
    if not await _can_view_employee(db, user, target):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    doc = await db.scalar(
        select(EmployeeDocument)
        .where(
            EmployeeDocument.employee_id == employee_id,
            EmployeeDocument.kind == PHOTO_KIND,
        )
        .order_by(EmployeeDocument.id.desc())
        .limit(1)
    )
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo")
    data = await get_storage(doc.storage_backend).load(db, doc.storage_key)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo")
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.delete("/{employee_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    employee_id: int,
    user: User = Depends(require_cap(Cap.MANAGE_PEOPLE)),
    db: AsyncSession = Depends(get_session),
):
    docs = (
        await db.scalars(
            select(EmployeeDocument).where(
                EmployeeDocument.employee_id == employee_id,
                EmployeeDocument.kind == PHOTO_KIND,
            )
        )
    ).all()
    await delete_documents(db, list(docs))
    await audit.record(
        db, actor_user_id=user.id, action="employee.photo.delete",
        target_type="employee", target_id=employee_id,
    )
    await db.commit()


# ------------------------------------------------------------- Document vault
@router.get("/{employee_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    employee_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    target = await _employee_or_404(db, employee_id)
    if not await _can_view_documents(db, user, target):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    docs = (
        await db.scalars(
            select(EmployeeDocument)
            .where(
                EmployeeDocument.employee_id == employee_id,
                EmployeeDocument.kind != PHOTO_KIND,
            )
            .order_by(EmployeeDocument.created_at.desc())
        )
    ).all()
    return [DocumentOut.model_validate(d) for d in docs]


@router.post("/{employee_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    employee_id: int,
    kind: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_cap(Cap.MANAGE_PEOPLE)),
    db: AsyncSession = Depends(get_session),
):
    await _employee_or_404(db, employee_id)
    if kind not in DOCUMENT_KINDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown document type: {kind}")
    data = await _read_upload(
        file, allowed=ALLOWED_DOCUMENT_TYPES, max_mb=settings.max_document_mb
    )

    key = secrets.token_hex(16)
    await get_storage().save(db, key, data)
    doc = EmployeeDocument(
        employee_id=employee_id,
        kind=kind,
        title=title.strip() or (file.filename or "Document"),
        filename=file.filename or "document",
        content_type=file.content_type,
        size_bytes=len(data),
        storage_backend=settings.storage_backend,
        storage_key=key,
        uploaded_by=user.id,
    )
    db.add(doc)
    await audit.record(
        db, actor_user_id=user.id, action="employee.document.upload",
        target_type="employee", target_id=employee_id, detail={"kind": kind, "title": doc.title},
    )
    await db.commit()
    await db.refresh(doc)
    return DocumentOut.model_validate(doc)


async def _load_doc(db: AsyncSession, employee_id: int, doc_id: int) -> EmployeeDocument:
    doc = await db.get(EmployeeDocument, doc_id)
    if not doc or doc.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


@router.get("/{employee_id}/documents/{doc_id}")
async def download_document(
    employee_id: int,
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    target = await _employee_or_404(db, employee_id)
    if not await _can_view_documents(db, user, target):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    doc = await _load_doc(db, employee_id, doc_id)
    data = await get_storage(doc.storage_backend).load(db, doc.storage_key)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing")
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.delete("/{employee_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    employee_id: int,
    doc_id: int,
    user: User = Depends(require_cap(Cap.MANAGE_PEOPLE)),
    db: AsyncSession = Depends(get_session),
):
    doc = await _load_doc(db, employee_id, doc_id)
    await delete_documents(db, [doc])
    await audit.record(
        db, actor_user_id=user.id, action="employee.document.delete",
        target_type="employee", target_id=employee_id, detail={"doc_id": doc_id},
    )
    await db.commit()

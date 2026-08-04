from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_cap
from app.auth.permissions import Cap
from app.db import get_session
from app.models.kpis import Kpi, KpiCategory
from app.models.users import User
from app.schemas.kpis import (
    CategoryOut,
    CategoryUpdate,
    KpiCreate,
    KpiOut,
    KpiUpdate,
)
from app.services import audit

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


async def _category_context(db: AsyncSession) -> tuple[dict[str, float], Counter]:
    """Returns (category name -> weight, active-KPI count per category)."""
    weights = {
        c.name: float(c.weight)
        for c in (
            await db.scalars(select(KpiCategory).where(KpiCategory.is_active.is_(True)))
        ).all()
    }
    counts = Counter(
        k.category
        for k in (await db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))).all()
    )
    return weights, counts


def _to_out(kpi: Kpi, weights: dict[str, float], counts: Counter) -> KpiOut:
    out = KpiOut.model_validate(kpi)
    weight = weights.get(kpi.category)
    n = counts.get(kpi.category, 0)
    out.category_weight = weight
    out.points = round(weight / n, 4) if weight and n else 0.0
    return out


# ---------------------------------------------------------------- Categories
@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    _weights, counts = await _category_context(db)
    cats = (
        await db.scalars(
            select(KpiCategory).where(KpiCategory.is_active.is_(True)).order_by(
                KpiCategory.weight.desc()
            )
        )
    ).all()
    out = []
    for c in cats:
        item = CategoryOut.model_validate(c)
        item.kpi_count = counts.get(c.name, 0)
        item.points_per_kpi = round(float(c.weight) / item.kpi_count, 4) if item.kpi_count else 0.0
        out.append(item)
    return out


@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    admin: User = Depends(require_cap(Cap.MANAGE_KPIS)),
    db: AsyncSession = Depends(get_session),
):
    cat = await db.get(KpiCategory, category_id)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    cat.weight = payload.weight
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="kpi_category.update",
        target_type="kpi_category",
        target_id=cat.id,
        detail={"weight": str(payload.weight)},
    )
    await db.commit()
    await db.refresh(cat)
    _weights, counts = await _category_context(db)
    item = CategoryOut.model_validate(cat)
    item.kpi_count = counts.get(cat.name, 0)
    item.points_per_kpi = round(float(cat.weight) / item.kpi_count, 4) if item.kpi_count else 0.0
    return item


# ---------------------------------------------------------------------- KPIs
@router.get("", response_model=list[KpiOut])
async def list_kpis(
    include_inactive: bool = Query(default=False),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    weights, counts = await _category_context(db)
    stmt = select(Kpi).order_by(Kpi.category, Kpi.name)
    if not include_inactive:
        stmt = stmt.where(Kpi.is_active.is_(True))
    kpis = (await db.scalars(stmt)).all()
    return [_to_out(k, weights, counts) for k in kpis]


async def _assert_category_exists(db: AsyncSession, name: str) -> None:
    exists = await db.scalar(
        select(KpiCategory).where(
            KpiCategory.name == name, KpiCategory.is_active.is_(True)
        )
    )
    if not exists:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unknown category '{name}'"
        )


@router.post("", response_model=KpiOut, status_code=status.HTTP_201_CREATED)
async def create_kpi(
    payload: KpiCreate,
    admin: User = Depends(require_cap(Cap.MANAGE_KPIS)),
    db: AsyncSession = Depends(get_session),
):
    await _assert_category_exists(db, payload.category)
    kpi = Kpi(**payload.model_dump())
    db.add(kpi)
    await db.flush()
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="kpi.create",
        target_type="kpi",
        target_id=kpi.id,
        detail={"name": kpi.name, "category": kpi.category},
    )
    await db.commit()
    await db.refresh(kpi)
    weights, counts = await _category_context(db)
    return _to_out(kpi, weights, counts)


@router.patch("/{kpi_id}", response_model=KpiOut)
async def update_kpi(
    kpi_id: int,
    payload: KpiUpdate,
    admin: User = Depends(require_cap(Cap.MANAGE_KPIS)),
    db: AsyncSession = Depends(get_session),
):
    kpi = await db.get(Kpi, kpi_id)
    if not kpi:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "KPI not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("category"):
        await _assert_category_exists(db, data["category"])
    for field, value in data.items():
        setattr(kpi, field, value)
    await db.commit()
    await db.refresh(kpi)
    weights, counts = await _category_context(db)
    return _to_out(kpi, weights, counts)


@router.delete("/{kpi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kpi(
    kpi_id: int,
    admin: User = Depends(require_cap(Cap.MANAGE_KPIS)),
    db: AsyncSession = Depends(get_session),
):
    kpi = await db.get(Kpi, kpi_id)
    if not kpi:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "KPI not found")
    kpi.is_active = False  # soft-delete: scores reference it
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="kpi.deactivate",
        target_type="kpi",
        target_id=kpi.id,
        detail={"name": kpi.name},
    )
    await db.commit()

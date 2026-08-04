"""Auto-generated employee numbers: <name-initials>-<random digits>.

Uniqueness is guaranteed by a UNIQUE constraint on employees.employee_number
(installed in migration 0007). The generator checks for collisions and retries;
the constraint is the ultimate backstop against races.
"""
import random
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employees import Employee

_DIGITS = 5  # 90k numbers per prefix; widened automatically if a prefix saturates


def name_prefix(full_name: str) -> str:
    """Two uppercase letters from the name: first + last initial (fallbacks apply)."""
    words = [w for w in re.split(r"\s+", (full_name or "").strip()) if re.search(r"[A-Za-z]", w)]
    if len(words) >= 2:
        prefix = words[0][0] + words[-1][0]
    elif words:
        prefix = words[0][:2]
    else:
        prefix = "EM"
    prefix = re.sub(r"[^A-Z]", "", prefix.upper())
    return (prefix + "EMP")[:2]  # always exactly two letters


def make_candidate(full_name: str, digits: int = _DIGITS, rng: random.Random | None = None) -> str:
    r = rng or random
    lo, hi = 10 ** (digits - 1), 10**digits - 1
    return f"{name_prefix(full_name)}-{r.randint(lo, hi)}"


async def generate_unique_employee_number(db: AsyncSession, full_name: str) -> str:
    """A fresh employee number not already used by any employee."""
    for attempt in range(1, 26):
        # Widen the digit count if we keep colliding (a saturated prefix).
        digits = _DIGITS + (attempt // 10)
        candidate = make_candidate(full_name, digits=digits)
        exists = await db.scalar(
            select(Employee.id).where(Employee.employee_number == candidate)
        )
        if not exists:
            return candidate
    # Practically unreachable; last resort keeps things moving.
    return make_candidate(full_name, digits=_DIGITS + 3)

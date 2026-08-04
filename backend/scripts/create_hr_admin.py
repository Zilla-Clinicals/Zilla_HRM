"""Create (or promote) the first HR admin.

Usage:
    uv run python -m scripts.create_hr_admin \
        --email admin@zillaclinicals.com --password "ChangeMe123!" --name "HR Admin"
"""
import argparse
import asyncio

from sqlalchemy import select

from app.auth.passwords import hash_password
from app.db import async_session_factory
from app.models._base import Role
from app.models.employees import Employee
from app.models.users import User


async def main(email: str, password: str, name: str) -> None:
    email = email.strip().lower()
    async with async_session_factory() as db:
        user = await db.scalar(select(User).where(User.email == email))
        if user:
            user.role = Role.admin
            user.is_active = True
            user.password_hash = hash_password(password)
            print(f"Updated existing user {email} -> admin (active).")
        else:
            user = User(
                email=email,
                role=Role.admin,
                is_active=True,
                password_hash=hash_password(password),
            )
            db.add(user)
            await db.flush()
            db.add(Employee(user_id=user.id, full_name=name, job_title="HR Administrator"))
            print(f"Created admin {email}.")
        await db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create the first HR admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="HR Admin")
    args = parser.parse_args()
    asyncio.run(main(args.email, args.password, args.name))

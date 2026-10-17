"""
ایجاد حساب مدیر کل
اجرا:
    python -m scripts.create_admin --username admin --email admin@example.com --password 'StrongPass123'
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password


async def create_admin(username: str, email: str, password: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where((User.username == username) | (User.email == email))
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.role = UserRole.SUPER_ADMIN
            existing.password_hash = hash_password(password)
            await db.commit()
            print(f"حساب موجود به مدیر کل ارتقا یافت: {username}")
            return
        user = User(
            username=username,
            email=email,
            display_name=username,
            password_hash=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"حساب مدیر کل ایجاد شد: {username}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(create_admin(args.username, args.email, args.password))
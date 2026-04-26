
import asyncio
import os
import sys

# Add the current directory to path so it can find 'app'
sys.path.append(os.getcwd())

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.user import User

async def check_user():
    email = "doctor@gmail.com"
    async with async_session_factory() as db:
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
        if user:
            print(f"FOUND: {user.email}")
            print(f"Role: {user.role}")
            print(f"Is Active: {user.is_active}")
            print(f"Is Approved: {user.is_approved}")
            print(f"Tenant ID: {user.tenant_id}")
        else:
            print(f"NOT FOUND: {email}")

if __name__ == "__main__":
    asyncio.run(check_user())

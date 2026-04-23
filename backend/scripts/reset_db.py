import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_session, async_sessionmaker

# Add the backend directory to sys.path to allow imports from 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.models.user import User
from app.core.security import hash_password

settings = get_settings()

async def reset_database():
    print("WARNING: This will delete ALL data in the database.")
    # In a real environment, you might want to add a confirmation prompt here
    # but since this is an automated script for the user, we proceed.
    
    db_url = settings.DATABASE_URL
    if "localhost" not in db_url and "ssl" not in db_url.lower():
        separator = "&" if "?" in db_url else "?"
        db_url += f"{separator}ssl=require"
    
    engine = create_async_session(db_url).bind
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        print("Truncating all tables...")
        # Order matters or use CASCADE
        await session.execute(text("TRUNCATE TABLE token_blocklist, bills, medical_tests, medical_test_categories, patients, doctors, users, tenants CASCADE"))
        
        print("Creating new SuperAdmin...")
        new_email = "superadmin@hospitalbilling.com"
        new_password = os.getenv("NEW_SUPERADMIN_PASSWORD", "SuperAdmin@123")
        
        hashed_pw = hash_password(new_password)
        superadmin = User(
            email=new_email,
            password_hash=hashed_pw,
            full_name="System Super Admin",
            role="superadmin",
            tenant_id=None,
            is_active=True,
            is_approved=True
        )
        
        session.add(superadmin)
        await session.commit()
        
        print(f"Database reset successful!")
        print(f"SuperAdmin Email: {new_email}")
        print(f"SuperAdmin Password: {new_password}")
        print("IMPORTANT: Change this password immediately after login.")

if __name__ == "__main__":
    asyncio.run(reset_database())

import os
import sys
import asyncio
from loguru import logger
from sqlalchemy import text, select

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.database import init_db, async_session_factory
from app.models.user import User
from app.models.tenant import Tenant
from app.core.security import hash_password

settings = get_settings()

async def run_migrations():
    logger.info("Running pre-start database migrations...")
    try:
        # 1. Initialize tables
        await init_db()
        logger.info("Database base tables checked/created.")

        async with async_session_factory() as db:
            # 2. Manual Migration - Users: tenant_id nullable, is_approved
            try:
                await db.execute(text("ALTER TABLE users ALTER COLUMN tenant_id DROP NOT NULL"))
                await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE"))
                await db.commit()
                logger.info("Migration: users updated (tenant_id nullable, is_approved added)")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (users) skipped: {e}")

            # 3. Manual Migration - Tenants
            try:
                await db.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE"))
                await db.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS biller_header TEXT"))
                await db.execute(text('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS modules JSON DEFAULT \'{"patients": true, "doctors": true, "tests": true, "billing": true, "reports": true, "staff": true}\'::json'))
                await db.commit()
                logger.info("Migration: tenants table updated")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (tenants) skipped: {e}")

            # 4. Manual Migration - BillItems: code column
            try:
                await db.execute(text("ALTER TABLE bill_items ADD COLUMN IF NOT EXISTS code VARCHAR(50)"))
                await db.commit()
                logger.info("Migration: bill_items.code column added")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (bill_items.code) skipped: {e}")

            # 5. Manual Migration - Users: modules JSONB column
            try:
                await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS modules JSONB"))
                await db.commit()
                logger.info("Migration: users.modules column added")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (users.modules) skipped: {e}")

            # 6. Manual Migration - Tenants: logo_url to TEXT
            try:
                await db.execute(text("ALTER TABLE tenants ALTER COLUMN logo_url TYPE TEXT"))
                await db.commit()
                logger.info("Migration: tenants.logo_url changed to TEXT")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (tenants.logo_url) skipped: {e}")

            # 7. Auto-approve existing staff
            try:
                await db.execute(text("UPDATE users SET is_approved = true WHERE tenant_id IS NOT NULL AND role IN ('staff', 'doctor') AND is_approved = false"))
                await db.commit()
                logger.info("Migration: existing staff users auto-approved")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (staff auto-approval) skipped: {e}")

            # 8. Auto-approve superadmins
            try:
                await db.execute(text("UPDATE users SET is_approved = true WHERE role = 'superadmin'"))
                await db.commit()
                logger.info("Migration: superadmins auto-approved")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (superadmin approval) skipped: {e}")

            # 9. Seed SuperAdmin
            result = await db.execute(
                select(User).where(User.email == settings.SUPERADMIN_EMAIL)
            )
            if not result.scalar_one_or_none():
                db.add(User(
                    email=settings.SUPERADMIN_EMAIL,
                    password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
                    full_name="System Super Admin",
                    role="superadmin",
                    tenant_id=None,
                    is_active=True,
                    is_approved=True
                ))
                await db.commit()
                logger.info("Successfully seeded superadmin.")
            
        logger.info("All manual migrations completed successfully.")

    except Exception as e:
        logger.error(f"Migration step skipped or failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_migrations())

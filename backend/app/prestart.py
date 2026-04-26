
import asyncio
import os
import sys
from loguru import logger
from sqlalchemy import text

# Add current directory to path
sys.path.append(os.getcwd())

from app.core.database import init_db, async_session_factory
from app.core.config import get_settings

settings = get_settings()

async def run_migrations():
    logger.info("Running pre-start database migrations...")
    
    # 1. Initialize DB (Create tables if not exist)
    try:
        await init_db()
        logger.info("Database base tables checked/created.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't exit here, try to continue with migrations
        
    async with async_session_factory() as db:
        # 2. Manual Migrations (Idempotent)
        try:
            # users: tenant_id nullable, is_approved
            await db.execute(text("ALTER TABLE users ALTER COLUMN tenant_id DROP NOT NULL"))
            await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE"))
            logger.info("Migration: users updated (tenant_id nullable, is_approved added)")
            
            # tenants: is_approved, biller_header, modules
            await db.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT TRUE"))
            await db.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS biller_header TEXT"))
            await db.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS modules JSONB DEFAULT '[]'"))
            logger.info("Migration: tenants table updated")
            
            # bill_items: code
            await db.execute(text("ALTER TABLE bill_items ADD COLUMN IF NOT EXISTS code VARCHAR"))
            logger.info("Migration: bill_items.code column added")
            
            # users: modules
            await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS modules JSONB DEFAULT '[]'"))
            logger.info("Migration: users.modules column added")
            
            # tenants: logo_url TEXT
            await db.execute(text("ALTER TABLE tenants ALTER COLUMN logo_url TYPE TEXT"))
            logger.info("Migration: tenants.logo_url changed to TEXT")
            
            # Auto-approve existing staff
            await db.execute(text("UPDATE users SET is_approved = TRUE WHERE role IN ('admin', 'staff', 'doctor') AND is_approved = FALSE"))
            logger.info("Migration: existing staff users auto-approved")
            
            # Auto-approve superadmins
            await db.execute(text("UPDATE users SET is_approved = TRUE WHERE role = 'superadmin'"))
            logger.info("Migration: superadmins auto-approved")
            
            await db.commit()
            logger.info("All manual migrations completed successfully.")
        except Exception as e:
            logger.warning(f"Migration step skipped or failed: {e}")
            await db.rollback()

async def main():
    try:
        await run_migrations()
    except Exception as e:
        logger.critical(f"Pre-start script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

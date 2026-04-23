@echo off
echo.
echo ==================================================
echo   Hospital Billing System - SuperAdmin Seeder
echo ==================================================
echo.
echo This script will connect to your Supabase database 
echo and create the SuperAdmin account manually.
echo.
echo Database: Supabase (rkqtsheedxpfhkddcddl)
echo.

cd backend
python scripts\reset_db.py

echo.
echo If you saw "Database reset successful", you can now 
echo login at hospital-billing-system-1.onrender.com
echo.
echo User: superadmin@hospitalbilling.com
echo Password: SuperAdmin@123
echo.
pause

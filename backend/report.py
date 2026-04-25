
import asyncio
import os
import sys

# Add the current directory to path so it can find 'app'
sys.path.append(os.getcwd())

from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.models.user import User
from app.models.tenant import Tenant
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.bill import Bill

async def generate_report():
    print("\n" + "="*40)
    print("HOSPITAL SYSTEM DATA REPORT")
    print("="*40)
    
    try:
        async with async_session_factory() as db:
            # 1. Tenants
            tenants_count = await db.scalar(select(func.count(Tenant.id)))
            
            # 2. Users
            users_count = await db.scalar(select(func.count(User.id)))
            superadmins = await db.scalar(select(func.count(User.id)).where(User.role == 'superadmin'))
            admins = await db.scalar(select(func.count(User.id)).where(User.role == 'admin'))
            staff = await db.scalar(select(func.count(User.id)).where(User.role == 'staff'))
            
            # 3. Patients & Doctors
            patients_count = await db.scalar(select(func.count(Patient.id)))
            doctors_count = await db.scalar(select(func.count(Doctor.id)))
            
            # 4. Bills & Revenue
            bills_count = await db.scalar(select(func.count(Bill.id)))
            total_revenue = await db.scalar(select(func.sum(Bill.total))) or 0
            
            print(f"Total Clinics (Tenants):    {tenants_count}")
            print(f"Total Users:               {users_count}")
            print(f"   - SuperAdmins:             {superadmins}")
            print(f"   - Clinic Admins:           {admins}")
            print(f"   - Hospital Staff:          {staff}")
            print("-" * 40)
            print(f"Total Patients:            {patients_count}")
            print(f"Total Doctors:             {doctors_count}")
            print(f"Total Bills Generated:     {bills_count}")
            print(f"Total Revenue Tracked:     INR {float(total_revenue):,.2f}")
    except Exception as e:
        print(f"Error generating report: {e}")
        print("Make sure the database is running and accessible at localhost:5432")
    
    print("="*40 + "\n")

if __name__ == "__main__":
    asyncio.run(generate_report())

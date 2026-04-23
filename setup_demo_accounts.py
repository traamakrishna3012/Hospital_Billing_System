import requests
import json
import time
import os
import sys

# ── Required Environment Variables ────────────────────────────
REQUIRED_VARS = ["DEMO_ADMIN_PASSWORD", "SUPERADMIN_PASSWORD"]
for var in REQUIRED_VARS:
    if not os.environ.get(var):
        sys.exit(f"Error: Required environment variable '{var}' is not set.")

BASE_URL = "https://hospital-billing-system-pccq.onrender.com/api/v1"

print("Starting fresh environment creation...")

# 1. Register a brand new Clinic (Admin)
admin_data = {
    "clinic_name": "Demo Hospital",
    "clinic_email": "hello@demohospital.com",
    "clinic_phone": "9876543210",
    "clinic_address": "123 Health Street",
    "admin_name": "Admin",
    "admin_email": "admin@demohospital.com",
    "admin_password": os.environ["DEMO_ADMIN_PASSWORD"]
}

print("Registering Admin & Clinic...")
res = None
for _ in range(3):
    try:
        res = requests.post(f"{BASE_URL}/auth/register", json=admin_data)
        if res.status_code in [200, 201]:
            break
        elif res.status_code == 409: # Conflict / already exists
            print("Clinic already exists! Logging in to existing...")
            res = requests.post(f"{BASE_URL}/auth/login", json={"email": admin_data["admin_email"], "password": admin_data["admin_password"]})
            break
        else:
            print(f"Failed to register. Status: {res.status_code}, {res.text}")
            time.sleep(2)
    except Exception as e:
        print(f"Exception: {e}")
        time.sleep(5)

if not res or res.status_code != 200:
    print("Could not get a valid user token. Exiting.")
    exit(1)

token = res.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}
print("Admin created & logged in successfully!")

# 2. Create a Doctor
doctor_data = {
    "name": "Dr. Sarah Johnson",
    "specialization": "Cardiology",
    "qualification": "MD Cardiology",
    "consultation_fee": 500.0
}
print("Creating Doctor...")
res_doc = requests.post(f"{BASE_URL}/doctors", json=doctor_data, headers=headers)
if res_doc.status_code == 200:
    print("Doctor created successfully!")
else:
    print(f"Failed to create doctor: {res_doc.text}")

# 3. Create a Patient
patient_data = {
    "name": "Alex Patient",
    "age": 35,
    "gender": "male",
    "phone": "9876543211",
    "email": "alex@patient.com"
}
print("Creating Patient...")
res_pat = requests.post(f"{BASE_URL}/patients", json=patient_data, headers=headers)
if res_pat.status_code == 200:
    print("Patient created successfully!")
else:
    print(f"Failed to create patient: {res_pat.text}")

print("\n--- NEW ACCOUNT CREDENTIALS ---")
print(f"Admin Portal: https://hospital-billing-system-lovat.vercel.app/login")
print(f"Admin Email: {admin_data['admin_email']}")
print(f"Admin Password: {admin_data['admin_password']}")
print("Doctor: Dr. Sarah Johnson")
print("Patient: Alex Patient")

# --- 4. SEED SUPERADMIN (PLATFORM MANAGEMENT) ---
# Note: In a real system, you'd do this via a secure internal script or directly in DB
print("\nSeeding SuperAdmin (Optional check via Backend API)...")
super_admin_email = os.environ.get("SUPERADMIN_EMAIL", "superadmin@hospitalbilling.com")
super_admin_pass = os.environ["SUPERADMIN_PASSWORD"]

# We can try to hit a hypothetical root-only creation or use this as a reminder to do it in DB
# For this lab, we'll assume the user might manually add or we can provide a small script to inject it.
# I'll add a helper function here for completeness.

def seed_superadmin():
    import requests
    # Note: We haven't created a public 'create-superadmin' endpoint for security reasons.
    # Usually this is done via CLI or initial SQL script.
    print(f"To log in as Super Admin, ensure you have a user with role='superadmin' and email='{super_admin_email}'")

seed_superadmin()


"""Package init — import all models for Alembic discovery."""

from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.patient import Patient  # noqa: F401
from app.models.doctor import Doctor  # noqa: F401
from app.models.test import TestCategory, MedicalTest  # noqa: F401
from app.models.bill import Bill, BillItem  # noqa: F401
from app.models.token_blocklist import TokenBlocklist  # noqa: F401

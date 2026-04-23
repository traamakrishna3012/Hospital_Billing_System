"""
Medical test and test category routes.
"""

from __future__ import annotations

import os
import re
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status, File, UploadFile
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert
from loguru import logger
import pandas as pd
import magic
import io

from app.core.deps import CurrentUser, DBSession, TenantID
from app.models.test import MedicalTest, TestCategory
from app.schemas.schemas import (
    MedicalTestCreate,
    MedicalTestResponse,
    MedicalTestUpdate,
    PaginatedResponse,
    TestCategoryCreate,
    TestCategoryResponse,
    TestCategoryUpdate,
)

router = APIRouter(prefix="/tests", tags=["Tests & Services"])

# ── Security Constants ────────────────────────────────────────
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_ROW_COUNT = 1000
ALLOWED_MIMES = {
    "text/csv",
    "text/plain",                   # some OS report CSV as text/plain
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_cell(value):
    """Neutralize spreadsheet formula injection in a cell value."""
    if isinstance(value, str) and value.startswith(_INJECTION_PREFIXES):
        return "'" + value
    return value


def _sanitize_filename(raw: str) -> str:
    """Strip dangerous characters from a filename for safe logging/use."""
    base = os.path.basename(raw) if raw else "upload"
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)


@router.post("/bulk-upload", status_code=status.HTTP_201_CREATED, summary="Bulk import tests")
async def bulk_upload_tests(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
    file: UploadFile = File(...)
):
    safe_name = _sanitize_filename(file.filename)
    logger.info(f"Bulk upload started by user {current_user.id}: {safe_name}")

    # ── V-06: File size cap ───────────────────────────────────
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum allowed size is 5MB.",
        )

    # ── V-04: Magic-byte MIME validation ──────────────────────
    detected_mime = magic.from_buffer(contents[:2048], mime=True)
    if detected_mime not in ALLOWED_MIMES:
        logger.warning(f"Rejected upload {safe_name}: detected MIME {detected_mime}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only CSV and Excel files are permitted.",
        )

    # ── V-08: Robust parsing ─────────────────────────────────
    try:
        if detected_mime in {"text/csv", "text/plain", "application/csv"}:
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        logger.error(f"Bulk upload parse error for {safe_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not parse the uploaded file. Please ensure it is a valid CSV or Excel file.",
        )

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parsed file contains no data or could not be read properly.",
        )

    # ── V-06: Row count cap ──────────────────────────────────
    if len(df) > MAX_ROW_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many rows. Maximum allowed is {MAX_ROW_COUNT}.",
        )

    # ── V-05: CSV injection sanitization ─────────────────────
    str_cols = df.select_dtypes(include=["object"]).columns
    df[str_cols] = df[str_cols].map(_sanitize_cell)

    # Standardize columns
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Needs: name, code, price. Category is optional
    required_cols = ["name", "price", "code"]
    if not all(col in df.columns for col in required_cols):
        missing = [c for c in required_cols if c not in df.columns]
        raise HTTPException(
            status_code=400,
            detail=f"File must contain 'name', 'price', and 'code' columns. Missing: {', '.join(missing)}",
        )

    records_added = 0
    records_skipped = 0
    categories_cache = {}

    # Fetch existing categories to avoid duplicates
    existing_cats = await db.execute(
        select(TestCategory).where(TestCategory.tenant_id == tenant_id)
    )
    for cat in existing_cats.scalars():
        categories_cache[cat.name.lower()] = cat.id

    # Pre-load existing test codes for this tenant to detect duplicates
    existing_codes_result = await db.execute(
        select(MedicalTest.code).where(MedicalTest.tenant_id == tenant_id)
    )
    existing_codes = {row[0] for row in existing_codes_result.all()}

    for _, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        if not name:
            continue

        code = str(row.get("code", "")).strip()
        cat_name = str(row.get("category", "")).strip()
        price_raw = (
            str(row.get("price", "0"))
            .replace(",", "")
            .replace("₹", "")
            .replace("$", "")
            .strip()
        )

        try:
            price = float(price_raw)
        except (ValueError, TypeError):
            price = 0.0

        cat_id = None
        if cat_name:
            if cat_name.lower() in categories_cache:
                cat_id = categories_cache[cat_name.lower()]
            else:
                new_cat = TestCategory(
                    tenant_id=tenant_id, name=cat_name, description="Auto-imported"
                )
                db.add(new_cat)
                await db.flush()
                categories_cache[cat_name.lower()] = new_cat.id
                cat_id = new_cat.id

        if not code:
            raise HTTPException(
                status_code=400,
                detail=f"Mandatory 'code' is missing for test: '{name}'. Please ensure every row has a unique test code.",
            )

        # Skip duplicate test codes
        if code in existing_codes:
            records_skipped += 1
            continue

        test = MedicalTest(
            tenant_id=tenant_id,
            name=name,
            code=code,
            category_id=cat_id,
            price=price,
            description="Imported in bulk",
        )
        db.add(test)
        existing_codes.add(code)  # Track newly added codes within this batch
        records_added += 1

    await db.commit()
    logger.info(f"Bulk upload complete for {safe_name}: {records_added} added, {records_skipped} skipped.")
    return {"message": f"Import complete: {records_added} added, {records_skipped} skipped (duplicates)."}


# ── Test Categories ───────────────────────────────────────────

@router.get("/categories", response_model=list[TestCategoryResponse], summary="List test categories")
async def list_categories(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(TestCategory)
        .where(TestCategory.tenant_id == tenant_id)
        .order_by(TestCategory.name)
    )
    return [TestCategoryResponse.model_validate(c) for c in result.scalars().all()]


@router.post(
    "/categories",
    response_model=TestCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
)
async def create_category(
    data: TestCategoryCreate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    # Check uniqueness
    existing = await db.execute(
        select(TestCategory).where(
            TestCategory.tenant_id == tenant_id,
            TestCategory.name == data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this name already exists",
        )

    category = TestCategory(tenant_id=tenant_id, **data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return TestCategoryResponse.model_validate(category)


@router.put("/categories/{category_id}", response_model=TestCategoryResponse, summary="Update category")
async def update_category(
    category_id: UUID,
    data: TestCategoryUpdate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(TestCategory).where(
            TestCategory.id == category_id,
            TestCategory.tenant_id == tenant_id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return TestCategoryResponse.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete category")
async def delete_category(
    category_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(TestCategory).where(
            TestCategory.id == category_id,
            TestCategory.tenant_id == tenant_id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    await db.delete(category)
    await db.commit()


# ── Medical Tests ─────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse, summary="List medical tests")
async def list_tests(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    category_id: UUID = Query(None),
    active_only: bool = Query(True),
):
    query = select(MedicalTest).options(selectinload(MedicalTest.category)).where(
        MedicalTest.tenant_id == tenant_id
    )
    count_query = select(func.count(MedicalTest.id)).where(
        MedicalTest.tenant_id == tenant_id
    )

    if active_only:
        query = query.where(MedicalTest.is_active == True)  # noqa: E712
        count_query = count_query.where(MedicalTest.is_active == True)  # noqa: E712

    if search:
        search_filter = or_(
            MedicalTest.name.ilike(f"%{search}%"),
            MedicalTest.code.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if category_id:
        query = query.where(MedicalTest.category_id == category_id)
        count_query = count_query.where(MedicalTest.category_id == category_id)

    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(MedicalTest.name).offset(offset).limit(page_size)
    )
    tests = result.scalars().all()

    return PaginatedResponse(
        items=[MedicalTestResponse.model_validate(t) for t in tests],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{test_id}", response_model=MedicalTestResponse, summary="Get test details")
async def get_test(
    test_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(MedicalTest)
        .options(selectinload(MedicalTest.category))
        .where(MedicalTest.id == test_id, MedicalTest.tenant_id == tenant_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    return MedicalTestResponse.model_validate(test)


@router.post("", response_model=MedicalTestResponse, status_code=status.HTTP_201_CREATED, summary="Add medical test")
async def create_test(
    data: MedicalTestCreate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    test = MedicalTest(tenant_id=tenant_id, **data.model_dump())
    db.add(test)
    await db.commit()
    await db.refresh(test)

    # Reload with category
    result = await db.execute(
        select(MedicalTest)
        .options(selectinload(MedicalTest.category))
        .where(MedicalTest.id == test.id)
    )
    test = result.scalar_one()
    return MedicalTestResponse.model_validate(test)


@router.put("/{test_id}", response_model=MedicalTestResponse, summary="Update medical test")
async def update_test(
    test_id: UUID,
    data: MedicalTestUpdate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(MedicalTest).where(
            MedicalTest.id == test_id, MedicalTest.tenant_id == tenant_id
        )
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(test, key, value)

    await db.commit()
    await db.refresh(test)
    return MedicalTestResponse.model_validate(test)


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete medical test")
async def delete_test(
    test_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(MedicalTest).where(
            MedicalTest.id == test_id, MedicalTest.tenant_id == tenant_id
        )
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    await db.delete(test)
    await db.commit()

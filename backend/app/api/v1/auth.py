"""
Authentication routes — register, login, refresh, profile.
"""


import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Body
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.deps import CurrentUser, DBSession
from app.models.tenant import Tenant
from app.models.user import User
from app.models.token_blocklist import TokenBlocklist
from app.schemas.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.email_service import send_welcome_email
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])






def _slugify(name: str) -> str:
    """Convert a clinic name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:100]


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new clinic",
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    background_tasks: BackgroundTasks,
    data: RegisterRequest = Body(...),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Register a new clinic/hospital. Creates a tenant and an admin user.
    Returns JWT tokens for immediate authentication.
    """
    # Check if admin email already exists
    existing = await db.execute(
        select(User).where(User.email == data.admin_email).limit(1)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Generate unique slug
    base_slug = _slugify(data.clinic_name)
    slug = base_slug
    counter = 1
    while True:
        existing_tenant = await db.execute(
            select(Tenant).where(Tenant.slug == slug).limit(1)
        )
        if not existing_tenant.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create tenant
    tenant = Tenant(
        name=data.clinic_name,
        slug=slug,
        email=data.clinic_email,
        phone=data.clinic_phone,
        address=data.clinic_address,
    )
    db.add(tenant)
    await db.flush()

    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=data.admin_email,
        password_hash=hash_password(data.admin_password),
        full_name=data.admin_name,
        role="admin",
        is_approved=tenant.is_approved
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = create_access_token(user.id, tenant.id, user.role)
    refresh_token = create_refresh_token(user.id, tenant.id)

    # Send welcome email (background task)
    background_tasks.add_task(send_welcome_email, tenant.name, user.full_name, user.email)

    # Fetch tenant modules
    tenant_modules = None
    if user.tenant_id:
        t_res = await db.execute(select(Tenant.modules).where(Tenant.id == user.tenant_id))
        tenant_modules = t_res.scalar_one_or_none()
    
    user_data = UserResponse.model_validate(user).model_dump()
    user_data["tenant_modules"] = tenant_modules

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_data,
    )


@router.post("/login", summary="User login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: LoginRequest = Body(...), 
    db: AsyncSession = Depends(get_async_session)
):
    """Authenticate with email and password. Returns JWT tokens as HttpOnly cookies and in JSON body."""
    result = await db.execute(
        select(User).where(User.email == data.email, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user.id, user.tenant_id, user.role)
    refresh_token = create_refresh_token(user.id, user.tenant_id)

    # Fetch tenant modules
    tenant_modules = None
    if user.tenant_id:
        t_res = await db.execute(select(Tenant.modules).where(Tenant.id == user.tenant_id))
        tenant_modules = t_res.scalar_one_or_none()

    user_data = UserResponse.model_validate(user).model_dump(mode='json')
    user_data["tenant_modules"] = tenant_modules

    from app.core.config import get_settings
    _settings = get_settings()

    response = JSONResponse(content={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_data,
    })

    # Set HttpOnly cookies — immune to XSS token theft
    _is_secure = _settings.APP_ENV != "development"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_is_secure,
        samesite="lax",
        max_age=_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=_is_secure,
        samesite="lax",
        max_age=_settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",  # Only sent to auth endpoints
    )

    return response

@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(data: RefreshRequest, db: DBSession):
    """Get a new access token using a refresh token."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token structure",
        )

    # Check if token is blocklisted
    is_blocklisted = await db.execute(select(TokenBlocklist).where(TokenBlocklist.jti == jti))
    if is_blocklisted.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    user_id = UUID(payload["sub"])
    
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Blocklist the consumed refresh token so it cannot be reused (token rotation)
    import datetime
    exp_timestamp = payload.get("exp")
    if exp_timestamp:
        expires_at = datetime.datetime.fromtimestamp(exp_timestamp, tz=datetime.timezone.utc)
        db.add(TokenBlocklist(jti=jti, expires_at=expires_at))
        await db.flush()

    access_token = create_access_token(user.id, user.tenant_id, user.role)
    new_refresh_token = create_refresh_token(user.id, user.tenant_id)

    # Fetch tenant modules
    tenant_modules = None
    if user.tenant_id:
        t_res = await db.execute(select(Tenant.modules).where(Tenant.id == user.tenant_id))
        tenant_modules = t_res.scalar_one_or_none()

    user_data = UserResponse.model_validate(user).model_dump()
    user_data["tenant_modules"] = tenant_modules

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=user_data,
    )


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(current_user: CurrentUser, db: DBSession):
    """Return the profile of the currently authenticated user including module permissions."""
    tenant_modules = None
    if current_user.tenant_id:
        t_res = await db.execute(select(Tenant.modules).where(Tenant.id == current_user.tenant_id))
        tenant_modules = t_res.scalar_one_or_none()

    # We manually patch the pydantic model with extra fields
    user_data = UserResponse.model_validate(current_user).model_dump()
    user_data["tenant_modules"] = tenant_modules
    return user_data

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
bearer_scheme = HTTPBearer(auto_error=False)

@router.post("/logout", summary="Logout user and invalidate token")
async def logout(
    request: Request,
    db: DBSession,
    data: RefreshRequest = Body(None),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """
    Invalidates the current refresh token and the provided access token by adding their JTIs to the blocklist.
    Also clears HttpOnly auth cookies.
    """
    import datetime

    # Get refresh token from body OR cookie
    rt = None
    if data and data.refresh_token:
        rt = data.refresh_token
    elif request.cookies.get("refresh_token"):
        rt = request.cookies.get("refresh_token")

    # 1. Blocklist Refresh Token
    if rt:
        refresh_payload = decode_token(rt)
        if refresh_payload and refresh_payload.get("jti"):
            exp_timestamp = refresh_payload.get("exp")
            if exp_timestamp:
                expires_at = datetime.datetime.fromtimestamp(exp_timestamp, tz=datetime.timezone.utc)
                db.add(TokenBlocklist(jti=refresh_payload["jti"], expires_at=expires_at))

    # 2. Blocklist Access Token (from header or cookie)
    access_tok = None
    if credentials and credentials.credentials:
        access_tok = credentials.credentials
    elif request.cookies.get("access_token"):
        access_tok = request.cookies.get("access_token")

    if access_tok:
        access_payload = decode_token(access_tok)
        if access_payload and access_payload.get("jti"):
            exp_timestamp = access_payload.get("exp")
            if exp_timestamp:
                expires_at = datetime.datetime.fromtimestamp(exp_timestamp, tz=datetime.timezone.utc)
                
                # Check for existing to avoid PrimaryKey integrity error if somehow same
                existing = await db.execute(select(TokenBlocklist).where(TokenBlocklist.jti == access_payload["jti"]))
                if not existing.scalar_one_or_none():
                    db.add(TokenBlocklist(jti=access_payload["jti"], expires_at=expires_at))

    await db.commit()

    # Clear HttpOnly cookies
    response = JSONResponse(content={"message": "Successfully logged out"})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    return response

"""Authentication endpoints: register, login, refresh, logout, me."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import authenticate
from app.services.auth_service import register as do_register

logger = logging.getLogger(__name__)


def _s(value: object) -> str:
    """Sanitize a value for log output — strips CR/LF to prevent log injection."""
    return str(value).replace("\r", " ").replace("\n", " ")


router = APIRouter(prefix="/auth", tags=["Auth"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


async def _set_user_region(user, request: Request, db: AsyncSession):
    """Detect and store user region from IP address."""
    try:
        from app.services.region_service import resolve_user_region

        await resolve_user_region(user, request, db)
        await db.commit()
    except Exception:  # noqa: S110
        pass  # non-critical, default to US


def _set_refresh_cookie(
    response: Response, token: str, *, persistent: bool = True
) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400 if persistent else None,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


# ── Register ────────────────────────────────────


@router.post("/register", response_model=TokenResponse)
async def register(
    req: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Create a new account and return tokens."""
    logger.info(
        "REGISTER attempt email=%s display_name=%s", _s(req.email), _s(req.display_name)
    )
    try:
        user = await do_register(db, req.email, req.password, req.display_name)
    except HTTPException:
        logger.warning(
            "REGISTER failed email=%s (duplicate or validation error)", _s(req.email)
        )
        raise
    except Exception:
        logger.exception("REGISTER unexpected error email=%s", _s(req.email))
        raise
    # Detect region from IP
    await _set_user_region(user, request, db)
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh)
    logger.info("REGISTER success user=%s email=%s", user.id, user.email)
    return TokenResponse(access_token=access)


# ── Login ───────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email + password and return tokens."""
    logger.info("LOGIN attempt email=%s", _s(req.email))
    user = await authenticate(db, req.email, req.password)
    # Detect region from IP if not set yet
    if not user.region:
        await _set_user_region(user, request, db)
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh, persistent=req.remember_me)
    return TokenResponse(access_token=access)


# ── Refresh ─────────────────────────────────────


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """Exchange a valid refresh token (from cookie) for a new access token."""
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        payload = decode_token(token)
    except (JWTError, ValueError) as e:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=401, detail="Refresh token expired or invalid"
        ) from e

    if payload.get("type") != "refresh":
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = uuid.UUID(payload.get("sub"))
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Issue new token pair
    new_access = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=new_access)


# ── Logout ──────────────────────────────────────


@router.post("/logout")
async def logout(response: Response, user: User = Depends(get_current_user)):
    """Clear the refresh token cookie."""
    _clear_refresh_cookie(response)
    return {"detail": "Logged out"}


# ── Me ─────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Return the current authenticated user's profile."""
    from app.services.pass_service import get_subscription_tier

    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        subscription_tier=await get_subscription_tier(user.id, db),
    )

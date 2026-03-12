"""Business logic for authentication: register, login, Google OAuth."""

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.models import User


class AuthService:

    @staticmethod
    async def register(db: AsyncSession, email: str, password: str, display_name: str) -> User:
        """Create a new local user. Raises 409 if email already taken."""
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        user = User(
            email=email,
            hashed_password=hash_password(password),
            display_name=display_name,
            auth_provider="local",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> User:
        """Verify email + password. Raises 401 on failure."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

        return user

    @staticmethod
    async def google_auth(db: AsyncSession, code: str) -> User:
        """Exchange Google auth code for tokens, upsert user. Raises on failure."""
        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange Google auth code")

            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token from Google")

            # Fetch user info
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch Google user info")

            userinfo = userinfo_resp.json()

        google_id = userinfo.get("id")
        email = userinfo.get("email")
        name = userinfo.get("name", email.split("@")[0] if email else "User")

        if not google_id or not email:
            raise HTTPException(status_code=400, detail="Incomplete Google profile")

        # Try to find existing user by google_id
        result = await db.execute(select(User).where(User.google_id == google_id))
        user = result.scalar_one_or_none()

        if not user:
            # Try by email (user may have registered locally first)
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if user:
                # Link Google to existing account
                user.google_id = google_id
                if user.auth_provider == "local":
                    user.auth_provider = "local+google"
            else:
                # Create new Google user
                user = User(
                    email=email,
                    display_name=name,
                    auth_provider="google",
                    google_id=google_id,
                )
                db.add(user)

        await db.commit()
        await db.refresh(user)
        return user

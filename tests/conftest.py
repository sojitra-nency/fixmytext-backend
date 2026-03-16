"""Test configuration — ensure DB tables exist before tests run."""

import asyncio
import pytest
from app.db.session import engine, Base
from app.db.models import User, UserPreferences, UserGamification, UserTemplate  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables before the test session starts."""
    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_create())

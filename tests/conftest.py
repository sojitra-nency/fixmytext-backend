"""Test configuration — ensure DB tables exist before tests run."""

import asyncio

import pytest

from app.db.models import User, UserGamification, UserPreferences, UserTemplate  # noqa: F401
from app.db.session import Base, engine


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables before the test session starts."""

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create())

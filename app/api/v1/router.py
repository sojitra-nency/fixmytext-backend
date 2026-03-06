"""
API v1 router — aggregates all endpoint sub-routers.

Add new feature routers here as the app grows.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import text

api_router = APIRouter()

api_router.include_router(text.router)

# Future routers (uncomment as you add them):
# from app.api.v1.endpoints import auth, users
# api_router.include_router(auth.router)
# api_router.include_router(users.router)

from fastapi import APIRouter

from app.api.endpoints import health, repositories

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(repositories.router, tags=["repositories"])

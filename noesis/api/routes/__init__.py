from fastapi import APIRouter

from noesis.api.routes.positions import router as positions_router

api_router = APIRouter()
api_router.include_router(positions_router)

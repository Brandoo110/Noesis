from fastapi import APIRouter

from noesis.api.routes.entities import router as entities_router
from noesis.api.routes.positions import router as positions_router
from noesis.api.routes.runs import router as runs_router
from noesis.api.routes.theses import router as theses_router

api_router = APIRouter()
api_router.include_router(entities_router)
api_router.include_router(positions_router)
api_router.include_router(runs_router)
api_router.include_router(theses_router)

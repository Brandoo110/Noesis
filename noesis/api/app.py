from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from noesis.api.routes import api_router
from noesis.graph.errors import (
    EntityResolveError,
    GroundingError,
    NoesisError,
    ResearchNodeError,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Noesis API")
    app.include_router(api_router)
    _register_exception_handlers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        EntityResolveError,
        _domain_handler(422),
    )
    app.add_exception_handler(
        GroundingError,
        _domain_handler(409),
    )
    app.add_exception_handler(
        ResearchNodeError,
        _domain_handler(502),
    )
    app.add_exception_handler(Exception, _unhandled_exception_handler)


def _domain_handler(status_code: int) -> Callable[[Request, NoesisError], JSONResponse]:
    async def handle(request: Request, exc: NoesisError) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "reason": exc.reason,
            },
        )

    return handle


async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "internal server error",
            "reason": None,
        },
    )


app = create_app()

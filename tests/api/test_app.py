from fastapi.testclient import TestClient

from noesis.api.app import create_app
from noesis.graph.errors import (
    EntityResolveError,
    GroundingError,
    ResearchNodeError,
)


def test_app_maps_domain_exceptions_to_stable_errors() -> None:
    app = create_app()

    @app.get("/entity")
    def entity_error() -> None:
        raise EntityResolveError("cannot resolve", reason="ambiguous_symbol")

    @app.get("/grounding")
    def grounding_error() -> None:
        raise GroundingError("missing evidence", reason="no_evidence")

    @app.get("/research")
    def research_error() -> None:
        raise ResearchNodeError("node failed", reason="node_failed")

    client = TestClient(app, raise_server_exceptions=False)

    entity = client.get("/entity")
    grounding = client.get("/grounding")
    research = client.get("/research")

    assert entity.status_code == 422
    assert entity.json() == {
        "error": "EntityResolveError",
        "message": "cannot resolve",
        "reason": "ambiguous_symbol",
    }
    assert grounding.status_code == 409
    assert grounding.json()["error"] == "GroundingError"
    assert research.status_code == 502
    assert research.json()["reason"] == "node_failed"


def test_app_maps_unhandled_exception_to_500() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("unexpected")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": "InternalServerError",
        "message": "internal server error",
        "reason": None,
    }

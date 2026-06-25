import pytest

from noesis.graph.errors import (
    EntityResolveError,
    GroundingError,
    IngestError,
    LLMUnavailableError,
    NoesisError,
    ResearchNodeError,
)


DOMAIN_ERRORS = [
    EntityResolveError,
    IngestError,
    GroundingError,
    ResearchNodeError,
    LLMUnavailableError,
]


def test_noesis_error_carries_message_and_reason() -> None:
    error = NoesisError("failed", reason="missing input")

    assert isinstance(error, Exception)
    assert str(error) == "failed"
    assert error.message == "failed"
    assert error.reason == "missing input"


@pytest.mark.parametrize("error_cls", DOMAIN_ERRORS)
def test_domain_errors_extend_noesis_error(error_cls: type[NoesisError]) -> None:
    error = error_cls("failed", reason="bad dependency")

    assert isinstance(error, NoesisError)
    assert isinstance(error, Exception)
    assert error.message == "failed"
    assert error.reason == "bad dependency"

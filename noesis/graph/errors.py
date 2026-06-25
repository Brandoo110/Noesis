class NoesisError(Exception):
    def __init__(self, message: str, *, reason: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.reason = reason


class EntityResolveError(NoesisError):
    pass


class IngestError(NoesisError):
    pass


class GroundingError(NoesisError):
    pass


class ResearchNodeError(NoesisError):
    pass


class LLMUnavailableError(NoesisError):
    pass

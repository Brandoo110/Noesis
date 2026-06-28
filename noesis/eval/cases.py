from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    symbol: str
    market: str
    name: str


EVAL_CASES: tuple[EvalCase, ...] = (
    EvalCase(symbol="AAPL", market="US", name="Apple Inc."),
    EvalCase(symbol="MSFT", market="US", name="Microsoft Corporation"),
    EvalCase(symbol="SONY", market="US", name="Sony Group Corporation"),
)

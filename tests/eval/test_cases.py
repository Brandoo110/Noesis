from noesis.eval.cases import EVAL_CASES


def test_eval_cases_include_core_symbols_with_required_fields() -> None:
    symbols = {case.symbol for case in EVAL_CASES}

    assert {"AAPL", "MSFT", "SONY"}.issubset(symbols)
    for case in EVAL_CASES:
        assert case.symbol
        assert case.market
        assert case.name

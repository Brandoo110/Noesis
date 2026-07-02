from noesis.eval.cases import EVAL_CASES


def test_eval_cases_include_core_symbols_with_required_fields() -> None:
    symbols = {case.symbol for case in EVAL_CASES}
    task_types = {case.task_type for case in EVAL_CASES}

    assert {"AAPL", "MSFT", "SONY"}.issubset(symbols)
    assert len(EVAL_CASES) >= 20
    assert {
        "company_profile",
        "supply_chain",
        "competitor",
        "risk",
        "financial_news",
    }.issubset(task_types)
    for case in EVAL_CASES:
        assert case.symbol
        assert case.market
        assert case.name
        assert case.task_type

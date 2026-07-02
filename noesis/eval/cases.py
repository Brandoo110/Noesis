from dataclasses import dataclass
from typing import Literal

EvalTaskType = Literal[
    "company_profile",
    "supply_chain",
    "competitor",
    "risk",
    "financial_news",
]


@dataclass(frozen=True)
class EvalCase:
    symbol: str
    market: str
    name: str
    task_type: EvalTaskType = "company_profile"


EVAL_CASES: tuple[EvalCase, ...] = (
    EvalCase(symbol="AAPL", market="US", name="Apple Inc.", task_type="company_profile"),
    EvalCase(symbol="MSFT", market="US", name="Microsoft Corporation", task_type="company_profile"),
    EvalCase(symbol="SONY", market="US", name="Sony Group Corporation", task_type="company_profile"),
    EvalCase(symbol="NVDA", market="US", name="NVIDIA Corporation", task_type="supply_chain"),
    EvalCase(symbol="TSM", market="US", name="Taiwan Semiconductor Manufacturing", task_type="supply_chain"),
    EvalCase(symbol="ASML", market="US", name="ASML Holding", task_type="supply_chain"),
    EvalCase(symbol="TM", market="US", name="Toyota Motor Corporation", task_type="supply_chain"),
    EvalCase(symbol="AMD", market="US", name="Advanced Micro Devices", task_type="competitor"),
    EvalCase(symbol="GOOGL", market="US", name="Alphabet Inc.", task_type="competitor"),
    EvalCase(symbol="NFLX", market="US", name="Netflix Inc.", task_type="competitor"),
    EvalCase(symbol="TSLA", market="US", name="Tesla Inc.", task_type="risk"),
    EvalCase(symbol="META", market="US", name="Meta Platforms", task_type="risk"),
    EvalCase(symbol="DIS", market="US", name="The Walt Disney Company", task_type="risk"),
    EvalCase(symbol="BABA", market="US", name="Alibaba Group Holding", task_type="risk"),
    EvalCase(symbol="AMZN", market="US", name="Amazon.com Inc.", task_type="financial_news"),
    EvalCase(symbol="JPM", market="US", name="JPMorgan Chase", task_type="financial_news"),
    EvalCase(symbol="XOM", market="US", name="Exxon Mobil", task_type="financial_news"),
    EvalCase(symbol="PFE", market="US", name="Pfizer Inc.", task_type="financial_news"),
    EvalCase(symbol="NKE", market="US", name="Nike Inc.", task_type="company_profile"),
    EvalCase(symbol="COST", market="US", name="Costco Wholesale", task_type="financial_news"),
)

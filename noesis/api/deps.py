from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
import sqlite3

from fastapi import Depends

from noesis.config.settings import Settings, get_settings
from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.graph.runner import build_graph_deps
from noesis.graph.state import GraphDeps
from noesis.tools.llm.router import LLMRouter
from noesis.tools.search.tavily import TavilySearchAdapter


def get_graph_deps(settings: Settings = Depends(get_settings)) -> Iterator[GraphDeps]:
    _ensure_parent(settings.db_path)
    _ensure_dir(settings.chroma_dir)
    conn = connect(settings.db_path)
    checkpoint_conn = sqlite3.connect(
        _checkpoint_path(settings.db_path),
        check_same_thread=False,
    )
    try:
        migrate(conn)
        yield build_graph_deps(
            conn=conn,
            checkpoint_conn=checkpoint_conn,
            chroma_dir=settings.chroma_dir,
            search=TavilySearchAdapter(settings.tavily_api_key),
            llm=LLMRouter.from_env(),
            now=_utc_now,
        )
    finally:
        checkpoint_conn.close()
        conn.close()


def _checkpoint_path(db_path: str) -> str:
    path = Path(db_path)
    if path.suffix:
        return str(path.with_suffix(f"{path.suffix}.checkpoints"))
    return f"{db_path}.checkpoints"


def _ensure_parent(path: str) -> None:
    parent = Path(path).expanduser().parent
    if str(parent) != ".":
        parent.mkdir(parents=True, exist_ok=True)


def _ensure_dir(path: str) -> None:
    Path(path).expanduser().mkdir(parents=True, exist_ok=True)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

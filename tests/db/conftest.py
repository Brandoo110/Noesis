from collections.abc import Iterator
from pathlib import Path
from sqlite3 import Connection

import pytest

from noesis.db.connection import connect
from noesis.db.migrate import migrate


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "noesis.db"


@pytest.fixture
def db(db_path: Path) -> Iterator[Connection]:
    conn = connect(db_path)
    migrate(conn)
    try:
        yield conn
    finally:
        conn.close()

from pathlib import Path
import sqlite3


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def migrate(conn: sqlite3.Connection) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()

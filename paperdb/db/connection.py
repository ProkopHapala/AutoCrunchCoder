"""SQLite connection management — WAL mode, foreign keys ON, single connection per process."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from paperdb.paths import get_db_path

_connection: sqlite3.Connection | None = None

def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Get or create the singleton SQLite connection.

    - PRAGMA foreign_keys=ON
    - PRAGMA journal_mode=WAL
    - Row factory set to sqlite3.Row for dict-like access
    """
    global _connection
    if _connection is not None and db_path is None:
        return _connection
    path = str(db_path) if db_path is not None else str(get_db_path())
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    if db_path is None:
        _connection = conn
    return conn

def close_connection():
    """Close the singleton connection if open."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None

@contextmanager
def db_transaction(conn: sqlite3.Connection | None = None):
    """Context manager for a transaction. Commits on success, rolls back on exception."""
    own_conn = conn is None
    if own_conn: conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    # don't close if we didn't create it

def init_schema(conn: sqlite3.Connection | None = None):
    """Execute schema.sql to create all tables if they don't exist."""
    own_conn = conn is None
    if own_conn: conn = get_connection()
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()

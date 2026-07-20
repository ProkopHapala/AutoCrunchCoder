"""SQLite connection management — WAL mode, foreign keys ON, durable writes."""
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
    # Autocommit makes individual Repository calls durable for short-lived CLI processes.
    # Multi-statement operations use db_transaction() explicitly.
    conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    if db_path is None:
        _connection = conn
    return conn

def close_connection(conn: sqlite3.Connection | None = None):
    """Close a supplied connection, or the default singleton when omitted."""
    global _connection
    target = conn if conn is not None else _connection
    if target is not None:
        target.close()
    if target is _connection:
        _connection = None

@contextmanager
def db_transaction(conn: sqlite3.Connection | None = None):
    """Context manager for a transaction. Commits on success, rolls back on exception."""
    if conn is None: conn = get_connection()
    nested = conn.in_transaction
    if not nested: conn.execute("BEGIN")
    try:
        yield conn
        if not nested: conn.commit()
    except Exception:
        if not nested: conn.rollback()
        raise

def init_schema(conn: sqlite3.Connection | None = None):
    """Execute schema.sql to create all tables if they don't exist."""
    own_conn = conn is None
    if own_conn: conn = get_connection()
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        conn.executescript(f.read())

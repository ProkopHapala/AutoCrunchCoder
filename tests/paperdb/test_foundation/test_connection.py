"""Test SQLite connection: WAL mode, FK enforcement."""
import sqlite3
import tempfile
import os
from pathlib import Path
from paperdb.db.connection import get_connection, init_schema, close_connection

def test_wal_mode():
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal", f"Expected WAL, got {mode}"
        conn.close()

def test_foreign_keys_on():
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1, f"Expected FK=1, got {fk}"
        conn.close()

def test_fk_enforcement():
    """Inserting a paper_file with non-existent paper_id should fail."""
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        init_schema(conn)
        try:
            conn.execute("INSERT INTO paper_files (paper_id, path) VALUES (999, '/fake.pdf')")
            assert False, "FK violation should have raised"
        except sqlite3.IntegrityError:
            pass  # expected
        conn.close()

def test_row_factory():
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        assert conn.row_factory == sqlite3.Row
        conn.close()

"""Test schema: all tables exist, FTS triggers work."""
import sqlite3
import tempfile
import os
from paperdb.db.connection import get_connection, init_schema, close_connection

EXPECTED_TABLES = {
    "papers", "paper_files", "processing_runs", "search_units",
    "tags", "tag_aliases", "paper_tags", "equations", "equation_variables",
    "methods", "method_equations", "summaries", "topics", "topic_papers",
    "topic_overviews", "context_packs", "citations"
}

def test_all_tables_exist():
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        init_schema(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {r[0] for r in rows}
        for t in EXPECTED_TABLES:
            assert t in table_names, f"Missing table: {t}"
        conn.close()

def test_fts_table_exists():
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        init_schema(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='search_units_fts'").fetchall()
        assert len(rows) == 1, "search_units_fts not found"
        conn.close()

def test_fts_trigger_insert():
    """Inserting a search_unit should auto-populate FTS."""
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        init_schema(conn)
        # need a paper first
        conn.execute("INSERT INTO papers (paper_key) VALUES ('Test_2020_Foo')")
        pid = conn.execute("SELECT id FROM papers WHERE paper_key='Test_2020_Foo'").fetchone()[0]
        conn.execute("INSERT INTO search_units (paper_id, content, section_path) VALUES (?, 'Gauss-Seidel iteration', '3.1')", (pid,))
        conn.commit()
        # query FTS
        rows = conn.execute("SELECT content FROM search_units_fts WHERE search_units_fts MATCH 'Gauss'").fetchall()
        assert len(rows) == 1, f"Expected 1 FTS match, got {len(rows)}"
        assert 'Gauss-Seidel' in rows[0][0]
        conn.close()

def test_fts_trigger_delete():
    """Deleting a search_unit should remove it from FTS."""
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        init_schema(conn)
        conn.execute("INSERT INTO papers (paper_key) VALUES ('Test_2020_Bar')")
        pid = conn.execute("SELECT id FROM papers WHERE paper_key='Test_2020_Bar'").fetchone()[0]
        conn.execute("INSERT INTO search_units (paper_id, content) VALUES (?, 'Ewald summation')", (pid,))
        conn.commit()
        conn.execute("DELETE FROM search_units WHERE paper_id = ?", (pid,))
        conn.commit()
        rows = conn.execute("SELECT content FROM search_units_fts WHERE search_units_fts MATCH 'Ewald'").fetchall()
        assert len(rows) == 0, f"FTS should be empty after delete, got {len(rows)}"
        conn.close()

def test_triggers_exist():
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        init_schema(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
        names = {r[0] for r in rows}
        assert "search_units_ai" in names
        assert "search_units_ad" in names
        assert "search_units_au" in names
        conn.close()

def test_preferred_file_unique_index():
    """Only one preferred file per paper."""
    close_connection()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "test.db")
        conn = get_connection(db)
        init_schema(conn)
        conn.execute("INSERT INTO papers (paper_key) VALUES ('Test_2020_Idx')")
        pid = conn.execute("SELECT id FROM papers WHERE paper_key='Test_2020_Idx'").fetchone()[0]
        conn.execute("INSERT INTO paper_files (paper_id, path, is_preferred) VALUES (?, '/a.pdf', 1)", (pid,))
        try:
            conn.execute("INSERT INTO paper_files (paper_id, path, is_preferred) VALUES (?, '/b.pdf', 1)", (pid,))
            conn.commit()
            assert False, "Should not allow two preferred files"
        except sqlite3.IntegrityError:
            pass
        conn.close()

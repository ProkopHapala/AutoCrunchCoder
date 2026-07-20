"""Mock Repository for testing Task 2 (identity/migration) without Task 1.

Implements the same interface as paperdb.db.repository.Repository using in-memory SQLite.
This allows tests to run before Task 1 is complete.
"""

import sqlite3
import os
import re

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE papers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_key TEXT NOT NULL UNIQUE,
    doi TEXT UNIQUE,
    arxiv_id TEXT,
    title TEXT,
    authors_text TEXT,
    year INTEGER,
    journal TEXT,
    abstract TEXT,
    keywords TEXT,
    essence TEXT,
    markdown_path TEXT,
    json_path TEXT,
    bibtex_path TEXT,
    bibtex_text TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE paper_files(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    path TEXT NOT NULL UNIQUE,
    file_role TEXT,
    version_label TEXT,
    file_size INTEGER,
    modified_time REAL,
    sha256 TEXT,
    exists_now INTEGER DEFAULT 1,
    is_preferred INTEGER DEFAULT 0,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX one_preferred_file_per_paper ON paper_files(paper_id) WHERE is_preferred = 1;
CREATE INDEX idx_paper_files_paper ON paper_files(paper_id);
CREATE INDEX idx_paper_files_sha256 ON paper_files(sha256);

CREATE TABLE search_units(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER,
    unit_type TEXT,
    source_type TEXT,
    source_id INTEGER,
    section_path TEXT,
    page_from INTEGER,
    page_to INTEGER,
    content TEXT
);

CREATE TABLE processing_runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    operation TEXT,
    backend TEXT,
    backend_version TEXT,
    model_name TEXT,
    prompt_version TEXT,
    configuration_json TEXT,
    config_hash TEXT,
    source_file_id INTEGER,
    input_sha256 TEXT,
    output_path TEXT,
    supersedes_run_id INTEGER,
    status TEXT,
    started_at TEXT,
    finished_at TEXT,
    message TEXT
);

CREATE TABLE tags(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,
    UNIQUE(canonical_name, category)
);

CREATE TABLE tag_aliases(
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    UNIQUE(tag_id, normalized_alias)
);

CREATE TABLE paper_tags(
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    source TEXT,
    run_id INTEGER,
    confidence REAL,
    raw_name TEXT,
    PRIMARY KEY(paper_id, tag_id, source, run_id)
);

CREATE TABLE summaries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER,
    model_name TEXT,
    prompt_version TEXT,
    content TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);
"""

class MockRepository:
    """In-memory SQLite implementation of the Repository interface for testing."""

    def __init__(self, db_path=':memory:'):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def _row_to_dict(self, row):
        return dict(row) if row is not None else None

    # --- Papers ---

    def upsert_paper(self, paper_key=None, doi=None, arxiv_id=None, title=None,
                     authors_text=None, year=None, journal=None, abstract=None,
                     keywords=None, essence=None, **kwargs):
        # Check if paper exists by key
        cur = self.conn.execute("SELECT id FROM papers WHERE paper_key = ?", (paper_key,))
        row = cur.fetchone()
        if row:
            pid = row['id']
            self.conn.execute("""UPDATE papers SET doi=?, arxiv_id=?, title=?, authors_text=?, year=?, 
                journal=?, abstract=?, keywords=?, essence=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (doi, arxiv_id, title, authors_text, year, journal, abstract, keywords, essence, pid))
            self.conn.commit()
            return pid
        cur = self.conn.execute("""INSERT INTO papers (paper_key, doi, arxiv_id, title, authors_text, year, journal, abstract, keywords, essence)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (paper_key, doi, arxiv_id, title, authors_text, year, journal, abstract, keywords, essence))
        self.conn.commit()
        return cur.lastrowid

    def get_paper_by_key(self, key):
        cur = self.conn.execute("SELECT * FROM papers WHERE paper_key = ?", (key,))
        return self._row_to_dict(cur.fetchone())

    def get_paper_by_doi(self, doi):
        cur = self.conn.execute("SELECT * FROM papers WHERE doi = ?", (doi,))
        return self._row_to_dict(cur.fetchone())

    def get_paper(self, paper_id):
        cur = self.conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
        return self._row_to_dict(cur.fetchone())

    def list_papers(self, limit=10000, offset=0):
        cur = self.conn.execute("SELECT * FROM papers LIMIT ? OFFSET ?", (limit, offset))
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def update_paper_paths(self, paper_id, markdown_path=None, json_path=None, bibtex_path=None, **kwargs):
        parts = []
        vals = []
        if markdown_path is not None:
            parts.append("markdown_path = ?")
            vals.append(markdown_path)
        if json_path is not None:
            parts.append("json_path = ?")
            vals.append(json_path)
        if bibtex_path is not None:
            parts.append("bibtex_path = ?")
            vals.append(bibtex_path)
        if not parts:
            return
        vals.append(paper_id)
        self.conn.execute(f"UPDATE papers SET {', '.join(parts)} WHERE id = ?", vals)
        self.conn.commit()

    def set_paper_bibtex(self, paper_id, bibtex_text, bibtex_path=None):
        self.conn.execute("UPDATE papers SET bibtex_text = ? WHERE id = ?", (bibtex_text, paper_id))
        self.conn.commit()

    # --- Files ---

    def add_paper_file(self, paper_id, path, file_role=None, sha256=None, file_size=None, modified_time=None, **kwargs):
        cur = self.conn.execute("""INSERT INTO paper_files (paper_id, path, file_role, sha256, file_size, modified_time)
            VALUES (?,?,?,?,?,?)""", (paper_id, path, file_role, sha256, file_size, modified_time))
        self.conn.commit()
        return cur.lastrowid

    def get_files_for_paper(self, paper_id):
        cur = self.conn.execute("SELECT * FROM paper_files WHERE paper_id = ?", (paper_id,))
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def find_file_by_hash(self, sha256):
        cur = self.conn.execute("SELECT * FROM paper_files WHERE sha256 = ?", (sha256,))
        return [self._row_to_dict(row) for row in cur.fetchall()]

    def find_file_by_path(self, path):
        cur = self.conn.execute("SELECT * FROM paper_files WHERE path = ?", (path,))
        return self._row_to_dict(cur.fetchone())

    def set_preferred_file(self, paper_id, file_id):
        self.conn.execute("UPDATE paper_files SET is_preferred = 0 WHERE paper_id = ?", (paper_id,))
        self.conn.execute("UPDATE paper_files SET is_preferred = 1 WHERE id = ?", (file_id,))
        self.conn.commit()

    def touch_file(self, file_id, sha256=None, file_size=None, modified_time=None):
        self.conn.execute("UPDATE paper_files SET last_seen=CURRENT_TIMESTAMP, exists_now=1, sha256=COALESCE(?,sha256), file_size=COALESCE(?,file_size), modified_time=COALESCE(?,modified_time) WHERE id=?", (sha256, file_size, modified_time, file_id))
        self.conn.commit()

    def move_file(self, file_id, path, file_size=None, modified_time=None):
        self.conn.execute("UPDATE paper_files SET path=?, file_size=COALESCE(?,file_size), modified_time=COALESCE(?,modified_time), exists_now=1 WHERE id=?", (path, file_size, modified_time, file_id))
        self.conn.commit()

    # --- Processing runs ---

    def start_run(self, paper_id, operation, backend=None, backend_version=None, model_name=None,
                  prompt_version=None, configuration_json=None, config_hash=None,
                  source_file_id=None, input_sha256=None, output_path=None, status='running', **kwargs):
        cur = self.conn.execute("""INSERT INTO processing_runs (paper_id, operation, backend, backend_version, model_name,
            prompt_version, configuration_json, config_hash, source_file_id, input_sha256, output_path, status, started_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (paper_id, operation, backend, backend_version, model_name, prompt_version,
             configuration_json, config_hash, source_file_id, input_sha256, output_path, status))
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id, status='ok', message=None, output_path=None):
        self.conn.execute("UPDATE processing_runs SET status=?, finished_at=CURRENT_TIMESTAMP, message=?, output_path=COALESCE(?,output_path) WHERE id=?",
                          (status, message, output_path, run_id))
        self.conn.commit()

    def find_equivalent_run(self, paper_id, operation, config_hash, input_sha256=None, backend=None, model_name=None, prompt_version=None):
        from types import SimpleNamespace
        row = self.conn.execute("""SELECT * FROM processing_runs WHERE paper_id=? AND operation=? AND config_hash=? AND status='ok'
            AND (? IS NULL OR input_sha256=?) AND (? IS NULL OR backend=?) AND (? IS NULL OR model_name=?) AND (? IS NULL OR prompt_version=?) ORDER BY id DESC LIMIT 1""",
            (paper_id, operation, config_hash, input_sha256, input_sha256, backend, backend, model_name, model_name, prompt_version, prompt_version)).fetchone()
        return SimpleNamespace(**dict(row)) if row else None

    def get_current_run(self, paper_id, operation):
        cur = self.conn.execute("""SELECT * FROM processing_runs WHERE paper_id = ? AND operation = ? AND status = 'ok'
            ORDER BY id DESC LIMIT 1""", (paper_id, operation))
        return self._row_to_dict(cur.fetchone())

    # --- Tags ---

    def upsert_tag(self, canonical_name, category):
        cur = self.conn.execute("SELECT id FROM tags WHERE canonical_name = ? AND category = ?", (canonical_name, category))
        row = cur.fetchone()
        if row:
            return row['id']
        cur = self.conn.execute("INSERT INTO tags (canonical_name, category) VALUES (?, ?)", (canonical_name, category))
        self.conn.commit()
        return cur.lastrowid

    def add_alias(self, tag_id, alias, normalized_alias):
        self.conn.execute("INSERT OR IGNORE INTO tag_aliases (tag_id, alias, normalized_alias) VALUES (?, ?, ?)",
                          (tag_id, alias, normalized_alias))
        self.conn.commit()

    def add_paper_tag(self, paper_id, tag_id, source='imported', raw_name=None, confidence=None, run_id=None, **kwargs):
        self.conn.execute("""INSERT OR IGNORE INTO paper_tags (paper_id, tag_id, source, run_id, confidence, raw_name)
            VALUES (?,?,?,?,?,?)""", (paper_id, tag_id, source, run_id, confidence, raw_name))
        self.conn.commit()

    def get_tags_for_paper(self, paper_id):
        cur = self.conn.execute("""SELECT t.* FROM tags t JOIN paper_tags pt ON pt.tag_id = t.id WHERE pt.paper_id = ?""", (paper_id,))
        return [self._row_to_dict(r) for r in cur.fetchall()]

    # --- Summaries ---

    def add_summary(self, paper_id, run_id, model_name=None, prompt_version=None, content=None, **kwargs):
        # Deactivate old summaries
        self.conn.execute("UPDATE summaries SET is_active = 0 WHERE paper_id = ?", (paper_id,))
        cur = self.conn.execute("""INSERT INTO summaries (paper_id, run_id, model_name, prompt_version, content)
            VALUES (?,?,?,?,?)""", (paper_id, run_id, model_name, prompt_version, content))
        self.conn.commit()
        return cur.lastrowid

    def get_active_summary(self, paper_id):
        cur = self.conn.execute("SELECT * FROM summaries WHERE paper_id = ? AND is_active = 1", (paper_id,))
        return self._row_to_dict(cur.fetchone())

    # --- Search units ---

    def replace_search_units(self, paper_id, units):
        self.conn.execute("DELETE FROM search_units WHERE paper_id = ?", (paper_id,))
        for u in units:
            value = u if isinstance(u, dict) else vars(u)
            self.conn.execute("""INSERT INTO search_units (paper_id, run_id, unit_type, source_type, section_path, content)
                VALUES (?,?,?,?,?,?)""", (value['paper_id'], value.get('run_id'), value.get('unit_type'), value.get('source_type'), value.get('section_path'), value.get('content')))
        self.conn.commit()

    def get_search_units_for_paper(self, paper_id):
        cur = self.conn.execute("SELECT * FROM search_units WHERE paper_id = ?", (paper_id,))
        return [self._row_to_dict(r) for r in cur.fetchall()]

    # --- Stats ---

    def get_status_counts(self):
        cur = self.conn.execute("SELECT COUNT(*) as n FROM papers")
        papers = cur.fetchone()['n']
        cur = self.conn.execute("SELECT COUNT(*) as n FROM paper_files")
        files = cur.fetchone()['n']
        cur = self.conn.execute("SELECT COUNT(*) as n FROM tags")
        tags = cur.fetchone()['n']
        return {'papers': papers, 'files': files, 'tags': tags}

    def close(self):
        self.conn.close()

"""Shared mock objects for testing taxonomy & synthesis modules.

Since Task 1 (db/repository.py, db/models.py) is not yet complete,
tests use these mock repository and agent objects that implement
the expected interface via in-memory SQLite.
"""

import sqlite3
import json
from typing import Optional

def make_mock_repo(db_path=":memory:") -> sqlite3.Connection:
    """Create an in-memory SQLite DB with the paperdb schema and return a wrapper."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return MockRepo(conn)

SCHEMA_SQL = """
CREATE TABLE papers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_key TEXT NOT NULL UNIQUE,
    doi TEXT UNIQUE,
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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

CREATE TABLE tag_assertions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    source TEXT,
    run_id INTEGER,
    confidence REAL,
    raw_name TEXT
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

CREATE TABLE methods(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER,
    name TEXT,
    method_type TEXT,
    purpose TEXT,
    complexity TEXT,
    confidence REAL,
    card_json TEXT,
    source_passages_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE method_equations(
    method_id INTEGER NOT NULL REFERENCES methods(id),
    equation_id INTEGER NOT NULL,
    role TEXT,
    PRIMARY KEY(method_id, equation_id, role)
);

CREATE TABLE equations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER,
    latex_raw TEXT,
    latex_normalized TEXT,
    equation_number TEXT,
    section_path TEXT,
    page_number INTEGER,
    bbox_json TEXT,
    context_before TEXT,
    context_after TEXT,
    parser TEXT,
    confidence REAL,
    verification_status TEXT
);

CREATE TABLE topics(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE topic_papers(
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    relevance TEXT,
    match_score REAL,
    PRIMARY KEY(topic_id, paper_id)
);

CREATE TABLE topic_overviews(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    content TEXT,
    original_query TEXT,
    filters_json TEXT,
    comparison_matrix_json TEXT,
    model_name TEXT,
    prompt_version TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
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
"""

class MockRepo:
    """Mock repository wrapping SQLite with the expected interface for Task 6."""

    def __init__(self, conn):
        self.conn = conn

    def _dict(self, row):
        return dict(row) if row else None

    def _dicts(self, rows):
        return [dict(r) for r in rows]

    # --- Tags ---
    def add_tag(self, canonical_name, category):
        cur = self.conn.execute("INSERT OR IGNORE INTO tags (canonical_name, category) VALUES (?, ?)", (canonical_name, category))
        self.conn.commit()
        if cur.lastrowid == 0:
            row = self.conn.execute("SELECT id FROM tags WHERE canonical_name=? AND category=?", (canonical_name, category)).fetchone()
            return row['id'] if row else None
        return cur.lastrowid

    def get_tag_by_name(self, canonical_name, category):
        row = self.conn.execute("SELECT * FROM tags WHERE canonical_name=? AND category=?", (canonical_name, category)).fetchone()
        return self._dict(row)

    def get_tag_by_name_any_category(self, canonical_name):
        rows = self.conn.execute("SELECT * FROM tags WHERE canonical_name=?", (canonical_name,)).fetchall()
        return self._dict(rows[0]) if rows else None

    def get_tag_by_id(self, tag_id):
        row = self.conn.execute("SELECT * FROM tags WHERE id=?", (tag_id,)).fetchone()
        return self._dict(row)

    def get_all_tags(self):
        return self._dicts(self.conn.execute("SELECT * FROM tags").fetchall())

    def delete_tag(self, tag_id):
        self.conn.execute("DELETE FROM tags WHERE id=?", (tag_id,))
        self.conn.commit()

    # --- Tag aliases ---
    def add_tag_alias(self, tag_id, alias, normalized_alias):
        self.conn.execute("INSERT OR IGNORE INTO tag_aliases (tag_id, alias, normalized_alias) VALUES (?, ?, ?)", (tag_id, alias, normalized_alias))
        self.conn.commit()

    def get_tag_aliases_by_normalized(self, normalized_alias):
        rows = self.conn.execute("SELECT ta.*, t.canonical_name, t.category FROM tag_aliases ta JOIN tags t ON ta.tag_id=t.id WHERE ta.normalized_alias=?", (normalized_alias,)).fetchall()
        return self._dicts(rows)

    def get_tag_aliases_by_tag(self, tag_id):
        return self._dicts(self.conn.execute("SELECT * FROM tag_aliases WHERE tag_id=?", (tag_id,)).fetchall())

    def delete_tag_aliases_by_tag(self, tag_id):
        self.conn.execute("DELETE FROM tag_aliases WHERE tag_id=?", (tag_id,))
        self.conn.commit()

    def count_tag_aliases(self):
        return self.conn.execute("SELECT COUNT(*) FROM tag_aliases").fetchone()[0]

    # --- Paper tags ---
    def add_paper_tag(self, paper_id, tag_id, source='llm', run_id=None, confidence=None, raw_name=None):
        values = (paper_id, tag_id, source, run_id, confidence, raw_name)
        self.conn.execute("INSERT OR IGNORE INTO paper_tags (paper_id, tag_id, source, run_id, confidence, raw_name) VALUES (?, ?, ?, ?, ?, ?)", values)
        self.conn.execute("INSERT INTO tag_assertions (paper_id, tag_id, source, run_id, confidence, raw_name) VALUES (?, ?, ?, ?, ?, ?)", values)
        self.conn.commit()

    def move_tag_assertions(self, from_tag_id, to_tag_id):
        self.conn.execute("UPDATE tag_assertions SET tag_id=? WHERE tag_id=?", (to_tag_id, from_tag_id))
        self.conn.commit()

    def get_paper_tags_by_tag(self, tag_id):
        return self._dicts(self.conn.execute("SELECT * FROM paper_tags WHERE tag_id=?", (tag_id,)).fetchall())

    def delete_paper_tags_by_tag(self, tag_id):
        self.conn.execute("DELETE FROM paper_tags WHERE tag_id=?", (tag_id,))
        self.conn.commit()

    def get_paper_tag_count(self, tag_id):
        return self.conn.execute("SELECT COUNT(*) FROM paper_tags WHERE tag_id=?", (tag_id,)).fetchone()[0]

    def count_paper_tags(self):
        return self.conn.execute("SELECT COUNT(*) FROM paper_tags").fetchone()[0]

    # --- Summaries ---
    def add_summary(self, paper_id, run_id=None, model_name='', prompt_version='', content='', is_active=1):
        self.conn.execute("UPDATE summaries SET is_active=0 WHERE paper_id=? AND is_active=1", (paper_id,))
        cur = self.conn.execute("INSERT INTO summaries (paper_id, run_id, model_name, prompt_version, content, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                                (paper_id, run_id, model_name, prompt_version, content, is_active))
        self.conn.commit()
        return cur.lastrowid

    def deactivate_summaries(self, paper_id):
        self.conn.execute("UPDATE summaries SET is_active=0 WHERE paper_id=?", (paper_id,))
        self.conn.commit()

    def get_active_summary(self, paper_id):
        row = self.conn.execute("SELECT * FROM summaries WHERE paper_id=? AND is_active=1 ORDER BY timestamp DESC LIMIT 1", (paper_id,)).fetchone()
        return self._dict(row)

    def get_summary_history(self, paper_id):
        return self._dicts(self.conn.execute("SELECT * FROM summaries WHERE paper_id=? ORDER BY timestamp DESC", (paper_id,)).fetchall())

    # --- Methods ---
    def add_method(self, paper_id, run_id=None, name='', method_type='', purpose='', complexity='', confidence=None, card_json='{}', source_passages_json='[]'):
        cur = self.conn.execute("INSERT INTO methods (paper_id, run_id, name, method_type, purpose, complexity, confidence, card_json, source_passages_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (paper_id, run_id, name, method_type, purpose, complexity, confidence, card_json, source_passages_json))
        self.conn.commit()
        return cur.lastrowid

    def get_methods(self, paper_id, method_type=None):
        if method_type:
            return self._dicts(self.conn.execute("SELECT * FROM methods WHERE paper_id=? AND method_type=?", (paper_id, method_type)).fetchall())
        return self._dicts(self.conn.execute("SELECT * FROM methods WHERE paper_id=?", (paper_id,)).fetchall())

    def link_method_equation(self, method_id, equation_id, role='core'):
        self.conn.execute("INSERT OR IGNORE INTO method_equations (method_id, equation_id, role) VALUES (?, ?, ?)", (method_id, equation_id, role))
        self.conn.commit()

    # --- Equations ---
    def get_equations_for_paper(self, paper_id):
        return self._dicts(self.conn.execute("SELECT * FROM equations WHERE paper_id=?", (paper_id,)).fetchall())

    # --- Papers ---
    def get_paper(self, paper_id):
        row = self.conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()
        return self._dict(row)

    def add_paper(self, paper_key, title='', doi=None, year=None, essence='', markdown_path=None):
        cur = self.conn.execute("INSERT INTO papers (paper_key, title, doi, year, essence, markdown_path) VALUES (?, ?, ?, ?, ?, ?)",
                                (paper_key, title, doi, year, essence, markdown_path))
        self.conn.commit()
        return cur.lastrowid

    # --- Topics ---
    def add_topic(self, name, description=''):
        try:
            cur = self.conn.execute("INSERT INTO topics (name, description) VALUES (?, ?)", (name, description))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            row = self.conn.execute("SELECT id FROM topics WHERE name=?", (name,)).fetchone()
            return row['id'] if row else None

    def add_topic_paper(self, topic_id, paper_id, relevance='', match_score=None):
        self.conn.execute("INSERT OR IGNORE INTO topic_papers (topic_id, paper_id, relevance, match_score) VALUES (?, ?, ?, ?)",
                          (topic_id, paper_id, relevance, match_score))
        self.conn.commit()

    def add_topic_overview(self, topic_id, content='', original_query='', filters_json='{}', comparison_matrix_json='{}', model_name='', prompt_version='v1', is_active=1):
        cur = self.conn.execute("INSERT INTO topic_overviews (topic_id, content, original_query, filters_json, comparison_matrix_json, model_name, prompt_version, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (topic_id, content, original_query, filters_json, comparison_matrix_json, model_name, prompt_version, is_active))
        self.conn.commit()
        return cur.lastrowid

    # --- Processing runs ---
    def create_processing_run(self, paper_id, operation='', backend='', model_name='', prompt_version='', status='pending'):
        cur = self.conn.execute("INSERT INTO processing_runs (paper_id, operation, backend, model_name, prompt_version, status) VALUES (?, ?, ?, ?, ?, ?)",
                                (paper_id, operation, backend, model_name, prompt_version, status))
        self.conn.commit()
        return cur.lastrowid


class MockAgent:
    """Mock LLM agent that returns pre-configured responses."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.response_idx = 0
        self.system_prompt = ""
        self.history = []
        self.max_context_length = 4096
        self.model_name = "mock-model"
        self.temperature = 0.0

    def set_system_prompt(self, prompt):
        self.system_prompt = prompt
        self.history = [{"role": "system", "content": prompt}]

    def query(self, prompt=None, messages=None, bTools=True, **kwargs):
        if self.response_idx < len(self.responses):
            content = self.responses[self.response_idx]
            self.response_idx += 1
        else:
            content = '{"domain": [], "physical_system": [], "phenomenon": [], "model_or_theory": [], "method": [], "solver": [], "data_structure": [], "discretization": [], "task": [], "implementation": [], "software": [], "material_or_molecule": [], "user": []}'

        class MockResponse:
            def __init__(self, content):
                self.content = content
        return MockResponse(content)

    def stream(self, prompt, **kwargs):
        yield self.query(prompt).content

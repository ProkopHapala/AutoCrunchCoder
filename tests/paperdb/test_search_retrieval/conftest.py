"""Shared test fixtures for search & retrieval tests.

Creates an in-memory SQLite DB with the schema from the design doc,
plus a mock Repository that provides the interface our code needs.
"""

import sqlite3
import os
import tempfile
from dataclasses import dataclass


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

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

CREATE VIRTUAL TABLE search_units_fts USING fts5(
    content,
    section_path,
    content='search_units',
    content_rowid='id'
);

CREATE TRIGGER search_units_ai AFTER INSERT ON search_units BEGIN
    INSERT INTO search_units_fts(rowid, content, section_path)
    VALUES (new.id, new.content, new.section_path);
END;
CREATE TRIGGER search_units_ad AFTER DELETE ON search_units BEGIN
    INSERT INTO search_units_fts(search_units_fts, rowid, content, section_path)
    VALUES ('delete', old.id, old.content, old.section_path);
END;
CREATE TRIGGER search_units_au AFTER UPDATE ON search_units BEGIN
    INSERT INTO search_units_fts(search_units_fts, rowid, content, section_path)
    VALUES ('delete', old.id, old.content, old.section_path);
    INSERT INTO search_units_fts(rowid, content, section_path)
    VALUES (new.id, new.content, new.section_path);
END;

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

CREATE TABLE equation_variables(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equation_id INTEGER NOT NULL REFERENCES equations(id),
    symbol TEXT,
    meaning TEXT,
    source_page INTEGER,
    source_context TEXT
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
    equation_id INTEGER NOT NULL REFERENCES equations(id),
    role TEXT,
    PRIMARY KEY(method_id, equation_id, role)
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

CREATE TABLE context_packs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    filters_json TEXT,
    selected_units_json TEXT,
    content TEXT,
    output_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE citations(
    citing_paper_id INTEGER NOT NULL REFERENCES papers(id),
    cited_doi TEXT,
    cited_title TEXT,
    matched_paper_id INTEGER REFERENCES papers(id),
    UNIQUE(citing_paper_id, cited_doi)
);
"""


@dataclass
class Paper:
    """Duck-typed Paper matching paperdb.db.models.Paper."""
    id: int = 0
    paper_key: str = ""
    doi: str = ""
    arxiv_id: str = ""
    title: str = ""
    authors_text: str = ""
    year: int = 0
    journal: str = ""
    abstract: str = ""
    keywords: str = ""
    essence: str = ""
    markdown_path: str = ""
    json_path: str = ""
    bibtex_path: str = ""


class MockRepository:
    """Minimal repository providing the interface that search modules need.
    Uses sqlite3.Row for dict-like row access.
    """
    def __init__(self, conn):
        self.conn = conn

    def get_paper(self, paper_id):
        row = self.conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        return Paper(
            id=d['id'], paper_key=d['paper_key'], doi=d.get('doi', ''),
            arxiv_id=d.get('arxiv_id', ''), title=d.get('title', ''),
            authors_text=d.get('authors_text', ''), year=d.get('year'),
            journal=d.get('journal', ''), abstract=d.get('abstract', ''),
            keywords=d.get('keywords', ''), essence=d.get('essence', ''),
            markdown_path=d.get('markdown_path', ''), json_path=d.get('json_path', ''),
            bibtex_path=d.get('bibtex_path', '')
        )

    def replace_search_units(self, paper_id, units):
        """Transactional delete+insert of search units for a paper."""
        self.conn.execute("BEGIN")
        self.conn.execute("DELETE FROM search_units WHERE paper_id = ?", (paper_id,))
        for u in units:
            self.conn.execute(
                "INSERT INTO search_units (paper_id, run_id, unit_type, source_type, source_id, section_path, page_from, page_to, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (u.paper_id, u.run_id, u.unit_type, u.source_type, u.source_id,
                 u.section_path, u.page_from, u.page_to, u.content)
            )
        self.conn.execute("COMMIT")

    def get_search_units_for_paper(self, paper_id):
        rows = self.conn.execute("SELECT * FROM search_units WHERE paper_id = ?", (paper_id,)).fetchall()
        return [dict(r) for r in rows]

    def save_context_pack(self, query, filters_json, selected_units_json, content, output_path=None):
        sql = "INSERT INTO context_packs (query, filters_json, selected_units_json, content, output_path) VALUES (?, ?, ?, ?, ?)"
        cur = self.conn.execute(sql, (query, filters_json, selected_units_json, content, output_path))
        return cur.lastrowid


def create_test_db():
    """Create an in-memory SQLite DB with schema and return (conn, repo)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    repo = MockRepository(conn)
    return conn, repo


def create_test_file_db():
    """Create a file-based SQLite DB (needed for FTS5 in some Python versions)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    repo = MockRepository(conn)
    return conn, repo, path


def insert_test_paper(repo, paper_key, title="", year=None, abstract="", essence="", doi="", authors_text=""):
    """Insert a test paper and return its id."""
    sql = """INSERT INTO papers (paper_key, doi, title, authors_text, year, abstract, essence)
             VALUES (?, ?, ?, ?, ?, ?, ?)"""
    cur = repo.conn.execute(sql, (paper_key, doi or None, title, authors_text, year, abstract, essence))
    repo.conn.commit()
    return cur.lastrowid


def insert_test_tag(repo, canonical_name, category):
    """Insert a tag and return its id."""
    cur = repo.conn.execute("INSERT INTO tags (canonical_name, category) VALUES (?, ?)", (canonical_name, category))
    repo.conn.commit()
    return cur.lastrowid


def insert_test_alias(repo, tag_id, alias):
    """Insert a tag alias."""
    normalized = alias.lower().strip()
    repo.conn.execute("INSERT INTO tag_aliases (tag_id, alias, normalized_alias) VALUES (?, ?, ?)", (tag_id, alias, normalized))
    repo.conn.commit()


def insert_test_paper_tag(repo, paper_id, tag_id, source='llm', confidence=1.0, raw_name=None):
    """Insert a paper-tag association."""
    repo.conn.execute(
        "INSERT INTO paper_tags (paper_id, tag_id, source, confidence, raw_name) VALUES (?, ?, ?, ?, ?)",
        (paper_id, tag_id, source, confidence, raw_name)
    )
    repo.conn.commit()


def insert_test_summary(repo, paper_id, content, is_active=1):
    """Insert a summary for a paper."""
    repo.conn.execute(
        "INSERT INTO summaries (paper_id, content, is_active) VALUES (?, ?, ?)",
        (paper_id, content, is_active)
    )
    repo.conn.commit()


def insert_test_method(repo, paper_id, name, complexity="O(n)", card_json=None):
    """Insert a method card for a paper."""
    repo.conn.execute(
        "INSERT INTO methods (paper_id, name, complexity, card_json) VALUES (?, ?, ?, ?)",
        (paper_id, name, complexity, card_json)
    )
    repo.conn.commit()


def insert_test_search_unit(repo, paper_id, unit_type, source_type, content, section_path="", run_id=None):
    """Insert a single search unit."""
    repo.conn.execute(
        "INSERT INTO search_units (paper_id, run_id, unit_type, source_type, section_path, content) VALUES (?, ?, ?, ?, ?, ?)",
        (paper_id, run_id, unit_type, source_type, section_path, content)
    )
    repo.conn.commit()

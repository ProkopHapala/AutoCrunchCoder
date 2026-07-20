-- Migration 001: Initial schema — identical to schema.sql
-- This file is the first numbered migration for explicit migration tracking.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS papers(
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

CREATE TABLE IF NOT EXISTS paper_files(
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

CREATE UNIQUE INDEX IF NOT EXISTS one_preferred_file_per_paper ON paper_files(paper_id) WHERE is_preferred = 1;
CREATE INDEX IF NOT EXISTS idx_paper_files_paper ON paper_files(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_files_sha256 ON paper_files(sha256);

CREATE TABLE IF NOT EXISTS processing_runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    operation TEXT,
    backend TEXT,
    backend_version TEXT,
    model_name TEXT,
    prompt_version TEXT,
    configuration_json TEXT,
    config_hash TEXT,
    source_file_id INTEGER REFERENCES paper_files(id),
    input_sha256 TEXT,
    output_path TEXT,
    supersedes_run_id INTEGER REFERENCES processing_runs(id),
    status TEXT,
    started_at TEXT,
    finished_at TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS search_units(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER REFERENCES processing_runs(id),
    unit_type TEXT,
    source_type TEXT,
    source_id INTEGER,
    section_path TEXT,
    page_from INTEGER,
    page_to INTEGER,
    content TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_units_fts USING fts5(
    content,
    section_path,
    content='search_units',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS search_units_ai AFTER INSERT ON search_units BEGIN
    INSERT INTO search_units_fts(rowid, content, section_path)
    VALUES (new.id, new.content, new.section_path);
END;
CREATE TRIGGER IF NOT EXISTS search_units_ad AFTER DELETE ON search_units BEGIN
    INSERT INTO search_units_fts(search_units_fts, rowid, content, section_path)
    VALUES ('delete', old.id, old.content, old.section_path);
END;
CREATE TRIGGER IF NOT EXISTS search_units_au AFTER UPDATE ON search_units BEGIN
    INSERT INTO search_units_fts(search_units_fts, rowid, content, section_path)
    VALUES ('delete', old.id, old.content, old.section_path);
    INSERT INTO search_units_fts(rowid, content, section_path)
    VALUES (new.id, new.content, new.section_path);
END;

CREATE TABLE IF NOT EXISTS tags(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,
    UNIQUE(canonical_name, category)
);

CREATE TABLE IF NOT EXISTS tag_aliases(
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    UNIQUE(tag_id, normalized_alias)
);

CREATE TABLE IF NOT EXISTS paper_tags(
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    source TEXT,
    run_id INTEGER REFERENCES processing_runs(id),
    confidence REAL,
    raw_name TEXT,
    PRIMARY KEY(paper_id, tag_id, source, run_id)
);

CREATE TABLE IF NOT EXISTS equations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER REFERENCES processing_runs(id),
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

CREATE TABLE IF NOT EXISTS equation_variables(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equation_id INTEGER NOT NULL REFERENCES equations(id),
    symbol TEXT,
    meaning TEXT,
    source_page INTEGER,
    source_context TEXT
);

CREATE TABLE IF NOT EXISTS methods(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER REFERENCES processing_runs(id),
    name TEXT,
    method_type TEXT,
    purpose TEXT,
    complexity TEXT,
    confidence REAL,
    card_json TEXT,
    source_passages_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS method_equations(
    method_id INTEGER NOT NULL REFERENCES methods(id),
    equation_id INTEGER NOT NULL REFERENCES equations(id),
    role TEXT,
    PRIMARY KEY(method_id, equation_id, role)
);

CREATE TABLE IF NOT EXISTS summaries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER REFERENCES processing_runs(id),
    model_name TEXT,
    prompt_version TEXT,
    content TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS topics(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS topic_papers(
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    relevance TEXT,
    match_score REAL,
    PRIMARY KEY(topic_id, paper_id)
);

CREATE TABLE IF NOT EXISTS topic_overviews(
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

CREATE TABLE IF NOT EXISTS context_packs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    filters_json TEXT,
    selected_units_json TEXT,
    content TEXT,
    output_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS citations(
    citing_paper_id INTEGER NOT NULL REFERENCES papers(id),
    cited_doi TEXT,
    cited_title TEXT,
    matched_paper_id INTEGER REFERENCES papers(id),
    UNIQUE(citing_paper_id, cited_doi)
);

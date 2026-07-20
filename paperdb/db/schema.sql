-- PaperDB canonical schema — from §9 of design doc
-- This file is executed via executescript() on first run.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Core paper record — semantic identity, not hash-based
CREATE TABLE IF NOT EXISTS papers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_key TEXT NOT NULL UNIQUE,        -- human-readable: Macklin_2016_XPBD
    doi TEXT UNIQUE,                       -- normalized: lowercase, no prefix
    arxiv_id TEXT,
    title TEXT,
    authors_text TEXT,                     -- "Macklin, Miles; Müller, Matthias"
    year INTEGER,                          -- integer, not text
    journal TEXT,
    abstract TEXT,
    keywords TEXT,
    essence TEXT,                          -- 1-2 sentence summary
    markdown_path TEXT,                    -- ~/paperdb/papers/2016/Macklin_2016_XPBD__p0427.md
    json_path TEXT,                        -- ~/paperdb/papers/2016/Macklin_2016_XPBD__p0427.json
    bibtex_path TEXT,                      -- ~/paperdb/papers/2016/Macklin_2016_XPBD__p0427.bib
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Multiple files for the same paper (dedup, versions, duplicates)
CREATE TABLE IF NOT EXISTS paper_files(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    path TEXT NOT NULL UNIQUE,
    file_role TEXT,                        -- 'publisher' | 'arxiv' | 'supplement' | 'manuscript' | 'duplicate'
    version_label TEXT,
    file_size INTEGER,
    modified_time REAL,
    sha256 TEXT,                           -- internal checksum, never in filenames
    exists_now INTEGER DEFAULT 1,
    is_preferred INTEGER DEFAULT 0,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP
);

-- At most one preferred file per paper
CREATE UNIQUE INDEX IF NOT EXISTS one_preferred_file_per_paper ON paper_files(paper_id) WHERE is_preferred = 1;
CREATE INDEX IF NOT EXISTS idx_paper_files_paper ON paper_files(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_files_sha256 ON paper_files(sha256);

-- Processing runs — replaces boolean flags with proper provenance
CREATE TABLE IF NOT EXISTS processing_runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    operation TEXT,                        -- 'convert' | 'summarize' | 'tag' | 'equations' | 'methods' | 'embed' | 'migrate_markdown' | 'migrate_summary'
    backend TEXT,                          -- 'docling' | 'mineru' | 'legacy_pdfminer' | 'legacy_docling' | 'legacy_llama8b' | 'llm'
    backend_version TEXT,
    model_name TEXT,                       -- which LLM (for summarize/tag/extract)
    prompt_version TEXT,
    configuration_json TEXT,
    config_hash TEXT,                      -- hash of config for skip-if-equivalent logic
    source_file_id INTEGER REFERENCES paper_files(id),  -- which PDF was processed
    input_sha256 TEXT,                     -- hash of input PDF — detects replaced/corrected files
    output_path TEXT,                      -- path to the output artifact
    supersedes_run_id INTEGER REFERENCES processing_runs(id),  -- prior run this replaces
    status TEXT,                           -- 'pending' | 'running' | 'ok' | 'partial' | 'failed' | 'superseded'
    started_at TEXT,
    finished_at TEXT,
    message TEXT
);

-- Searchable units — FTS at section/paragraph/equation/method level, NOT paper-level
CREATE TABLE IF NOT EXISTS search_units(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER REFERENCES processing_runs(id),
    unit_type TEXT,                        -- 'summary' | 'section' | 'paragraph' | 'equation' | 'method'
    source_type TEXT,                      -- 'section' | 'equation' | 'method' | 'summary'
    source_id INTEGER,                     -- FK to the source row (equations.id, methods.id, etc.)
    section_path TEXT,                     -- e.g. "3.1 Compliance"
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

-- FTS5 synchronization triggers (external-content tables do NOT auto-sync)
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

-- Tags — canonical names with categories
CREATE TABLE IF NOT EXISTS tags(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,               -- 'domain' | 'physical_system' | 'phenomenon' | 'model_or_theory' |
                                          -- 'method' | 'solver' | 'data_structure' | 'discretization' |
                                          -- 'task' | 'implementation' | 'software' | 'material_or_molecule' | 'user'
    UNIQUE(canonical_name, category)
);

-- Tag aliases — preserve original forms, map to canonical (not globally unique — abbreviations can be ambiguous)
CREATE TABLE IF NOT EXISTS tag_aliases(
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,         -- lowercase, stripped
    UNIQUE(tag_id, normalized_alias)
);

-- Paper-tag assertions — preserve raw names, source, confidence, run provenance
CREATE TABLE IF NOT EXISTS paper_tags(
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    source TEXT,                           -- 'llm' | 'user' | 'bibtex' | 'imported'
    run_id INTEGER REFERENCES processing_runs(id),  -- which run produced this (distinguishes two LLM tagging runs)
    confidence REAL,
    raw_name TEXT,                         -- original tag text before canonicalization
    PRIMARY KEY(paper_id, tag_id, source, run_id)
);

-- Immutable raw assertions survive canonical tag merges and repeated extraction runs.
CREATE TABLE IF NOT EXISTS tag_assertions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    source TEXT,
    run_id INTEGER REFERENCES processing_runs(id),
    confidence REAL,
    raw_name TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS tag_assertions_identity ON tag_assertions(paper_id, tag_id, IFNULL(source,''), IFNULL(run_id,-1), IFNULL(raw_name,''));

-- Equations with source fidelity
CREATE TABLE IF NOT EXISTS equations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER REFERENCES processing_runs(id),
    latex_raw TEXT,                        -- what parser extracted — never overwrite
    latex_normalized TEXT,                 -- cleaned up by LLM or symbolic parser
    equation_number TEXT,
    section_path TEXT,
    page_number INTEGER,
    bbox_json TEXT,                        -- bounding box for visual QA
    context_before TEXT,
    context_after TEXT,
    parser TEXT,
    confidence REAL,
    verification_status TEXT               -- 'unverified' | 'visual_qa_pass' | 'visual_qa_fail' | 'manual'
);

-- Variable definitions as separate evidence records
CREATE TABLE IF NOT EXISTS equation_variables(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equation_id INTEGER NOT NULL REFERENCES equations(id),
    symbol TEXT,
    meaning TEXT,
    source_page INTEGER,
    source_context TEXT
);

-- Method cards — source algorithm vs reconstructed method (simplified: card_json for evolving fields)
CREATE TABLE IF NOT EXISTS methods(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER REFERENCES processing_runs(id),
    name TEXT,
    method_type TEXT,                      -- 'source_algorithm' | 'reconstructed_method'
    purpose TEXT,
    complexity TEXT,
    confidence REAL,
    card_json TEXT,                        -- evolving structured details: assumptions, state_variables, inputs, outputs, initialization, steps, boundary_conditions, convergence, parallelization, limitations
    source_passages_json TEXT,             -- [{"page": 4, "section": "3.1", "text": "..."}]
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Method-equation junction (referential integrity without heavy schema)
CREATE TABLE IF NOT EXISTS method_equations(
    method_id INTEGER NOT NULL REFERENCES methods(id),
    equation_id INTEGER NOT NULL REFERENCES equations(id),
    role TEXT,                             -- 'core' | 'update' | 'initialization' | 'boundary'
    PRIMARY KEY(method_id, equation_id, role)
);

-- Versioned summaries (expensive to regenerate, keep history)
CREATE TABLE IF NOT EXISTS summaries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER REFERENCES processing_runs(id),
    model_name TEXT,
    prompt_version TEXT,
    content TEXT,                          -- full summary markdown
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Topical overviews (generated review-like documents)
CREATE TABLE IF NOT EXISTS topics(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,                      -- e.g. "molecular force fields", "GPU collision methods"
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS topic_papers(
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    relevance TEXT,                        -- why this paper was selected
    match_score REAL,
    PRIMARY KEY(topic_id, paper_id)
);

CREATE TABLE IF NOT EXISTS topic_overviews(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    content TEXT,                          -- generated overview markdown
    original_query TEXT,
    filters_json TEXT,
    comparison_matrix_json TEXT,
    model_name TEXT,
    prompt_version TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Context packs (the central output — persistable for reproducibility)
CREATE TABLE IF NOT EXISTS context_packs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    filters_json TEXT,
    selected_units_json TEXT,              -- which search_units were included
    content TEXT,                          -- assembled context pack text
    output_path TEXT,                      -- if saved to file
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Citations (future)
CREATE TABLE IF NOT EXISTS citations(
    citing_paper_id INTEGER NOT NULL REFERENCES papers(id),
    cited_doi TEXT,
    cited_title TEXT,
    matched_paper_id INTEGER REFERENCES papers(id),
    UNIQUE(citing_paper_id, cited_doi)
);

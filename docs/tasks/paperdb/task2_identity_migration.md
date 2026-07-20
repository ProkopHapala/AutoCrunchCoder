# Task 2: Identity, Scanner & Migration

## Your role

You build the **identity layer** (hashing, dedup, DOI normalization, BibTeX parsing), the **PDF scanner** (find PDFs in folders, compute hashes, match to papers), and the **legacy migration script** (convert old `consolidated.db` + existing markdown/summaries into the new schema).

## Files you own (ONLY modify these)

```
paperdb/identity/hashing.py        # SHA-256 computation (lazy: compare size+mtime first)
paperdb/identity/matching.py       # dedup by hash, DOI, title+authors+year
paperdb/identity/metadata.py       # DOI normalization, BibTeX parsing (reuses pyCruncher.bib_utils)
paperdb/ingest/scanner.py          # find PDFs in folders, compute hashes, store in paper_files
paperdb/ingest/migration.py        # legacy data conversion (Phase A of §16)
```

## Files you must NOT touch

- `paperdb/__init__.py`, `paperdb/paths.py`, `paperdb/config.py` — Task 1
- `paperdb/db/*` — Task 1 (you USE repository.py, not modify it)
- `paperdb/search/*` — Task 3
- `paperdb/cli.py`, `paperdb/mcp.py` — Task 4
- `paperdb/extract/*`, `paperdb/ingest/pipeline.py`, `jobs.py`, `fetch.py` — Task 5
- `paperdb/taxonomy/*`, `paperdb/synthesis/*` — Task 6
- `paperdb/identity/__init__.py`, `paperdb/ingest/__init__.py` — Task 1 (created empty, do not modify)

## Reference

Read `docs/topical_audit/paper_db_notes.md` — especially:
- **§6 C1** (semantic paper identity) — `paper_key` generation, DOI normalization
- **§6 C6** (deduplication) — multi-criteria matching
- **§9** (schema) — `papers`, `paper_files`, `processing_runs` tables
- **§16** (migration) — Phase A (convert) / Phase B (validate+retire), two-phase approach
- **§18 D3** (PDF storage) — index in-place, semantic paper_key
- **§18 D14** (old data) — convert to new representation, two-phase migration

## Dependencies

- **Task 1 must be complete** (or API interface defined). You need:
  - `paperdb.db.repository.Repository` for all DB operations
  - `paperdb.db.models` for `Paper`, `PaperFile`, `ProcessingRun` models
  - `paperdb.paths` for data directory resolution
  - `paperdb.PaperDB` for the API facade

## Steps

### Step 1: Hashing (`paperdb/identity/hashing.py`)

```python
def compute_sha256(path, lazy=True) -> str:
    """Compute SHA-256 of a file. If lazy=True, check size+mtime cache first."""
```

- Lazy mode: store `(path, size, mtime, sha256)` in a simple JSON cache at `~/paperdb/.hash_cache.json`. If size+mtime match, return cached hash. Otherwise compute.
- Full mode: always compute.
- Used by scanner and matching.

### Step 2: Matching (`paperdb/identity/matching.py`)

```python
def generate_paper_key(authors, year, title, existing_stem=None) -> str:
    """Generate semantic paper_key: Author_Year_Keyword (e.g. Macklin_2016_XPBD)."""

def match_by_hash(hash_value, repo) -> int | None:
    """Find existing paper by SHA-256."""

def match_by_doi(doi, repo) -> int | None:
    """Find existing paper by normalized DOI."""

def match_by_metadata(title, authors, year, repo) -> int | None:
    """Fuzzy match by title+authors+year. Use simple string similarity, not embeddings."""

def find_or_create_paper(pdf_path, repo, metadata=None) -> tuple[int, bool]:
    """Try all match methods. Return (paper_id, was_created)."""
```

- DOI normalization: lowercase, strip `https://doi.org/`, `doi:`, leading zeros in some fields. See §9.
- `paper_key` generation: first author lastname + year + first significant word from title (or keyword from metadata). Handle collisions by appending `_2`, `_3`, etc.
- If `existing_stem` is provided (from legacy DB), prefer it.

### Step 3: Metadata (`paperdb/identity/metadata.py`)

```python
def normalize_doi(doi) -> str:
    """Normalize DOI: lowercase, strip prefixes."""

def parse_bibtex(bibtex_text) -> list[dict]:
    """Parse BibTeX entries. Reuse pyCruncher.bib_utils if available."""

def match_bibtex_to_paper(entry, repo) -> int | None:
    """Match a BibTeX entry to an existing paper by DOI, title, or filename."""

def crossref_lookup(doi) -> dict:
    """Fetch metadata from CrossRef API by DOI. Returns title, authors, year, journal."""

def arxiv_lookup(arxiv_id) -> dict:
    """Fetch metadata from arXiv API."""
```

- CrossRef API: `https://api.crossref.org/works/{doi}`
- arXiv API: `http://export.arxiv.org/api/query?id_list={arxiv_id}`
- Reuse `pyCruncher.bib_utils` for BibTeX parsing if it exists (check first).

### Step 4: Scanner (`paperdb/ingest/scanner.py`)

```python
def scan_folder(folder_path, recursive=True, repo=None) -> list[dict]:
    """Find all PDFs in folder. For each:
    1. Compute SHA-256 (lazy)
    2. Match to existing paper (hash, DOI from filename, metadata)
    3. If no match, create new paper record
    4. Add paper_files entry
    Returns list of {paper_id, path, was_new, matched_by}
    """

def scan_mendeley(bibtex_path, pdf_folder, repo=None) -> list[dict]:
    """Scan Mendeley: parse BibTeX, match PDFs by filename/DOI, import metadata."""
```

- PDFs stay in place — never move, copy, or rename.
- Store paths in `paper_files` table via `repo.add_paper_file()`.
- Detect moved PDFs: if hash matches but path differs, update path.

### Step 5: Migration (`paperdb/ingest/migration.py`)

This is the **Phase A** migration from §16. The goal is to convert legacy data into the new representation, NOT to preserve old formats.

```python
def migrate_legacy(legacy_dir, repo, data_dir) -> dict:
    """Phase A migration:
    1. Inventory legacy artifacts (consolidated.db, markdown dirs, summaries)
    2. Import papers from consolidated.db (895 papers, tags, article_tags)
    3. Generate paper_key for each
    4. Select best existing markdown (docling > pdfminer)
    5. Record as processing_runs with operation='migrate_markdown', backend='legacy_docling'
    6. Import existing summaries as processing_runs with operation='migrate_summary'
    7. Run tag cleanup (apply clean_tags.py rules, build tag_aliases)
    8. Scan PDF folders, match to papers
    9. Generate .md/.json/.bib bundles
    10. Build search_units from migrated markdown
    11. Produce migration report
    Returns {papers_migrated, papers_failed, conflicts, report_path}
    """
```

Key principles:
- **Do NOT re-generate markdown or summaries with LLM** — reuse existing. LLM processing is costly.
- **Do NOT delete any existing files** — copy to `~/paperdb/legacy/` first.
- Record provenance: `processing_runs` with `operation='migrate_markdown'`, `backend='legacy_docling'` (or `legacy_pdfminer`), `input_sha256`, `output_path`.
- Select best markdown by policy: docling+formulas > docling > vlm > pdfminer.
- Preserve raw tag assertions in `paper_tags.raw_name`.
- Generate `paper_key` from authors/year/title or existing stem from legacy DB.
- Produce conflict report at `~/paperdb/logs/migration_report.md`.

Legacy data locations (from §3 of design doc):
- `tests/paper_pipeline_out/consolidated.db` — 895 papers, tags, article_tags
- `tests/paper_pipeline_out/*/markdown/` — markdown by stem name
- `tests/paper_pipeline_out/*/summaries/` — summaries
- `~/Desktop/PAPERs/` — 1254 PDFs
- Mendeley BibTeX: `~/Mendeley_Desktop_bibtex/INTERESTS.bib`, `library.bib`

### Step 6: Tests

1. Create `tests/paperdb/test_identity_migration/`:
   - `test_hashing.py` — lazy vs full, cache behavior
   - `test_matching.py` — paper_key generation, dedup by hash/DOI/metadata
   - `test_metadata.py` — DOI normalization, BibTeX parsing, CrossRef mock
   - `test_scanner.py` — scan a test folder, verify paper_files entries
   - `test_migration.py` — migrate a small test DB, verify paper count, search units, report

## Deliverable checklist

- [ ] `paperdb/identity/hashing.py` — lazy SHA-256 with cache
- [ ] `paperdb/identity/matching.py` — paper_key generation, multi-criteria dedup
- [ ] `paperdb/identity/metadata.py` — DOI normalization, BibTeX, CrossRef/arXiv lookup
- [ ] `paperdb/ingest/scanner.py` — folder scanning, Mendeley import
- [ ] `paperdb/ingest/migration.py` — Phase A legacy migration
- [ ] Tests in `tests/paperdb/test_identity_migration/`

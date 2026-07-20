# Task 5: Extraction & Ingest Pipeline

## Your role

You build the **extraction and ingestion pipeline**: the Docling backend (PDF → Markdown + structured output), equation extraction (LaTeX with source coordinates), method card extraction, the ingest pipeline orchestrator, incremental job execution, and internet fetch (CrossRef, arXiv PDF download).

## Files you own (ONLY modify these)

```
paperdb/extract/base.py              # base parser interface
paperdb/extract/docling_backend.py   # primary: Docling structured output + Markdown
paperdb/extract/equations.py         # equation extraction with source coordinates
paperdb/extract/methods.py           # method card extraction (source_algorithm vs reconstructed_method)
paperdb/ingest/pipeline.py           # orchestrate: convert → summarize → tag → extract equations → extract methods
paperdb/ingest/jobs.py               # incremental job execution, skip if equivalent run exists
paperdb/ingest/fetch.py              # download PDFs + metadata from DOI/URL (CrossRef, arXiv)
```

## Files you must NOT touch

- `paperdb/__init__.py`, `paperdb/paths.py`, `paperdb/config.py` — Task 1
- `paperdb/db/*` — Task 1 (you USE repository.py, not modify it)
- `paperdb/identity/*`, `paperdb/ingest/scanner.py`, `migration.py` — Task 2
- `paperdb/search/*` — Task 3
- `paperdb/cli.py`, `paperdb/mcp.py` — Task 4
- `paperdb/taxonomy/*`, `paperdb/synthesis/*` — Task 6
- All `__init__.py` files — Task 1

## Reference

Read `docs/topical_audit/paper_db_notes.md` — especially:
- **§6 C3** (structured extraction) — equations, methods, source coordinates
- **§9** (schema) — `equations`, `equation_variables`, `methods`, `method_equations`, `processing_runs` tables
- **§17 Phase 2** (reliable new ingestion) — ingest pipeline, Docling backend, incremental jobs, fetch
- **§17 Phase 3** (scientific extraction) — equation extraction, method cards
- **§18 D9** (method cards) — source_algorithm vs reconstructed_method
- **§18 D10** (equation handling) — latex_raw vs latex_normalized, source fidelity
- **§18 D15** (processing state) — processing_runs, skip-if-equivalent logic

## Dependencies

- **Task 1 must be complete** (or API interface defined). You need:
  - `paperdb.db.repository.Repository` for storing equations, methods, processing runs
  - `paperdb.db.models` for `Equation`, `Method`, `ProcessingRun` models
  - `paperdb.config` for LLM config (`get_llm_config()`)
  - `paperdb.paths` for data directory (where to write markdown/JSON)

- **Task 2** provides `paperdb.identity.metadata` (CrossRef, arXiv lookup) — you can use it in `fetch.py`.
- **Task 6** provides `paperdb.taxonomy.extraction` (LLM tag extraction) and `paperdb.synthesis.summaries` (LLM summaries) — your pipeline orchestrates these but does NOT implement them. Call them via `PaperDB` API or import them. If not ready, skip those steps.

## Interface contract

Your `pipeline.py` orchestrates the full ingest flow. It calls functions from other tasks' modules:

```python
# From Task 6 (taxonomy)
from paperdb.taxonomy.extraction import extract_tags  # LLM tag extraction
from paperdb.synthesis.summaries import generate_summary  # LLM summary

# From Task 2 (identity)
from paperdb.identity.metadata import crossref_lookup, arxiv_lookup
```

If these modules don't exist yet, catch `ImportError` and skip that step (log a warning). The pipeline should still work for convert + equation extraction without LLM steps.

## Steps

### Step 1: Base parser interface (`paperdb/extract/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ExtractionResult:
    markdown: str                    # full markdown text
    structured_json: dict            # normalized structured output
    equations: list[dict]            # extracted equations with source coords
    sections: list[dict]             # section hierarchy with content
    tables: list[dict]               # extracted tables
    metadata: dict                   # extraction metadata (backend, version, timing)

class BaseParser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> ExtractionResult: ...
```

### Step 2: Docling backend (`paperdb/extract/docling_backend.py`)

```python
class DoclingParser(BaseParser):
    def parse(self, pdf_path: str) -> ExtractionResult:
        """Use Docling to convert PDF to structured output + Markdown.
        - Save normalized structure into the single paper JSON (NOT a separate docling.json)
        - Raw Docling debug output goes to logs/debug/ only when --keep-parser-debug is requested
        - Preserve equations in LaTeX, section hierarchy, reading order
        """
```

Key requirements:
- **Markdown is the central complete representation** (§18 D20) — must preserve complete readable text in correct reading order, section hierarchy, equations in LaTeX, tables/captions/algorithms where possible.
- **Do NOT produce a separate `docling.json`** — the single paper JSON contains the useful normalized Docling structure. Raw parser debug output goes to `logs/debug/` only when explicitly requested via `--keep-parser-debug`.
- Check if `docling` package is available. If not, raise a clear error.

### Step 3: Equation extraction (`paperdb/extract/equations.py`)

```python
def extract_equations(structured_json: dict, paper_id: int, run_id: int, repo) -> list[Equation]:
    """Extract equations from Docling structured output.
    Store via repo.upsert_equation():
    - latex_raw: what parser extracted (never overwrite)
    - latex_normalized: cleaned up by LLM or symbolic parser
    - equation_number, section_path, page_number
    - bbox_json: bounding box for visual QA
    - context_before, context_after
    - parser, confidence, verification_status='unverified'
    Also extract variable definitions via repo.add_variable().
    """
```

Key principles (§18 D10):
- **Source fidelity**: store both `latex_raw` and `latex_normalized` — never overwrite raw.
- Variable definitions as separate evidence records with source location.
- Equation extraction and paper classification are separate concerns.

### Step 4: Method extraction (`paperdb/extract/methods.py`)

```python
def extract_methods(markdown: str, equations: list[Equation], paper_id: int, run_id: int,
                    repo, llm_config=None) -> list[Method]:
    """Extract method cards from markdown + equations.
    - method_type: 'source_algorithm' (verbatim from paper) or 'reconstructed_method' (LLM interpretation)
    - Store structured details in card_json:
      assumptions, state_variables, inputs, outputs, initialization, steps,
      boundary_conditions, convergence, parallelization, limitations
    - source_passages_json: [{"page": 4, "section": "3.1", "text": "..."}]
    - Link equations via repo.link_method_equation(method_id, equation_id, role)
    - Use pyCruncher.Agent for LLM-based reconstruction
    """
```

Key principles (§18 D9):
- Distinguish `source_algorithm` (verbatim) vs `reconstructed_method` (LLM interpretation).
- Every reconstructed field refers back to source passages — lets coding agent distinguish "paper says this" from "model inferred this".
- Use `card_json` for evolving structured details (simpler than many columns).
- Use `method_equations` junction table for equation references (not JSON FKs).

### Step 5: Ingest pipeline (`paperdb/ingest/pipeline.py`)

```python
def ingest_paper(paper_id: int, repo, operations=None, llm_config=None, force=False) -> dict:
    """Orchestrate full ingestion for a single paper:
    1. Get preferred PDF path from paper_files
    2. Convert: DoclingParser.parse() → markdown + structured_json
       - Record processing_run: operation='convert', backend='docling'
       - Write .md file (atomic: temp → validate → rename)
    3. Extract equations: extract_equations(structured_json, ...)
       - Record processing_run: operation='equations'
    4. Extract methods: extract_methods(markdown, equations, ...)
       - Record processing_run: operation='methods'
    5. Generate summary (if Task 6 ready): synthesis.summaries.generate_summary()
       - Record processing_run: operation='summarize'
    6. Extract tags (if Task 6 ready): taxonomy.extraction.extract_tags()
       - Record processing_run: operation='tag'
    7. Generate .json and .bib files (atomic writes)
    8. Build search_units from markdown (if Task 3 ready): search.fts.build_search_units_from_markdown()

    Skip operations that have an equivalent successful processing_run
    (same operation + input_sha256 + backend + config_hash + model + prompt).
    Use force=True to re-run regardless.

    Returns {paper_id, operations_run, operations_skipped, errors}
    """
```

### Step 6: Incremental jobs (`paperdb/ingest/jobs.py`)

```python
def find_equivalent_run(paper_id, operation, input_sha256, backend, config_hash, model, prompt, repo) -> int | None:
    """Check if an equivalent successful processing_run exists.
    Same: operation + input_sha256 + backend/version + config_hash + model + prompt_version
    Status must be 'ok'. If found, return run_id. Otherwise None.
    """

def run_job(paper_id, operation, backend, config, repo, llm_config=None) -> int:
    """Execute a single processing job:
    1. Check for equivalent run — skip if exists (unless forced)
    2. Create processing_run with status='running'
    3. Execute the operation
    4. On success: status='ok', supersede prior runs for this operation
    5. On failure: status='failed', log error
    Returns run_id.
    """

def ingest_batch(paper_ids: list[int], repo, operations=None, llm_config=None) -> dict:
    """Process multiple papers. Skip papers with all operations already done.
    Returns {processed, skipped, failed, details}
    """
```

### Step 7: Internet fetch (`paperdb/ingest/fetch.py`)

```python
def fetch_by_doi(doi: str, dest_dir: str) -> dict:
    """Fetch paper metadata from CrossRef, attempt to find/download PDF.
    Returns {metadata, pdf_path (or None)}
    """

def fetch_by_arxiv(arxiv_id: str, dest_dir: str) -> dict:
    """Fetch from arXiv: metadata + PDF download.
    """

def fetch_by_url(url: str, dest_dir: str) -> dict:
    """Download PDF from a direct URL.
    """

def add_paper_from_source(source: str, repo, dest_dir=None) -> int:
    """Add a paper from path, URL, or DOI.
    1. Determine source type (path, URL, DOI, arXiv ID)
    2. Fetch metadata + PDF if needed
    3. Create paper record with paper_key
    4. Add paper_files entry
    Returns paper_id
    """
```

- Use `paperdb.identity.metadata.crossref_lookup()` and `arxiv_lookup()` from Task 2.
- Download PDFs to a user-specified directory (NOT `~/paperdb/` — PDFs are not owned by paperdb).
- Handle redirects, rate limits, and errors gracefully (but loudly — no silent failures).

### Step 8: Tests

1. Create `tests/paperdb/test_extraction_ingest/`:
   - `test_docling.py` — parse a test PDF, verify markdown output, equation extraction
   - `test_equations.py` — equation extraction, latex_raw vs latex_normalized, variable definitions
   - `test_methods.py` — method card extraction, card_json structure, method_equations links
   - `test_pipeline.py` — full ingest flow, skip-if-equivalent logic, atomic file writes
   - `test_fetch.py` — CrossRef/arXiv lookup (mock HTTP), PDF download

## Deliverable checklist

- [ ] `paperdb/extract/base.py` — base parser interface
- [ ] `paperdb/extract/docling_backend.py` — Docling PDF → Markdown + structured output
- [ ] `paperdb/extract/equations.py` — equation extraction with source coordinates
- [ ] `paperdb/extract/methods.py` — method card extraction with card_json
- [ ] `paperdb/ingest/pipeline.py` — full ingest orchestration
- [ ] `paperdb/ingest/jobs.py` — incremental job execution, skip-if-equivalent
- [ ] `paperdb/ingest/fetch.py` — CrossRef/arXiv/URL fetch
- [ ] Tests in `tests/paperdb/test_extraction_ingest/`

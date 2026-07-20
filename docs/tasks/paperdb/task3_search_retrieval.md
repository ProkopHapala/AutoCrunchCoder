# Task 3: Search & Retrieval

## Your role

You build the **search and retrieval layer**: FTS5 full-text search on `search_units`, weighted ranking with `--explain`, and context pack assembly (the central output of the system).

## Files you own (ONLY modify these)

```
paperdb/search/fts.py              # FTS5 search on search_units table
paperdb/search/ranking.py          # weighted scoring with explainable breakdown
paperdb/search/context.py          # context pack assembly (two-stage retrieval)
```

## Files you must NOT touch

- `paperdb/__init__.py`, `paperdb/paths.py`, `paperdb/config.py` — Task 1
- `paperdb/db/*` — Task 1 (you USE repository.py, not modify it)
- `paperdb/identity/*`, `paperdb/ingest/scanner.py`, `migration.py` — Task 2
- `paperdb/cli.py`, `paperdb/mcp.py` — Task 4
- `paperdb/extract/*`, `paperdb/ingest/pipeline.py`, `jobs.py`, `fetch.py` — Task 5
- `paperdb/taxonomy/*`, `paperdb/synthesis/*` — Task 6
- `paperdb/search/__init__.py` — Task 1 (created empty, do not modify)

## Reference

Read `docs/topical_audit/paper_db_notes.md` — especially:
- **§9** (schema) — `search_units` table, FTS5 triggers, `context_packs` table
- **§15** (retrieval and search) — Phase 1 (tags + FTS5), weighted ranking, two-stage retrieval, context pack format
- **§18 D16** (FTS granularity) — search_units, not paper-level
- **§18 D19** (source of truth) — SQLite authoritative

## Dependencies

- **Task 1 must be complete** (or API interface defined). You need:
  - `paperdb.db.repository.Repository` for DB queries (search_units, paper_tags, papers)
  - `paperdb.db.models` for `SearchUnit`, `Paper`, `Tag`, `ContextPack` models
  - `paperdb.PaperDB` — you will implement the `search()` and `retrieve_context()` methods on PaperDB (or provide functions that PaperDB delegates to)

## Interface contract

Task 1's `PaperDB` class defines these methods that YOUR code implements:
```python
def search(self, query, required_tags=None, preferred_tags=None, excluded_tags=None, year_range=None, limit=20, explain=False) -> list[SearchResult]: ...
def retrieve_context(self, query, token_budget=24000, include=None, filters=None) -> ContextPack: ...
```

You provide the implementation in `paperdb/search/` modules. Task 1's `PaperDB` will delegate to your functions. Coordinate with Task 1 on the `SearchResult` model.

## Steps

### Step 1: FTS5 search (`paperdb/search/fts.py`)

```python
def fts_search(query, repo, limit=100) -> list[dict]:
    """Execute FTS5 query on search_units_fts.
    Returns list of {unit_id, paper_id, content, section_path, rank, unit_type, source_type, source_id}.
    Uses BM25 ranking from FTS5.
    """

def build_search_units_from_markdown(paper_id, markdown_text, run_id, repo) -> list[SearchUnit]:
    """Split markdown into search units by headings/equations.
    Types: 'summary', 'section', 'paragraph', 'equation', 'method'.
    Store via repo.replace_search_units() (transactional delete+insert, FTS triggers auto-sync).
    """
```

- FTS5 query: use `MATCH` with query terms. Support phrase queries.
- The FTS5 triggers (defined in schema by Task 1) auto-sync on insert/delete/update of `search_units`.
- Only units from the current successful run should be indexed. Use `replace_search_units()` which transactionally deletes old units and inserts new ones.

### Step 2: Ranking (`paperdb/search/ranking.py`)

```python
def rank_papers(query, fts_results, repo, required_tags=None, preferred_tags=None,
                excluded_tags=None, year_range=None, explain=False) -> list[SearchResult]:
    """Two-stage retrieval:
    Stage A: Select candidate papers from FTS results + tag filters.
    Stage B: Score and rank papers.

    Scoring (from §15 of design doc):
    - Required tag match: +10 (filter — paper must have ALL required tags)
    - Preferred tag match: +4 per tag
    - User-assigned tag: +6
    - Title match: +5
    - Abstract/summary match: +2
    - Full-text (search_units) match: +1 per matching unit

    If explain=True, include breakdown:
    SearchResult(paper=..., score=23, breakdown={"title": 5, "preferred_tags": 8, "fts": 10}, matching_units=[...])
    """
```

- **Required tags** are filters — paper must have ALL of them (AND logic).
- **Preferred tags** are boosters — each match adds to score.
- **Excluded tags** are filters — paper must NOT have any of them.
- **Year range** is a filter — `year >= from_year AND year <= to_year`.
- Tag resolution: use `tag_aliases` to expand tags (e.g. "DFT" → "density functional theory").
- Return `SearchResult` objects with `paper`, `score`, `breakdown`, `matching_units`.

### Step 3: Context pack (`paperdb/search/context.py`)

```python
def assemble_context_pack(query, repo, token_budget=24000, include=None, filters=None) -> ContextPack:
    """Two-stage retrieval + context pack assembly.

    1. Search papers (stage A) — use ranking.rank_papers()
    2. Select top N papers within token budget
    3. For each paper, retrieve relevant search units (stage B)
    4. Assemble context pack:
       - Query and filters
       - Paper summaries (from active summaries)
       - Relevant sections/equations/methods (from search_units)
       - Match explanations
       - Comparison matrix (if multiple papers)
       - Bibliography (BibTeX entries)
    5. Estimate token count (rough: chars/4)
    6. Truncate to token budget
    7. Save to context_packs table if --save requested
    """
```

Context pack format (from §15 of design doc):
```markdown
# Context pack: <query>

## Papers (N selected)

### 1. Macklin_2016_XPBD
**Score**: 23 (title: 5, tags: 8, fts: 10)
**Summary**: ...
**Key equations**: ...
**Relevant sections**: ...

### 2. ...

## Comparison matrix
| Paper | Method | Complexity | ... |
|-------|--------|------------|-----|
| ...   | ...    | ...        | ... |

## Bibliography
@article{Macklin_2016_XPBD, ...}
```

- `include` parameter: list of content types to include (`"equations"`, `"methods"`, `"assumptions"`, `"sections"`, `"summary"`). Default: all.
- `filters`: same as search (required_tags, preferred_tags, year_range, etc.).
- Token budget: rough estimate (chars / 4). Prioritize: summary > equations > methods > sections.
- Context pack is ephemeral by default. Saved to `context_packs` table only when explicitly requested.

### Step 4: Tests

1. Create `tests/paperdb/test_search_retrieval/`:
   - `test_fts.py` — insert search units, verify FTS results, trigger sync
   - `test_ranking.py` — scoring with various tag/title/fts combinations, --explain output
   - `test_context.py` — context pack assembly, token budget truncation, comparison matrix
   - `test_search_units.py` — markdown splitting into units, transactional replacement

## Deliverable checklist

- [ ] `paperdb/search/fts.py` — FTS5 search, markdown-to-search-units splitting
- [ ] `paperdb/search/ranking.py` — weighted scoring with explainable breakdown
- [ ] `paperdb/search/context.py` — context pack assembly with two-stage retrieval
- [ ] Tests in `tests/paperdb/test_search_retrieval/`

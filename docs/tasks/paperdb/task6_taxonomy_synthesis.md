# Task 6: Taxonomy & Synthesis

## Your role

You build the **taxonomy layer** (LLM tag extraction, tag aliases, canonical mapping) and the **synthesis layer** (versioned summaries, method card construction with evidence links, topical overviews/review generation).

## Files you own (ONLY modify these)

```
paperdb/taxonomy/extraction.py      # LLM tag extraction with extended categories
paperdb/taxonomy/aliases.py         # tag consolidation, canonical mapping, raw assertion preservation
paperdb/synthesis/summaries.py      # versioned summaries via pyCruncher.Agent
paperdb/synthesis/method_cards.py   # method card construction with evidence links
paperdb/synthesis/topic_reviews.py  # topical overviews: query → papers → method cards → comparison → synthesis
```

## Files you must NOT touch

- `paperdb/__init__.py`, `paperdb/paths.py`, `paperdb/config.py` — Task 1
- `paperdb/db/*` — Task 1 (you USE repository.py, not modify it)
- `paperdb/identity/*`, `paperdb/ingest/*` — Task 2
- `paperdb/search/*` — Task 3
- `paperdb/cli.py`, `paperdb/mcp.py` — Task 4
- `paperdb/extract/*` — Task 5
- All `__init__.py` files — Task 1

## Reference

Read `docs/topical_audit/paper_db_notes.md` — especially:
- **§6 C7** (tag management) — raw assertions, categories, provisional tags
- **§9** (schema) — `tags`, `tag_aliases`, `paper_tags` (with `run_id`), `summaries`, `methods`, `topics`, `topic_papers`, `topic_overviews` tables
- **§15** (retrieval) — context pack format, comparison matrix
- **§17 Phase 3** (scientific extraction) — tag extraction, versioned summaries
- **§17 Phase 5** (synthesis) — topical overviews, compare methods, tag consolidation
- **§18 D6** (tag taxonomy) — provisional tags first, preserve raw assertions, extended categories
- **§18 D9** (method cards) — source_algorithm vs reconstructed_method

## Dependencies

- **Task 1 must be complete** (or API interface defined). You need:
  - `paperdb.db.repository.Repository` for storing tags, summaries, methods, topics
  - `paperdb.db.models` for `Tag`, `TagAlias`, `PaperTag`, `Summary`, `Method`, `Topic` models
  - `paperdb.config` for LLM config (`get_llm_config()`)
  - `pyCruncher.Agent` for LLM access (all synthesis uses LLM)

- **Task 3** provides search functionality — your `topic_reviews.py` calls `PaperDB.search()` to find relevant papers.
- **Task 5** provides `extract/methods.py` — your `method_cards.py` may complement it (see note below).

## Interface contract

Your modules are called by Task 5's ingest pipeline:

```python
# From your taxonomy/extraction.py
from paperdb.taxonomy.extraction import extract_tags  # called by pipeline

# From your synthesis/summaries.py
from paperdb.synthesis.summaries import generate_summary  # called by pipeline
```

Your `topic_reviews.py` calls Task 3's search and Task 1's PaperDB API:
```python
from paperdb import PaperDB
db = PaperDB()
papers = db.search(query, limit=30)
```

## Steps

### Step 1: Tag extraction (`paperdb/taxonomy/extraction.py`)

```python
def extract_tags(markdown: str, paper_id: int, run_id: int, repo, llm_config=None) -> list[PaperTag]:
    """Extract tags from paper markdown using LLM.
    - Use pyCruncher.Agent with configured LLM
    - Extended tag categories (from §18 D6):
      domain, physical_system, phenomenon, model_or_theory, method, solver,
      data_structure, discretization, task, implementation, software,
      material_or_molecule, user
    - Initially emphasize: domain, physical_system, model_or_theory, task, method,
      solver, data_structure, implementation, software
    - Remaining categories populated when genuinely applicable
    - Empty categories are harmless; noisy invented tags are not
    - Preserve raw tag text in paper_tags.raw_name
    - Store with source='llm', run_id, confidence
    - Canonicalize via aliases.resolve_to_canonical()
    """
```

Key principles (§18 D6):
- **Provisional tags first** — don't try to get it perfect from the start.
- **Preserve raw tag assertions** — store `raw_name` + `canonical_tag_id` + `source` + `confidence`.
- Let data inform classification over time.

### Step 2: Tag aliases (`paperdb/taxonomy/aliases.py`)

```python
def normalize_alias(alias: str) -> str:
    """Lowercase, strip whitespace and punctuation."""

def resolve_to_canonical(alias: str, repo, category=None) -> list[Tag]:
    """Resolve an alias to canonical tag(s).
    Returns list because abbreviations can be ambiguous:
    MD = molecular dynamics OR Markdown
    SCF = self-consistent field OR another domain-specific acronym
    Category and query context resolve ambiguity.
    """

def add_alias(tag_id: int, alias: str, repo):
    """Add a tag alias. Normalizes before storing.
    Uses UNIQUE(tag_id, normalized_alias) — same alias can map to different tags.
    """

def merge_tags(tag_id: int, alias_tag_id: int, repo):
    """Merge one tag into another. Move all paper_tags and tag_aliases.
    Preserve raw_name in paper_tags — don't delete original forms.
    """

def apply_clean_tags_rules(rules_path: str, repo):
    """Apply consolidation rules from clean_tags.py (if available).
    Build tag_aliases table from rules. Preserve raw assertions.
    """

def analyze_tag_distribution(repo) -> dict:
    """Analyze tag distribution: frequency, category coverage, orphan tags.
    Useful for consolidation decisions.
    """
```

Key principle: tag aliases are **NOT globally unique** (§9 schema). `MD` can map to both "molecular dynamics" and "Markdown". The `UNIQUE(tag_id, normalized_alias)` constraint allows this.

### Step 3: Summaries (`paperdb/synthesis/summaries.py`)

```python
def generate_summary(markdown: str, paper_id: int, run_id: int, repo,
                     llm_config=None, prompt_version="v1") -> str:
    """Generate a scientific summary from paper markdown using LLM.
    - Use pyCruncher.Agent with configured LLM
    - Summary structure: Essence, Key equations, Methods, Relevance
    - Store via repo.add_summary() with model_name, prompt_version, is_active=1
    - Previous active summary is deactivated (not deleted — keep history)
    - Summary is expensive to regenerate — keep version history
    Returns summary markdown text.
    """
```

- Summaries are **versioned** — keep history. Deactivate old, don't delete.
- The summary is embedded in the paper's `.md` file (in the "Generated scientific summary" section, clearly separated from source text).

### Step 4: Method cards (`paperdb/synthesis/method_cards.py`)

Note: Task 5's `extract/methods.py` does the initial extraction from Docling structured output. Your `method_cards.py` handles the **reconstruction and enrichment** — building `reconstructed_method` cards from multiple passages using LLM.

```python
def reconstruct_method(paper_id: int, run_id: int, repo, llm_config=None) -> list[Method]:
    """Build reconstructed_method cards from source_algorithm cards + paper text.
    - Read source_algorithm methods (from Task 5's extraction)
    - Read relevant paper sections
    - Use LLM to synthesize a coherent method description
    - method_type='reconstructed_method'
    - card_json contains: assumptions, state_variables, inputs, outputs,
      initialization, steps, boundary_conditions, convergence,
      parallelization, limitations
    - source_passages_json: references back to source passages
    - Link equations via repo.link_method_equation()
    - confidence: LLM self-reported
    Returns list of reconstructed Method objects.
    """
```

Key principle (§18 D9): Every reconstructed field refers back to source passages — lets coding agent distinguish "paper says this" from "model inferred this".

### Step 5: Topic reviews (`paperdb/synthesis/topic_reviews.py`)

```python
def build_topic_review(topic: str, repo, db=None, focus=None, constraints=None,
                       max_papers=30, llm_config=None) -> TopicOverview:
    """Multi-step topical overview generation:
    1. Interpret query → search terms + relevant tags
    2. Find papers: db.search(topic, limit=max_papers)
    3. Retrieve method cards for each paper
    4. Build comparison matrix along relevant axes
    5. Synthesize evidence-backed review using LLM
    6. Store in topics + topic_papers + topic_overviews tables
    Returns TopicOverview with content (markdown).
    """

def build_comparison_matrix(papers: list[Paper], methods: list[Method],
                            axes: list[str], repo) -> dict:
    """Build a comparison matrix across papers along specified axes.
    axes examples: spatial_structure, complexity, synchronization, construction_cost, etc.
    Returns {axes: [...], papers: [...], matrix: [[...]]}
    """
```

- This is the "review paper for LLMs" feature — generates overview documents comparing methods across papers.
- Evidence-backed: every claim in the review links back to specific papers and passages.
- Store in `topics`, `topic_papers`, `topic_overviews` tables.

### Step 6: Tests

1. Create `tests/paperdb/test_taxonomy_synthesis/`:
   - `test_extraction.py` — tag extraction from sample markdown, verify categories, raw_name preservation
   - `test_aliases.py` — alias resolution, ambiguity handling, merge operations
   - `test_summaries.py` — summary generation (mock LLM), versioning, deactivation
   - `test_method_cards.py` — method reconstruction, card_json structure, evidence links
   - `test_topic_reviews.py` — topic review generation (mock search + LLM), comparison matrix

## Deliverable checklist

- [x] `paperdb/taxonomy/extraction.py` — LLM tag extraction with extended categories
- [x] `paperdb/taxonomy/aliases.py` — alias resolution (non-unique), merge, clean_tags rules
- [x] `paperdb/synthesis/summaries.py` — versioned summaries via pyCruncher.Agent
- [x] `paperdb/synthesis/method_cards.py` — method reconstruction with evidence links
- [x] `paperdb/synthesis/topic_reviews.py` — topical overviews with comparison matrix
- [x] Tests in `tests/paperdb/test_taxonomy_synthesis/` (33 tests, all passing)

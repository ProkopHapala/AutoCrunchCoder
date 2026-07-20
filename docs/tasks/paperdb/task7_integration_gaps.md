# Task 7: Integration Gaps & Interface Mismatches

**Status**: Identified during code review (post-parallel implementation)
**Owner**: Integration agent
**Priority**: HIGH — system will not function end-to-end without these fixes

## Problem

During parallel implementation, each agent developed their submodule against an assumed
Repository API. The actual `Repository` class (`paperdb/db/repository.py`, Task 1) uses
Pydantic model objects as parameters, but several submodules call it with keyword arguments.
These mismatches will cause runtime errors when the modules are used together.

## Gap 1: `repo.upsert_paper()` signature mismatch

**Repository API**: `upsert_paper(self, paper: Paper) -> int` — takes a `Paper` Pydantic object.

**Called as** (in `identity/matching.py:136`, `ingest/scanner.py:88`, `ingest/migration.py:325`, `ingest/fetch.py:316`):
```python
repo.upsert_paper(paper_key=..., doi=..., title=..., authors_text=..., year=..., ...)
```

**Fix**: Either change `Repository.upsert_paper` to accept keyword args, or change all callers to construct `Paper(...)` objects before calling.

## Gap 2: `repo.add_paper_file()` signature mismatch

**Repository API**: `add_paper_file(self, pf: PaperFile) -> int` — takes a `PaperFile` object.

**Called as** (in `ingest/scanner.py:52,57,108,118,333`, `ingest/fetch.py:299,333`):
```python
repo.add_paper_file(paper_id=..., path=..., sha256=..., file_size=..., ...)
```

**Fix**: Same pattern — construct `PaperFile(...)` in callers, or change Repository to accept kwargs.

## Gap 3: `repo.upsert_tag()` signature mismatch

**Repository API**: `upsert_tag(self, tag: Tag) -> int` — takes a `Tag` object.

**Called as** (in `ingest/migration.py:285`, `taxonomy/extraction.py:151`):
```python
repo.upsert_tag(canonical_name=..., category=...)
# also: repo.add_tag(canonical_name, category) — method doesn't exist
```

**Fix**: Construct `Tag(...)` or add a convenience wrapper.

## Gap 4: `repo.add_paper_tag()` signature mismatch

**Repository API**: `add_paper_tag(self, pt: PaperTag)` — takes a `PaperTag` object.

**Called as** (in `ingest/migration.py:394`, `taxonomy/extraction.py:165`):
```python
repo.add_paper_tag(paper_id=..., tag_id=..., source=..., run_id=..., confidence=..., raw_name=...)
```

**Fix**: Construct `PaperTag(...)` or change signature.

## Gap 5: `repo.start_run()` signature mismatch

**Repository API**: `start_run(self, run: ProcessingRun) -> int` — takes a `ProcessingRun` object.

**Called as** (in `ingest/migration.py:349,357,365,375,424`):
```python
repo.start_run(paper_id=..., operation=..., backend=..., input_sha256=..., output_path=..., status=...)
```

**Fix**: Construct `ProcessingRun(...)` or change signature.

## Gap 6: `repo.add_summary()` signature mismatch

**Repository API**: `add_summary(self, s: Summary) -> int` — takes a `Summary` object.

**Called as** (in `ingest/migration.py:378`, `synthesis/summaries.py:79`):
```python
repo.add_summary(paper_id=..., run_id=..., model_name=..., prompt_version=..., content=..., is_active=1)
```

**Fix**: Construct `Summary(...)` or change signature.

## Gap 7: Method name mismatches (synthesis)

- `method_cards.py` calls `repo.add_method(...)` → Repository has `upsert_method(m: Method)`
- `method_cards.py` calls `repo.get_methods(paper_id, method_type=...)` → Repository has `get_methods_for_paper(paper_id)` (no method_type filter)
- `topic_reviews.py` calls `repo.add_topic(...)` → Repository has `upsert_topic(t: Topic)`
- `topic_reviews.py` calls `repo.add_topic_paper(...)` → Repository has `add_topic_paper(tp: TopicPaper)`
- `topic_reviews.py` calls `repo.add_topic_overview(...)` → Repository has `save_topic_overview(to: TopicOverview)`

## Gap 8: Missing Repository methods (taxonomy/aliases.py)

The following methods are called in `taxonomy/aliases.py` but do NOT exist in `Repository`:

- `repo.get_tag_by_name(name, category)` — needed by extraction.py too
- `repo.get_tag_by_name_any_category(name)`
- `repo.get_tag_aliases_by_normalized(normalized)`
- `repo.get_tag_by_id(tag_id)`
- `repo.get_paper_tags_by_tag(tag_id)`
- `repo.get_tag_aliases_by_tag(tag_id)`
- `repo.delete_paper_tags_by_tag(tag_id)`
- `repo.delete_tag_aliases_by_tag(tag_id)`
- `repo.delete_tag(tag_id)`
- `repo.get_all_tags()`
- `repo.get_paper_tag_count(tag_id)`
- `repo.count_tag_aliases()`
- `repo.count_paper_tags()`
- `repo.add_tag_alias(tag_id, alias, normalized)` — Repository has `add_alias(tag_id, alias, normalized_alias)`

## Gap 9: `repo.find_file_by_hash()` return type mismatch

**Repository API**: Returns `list[PaperFile]` (multiple files can share a hash).

**Called as** (in `ingest/scanner.py:48`, `ingest/fetch.py:295`):
```python
hash_match = repo.find_file_by_hash(sha)
if hash_match is not None:
    pid = hash_match.get('paper_id')  # expects dict, not list
```

**Fix**: Callers should handle `list[PaperFile]` return, or Repository should return first match.

## Gap 10: `repo.touch_file()` missing

**Called in** `ingest/scanner.py:43`:
```python
if hasattr(repo, 'touch_file'):
    repo.touch_file(file_id)
```

The `hasattr` guard prevents a crash, but the method doesn't exist so `last_seen` is never updated.

## Gap 11: `repo.set_paper_bibtex()` missing

**Called in** `ingest/scanner.py:121`:
```python
if hasattr(repo, 'set_paper_bibtex'):
    repo.set_paper_bibtex(pid, entry['bibtex_raw'])
```

Guarded by `hasattr`, but BibTeX raw text is never stored.

## Gap 12: `repo.get_methods(paper_id, method_type=...)` missing

**Called in** `synthesis/method_cards.py:60`, `synthesis/topic_reviews.py:129`.

Repository only has `get_methods_for_paper(paper_id)` without method_type filtering.

## Gap 13: `repo.supersede_run()` not called by `finish_job()`

`ingest/jobs.py:finish_job()` calls `repo.supersede_run()` but the `get_runs_for_paper` call
inside it uses `run_id` instead of `paper_id` — the logic is confused. The `finish_run` in
Repository doesn't supersede either.

## Recommended Fix Strategy

**Option A (minimal, recommended)**: Add convenience wrapper methods to `Repository` that
accept keyword arguments and construct the Pydantic objects internally. This avoids touching
all the caller sites.

```python
# Example wrappers to add to Repository:
def upsert_paper_kwargs(self, paper_key, doi=None, title=None, ...) -> int:
    return self.upsert_paper(Paper(paper_key=paper_key, doi=doi, title=title, ...))
```

**Option B**: Change all callers to construct Pydantic model objects before calling Repository.
More invasive but cleaner.

## Tests

After fixing, run:
```bash
cd /home/prokop/git/AutoCrunchCoder
python -m pytest tests/paperdb/ -x --tb=short
```

## Deliverable checklist

- [ ] All interface mismatches resolved
- [ ] `python -c "from paperdb import PaperDB; db = PaperDB(); db.status()"` works
- [ ] `python -c "from paperdb import PaperDB; db = PaperDB(); db.search('test')"` works (empty result, no crash)
- [ ] Integration test: scan folder → ingest → search → retrieve_context end-to-end
- [ ] All existing tests still pass

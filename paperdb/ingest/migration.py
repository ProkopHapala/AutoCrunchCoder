"""Phase A legacy migration: convert consolidated.db + existing markdown/summaries into new schema.

Key principles:
- Do NOT re-generate markdown or summaries with LLM — reuse existing.
- Do NOT delete any existing files — copy to ~/paperdb/legacy/ first.
- Record provenance via processing_runs with operation='migrate_markdown'/'migrate_summary'.
- Select best markdown by policy: docling+formulas > docling > vlm > pdfminer.
- Preserve raw tag assertions in paper_tags.raw_name.
- Generate paper_key from authors/year/title or existing stem from legacy DB.
"""

import sqlite3
import os
import re
import json
import shutil
from pathlib import Path
from paperdb.identity.matching import generate_paper_key, resolve_collisions, normalize_doi
from paperdb.identity.hashing import compute_sha256
from paperdb.db.connection import db_transaction
from paperdb.search.fts import build_search_units_from_markdown

# Markdown backend priority (higher = better)
BACKEND_PRIORITY = {'docling': 4, 'docling+formulas': 5, 'vlm': 3, 'pdfminer': 1, 'legacy_docling': 4, 'legacy_pdfminer': 1}

# Tag consolidation rules (from tests/clean_tags.py)
CONSOLIDATION_RULES = {
    "atomic force microscopy (afm)": [r"atomic force microscop", r"\bafm\b", r"noncontact atomic force microscopy", r"nc-afm"],
    "scanning tunneling microscopy (stm)": [r"scanning tunneling microscop", r"\bstm\b"],
    "density functional theory (dft)": [r"density functional theory", r"\bdft\b"],
    "machine learning": [r"machine learning", r"deep learning", r"neural network", r"reinforcement learning"],
    "molecular dynamics (md)": [r"molecular dynamics", r"\bmd simulations?\b"],
}

def _infer_backend(md_path: str, run_name: str = '') -> str:
    """Infer conversion backend from path/run_name."""
    path_lower = (md_path or '').lower()
    run_lower = (run_name or '').lower()
    if 'pdfminer' in path_lower or 'papers_meta' in path_lower or 'pdfminer' in run_lower:
        return 'legacy_pdfminer'
    if 'docling' in path_lower or 'ghost' in path_lower or 'pipeline_new' in path_lower or 'docling' in run_lower:
        return 'legacy_docling'
    if 'vlm' in path_lower or 'vlm' in run_lower:
        return 'vlm'
    return 'legacy_docling'  # default to docling if unknown

def _select_best_md(candidates: list[dict]) -> dict | None:
    """Select best markdown from candidates by backend priority."""
    if not candidates:
        return None
    best = max(candidates, key=lambda c: BACKEND_PRIORITY.get(c['backend'], 0))
    return best

def _find_md_candidates(stem: str, legacy_dir: str) -> list[dict]:
    """Find all markdown files for a given stem in legacy directories."""
    candidates = []
    # Search in per-run directories
    for entry in os.listdir(legacy_dir) if os.path.isdir(legacy_dir) else []:
        run_dir = os.path.join(legacy_dir, entry)
        if not os.path.isdir(run_dir):
            continue
        # markdown/ directory
        md_dir = os.path.join(run_dir, 'markdown')
        if os.path.isdir(md_dir):
            for fname in os.listdir(md_dir):
                if fname.endswith('.md') and stem in fname:
                    md_path = os.path.join(md_dir, fname)
                    backend = _infer_backend(md_path, entry)
                    candidates.append({'path': md_path, 'backend': backend, 'run': entry})
        # shadow tree
        shadow_dir = os.path.join(run_dir, 'shadow')
        if os.path.isdir(shadow_dir):
            for root, dirs, files in os.walk(shadow_dir):
                for fname in files:
                    if fname.endswith('.md') and stem in fname:
                        md_path = os.path.join(root, fname)
                        backend = _infer_backend(md_path, entry)
                        candidates.append({'path': md_path, 'backend': backend, 'run': entry})
    return candidates

def _find_summary(stem: str, legacy_dir: str) -> dict | None:
    """Find best summary for a given stem."""
    candidates = []
    for entry in os.listdir(legacy_dir) if os.path.isdir(legacy_dir) else []:
        run_dir = os.path.join(legacy_dir, entry)
        if not os.path.isdir(run_dir):
            continue
        summary_dir = os.path.join(run_dir, 'summaries')
        if os.path.isdir(summary_dir):
            for fname in os.listdir(summary_dir):
                if fname.endswith('.md') and stem in fname:
                    candidates.append({'path': os.path.join(summary_dir, fname), 'run': entry})
    # Prefer summaries from _pipleline_new (full pipeline) over PAPERS_meta (low quality)
    candidates.sort(key=lambda c: 'pipeline_new' in c['run'], reverse=True)
    return candidates[0] if candidates else None

def _normalize_tag_name(name: str) -> str:
    """Normalize tag name for alias matching."""
    return re.sub(r'[^a-z0-9 ]', '', (name or '').lower()).strip()

def _apply_tag_consolidation(tags: list[dict]) -> tuple[list[dict], list[tuple[str, str]]]:
    """Apply consolidation rules. Returns (consolidated_tags, aliases) where aliases is [(raw_name, canonical_name)]."""
    aliases = []
    result = []
    seen_normalized = {}

    for tag in tags:
        name = tag['name']
        category = tag.get('category', 'unknown')
        normalized = _normalize_tag_name(name)
        matched_canonical = None

        for canonical_name, patterns in CONSOLIDATION_RULES.items():
            for pattern in patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    matched_canonical = canonical_name
                    break
            if matched_canonical:
                break

        if matched_canonical:
            aliases.append((name, matched_canonical))
            canonical = matched_canonical
        else:
            canonical = name

        if canonical not in seen_normalized:
            seen_normalized[canonical] = len(result)
            result.append({'name': canonical, 'category': category})
        else:
            # Merge category if one was unknown
            idx = seen_normalized[canonical]
            if result[idx].get('category') == 'unknown' and category != 'unknown':
                result[idx]['category'] = category

        if name != canonical:
            aliases.append((name, canonical))

    return result, aliases

def _read_legacy_db(db_path: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Read papers, tags, article_tags from legacy consolidated.db."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM papers")
    papers = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM tags")
    tags = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM article_tags")
    article_tags = [dict(r) for r in cur.fetchall()]

    conn.close()
    return papers, tags, article_tags

def _generate_md_bundle(paper_id: int, paper_key: str, md_content: str, summary_content: str, metadata: dict, out_dir: str) -> dict:
    """Generate .md/.json/.bib bundle for a paper. Returns paths."""
    year = metadata.get('year') or 'unknown'
    year_dir = os.path.join(out_dir, 'papers', str(year))
    os.makedirs(year_dir, exist_ok=True)
    base = f"{paper_key}__p{paper_id:04d}"

    md_path = os.path.join(year_dir, f"{base}.md")
    json_path = os.path.join(year_dir, f"{base}.json")
    bib_path = os.path.join(year_dir, f"{base}.bib")

    # Write markdown: YAML frontmatter + summary + source text
    frontmatter = "---\n"
    for key, value in (("paper_id", paper_id), ("paper_key", paper_key), ("doi", metadata.get("doi")),
                       ("title", metadata.get("title")), ("authors", metadata.get("authors")),
                       ("year", metadata.get("year")), ("conversion_backend", metadata.get("backend", "unknown"))):
        if value is not None and value != "": frontmatter += f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
    frontmatter += "---\n\n"

    full_md = frontmatter
    if summary_content:
        full_md += "# Generated scientific summary\n\n> This section was generated from the paper and is not source text.\n\n" + summary_content + "\n\n---\n\n"
    full_md += "# Extracted source text\n\n" + (md_content or '')

    # Atomic write
    _atomic_write(md_path, full_md)

    # Write JSON companion
    json_data = {
        'paper_id': paper_id,
        'paper_key': paper_key,
        'identifiers': {'doi': metadata.get('doi')},
        'conversion': {'backend': metadata.get('backend', 'unknown'), 'status': 'ok'},
        'tags': metadata.get('tags', {}),
    }
    _atomic_write(json_path, json.dumps(json_data, indent=2))

    # Write BibTeX if available
    bibtex = metadata.get('bibtex_text')
    if bibtex:
        _atomic_write(bib_path, bibtex)

    return {'md_path': md_path, 'json_path': json_path, 'bib_path': bib_path if bibtex else None}

def _atomic_write(path: str, content: str):
    """Write file atomically: temp file → rename."""
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(content)
    os.replace(tmp, path)

def _build_search_units(paper_id: int, md_content: str, run_id: int, repo) -> int:
    """Build migration search units through the shared Markdown splitter."""
    return len(build_search_units_from_markdown(paper_id, md_content, run_id, repo))


def _owned_artifact(path: str, source_root: str, copy_root: str) -> str:
    """Return an owned legacy copy for an artifact, copying external candidates."""
    path = os.path.abspath(path)
    try: inside = os.path.commonpath([path, source_root]) == source_root
    except ValueError: inside = False
    if inside:
        owned = os.path.join(copy_root, os.path.relpath(path, source_root))
    else:
        digest = compute_sha256(path)[:16]
        owned = os.path.join(copy_root, 'external_artifacts', f"{digest}_{os.path.basename(path)}")
        os.makedirs(os.path.dirname(owned), exist_ok=True)
        if not os.path.exists(owned): shutil.copy2(path, owned)
    if not os.path.isfile(owned): raise FileNotFoundError(f"Owned legacy artifact missing: {owned}")
    return owned


def _record_artifact_run(repo, paper_id: int, operation: str, backend: str, path: str,
                         model_name: str | None = None, prompt_version: str | None = None) -> tuple[int, bool]:
    input_sha = compute_sha256(path)
    existing = repo.find_equivalent_run(paper_id=paper_id, operation=operation, config_hash='legacy-v1', input_sha256=input_sha,
                                        backend=backend, model_name=model_name, prompt_version=prompt_version)
    if existing:
        return existing.id, False
    run_id = repo.start_run(paper_id=paper_id, operation=operation, backend=backend, model_name=model_name,
                            prompt_version=prompt_version, config_hash='legacy-v1', input_sha256=input_sha, output_path=path)
    repo.finish_run(run_id, status='ok', output_path=path)
    return run_id, True


def migrate_legacy(legacy_dir, repo, data_dir) -> dict:
    """Non-destructively and idempotently import a legacy database and its artifacts."""
    source = os.path.abspath(os.path.expanduser(legacy_dir))
    data_dir = os.path.abspath(os.path.expanduser(data_dir))
    if os.path.isfile(source):
        consolidated_db = source
        legacy_dir = os.path.dirname(source)
    else:
        legacy_dir = source
        consolidated_db = os.path.join(legacy_dir, 'consolidated.db')
    if not os.path.isfile(consolidated_db):
        raise FileNotFoundError(f"consolidated.db not found at {consolidated_db}")

    legacy_copy_dir = os.path.join(data_dir, 'legacy')
    if os.path.commonpath([legacy_copy_dir, legacy_dir]) == legacy_dir:
        raise ValueError('PaperDB data directory must not be inside the legacy source tree')
    os.makedirs(legacy_copy_dir, exist_ok=True)
    shutil.copytree(legacy_dir, legacy_copy_dir, dirs_exist_ok=True)
    copied_db = os.path.join(legacy_copy_dir, os.path.basename(consolidated_db))
    if not os.path.isfile(copied_db):
        shutil.copy2(consolidated_db, copied_db)

    papers, tags, article_tags = _read_legacy_db(copied_db)
    print(f"Legacy: {len(papers)} papers, {len(tags)} tags, {len(article_tags)} article_tags")
    consolidated_tags, tag_aliases_list = _apply_tag_consolidation(tags)
    tag_name_to_id = {}
    for tag in consolidated_tags:
        tid = repo.upsert_tag(canonical_name=tag['name'], category=tag.get('category', 'domain'))
        tag_name_to_id[tag['name'].lower()] = tid
    for raw_name, canonical in tag_aliases_list:
        canonical_id = tag_name_to_id.get(canonical.lower())
        if canonical_id:
            repo.add_alias(tag_id=canonical_id, alias=raw_name, normalized_alias=_normalize_tag_name(raw_name))

    stem_tags = {}
    tag_id_to_name = {tag['id']: tag['name'] for tag in tags}
    for assertion in article_tags:
        tag_name = tag_id_to_name.get(assertion['tag_id'])
        if tag_name:
            stem_tags.setdefault(assertion['article_id'], []).append(tag_name)

    papers_migrated = papers_failed = 0
    conflicts, needs_reprocessing = [], []
    for legacy_paper in papers:
        stem = legacy_paper.get('stem', '')
        try:
            with db_transaction(repo.conn):
                authors = legacy_paper.get('authors', '')
                try:
                    year = int(legacy_paper.get('year')) if legacy_paper.get('year') else None
                except (ValueError, TypeError):
                    year = None
                title = legacy_paper.get('title', '')
                doi = normalize_doi(legacy_paper.get('doi'))
                proposed_key = generate_paper_key(authors, year, title, existing_stem=stem)
                existing = repo.get_paper_by_doi(doi) if doi else repo.get_paper_by_key(proposed_key)
                paper_key = (existing.get('paper_key') if isinstance(existing, dict) else existing.paper_key) if existing else resolve_collisions(proposed_key, repo)
                paper_id = repo.upsert_paper(paper_key=paper_key, doi=doi, title=title, authors_text=authors, year=year,
                                             journal=legacy_paper.get('journal'), keywords=legacy_paper.get('keywords'), essence=legacy_paper.get('essence'))

                candidates = _find_md_candidates(stem, legacy_dir)
                for field in ('md_path', 'shadow_md_path'):
                    candidate_path = legacy_paper.get(field)
                    if candidate_path and os.path.isfile(candidate_path):
                        candidates.append({'path': candidate_path, 'backend': _infer_backend(candidate_path, legacy_paper.get('run_name', '')), 'run': legacy_paper.get('run_name', '')})
                candidates = list({os.path.abspath(candidate['path']): candidate for candidate in candidates}.values())
                candidates = [{**candidate, 'path': _owned_artifact(candidate['path'], legacy_dir, legacy_copy_dir)} for candidate in candidates]
                for candidate in candidates:
                    _record_artifact_run(repo, paper_id, 'migrate_markdown', candidate['backend'], candidate['path'])
                best_md = _select_best_md(candidates)
                md_content = Path(best_md['path']).read_text(encoding='utf-8') if best_md else ''
                md_backend = best_md['backend'] if best_md else 'unknown'

                summary_content = ''
                summary_info = _find_summary(stem, legacy_dir)
                if summary_info and os.path.isfile(summary_info['path']):
                    summary_path = _owned_artifact(summary_info['path'], legacy_dir, legacy_copy_dir)
                    summary_content = Path(summary_path).read_text(encoding='utf-8')
                    summary_run_id, is_new = _record_artifact_run(repo, paper_id, 'migrate_summary', 'legacy_llama8b', summary_path, 'llama-8b', 'legacy')
                    if is_new:
                        repo.add_summary(paper_id=paper_id, run_id=summary_run_id, model_name='llama-8b', prompt_version='legacy', content=summary_content)

                paper_tag_names = stem_tags.get(stem, [])
                for raw_name in paper_tag_names:
                    canonical = next((canon for raw, canon in tag_aliases_list if raw.lower() == raw_name.lower()), raw_name)
                    tag_id = tag_name_to_id.get(canonical.lower())
                    if tag_id is None:
                        tag_id = repo.upsert_tag(canonical_name=canonical, category='domain')
                        tag_name_to_id[canonical.lower()] = tag_id
                    repo.add_paper_tag(paper_id=paper_id, tag_id=tag_id, source='imported', raw_name=raw_name)

                pdf_path = legacy_paper.get('original_pdf_path') or legacy_paper.get('shadow_pdf_path')
                if pdf_path and os.path.isfile(pdf_path):
                    sha = compute_sha256(pdf_path, lazy=True)
                    stat = os.stat(pdf_path)
                    if not repo.find_file_by_hash(sha):
                        repo.add_paper_file(paper_id=paper_id, path=os.path.abspath(pdf_path), sha256=sha, file_size=stat.st_size, modified_time=stat.st_mtime, file_role='publisher')

                tag_dict = {}
                for raw_name in paper_tag_names:
                    category = next((tag.get('category') for tag in tags if tag['name'].lower() == raw_name.lower() and tag.get('category')), 'domain')
                    tag_dict.setdefault(category, []).append(raw_name)
                bundle = _generate_md_bundle(paper_id, paper_key, md_content, summary_content,
                    {'doi': doi, 'title': title, 'authors': authors, 'year': year, 'backend': md_backend, 'tags': tag_dict, 'bibtex_text': legacy_paper.get('bibtex_text')}, data_dir)
                repo.update_paper_paths(paper_id=paper_id, markdown_path=bundle['md_path'], json_path=bundle['json_path'], bibtex_path=bundle['bib_path'])

                compiled_markdown = Path(bundle['md_path']).read_text(encoding='utf-8')
                search_hash_path = bundle['md_path']
                search_run_id, is_new = _record_artifact_run(repo, paper_id, 'build_search_units', 'migration', search_hash_path)
                if is_new or not repo.get_search_units_for_paper(paper_id):
                    _build_search_units(paper_id, compiled_markdown, search_run_id, repo)

                if md_backend in ('legacy_pdfminer', 'pdfminer') or not summary_content:
                    needs_reprocessing.append({'paper_key': paper_key, 'reason': f"backend={md_backend}, has_summary={bool(summary_content)}"})
                papers_migrated += 1
        except Exception as error:
            papers_failed += 1
            conflicts.append({'stem': stem, 'error': str(error), 'title': legacy_paper.get('title', '')})
            print(f"FAILED: stem={stem}, error={error}")

    logs_dir = os.path.join(data_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    report_path = os.path.join(logs_dir, 'migration_report.md')
    _write_report(report_path, papers_migrated, papers_failed, conflicts, needs_reprocessing, len(tags), len(consolidated_tags), len(tag_aliases_list))
    return {'papers_migrated': papers_migrated, 'papers_failed': papers_failed, 'conflicts': conflicts,
            'needs_reprocessing': needs_reprocessing, 'report_path': report_path}

def _write_report(path: str, migrated: int, failed: int, conflicts: list, needs_reproc: list, old_tags: int, new_tags: int, aliases: int):
    """Write migration report to markdown."""
    lines = [
        "# Migration Report\n",
        f"## Summary\n",
        f"- Papers migrated: **{migrated}**",
        f"- Papers failed: **{failed}**",
        f"- Tags before consolidation: {old_tags}",
        f"- Tags after consolidation: {new_tags}",
        f"- Tag aliases created: {aliases}",
        f"- Papers needing reprocessing: {len(needs_reproc)}\n",
    ]
    if conflicts:
        lines.append("## Failed Papers\n")
        lines.append("| Stem | Title | Error |\n|------|-------|-------|\n")
        for c in conflicts:
            lines.append(f"| {c['stem']} | {c.get('title', '')} | {c['error']} |\n")
    if needs_reproc:
        lines.append("\n## Papers Needing Reprocessing\n")
        lines.append("| Paper Key | Reason |\n|-----------|--------|\n")
        for p in needs_reproc:
            lines.append(f"| {p['paper_key']} | {p['reason']} |\n")
    with open(path, 'w') as f:
        f.write(''.join(lines))
    print(f"Migration report written to {path}")

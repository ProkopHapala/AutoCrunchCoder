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
    year = metadata.get('year', 'unknown')
    year_dir = os.path.join(out_dir, 'papers', str(year))
    os.makedirs(year_dir, exist_ok=True)
    base = f"{paper_key}__p{paper_id:04d}"

    md_path = os.path.join(year_dir, f"{base}.md")
    json_path = os.path.join(year_dir, f"{base}.json")
    bib_path = os.path.join(year_dir, f"{base}.bib")

    # Write markdown: YAML frontmatter + summary + source text
    frontmatter = "---\n"
    frontmatter += f"paper_id: {paper_id}\npaper_key: {paper_key}\n"
    if metadata.get('doi'):
        frontmatter += f"doi: {metadata['doi']}\n"
    if metadata.get('title'):
        frontmatter += f"title: {metadata['title']}\n"
    if metadata.get('authors'):
        frontmatter += f"authors: {metadata['authors']}\n"
    if metadata.get('year'):
        frontmatter += f"year: {metadata['year']}\n"
    frontmatter += f"conversion_backend: {metadata.get('backend', 'unknown')}\n"
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

    return {'md_path': md_path, 'json_path': json_path, 'bib_path': bib_path}

def _atomic_write(path: str, content: str):
    """Write file atomically: temp file → rename."""
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(content)
    os.replace(tmp, path)

def _build_search_units(paper_id: int, md_content: str, run_id: int, repo) -> int:
    """Build search_units from markdown by splitting on headings. Returns count."""
    units = []
    current_section = ''
    current_content = []
    for line in md_content.split('\n'):
        if line.startswith('#'):
            if current_content:
                units.append({
                    'paper_id': paper_id,
                    'run_id': run_id,
                    'unit_type': 'section',
                    'source_type': 'section',
                    'section_path': current_section,
                    'content': '\n'.join(current_content).strip(),
                })
            current_section = line.lstrip('#').strip()
            current_content = [line]
        else:
            current_content.append(line)
    if current_content:
        units.append({
            'paper_id': paper_id,
            'run_id': run_id,
            'unit_type': 'section',
            'source_type': 'section',
            'section_path': current_section,
            'content': '\n'.join(current_content).strip(),
        })
    if hasattr(repo, 'replace_search_units'):
        repo.replace_search_units(paper_id, units)
    return len(units)

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
    legacy_dir = os.path.abspath(legacy_dir)
    data_dir = os.path.abspath(data_dir)

    # 1. Copy legacy data to ~/paperdb/legacy/ (non-destructive)
    legacy_copy_dir = os.path.join(data_dir, 'legacy')
    os.makedirs(legacy_copy_dir, exist_ok=True)
    consolidated_db = os.path.join(legacy_dir, 'consolidated.db')
    if not os.path.exists(consolidated_db):
        raise FileNotFoundError(f"consolidated.db not found at {consolidated_db}")

    # Copy consolidated.db if not already copied
    copied_db = os.path.join(legacy_copy_dir, 'consolidated.db')
    if not os.path.exists(copied_db):
        shutil.copy2(consolidated_db, copied_db)

    # 2. Read legacy data
    papers, tags, article_tags = _read_legacy_db(copied_db)
    print(f"Legacy: {len(papers)} papers, {len(tags)} tags, {len(article_tags)} article_tags")

    # 3. Tag consolidation
    consolidated_tags, tag_aliases_list = _apply_tag_consolidation(tags)
    tag_name_to_id = {}
    for tag in consolidated_tags:
        tid = repo.upsert_tag(canonical_name=tag['name'], category=tag.get('category', 'domain'))
        tag_name_to_id[tag['name'].lower()] = tid
    for raw_name, canonical in tag_aliases_list:
        canonical_id = tag_name_to_id.get(canonical.lower())
        if canonical_id:
            normalized = _normalize_tag_name(raw_name)
            repo.add_alias(tag_id=canonical_id, alias=raw_name, normalized_alias=normalized)

    # Build article_tags lookup: stem -> [(tag_name, tag_id)]
    stem_tags = {}
    tag_id_to_name = {t['id']: t['name'] for t in tags}
    for at in article_tags:
        stem = at['article_id']
        tag_name = tag_id_to_name.get(at['tag_id'])
        if tag_name:
            stem_tags.setdefault(stem, []).append(tag_name)

    # 4. Import papers
    papers_migrated = 0
    papers_failed = 0
    conflicts = []
    needs_reprocessing = []

    for p in papers:
        stem = p.get('stem', '')
        try:
            # Generate paper_key
            authors = p.get('authors', '')
            year = p.get('year')
            try:
                year = int(year) if year else None
            except (ValueError, TypeError):
                year = None
            title = p.get('title', '')
            doi = normalize_doi(p.get('doi'))

            paper_key = generate_paper_key(authors, year, title, existing_stem=stem)
            paper_key = resolve_collisions(paper_key, repo)

            # Create paper record
            paper_id = repo.upsert_paper(
                paper_key=paper_key,
                doi=doi,
                title=title,
                authors_text=authors,
                year=year,
                journal=p.get('journal'),
                keywords=p.get('keywords'),
                essence=p.get('essence'),
            )

            # 5. Find and select best markdown
            md_candidates = _find_md_candidates(stem, legacy_dir)
            best_md = _select_best_md(md_candidates)
            md_content = ''
            md_backend = 'unknown'
            md_path = None
            if best_md and os.path.exists(best_md['path']):
                with open(best_md['path'], 'r') as f:
                    md_content = f.read()
                md_backend = best_md['backend']
                md_path = best_md['path']
                # Record processing run for markdown migration
                input_sha = compute_sha256(best_md['path']) if os.path.exists(best_md['path']) else None
                run_id = repo.start_run(paper_id=paper_id, operation='migrate_markdown', backend=md_backend, input_sha256=input_sha, output_path=md_path, status='ok')
                repo.finish_run(run_id, status='ok')
            elif p.get('md_path') and os.path.exists(p['md_path']):
                with open(p['md_path'], 'r') as f:
                    md_content = f.read()
                md_backend = _infer_backend(p['md_path'], p.get('run_name', ''))
                md_path = p['md_path']
                input_sha = compute_sha256(p['md_path'])
                run_id = repo.start_run(paper_id=paper_id, operation='migrate_markdown', backend=md_backend, input_sha256=input_sha, output_path=md_path, status='ok')
                repo.finish_run(run_id, status='ok')
            elif p.get('shadow_md_path') and os.path.exists(p['shadow_md_path']):
                with open(p['shadow_md_path'], 'r') as f:
                    md_content = f.read()
                md_backend = _infer_backend(p['shadow_md_path'], p.get('run_name', ''))
                md_path = p['shadow_md_path']
                input_sha = compute_sha256(p['shadow_md_path'])
                run_id = repo.start_run(paper_id=paper_id, operation='migrate_markdown', backend=md_backend, input_sha256=input_sha, output_path=md_path, status='ok')
                repo.finish_run(run_id, status='ok')

            # 6. Find and import summary
            summary_content = ''
            summary_info = _find_summary(stem, legacy_dir)
            if summary_info and os.path.exists(summary_info['path']):
                with open(summary_info['path'], 'r') as f:
                    summary_content = f.read()
                sum_sha = compute_sha256(summary_info['path'])
                sum_run_id = repo.start_run(paper_id=paper_id, operation='migrate_summary', backend='legacy_llama8b', input_sha256=sum_sha, output_path=summary_info['path'], status='ok')
                repo.finish_run(sum_run_id, status='ok')
                if hasattr(repo, 'add_summary'):
                    repo.add_summary(paper_id=paper_id, run_id=sum_run_id, model_name='llama-8b', prompt_version='legacy', content=summary_content)

            # 7. Import tags
            paper_tag_names = stem_tags.get(stem, [])
            for tag_name in paper_tag_names:
                # Find canonical tag (after consolidation)
                canonical = tag_name
                for raw, canon in tag_aliases_list:
                    if raw.lower() == tag_name.lower():
                        canonical = canon
                        break
                tag_id = tag_name_to_id.get(canonical.lower())
                if tag_id is None:
                    # Create new tag if not in consolidation
                    tag_id = repo.upsert_tag(canonical_name=canonical, category='domain')
                    tag_name_to_id[canonical.lower()] = tag_id
                repo.add_paper_tag(paper_id=paper_id, tag_id=tag_id, source='imported', raw_name=tag_name)

            # 8. Index PDF path if it exists
            pdf_path = p.get('original_pdf_path') or p.get('shadow_pdf_path')
            if pdf_path and os.path.exists(pdf_path):
                sha = compute_sha256(pdf_path, lazy=True)
                st = os.stat(pdf_path)
                existing = repo.find_file_by_hash(sha)
                if not existing:
                    repo.add_paper_file(paper_id=paper_id, path=os.path.abspath(pdf_path), sha256=sha, file_size=st.st_size, modified_time=st.st_mtime, file_role='publisher')

            # 9. Generate .md/.json/.bib bundle
            tag_dict = {}
            for tag_name in paper_tag_names:
                cat = 'domain'  # default
                for t in tags:
                    if t['name'].lower() == tag_name.lower() and t.get('category'):
                        cat = t['category']
                        break
                tag_dict.setdefault(cat, []).append(tag_name)

            bundle = _generate_md_bundle(
                paper_id, paper_key, md_content, summary_content,
                {'doi': doi, 'title': title, 'authors': authors, 'year': year, 'backend': md_backend, 'tags': tag_dict, 'bibtex_text': p.get('bibtex_text')},
                data_dir
            )
            repo.update_paper_paths(paper_id=paper_id, markdown_path=bundle['md_path'], json_path=bundle['json_path'], bibtex_path=bundle.get('bib_path'))

            # 10. Build search units from migrated markdown
            if md_content:
                run_id = repo.start_run(paper_id=paper_id, operation='build_search_units', backend='migration', status='ok')
                _build_search_units(paper_id, md_content, run_id, repo)
                repo.finish_run(run_id, status='ok')

            # Mark needs-reprocessing
            if md_backend in ('legacy_pdfminer', 'pdfminer') or not summary_content:
                needs_reprocessing.append({'paper_key': paper_key, 'reason': f"backend={md_backend}, has_summary={bool(summary_content)}"})

            papers_migrated += 1
        except Exception as e:
            papers_failed += 1
            conflicts.append({'stem': stem, 'error': str(e), 'title': p.get('title', '')})
            print(f"FAILED: stem={stem}, error={e}")

    # 11. Produce migration report
    logs_dir = os.path.join(data_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    report_path = os.path.join(logs_dir, 'migration_report.md')
    _write_report(report_path, papers_migrated, papers_failed, conflicts, needs_reprocessing, len(tags), len(consolidated_tags), len(tag_aliases_list))

    return {
        'papers_migrated': papers_migrated,
        'papers_failed': papers_failed,
        'conflicts': conflicts,
        'needs_reprocessing': needs_reprocessing,
        'report_path': report_path,
    }

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

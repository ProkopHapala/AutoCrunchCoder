"""Tag consolidation, canonical mapping, raw assertion preservation.

Key principle: tag aliases are NOT globally unique (§9 schema).
`MD` can map to both "molecular dynamics" and "Markdown".
The UNIQUE(tag_id, normalized_alias) constraint allows this.

Functions:
- normalize_alias: lowercase, strip whitespace and punctuation
- resolve_to_canonical: resolve alias to canonical tag(s) — returns list due to ambiguity
- add_alias: add a tag alias (normalizes before storing)
- merge_tags: merge one tag into another, preserving raw_name in paper_tags
- apply_clean_tags_rules: apply consolidation rules from clean_tags.py
- analyze_tag_distribution: analyze tag frequency, category coverage, orphans
"""

import re
import json
from typing import Optional
from pathlib import Path

def normalize_alias(alias: str) -> str:
    """Lowercase, strip whitespace and punctuation."""
    s = alias.lower().strip()
    # Remove common punctuation but keep alphanumerics, spaces, hyphens, underscores
    s = re.sub(r'[^\w\s\-]', '', s)
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def resolve_to_canonical(alias: str, repo, category=None) -> list:
    """Resolve an alias to canonical tag(s).

    Returns list because abbreviations can be ambiguous:
      MD = molecular dynamics OR Markdown
      SCF = self-consistent field OR another domain-specific acronym
    Category and query context resolve ambiguity.

    Args:
        alias: Raw tag text to resolve.
        repo: Repository with get_tag_aliases_by_normalized method.
        category: Optional category filter to disambiguate.

    Returns:
        List of tag dicts: [{'id': ..., 'canonical_name': ..., 'category': ...}]
    """
    normalized = normalize_alias(alias)
    if not normalized:
        return []

    # First try the canonical name, then every alias match. Repository errors
    # are contract failures and must not be converted into "no match".
    tag = repo.get_tag_by_name(normalized, category) if category else repo.get_tag_by_name_any_category(normalized)
    if tag:
        return [tag if isinstance(tag, dict) else {'id': tag.id, 'canonical_name': tag.canonical_name, 'category': tag.category}]
    results = []
    for alias_row in repo.get_tag_aliases_by_normalized(normalized):
        if isinstance(alias_row, dict):
            value = {'id': alias_row.get('tag_id', alias_row.get('id')), 'canonical_name': alias_row.get('canonical_name'), 'category': alias_row.get('category')}
        else:
            value = {'id': getattr(alias_row, 'tag_id', getattr(alias_row, 'id', None)), 'canonical_name': getattr(alias_row, 'canonical_name', None), 'category': getattr(alias_row, 'category', None)}
        if category and value.get('category') != category: continue
        if value.get('canonical_name') is None:
            full = repo.get_tag_by_id(value['id'])
            if full: value = full if isinstance(full, dict) else {'id': full.id, 'canonical_name': full.canonical_name, 'category': full.category}
        results.append(value)
    return results

def add_alias(tag_id: int, alias: str, repo):
    """Add a tag alias. Normalizes before storing.

    Uses UNIQUE(tag_id, normalized_alias) — same alias can map to different tags.
    """
    normalized = normalize_alias(alias)
    if not normalized:
        raise ValueError(f"Cannot add empty alias for tag_id={tag_id}")
    repo.add_tag_alias(tag_id, alias, normalized)

def merge_tags(tag_id: int, alias_tag_id: int, repo):
    """Merge a tag transactionally while preserving every raw assertion."""
    if tag_id == alias_tag_id: raise ValueError("Cannot merge a tag into itself")
    from paperdb.db.connection import db_transaction
    with db_transaction(repo.conn):
        for pt in repo.get_paper_tags_by_tag(alias_tag_id):
            data = pt if isinstance(pt, dict) else pt.model_dump()
            repo.add_paper_tag(paper_id=data["paper_id"], tag_id=tag_id, source=data.get("source"), run_id=data.get("run_id"), confidence=data.get("confidence"), raw_name=data.get("raw_name"))
        for alias in repo.get_tag_aliases_by_tag(alias_tag_id):
            data = alias if isinstance(alias, dict) else alias.model_dump()
            repo.add_tag_alias(tag_id=tag_id, alias=data["alias"], normalized_alias=data["normalized_alias"])
        repo.move_tag_assertions(alias_tag_id, tag_id)
        repo.delete_paper_tags_by_tag(alias_tag_id)
        repo.delete_tag_aliases_by_tag(alias_tag_id)
        repo.delete_tag(alias_tag_id)

def apply_clean_tags_rules(rules_path: str, repo):
    """Apply consolidation rules from a clean_tags.py-style rules file.

    The rules file is a Python module with CONSOLIDATION_RULES dict mapping
    canonical names to lists of regex patterns.

    Builds tag_aliases table from rules. Preserves raw assertions.

    Args:
        rules_path: Path to Python file with CONSOLIDATION_RULES dict.
        repo: Repository object.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("clean_tags_rules", rules_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rules = getattr(mod, 'CONSOLIDATION_RULES', {})
    if not rules:
        print("[aliases] No CONSOLIDATION_RULES found in rules file")
        return

    # Get all existing tags
    all_tags = repo.get_all_tags()

    tag_list = []
    for t in all_tags:
        t = t if isinstance(t, dict) else {'id': t.id, 'canonical_name': t.canonical_name, 'category': t.category}
        tag_list.append(t)

    changes = 0
    for canonical_name, patterns in rules.items():
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        # Find all matching tags
        matching = []
        for t in tag_list:
            if t['canonical_name'] == canonical_name:
                continue
            for p in compiled:
                if p.search(t['canonical_name']):
                    matching.append(t)
                    break

        if not matching:
            continue

        # Ensure canonical tag exists
        canonical_tag = None
        for t in tag_list:
            if t['canonical_name'] == canonical_name:
                canonical_tag = t
                break

        if not canonical_tag:
            # Create it — guess category from first match
            cat = matching[0].get('category', 'domain') if matching else 'domain'
            tag_id = repo.add_tag(canonical_name, cat)
            canonical_tag = {'id': tag_id, 'canonical_name': canonical_name, 'category': cat}
            tag_list.append(canonical_tag)
        else:
            tag_id = canonical_tag['id']

        # Merge each matching tag into canonical
        for old_tag in matching:
            print(f"[aliases] Merging '{old_tag['canonical_name']}' -> '{canonical_name}'")
            # Add alias before merging
            add_alias(tag_id, old_tag['canonical_name'], repo)
            merge_tags(tag_id, old_tag['id'], repo)
            changes += 1

    print(f"[aliases] Tag consolidation complete. Merged {changes} tags.")

def analyze_tag_distribution(repo) -> dict:
    """Analyze tag distribution: frequency, category coverage, orphan tags.

    Useful for consolidation decisions.

    Returns:
        {
            'total_tags': int,
            'total_aliases': int,
            'total_paper_tags': int,
            'by_category': {category: {'count': int, 'tags': [(name, freq)]}},
            'orphan_tags': [tag names with 0 paper_tags],
            'top_tags': [(name, freq)] top 20,
        }
    """
    result = {
        'total_tags': 0,
        'total_aliases': 0,
        'total_paper_tags': 0,
        'by_category': {},
        'orphan_tags': [],
        'top_tags': [],
    }

    all_tags = repo.get_all_tags()

    tag_freq = {}
    for t in all_tags:
        t = t if isinstance(t, dict) else {'id': t.id, 'canonical_name': t.canonical_name, 'category': t.category}
        count = repo.get_paper_tag_count(t['id'])
        tag_freq[t['canonical_name']] = count
        cat = t.get('category', 'unknown')
        if cat not in result['by_category']:
            result['by_category'][cat] = {'count': 0, 'tags': []}
        result['by_category'][cat]['count'] += 1
        result['by_category'][cat]['tags'].append((t['canonical_name'], count))

        if count == 0:
            result['orphan_tags'].append(t['canonical_name'])

    result['total_tags'] = len(all_tags)

    result['total_aliases'] = repo.count_tag_aliases()
    result['total_paper_tags'] = repo.count_paper_tags()

    # Sort tags within each category by frequency
    for cat in result['by_category']:
        result['by_category'][cat]['tags'].sort(key=lambda x: -x[1])

    # Top 20 tags overall
    result['top_tags'] = sorted(tag_freq.items(), key=lambda x: -x[1])[:20]

    return result

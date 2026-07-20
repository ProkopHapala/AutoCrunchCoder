"""Weighted scoring with explainable breakdown for paper search ranking."""

from dataclasses import dataclass, field
from typing import Optional
from .fts import fts_search, fts_search_for_papers, SearchUnit


# --- SearchResult (owned by Task 3; Task 1's models.py can import or align) ---

@dataclass
class SearchResult:
    paper: object              # Paper model (duck-typed: id, paper_key, title, year, authors_text, essence, abstract)
    score: int = 0
    breakdown: dict = field(default_factory=dict)
    matching_units: list = field(default_factory=list)  # list of FTS result dicts


# --- Scoring constants (from §15 of design doc) ---

SCORE_REQUIRED_TAG = 10
SCORE_PREFERRED_TAG = 4
SCORE_USER_TAG = 6
SCORE_TITLE = 5
SCORE_ABSTRACT = 2
SCORE_FTS = 1


def rank_papers(query, fts_results, repo, required_tags=None, preferred_tags=None,
                excluded_tags=None, year_range=None, explain=False):
    """Two-stage retrieval:
    Stage A: Select candidate papers from FTS results + tag filters.
    Stage B: Score and rank papers.

    Returns list[SearchResult] sorted by score descending.
    """
    required_tags = required_tags or []
    preferred_tags = preferred_tags or []
    excluded_tags = excluded_tags or []

    # --- Stage A: collect candidate paper_ids from FTS results ---
    fts_by_paper = {}  # paper_id -> list of fts result dicts
    for r in fts_results:
        pid = r['paper_id']
        fts_by_paper.setdefault(pid, []).append(r)

    candidate_ids = set(fts_by_paper.keys())

    # If we have required tags, also include papers that have those tags
    # (they should be candidates even if FTS didn't match, for tag-only search)
    if required_tags and not candidate_ids:
        candidate_ids = _get_paper_ids_with_tags(required_tags, repo, match_all=True)

    if not candidate_ids:
        return []

    # --- Apply filters ---

    # Excluded tags: remove papers that have ANY excluded tag
    if excluded_tags:
        excluded_ids = _get_paper_ids_with_tags(excluded_tags, repo, match_all=False)
        candidate_ids -= excluded_ids

    # Required tags: paper must have ALL required tags
    if required_tags:
        required_ids = _get_paper_ids_with_tags(required_tags, repo, match_all=True)
        candidate_ids &= required_ids

    # Year range filter
    if year_range:
        year_from, year_to = year_range
        candidate_ids = {pid for pid in candidate_ids
                         if _paper_in_year_range(pid, year_from, year_to, repo)}

    if not candidate_ids:
        return []

    # --- Stage B: score and rank ---
    results = []
    query_lower = query.lower()
    query_terms = set(query_lower.split())

    for pid in candidate_ids:
        paper = _get_paper(pid, repo)
        if paper is None:
            continue

        breakdown = {}
        score = 0

        # Title match
        title = (paper.title or '').lower()
        if title and query_lower in title:
            breakdown['title'] = SCORE_TITLE
            score += SCORE_TITLE
        elif title and any(term in title for term in query_terms):
            breakdown['title'] = SCORE_TITLE
            score += SCORE_TITLE

        # Abstract/summary match
        abstract = (paper.abstract or '').lower()
        essence = (paper.essence or '').lower()
        combined = abstract + ' ' + essence
        if query_lower in combined:
            breakdown['abstract'] = SCORE_ABSTRACT
            score += SCORE_ABSTRACT
        elif any(term in combined for term in query_terms):
            breakdown['abstract'] = SCORE_ABSTRACT
            score += SCORE_ABSTRACT

        # Tag scoring
        paper_tags = _get_paper_tags(pid, repo)  # list of (canonical_name, category, source)
        paper_tag_names_lower = {t[0].lower() for t in paper_tags}

        # Preferred tags: +4 per matching tag
        preferred_matches = 0
        for pt in preferred_tags:
            resolved = _resolve_tag(pt, repo)
            if resolved and resolved.lower() in paper_tag_names_lower:
                preferred_matches += SCORE_PREFERRED_TAG
        if preferred_matches:
            breakdown['preferred_tags'] = preferred_matches
            score += preferred_matches

        # User-assigned tags: +6 per user tag
        user_tag_matches = sum(1 for t in paper_tags if t[2] == 'user')
        if user_tag_matches:
            breakdown['user_tags'] = user_tag_matches * SCORE_USER_TAG
            score += user_tag_matches * SCORE_USER_TAG

        # FTS match: +1 per matching unit
        fts_units = fts_by_paper.get(pid, [])
        fts_score = len(fts_units) * SCORE_FTS
        if fts_score:
            breakdown['fts'] = fts_score
            score += fts_score

        # Required tag match: +10 (paper already filtered to have all)
        if required_tags:
            breakdown['required_tags'] = SCORE_REQUIRED_TAG
            score += SCORE_REQUIRED_TAG

        matching_units = fts_units if explain else []

        results.append(SearchResult(
            paper=paper, score=score, breakdown=breakdown,
            matching_units=matching_units
        ))

    # Sort by score descending, then by paper_key for stability
    results.sort(key=lambda r: (-r.score, getattr(r.paper, 'paper_key', '') or ''))
    return results


def search(query, repo, required_tags=None, preferred_tags=None, excluded_tags=None,
           year_range=None, limit=20, explain=False):
    """Full search pipeline: FTS5 → rank_papers. Convenience function for PaperDB.search()."""
    fts_results = fts_search(query, repo, limit=limit * 5)  # over-fetch for ranking
    results = rank_papers(query, fts_results, repo,
                          required_tags=required_tags, preferred_tags=preferred_tags,
                          excluded_tags=excluded_tags, year_range=year_range,
                          explain=explain)
    return results[:limit]


# --- Helper functions (use repo for DB access) ---

def _get_paper(paper_id, repo):
    """Get paper by id. Returns duck-typed Paper object."""
    return repo.get_paper(paper_id)


def _get_paper_ids_with_tags(tag_names, repo, match_all=True):
    """Get set of paper_ids that have the given tags.
    Resolves tag aliases. If match_all=True, paper must have ALL tags (AND).
    If match_all=False, paper must have ANY tag (OR).
    """
    paper_tag_sets = []
    for tn in tag_names:
        resolved = _resolve_tag(tn, repo)
        if resolved is None:
            # Try direct match on canonical_name
            tag_ids = _find_tag_ids(tn, repo)
        else:
            tag_ids = _find_tag_ids(resolved, repo)
        if not tag_ids:
            if match_all:
                return set()  # can't match all if one tag doesn't exist
            continue
        placeholders = ",".join("?" * len(tag_ids))
        sql = f"""
            SELECT DISTINCT paper_id FROM paper_tags
            WHERE tag_id IN ({placeholders})
        """
        rows = repo.conn.execute(sql, tag_ids).fetchall()
        ids = {r[0] for r in rows}
        paper_tag_sets.append(ids)

    if not paper_tag_sets:
        return set()

    if match_all:
        result = paper_tag_sets[0]
        for s in paper_tag_sets[1:]:
            result &= s
        return result
    else:
        result = set()
        for s in paper_tag_sets:
            result |= s
        return result


def _resolve_tag(tag_name, repo):
    """Resolve a tag name through tag_aliases to canonical name. Returns canonical_name or None."""
    normalized = tag_name.lower().strip()
    sql = """
        SELECT t.canonical_name FROM tag_aliases ta
        JOIN tags t ON t.id = ta.tag_id
        WHERE ta.normalized_alias = ?
    """
    row = repo.conn.execute(sql, (normalized,)).fetchone()
    if row:
        return row[0]
    # Also check direct canonical_name match
    sql2 = "SELECT canonical_name FROM tags WHERE lower(canonical_name) = ?"
    row = repo.conn.execute(sql2, (normalized,)).fetchone()
    if row:
        return row[0]
    return None


def _find_tag_ids(tag_name, repo):
    """Find tag_ids for a tag name (canonical or alias)."""
    normalized = tag_name.lower().strip()
    # Check aliases
    sql = "SELECT tag_id FROM tag_aliases WHERE normalized_alias = ?"
    rows = repo.conn.execute(sql, (normalized,)).fetchall()
    ids = [r[0] for r in rows]
    if ids:
        return ids
    # Check canonical name directly
    sql2 = "SELECT id FROM tags WHERE lower(canonical_name) = ?"
    rows = repo.conn.execute(sql2, (normalized,)).fetchall()
    return [r[0] for r in rows]


def _get_paper_tags(paper_id, repo):
    """Get tags for a paper. Returns list of (canonical_name, category, source)."""
    sql = """
        SELECT t.canonical_name, t.category, pt.source
        FROM paper_tags pt
        JOIN tags t ON t.id = pt.tag_id
        WHERE pt.paper_id = ?
    """
    rows = repo.conn.execute(sql, (paper_id,)).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def _paper_in_year_range(paper_id, year_from, year_to, repo):
    """Check if paper's year is within [year_from, year_to]."""
    sql = "SELECT year FROM papers WHERE id = ?"
    row = repo.conn.execute(sql, (paper_id,)).fetchone()
    if row is None or row[0] is None:
        return False
    return year_from <= row[0] <= year_to

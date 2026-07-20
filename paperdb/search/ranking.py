'''Explainable two-stage paper ranking.'''

from dataclasses import dataclass, field

from .fts import fts_search


@dataclass
class SearchResult:
    paper: object
    score: int = 0
    breakdown: dict = field(default_factory=dict)
    matching_units: list = field(default_factory=list)


SCORE_REQUIRED_TAG = 10
SCORE_PREFERRED_TAG = 4
SCORE_USER_TAG = 6
SCORE_TITLE = 5
SCORE_ABSTRACT = 2
SCORE_FTS = 1


def _split_query(query: str) -> tuple[str, list[str]]:
    '''Separate free text from inline ``category:name`` tag constraints.'''
    text, tags = [], []
    for token in query.split():
        if ':' in token and not token.lower().startswith(('http:', 'https:', 'doi:')):
            category, name = token.split(':', 1)
            if category and name:
                tags.append(f"{category}:{name.replace('_', ' ')}")
                continue
        text.append(token)
    return ' '.join(text), tags


def rank_papers(query, fts_results, repo, required_tags=None, preferred_tags=None,
                excluded_tags=None, year_range=None, explain=False):
    required_tags = required_tags or []
    preferred_tags = preferred_tags or []
    excluded_tags = excluded_tags or []
    text_query, inline_tags = _split_query(query)
    required_tags = [*required_tags, *inline_tags]

    fts_by_paper = {}
    for row in fts_results:
        fts_by_paper.setdefault(row['paper_id'], []).append(row)
    candidate_ids = set(fts_by_paper)
    candidate_ids |= _metadata_candidates(text_query, repo)
    for tag in [*required_tags, *preferred_tags]:
        candidate_ids |= _get_paper_ids_with_tags([tag], repo, match_all=False)
    if not text_query and not required_tags and not preferred_tags:
        candidate_ids = {p.id for p in repo.list_papers(limit=100000)}

    if excluded_tags:
        candidate_ids -= _get_paper_ids_with_tags(excluded_tags, repo, match_all=False)
    if required_tags:
        candidate_ids &= _get_paper_ids_with_tags(required_tags, repo, match_all=True)
    if year_range:
        lo, hi = year_range
        candidate_ids = {pid for pid in candidate_ids if _paper_in_year_range(pid, lo, hi, repo)}

    query_lower = text_query.lower().strip()
    query_terms = {term for term in query_lower.split() if term}
    tag_query_names = set()
    for tag in [*required_tags, *preferred_tags]:
        resolved = _resolve_tag_name(tag, repo)
        if resolved:
            tag_query_names.add(resolved.lower())

    results = []
    for pid in candidate_ids:
        paper = repo.get_paper(pid)
        if paper is None:
            continue
        score, breakdown = 0, {}
        title = (paper.title or '').lower()
        if query_lower and (query_lower in title or any(term in title for term in query_terms)):
            breakdown['title'] = SCORE_TITLE; score += SCORE_TITLE
        combined = f"{paper.abstract or ''} {paper.essence or ''}".lower()
        if query_lower and (query_lower in combined or any(term in combined for term in query_terms)):
            breakdown['abstract'] = SCORE_ABSTRACT; score += SCORE_ABSTRACT

        paper_tags = _get_paper_tags(pid, repo)
        names = {name.lower() for name, _, _ in paper_tags}
        preferred_matches = sum(SCORE_PREFERRED_TAG for tag in preferred_tags if (_resolve_tag_name(tag, repo) or '').lower() in names)
        if preferred_matches:
            breakdown['preferred_tags'] = preferred_matches; score += preferred_matches

        matching_user = 0
        for name, _, source in paper_tags:
            name_lower = name.lower()
            mentioned = name_lower in tag_query_names or bool(query_terms & set(name_lower.split()))
            if source == 'user' and mentioned:
                matching_user += 1
        if matching_user:
            breakdown['user_tags'] = matching_user * SCORE_USER_TAG; score += matching_user * SCORE_USER_TAG

        fts_units = sorted(fts_by_paper.get(pid, []), key=lambda row: row.get('rank', 0))
        fts_score = min(len(fts_units), 3) * SCORE_FTS
        if fts_score:
            breakdown['fts'] = fts_score; score += fts_score
        if required_tags:
            breakdown['required_tags'] = len(required_tags) * SCORE_REQUIRED_TAG; score += breakdown['required_tags']
        results.append(SearchResult(paper=paper, score=score, breakdown=breakdown, matching_units=fts_units if explain else []))

    results.sort(key=lambda result: (-result.score, result.matching_units[0].get('rank', 0) if result.matching_units else float('inf'), result.paper.paper_key or ''))
    return results


def search(query, repo, required_tags=None, preferred_tags=None, excluded_tags=None,
           year_range=None, limit=20, explain=False):
    text_query, _ = _split_query(query)
    fts_results = fts_search(text_query, repo, limit=max(limit * 10, 100)) if text_query else []
    results = rank_papers(query, fts_results, repo, required_tags=required_tags,
                          preferred_tags=preferred_tags, excluded_tags=excluded_tags,
                          year_range=year_range, explain=explain)
    return results[:limit]


def _metadata_candidates(query, repo):
    terms = [term.lower() for term in query.split() if term]
    if not terms:
        return set()
    clause = "lower(COALESCE(title,'') || ' ' || COALESCE(abstract,'') || ' ' || COALESCE(essence,'')) LIKE ?"
    rows = repo.conn.execute(f"SELECT id FROM papers WHERE {' OR '.join(clause for _ in terms)}", tuple(f"%{term}%" for term in terms)).fetchall()
    return {row[0] for row in rows}


def _parse_tag_ref(tag):
    if isinstance(tag, (list, tuple)) and len(tag) == 2:
        return str(tag[0]).strip(), str(tag[1]).strip()
    text = str(tag).strip()
    if ':' in text:
        category, name = text.split(':', 1)
        return category.strip(), name.strip().replace('_', ' ')
    return None, text


def _tag_ids(tag, repo):
    category, name = _parse_tag_ref(tag)
    normalized = name.lower()
    sql = "SELECT DISTINCT t.id FROM tags t LEFT JOIN tag_aliases a ON a.tag_id=t.id WHERE (lower(t.canonical_name)=? OR a.normalized_alias=?)"
    params = [normalized, normalized]
    if category:
        sql += ' AND lower(t.category)=?'
        params.append(category.lower())
    return [row[0] for row in repo.conn.execute(sql, tuple(params)).fetchall()]


def _resolve_tag_name(tag, repo):
    ids = _tag_ids(tag, repo)
    if not ids:
        return None
    row = repo.conn.execute('SELECT canonical_name FROM tags WHERE id=?', (ids[0],)).fetchone()
    return row[0] if row else None


def _get_paper_ids_with_tags(tags, repo, match_all=True):
    sets = []
    for tag in tags:
        ids = _tag_ids(tag, repo)
        if not ids:
            if match_all:
                return set()
            continue
        placeholders = ','.join('?' for _ in ids)
        rows = repo.conn.execute(f'SELECT DISTINCT paper_id FROM paper_tags WHERE tag_id IN ({placeholders})', ids).fetchall()
        sets.append({row[0] for row in rows})
    if not sets:
        return set()
    return set.intersection(*sets) if match_all else set.union(*sets)


def _get_paper_tags(paper_id, repo):
    sql = 'SELECT DISTINCT t.canonical_name, t.category, pt.source FROM paper_tags pt JOIN tags t ON t.id=pt.tag_id WHERE pt.paper_id=?'
    rows = repo.conn.execute(sql, (paper_id,)).fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def _paper_in_year_range(paper_id, year_from, year_to, repo):
    row = repo.conn.execute('SELECT year FROM papers WHERE id=?', (paper_id,)).fetchone()
    return bool(row and row[0] is not None and year_from <= row[0] <= year_to)

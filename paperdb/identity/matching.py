"""Paper identity: semantic paper_key generation and multi-criteria dedup.

Dedup priority: SHA-256 (exact) > DOI (normalized) > title+authors+year (fuzzy).
paper_key format: FirstAuthor_Year_Keyword (e.g. Macklin_2016_XPBD).
"""

import re
from difflib import SequenceMatcher
from paperdb.identity.hashing import compute_sha256
from paperdb.identity.metadata import normalize_doi

_STOPWORDS = {'the', 'a', 'an', 'of', 'for', 'and', 'on', 'in', 'with', 'to', 'from', 'by', 'via', 'using'}

def _first_author_lastname(authors: str) -> str:
    """Extract first author's lastname from 'Last, First; Last2, First2' or 'First Last and First2 Last2'."""
    if not authors:
        return 'Unknown'
    first = authors.split(';')[0].split(' and ')[0].strip()
    if ',' in first:
        return first.split(',')[0].strip()
    parts = first.split()
    if len(parts) >= 2:
        return parts[-1]  # "Miles Macklin" -> "Macklin"
    return first

def _title_keyword(title: str) -> str:
    """Extract first significant word from title (skip stopwords)."""
    if not title:
        return 'Untitled'
    words = re.findall(r'[A-Za-z0-9]+', title)
    for w in words:
        if w.lower() not in _STOPWORDS and len(w) > 1:
            return w
    return words[0] if words else 'Untitled'

def _sanitize_key(s: str) -> str:
    """Sanitize a string for use in paper_key: alphanumeric + underscore only."""
    return re.sub(r'[^A-Za-z0-9_]', '', s)

def generate_paper_key(authors, year, title, existing_stem=None) -> str:
    """Generate semantic paper_key: Author_Year_Keyword (e.g. Macklin_2016_XPBD)."""
    if existing_stem:
        return _sanitize_key(existing_stem)
    lastname = _sanitize_key(_first_author_lastname(authors))
    yr = str(year) if year else '0000'
    keyword = _sanitize_key(_title_keyword(title))
    return f"{lastname}_{yr}_{keyword}"

def resolve_collisions(paper_key: str, repo) -> str:
    """If paper_key exists in DB, append _2, _3, etc."""
    base = paper_key
    suffix = 2
    while repo.get_paper_by_key(paper_key) is not None:
        paper_key = f"{base}_{suffix}"
        suffix += 1
    return paper_key

def match_by_hash(hash_value, repo) -> int | None:
    """Find existing paper by SHA-256 in paper_files."""
    rows = repo.find_file_by_hash(hash_value)
    if not rows:
        return None
    row = rows[0]
    return row.get('paper_id') if isinstance(row, dict) else row.paper_id

def match_by_doi(doi, repo) -> int | None:
    """Find existing paper by normalized DOI."""
    if not doi:
        return None
    ndoi = normalize_doi(doi)
    row = repo.get_paper_by_doi(ndoi)
    if row is None:
        return None
    return row.get('id') if isinstance(row, dict) else row.id

def _normalize_title(s: str) -> str:
    """Normalize title for fuzzy matching: lowercase, strip punctuation."""
    return re.sub(r'[^a-z0-9 ]', '', (s or '').lower()).strip()

def _normalize_authors(s: str) -> str:
    """Normalize authors: lowercase, strip punctuation, split into tokens."""
    return re.sub(r'[^a-z0-9 ]', '', (s or '').lower()).strip()

def match_by_metadata(title, authors, year, repo) -> int | None:
    """Fuzzy match by title+authors+year. Uses SequenceMatcher, not embeddings."""
    if not title:
        return None
    norm_title = _normalize_title(title)
    norm_authors = _normalize_authors(authors)
    best_id = None
    best_score = 0.0
    for p in repo.list_papers():
        p_title = _normalize_title(p.get('title') if isinstance(p, dict) else p.title)
        title_sim = SequenceMatcher(None, norm_title, p_title).ratio()
        if title_sim < 0.6:
            continue
        p_authors = _normalize_authors(p.get('authors_text') if isinstance(p, dict) else p.authors_text)
        author_sim = SequenceMatcher(None, norm_authors, p_authors).ratio() if norm_authors and p_authors else 0.5
        p_year = p.get('year') if isinstance(p, dict) else p.year
        year_match = 1.0 if year and p_year and int(year) == int(p_year) else 0.0
        score = title_sim * 0.6 + author_sim * 0.2 + year_match * 0.2
        if score > best_score and score >= 0.7:
            best_score = score
            best_id = p.get('id') if isinstance(p, dict) else p.id
    return best_id

def find_or_create_paper(pdf_path, repo, metadata=None) -> tuple[int, bool]:
    """Try all match methods. Return (paper_id, was_created)."""
    metadata = metadata or {}

    # 1. Hash match (exact)
    sha = compute_sha256(pdf_path)
    pid = match_by_hash(sha, repo)
    if pid is not None:
        return (pid, False)

    # 2. DOI match
    doi = metadata.get('doi')
    if doi:
        pid = match_by_doi(doi, repo)
        if pid is not None:
            return (pid, False)

    # 3. Metadata fuzzy match
    title = metadata.get('title')
    authors = metadata.get('authors') or metadata.get('authors_text')
    year = metadata.get('year')
    pid = match_by_metadata(title, authors, year, repo)
    if pid is not None:
        return (pid, False)

    # 4. No match — create new paper
    paper_key = generate_paper_key(authors, year, title, existing_stem=metadata.get('stem'))
    paper_key = resolve_collisions(paper_key, repo)
    ndoi = normalize_doi(doi) if doi else None

    paper_id = repo.upsert_paper(
        paper_key=paper_key,
        doi=ndoi,
        arxiv_id=metadata.get('arxiv_id'),
        title=title,
        authors_text=authors,
        year=int(year) if year else None,
        journal=metadata.get('journal'),
        abstract=metadata.get('abstract'),
        keywords=metadata.get('keywords'),
        essence=metadata.get('essence'),
    )
    return (paper_id, True)

"""PDF scanner: find PDFs in folders, compute hashes, match to papers, store paths.

PDFs stay in place — never move, copy, or rename.
Detect moved PDFs: if hash matches but path differs, update path.
"""

import os
import glob
from paperdb.identity.hashing import compute_sha256
from paperdb.identity.matching import find_or_create_paper, match_by_hash
from paperdb.identity.metadata import parse_bibtex, normalize_doi, match_bibtex_to_paper

def scan_folder(folder_path, recursive=True, repo=None) -> list[dict]:
    """Find all PDFs in folder. For each:
    1. Compute SHA-256 (lazy)
    2. Match to existing paper (hash, DOI from filename, metadata)
    3. If no match, create new paper record
    4. Add paper_files entry
    Returns list of {paper_id, path, was_new, matched_by}
    """
    if repo is None:
        raise ValueError("repo is required for scan_folder")
    pattern = os.path.join(folder_path, '**', '*.pdf') if recursive else os.path.join(folder_path, '*.pdf')
    pdfs = sorted(glob.glob(pattern, recursive=recursive))
    results = []
    for pdf in pdfs:
        result = _index_pdf(pdf, repo)
        results.append(result)
    return results

def _index_pdf(pdf_path: str, repo) -> dict:
    """Index a single PDF: hash, match/create paper, add file record."""
    abspath = os.path.abspath(pdf_path)
    sha = compute_sha256(abspath, lazy=True)
    st = os.stat(abspath)

    # Check if this exact path is already indexed
    existing_file = repo.find_file_by_path(abspath) if hasattr(repo, 'find_file_by_path') else None
    if existing_file is not None:
        # Already indexed at this path — update last_seen
        file_id = existing_file.get('id') if isinstance(existing_file, dict) else existing_file.id
        if hasattr(repo, 'touch_file'):
            repo.touch_file(file_id)
        pid = existing_file.get('paper_id') if isinstance(existing_file, dict) else existing_file.paper_id
        return {'paper_id': pid, 'path': abspath, 'was_new': False, 'matched_by': 'existing_path'}

    # Check if hash matches an existing file (moved PDF)
    hash_matches = repo.find_file_by_hash(sha)
    if hash_matches:
        hm = hash_matches[0]
        pid = hm.get('paper_id') if isinstance(hm, dict) else hm.paper_id
        # Add new path for existing paper
        repo.add_paper_file(paper_id=pid, path=abspath, sha256=sha, file_size=st.st_size, modified_time=st.st_mtime, file_role='duplicate')
        return {'paper_id': pid, 'path': abspath, 'was_new': False, 'matched_by': 'hash_moved'}

    # Try to match/create paper
    pid, was_created = find_or_create_paper(abspath, repo)
    repo.add_paper_file(paper_id=pid, path=abspath, sha256=sha, file_size=st.st_size, modified_time=st.st_mtime, file_role='publisher')
    return {'paper_id': pid, 'path': abspath, 'was_new': was_created, 'matched_by': 'created' if was_created else 'metadata'}

def scan_mendeley(bibtex_path, pdf_folder, repo=None) -> list[dict]:
    """Scan Mendeley: parse BibTeX, match PDFs by filename/DOI, import metadata."""
    if repo is None:
        raise ValueError("repo is required for scan_mendeley")
    with open(bibtex_path, 'r') as f:
        entries = parse_bibtex(f.read())
    results = []
    for entry in entries:
        result = _import_mendeley_entry(entry, pdf_folder, repo)
        if result:
            results.append(result)
    return results

def _import_mendeley_entry(entry: dict, pdf_folder: str, repo) -> dict | None:
    """Import a single Mendeley BibTeX entry + its PDF."""
    # 1. Try to match to existing paper
    pid = match_bibtex_to_paper(entry, repo)
    was_new = False

    if pid is None:
        # Create new paper from BibTeX metadata
        from paperdb.identity.matching import generate_paper_key, resolve_collisions
        authors = entry.get('authors', '')
        year = entry.get('year')
        title = entry.get('title', '')
        paper_key = generate_paper_key(authors, year, title, existing_stem=entry.get('entry_id'))
        paper_key = resolve_collisions(paper_key, repo)
        doi = entry.get('doi')
        pid = repo.upsert_paper(
            paper_key=paper_key,
            doi=doi,
            title=title,
            authors_text=authors,
            year=year,
            journal=entry.get('journal'),
            abstract=entry.get('abstract'),
            keywords=entry.get('keywords'),
        )
        was_new = True

    # 2. Find and index the PDF
    pdf_path = entry.get('pdf_path')
    if pdf_path and os.path.exists(pdf_path):
        sha = compute_sha256(pdf_path, lazy=True)
        st = os.stat(pdf_path)
        # Check if file already indexed
        existing = repo.find_file_by_hash(sha)
        if not existing:
            repo.add_paper_file(paper_id=pid, path=os.path.abspath(pdf_path), sha256=sha, file_size=st.st_size, modified_time=st.st_mtime, file_role='mendeley')
    elif pdf_path:
        # Try to find PDF in pdf_folder by filename
        basename = os.path.basename(pdf_path)
        candidate = os.path.join(pdf_folder, basename)
        if os.path.exists(candidate):
            sha = compute_sha256(candidate, lazy=True)
            st = os.stat(candidate)
            existing = repo.find_file_by_hash(sha)
            if not existing:
                repo.add_paper_file(paper_id=pid, path=os.path.abspath(candidate), sha256=sha, file_size=st.st_size, modified_time=st.st_mtime, file_role='mendeley')

    # 3. Store BibTeX text if available
    if entry.get('bibtex_raw') and hasattr(repo, 'set_paper_bibtex'):
        repo.set_paper_bibtex(pid, entry['bibtex_raw'])

    return {'paper_id': pid, 'entry_id': entry.get('entry_id'), 'was_new': was_new, 'title': entry.get('title')}

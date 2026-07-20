"""DOI normalization, BibTeX parsing, CrossRef/arXiv metadata lookup.

Reuses pyCruncher.bib_utils.decode_latex for LaTeX accent decoding if available.
Falls back to bibtexparser directly for structured parsing.
"""

import re
import os
import xml.etree.ElementTree as ET
import requests

# Optional: reuse LaTeX decoding from pyCruncher
try:
    from pyCruncher.bib_utils import decode_latex as _decode_latex_pyCruncher
except ImportError:
    _decode_latex_pyCruncher = None

_LATEX_ACCENTS = {
    r'{\"u}': 'ü', r'{\"a}': 'ä', r'{\"o}': 'ö',
    r"{\'e}": 'é', r"{\'a}": 'á', r"{\'i}": 'í', r"{\'o}": 'ó', r"{\'u}": 'ú',
    r'\\"u': 'ü', r'\\"a': 'ä', r'\\"o': 'ö',
    r"\\'e": 'é', r"\\'a": 'á', r"\\'i": 'í', r"\\'o": 'ó', r"\\'u": 'ú',
    r'\`a': 'à', r'\`e': 'è',
    r'\^a': 'â', r'\^e': 'ê', r'\^o': 'ô',
    r'\~n': 'ñ', r'\~N': 'Ñ',
    r'\ss': 'ß', r'\aa': 'å', r'\AA': 'Å',
    r'\ae': 'æ', r'\AE': 'Æ',
    r'\o': 'ø', r'\O': 'Ø',
    r'\l': 'ł', r'\L': 'Ł',
}

def decode_latex(s):
    """Decode LaTeX-encoded string to Unicode. Tries pyCruncher.bib_utils first, then simple fallback."""
    if not s:
        return s
    if _decode_latex_pyCruncher:
        try:
            return _decode_latex_pyCruncher(s)
        except Exception:
            pass
    # Simple fallback: replace common LaTeX accents
    result = s
    for latex, unicode_char in _LATEX_ACCENTS.items():
        result = result.replace(latex, unicode_char)
    # Also handle backslash-stripped versions (bibtexparser sometimes strips \)
    result = result.replace('{"u}', 'ü').replace('{"a}', 'ä').replace('{"o}', 'ö')
    result = result.replace("{'e}", 'é').replace("{'a}", 'á').replace("{'i}", 'í')
    result = result.replace("{'o}", 'ó').replace("{'u}", 'ú')
    # Strip remaining braces
    result = re.sub(r'\{(.+?)\}', r'\1', result)
    return result

import bibtexparser

# --- DOI normalization ---

def normalize_doi(doi) -> str:
    """Normalize DOI: lowercase, strip https://doi.org/, doi: prefixes."""
    if not doi:
        return None
    s = doi.strip()
    for prefix in ('https://doi.org/', 'http://doi.org/', 'doi.org/', 'doi:', 'DOI:', 'DOI '):
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix):]
            break
    return s.strip().lower()

# --- BibTeX parsing ---

def parse_bibtex(bibtex_text: str) -> list[dict]:
    """Parse BibTeX entries. Returns list of dicts with normalized fields."""
    db = bibtexparser.loads(bibtex_text)
    results = []
    for entry in db.entries:
        title = entry.get('title', '').strip()
        if title.startswith('{') and title.endswith('}'):
            title = title[1:-1]
        title = decode_latex(title)
        authors = decode_latex(entry.get('author', ''))
        doi = normalize_doi(entry.get('doi'))
        keywords = decode_latex(entry.get('keywords', ''))
        abstract = decode_latex(entry.get('abstract', ''))
        year = entry.get('year')
        try:
            year = int(year) if year else None
        except ValueError:
            year = None
        # Mendeley file field: ":/path/to/file.pdf:pdf" → clean path
        file_field = entry.get('file', '')
        pdf_path = None
        if file_field:
            pdf_path = file_field
            if pdf_path.startswith(':'):
                pdf_path = pdf_path[1:]
            if pdf_path.endswith(':pdf'):
                pdf_path = pdf_path[:-4]
            pdf_path = decode_latex(pdf_path)
        results.append({
            'entry_id': entry.get('ID'),
            'entry_type': entry.get('ENTRYTYPE'),
            'title': title,
            'authors': authors,
            'year': year,
            'doi': doi,
            'journal': decode_latex(entry.get('journal', '')),
            'keywords': keywords,
            'abstract': abstract,
            'url': entry.get('url', ''),
            'pdf_path': pdf_path,
            'bibtex_raw': bibtexparser.dumps([entry]),
        })
    return results

def match_bibtex_to_paper(entry: dict, repo) -> int | None:
    """Match a BibTeX entry to an existing paper by DOI, title, or filename."""
    # 1. DOI match
    doi = entry.get('doi')
    if doi:
        row = repo.get_paper_by_doi(doi)
        if row is not None:
            return row.get('id') if isinstance(row, dict) else row.id
    # 2. Title fuzzy match
    from paperdb.identity.matching import match_by_metadata
    pid = match_by_metadata(entry.get('title'), entry.get('authors'), entry.get('year'), repo)
    if pid is not None:
        return pid
    # 3. Filename match — try to match pdf_path to existing paper_files
    pdf_path = entry.get('pdf_path')
    if pdf_path and os.path.basename(pdf_path):
        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        row = repo.get_paper_by_key(stem)
        if row is not None:
            return row.get('id') if isinstance(row, dict) else row.id
    return None

def local_pdf_metadata(pdf_path: str) -> dict:
    """Extract conservative local metadata for semantic identity without modifying the PDF."""
    from pathlib import Path
    stem = Path(pdf_path).stem
    metadata = {"stem": stem}
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None
    if PdfReader is not None:
        reader = PdfReader(pdf_path)
        doc = reader.metadata or {}
        title = str(doc.get("/Title") or "").strip()
        author = str(doc.get("/Author") or "").strip()
        if title: metadata["title"] = title
        if author: metadata["authors"] = author
        creation = str(doc.get("/CreationDate") or "")
        year_match = re.search(r"(?:19|20)\d{2}", creation)
        if year_match: metadata["year"] = int(year_match.group(0))
    tokens = [t for t in re.split(r"[_\-]+", stem) if t]
    if "year" not in metadata:
        year_token = next((t for t in tokens if re.fullmatch(r"(?:19|20)\d{2}", t)), None)
        if year_token: metadata["year"] = int(year_token)
    if "authors" not in metadata and tokens:
        metadata["authors"] = tokens[0]
    if "title" not in metadata:
        title_tokens = [t for t in tokens[1:] if not re.fullmatch(r"(?:19|20)\d{2}", t)]
        metadata["title"] = " ".join(title_tokens) or stem
    return metadata

# --- CrossRef lookup ---

CROSSREF_API = 'https://api.crossref.org/works/'

def crossref_lookup(doi: str) -> dict:
    """Fetch metadata from CrossRef API by DOI. Returns title, authors, year, journal."""
    ndoi = normalize_doi(doi)
    if not ndoi:
        raise ValueError(f"Invalid DOI: {doi}")
    url = CROSSREF_API + ndoi
    resp = requests.get(url, headers={'User-Agent': 'paperdb/0.1 (mailto:prokop@example.com)'}, timeout=30)
    resp.raise_for_status()
    data = resp.json()['message']
    title = data.get('title', [''])[0] if data.get('title') else None
    authors = []
    for a in data.get('author', []):
        name = f"{a.get('family', '')}, {a.get('given', '')}".strip(', ')
        authors.append(name)
    authors_text = '; '.join(authors)
    year = None
    for date_field in ('published-print', 'published-online', 'issued', 'created'):
        if date_field in data and data[date_field].get('date-parts'):
            parts = data[date_field]['date-parts'][0]
            if parts and parts[0]:
                year = parts[0]
                break
    journal = data.get('container-title', [''])[0] if data.get('container-title') else None
    abstract = data.get('abstract', '')
    return {
        'doi': ndoi,
        'title': title,
        'authors': authors_text,
        'year': year,
        'journal': journal,
        'abstract': abstract,
    }

# --- arXiv lookup ---

ARXIV_API = 'http://export.arxiv.org/api/query'

def arxiv_lookup(arxiv_id: str) -> dict:
    """Fetch metadata from arXiv API."""
    arxiv_id = arxiv_id.strip()
    if arxiv_id.startswith('http'):
        arxiv_id = arxiv_id.rstrip('/').split('/')[-1]
    if arxiv_id.startswith('arXiv:'):
        arxiv_id = arxiv_id[6:]
    url = f"{ARXIV_API}?id_list={arxiv_id}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entry = root.find('atom:entry', ns)
    if entry is None:
        raise ValueError(f"arXiv entry not found for: {arxiv_id}")
    title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
    title = re.sub(r'\s+', ' ', title)
    authors = []
    for author in entry.findall('atom:author', ns):
        name = author.find('atom:name', ns).text
        parts = name.split()
        if len(parts) >= 2:
            authors.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
        else:
            authors.append(name)
    authors_text = '; '.join(authors)
    published = entry.find('atom:published', ns).text
    year = int(published[:4]) if published else None
    abstract = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
    abstract = re.sub(r'\s+', ' ', abstract)
    # PDF link
    pdf_url = None
    for link in entry.findall('atom:link', ns):
        if link.get('title') == 'pdf':
            pdf_url = link.get('href')
    return {
        'arxiv_id': arxiv_id,
        'title': title,
        'authors': authors_text,
        'year': year,
        'abstract': abstract,
        'pdf_url': pdf_url,
    }

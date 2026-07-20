"""Internet fetch — download PDFs + metadata from DOI/URL.

Supports:
- CrossRef API: fetch metadata by DOI
- arXiv API: fetch metadata + PDF download
- Direct URL: download PDF from a URL

Uses paperdb.identity.metadata (Task 2) for crossref_lookup and arxiv_lookup
if available. Falls back to direct API calls if Task 2 is not ready.
"""
import os, re, logging, hashlib
from pathlib import Path
from typing import Optional
import urllib.request, urllib.error

from ..db.models import Paper, PaperFile

logger = logging.getLogger(__name__)

CROSSREF_API = "https://api.crossref.org/works/{doi}"
CROSSREF_BIBTEX_API = "https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
ARXIV_API = "http://export.arxiv.org/api/query?id_list={arxiv_id}"
ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}"


def _http_get(url: str, headers: Optional[dict] = None, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _http_get_text(url: str, headers: Optional[dict] = None, timeout: int = 30) -> str:
    return _http_get(url, headers, timeout).decode("utf-8", errors="replace")


def _download_file(url: str, dest_path: str, timeout: int = 120) -> str:
    """Download a file from URL to dest_path. Returns dest_path."""
    data = _http_get(url, timeout=timeout)
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(data)
    return dest_path


def _compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_doi(doi: str) -> str:
    """Normalize DOI: lowercase, strip prefixes."""
    d = doi.strip().lower()
    d = re.sub(r'^https?://(dx\.)?doi\.org/', '', d)
    d = re.sub(r'^doi:\s*', '', d)
    return d


def _detect_arxiv_id(s: str) -> Optional[str]:
    """Detect arXiv ID from string (URL, ID, etc.)."""
    s = s.strip()
    # Direct ID: 2401.02058 or 2401.02058v1
    if re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', s):
        return s
    # From URL: https://arxiv.org/abs/2401.02058
    m = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)', s)
    if m:
        return m.group(1)
    # Old-style: hep-th/9901001
    m = re.match(r'^([a-z-]+/\d{7})$', s)
    if m:
        return m.group(1)
    return None


def _detect_doi(s: str) -> Optional[str]:
    """Detect DOI from string."""
    s = s.strip()
    # Direct DOI: 10.xxxx/...
    if re.match(r'^10\.\d{4,}/', s):
        return _normalize_doi(s)
    # From URL: https://doi.org/10.xxxx/...
    m = re.search(r'doi\.org/(10\.\d{4,}/.+)', s, re.IGNORECASE)
    if m:
        return _normalize_doi(m.group(1))
    return None


def fetch_by_doi(doi: str, dest_dir: str) -> dict:
    """Fetch paper metadata from CrossRef, attempt to find/download PDF.

    Returns:
        {metadata, pdf_path (or None)}
    """
    doi = _normalize_doi(doi)

    # Try Task 2's crossref_lookup first
    try:
        from ..identity.metadata import crossref_lookup
        metadata = crossref_lookup(doi)
    except ImportError:
        metadata = _crossref_lookup_direct(doi)

    if not metadata:
        raise RuntimeError(f"CrossRef lookup failed for DOI: {doi}")

    # Try to find PDF — CrossRef sometimes has a link to full-text
    pdf_path = None
    pdf_url = metadata.get("pdf_url")
    if pdf_url:
        try:
            filename = f"{doi.replace('/', '_')}.pdf"
            pdf_path = _download_file(pdf_url, os.path.join(dest_dir, filename))
            logger.info(f"Downloaded PDF: {pdf_path}")
        except Exception as e:
            logger.warning(f"PDF download failed for DOI {doi}: {e}")

    return {"metadata": metadata, "pdf_path": pdf_path}


def _crossref_lookup_direct(doi: str) -> dict:
    """Direct CrossRef API call (fallback when Task 2 is not available)."""
    import json
    url = CROSSREF_API.format(doi=doi)
    try:
        text = _http_get_text(url)
        data = json.loads(text)
        msg = data.get("message", {})
        authors = []
        for a in msg.get("author", []):
            name = f"{a.get('given', '')} {a.get('family', '')}".strip()
            authors.append(name)
        return {
            "doi": doi,
            "title": msg.get("title", [""])[0] if msg.get("title") else None,
            "authors": "; ".join(authors),
            "year": msg.get("published-print", {}).get("date-parts", [[None]])[0][0]
                     or msg.get("published-online", {}).get("date-parts", [[None]])[0][0],
            "journal": msg.get("container-title", [""])[0] if msg.get("container-title") else None,
            "abstract": msg.get("abstract"),
            "pdf_url": msg.get("link", [{}])[0].get("URL") if msg.get("link") else None,
            "bibtex": _crossref_bibtex(doi),
        }
    except Exception as e:
        logger.error(f"CrossRef lookup error for {doi}: {e}")
        return {}


def _crossref_bibtex(doi: str) -> Optional[str]:
    """Fetch BibTeX from CrossRef."""
    url = CROSSREF_BIBTEX_API.format(doi=doi)
    try:
        return _http_get_text(url)
    except Exception as e:
        logger.warning(f"CrossRef BibTeX fetch failed for {doi}: {e}")
        return None


def fetch_by_arxiv(arxiv_id: str, dest_dir: str) -> dict:
    """Fetch from arXiv: metadata + PDF download.

    Returns:
        {metadata, pdf_path}
    """
    arxiv_id = _detect_arxiv_id(arxiv_id) or arxiv_id

    # Try Task 2's arxiv_lookup first
    try:
        from ..identity.metadata import arxiv_lookup
        metadata = arxiv_lookup(arxiv_id)
    except ImportError:
        metadata = _arxiv_lookup_direct(arxiv_id)

    if not metadata:
        raise RuntimeError(f"arXiv lookup failed for: {arxiv_id}")

    # Download PDF
    pdf_url = ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    filename = f"arxiv_{arxiv_id.replace('/', '_')}.pdf"
    pdf_path = os.path.join(dest_dir, filename)
    try:
        _download_file(pdf_url, pdf_path)
        logger.info(f"Downloaded arXiv PDF: {pdf_path}")
    except Exception as e:
        raise RuntimeError(f"arXiv PDF download failed for {arxiv_id}: {e}")

    return {"metadata": metadata, "pdf_path": pdf_path}


def _arxiv_lookup_direct(arxiv_id: str) -> dict:
    """Direct arXiv API call (fallback when Task 2 is not available)."""
    import xml.etree.ElementTree as ET
    url = ARXIV_API.format(arxiv_id=arxiv_id)
    try:
        text = _http_get_text(url)
        root = ET.fromstring(text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            return {}
        title = entry.find("atom:title", ns)
        summary = entry.find("atom:summary", ns)
        published = entry.find("atom:published", ns)
        authors = entry.findall("atom:author", ns)
        author_names = []
        for a in authors:
            name = a.find("atom:name", ns)
            if name is not None:
                author_names.append(name.text)
        year = None
        if published is not None and published.text:
            year = int(published.text[:4])
        return {
            "arxiv_id": arxiv_id,
            "title": title.text.strip().replace("\n", " ") if title is not None else None,
            "authors": "; ".join(author_names),
            "year": year,
            "abstract": summary.text.strip() if summary is not None else None,
            "journal": "arXiv",
        }
    except Exception as e:
        logger.error(f"arXiv lookup error for {arxiv_id}: {e}")
        return {}


def fetch_by_url(url: str, dest_dir: str) -> dict:
    """Download PDF from a direct URL.

    Returns:
        {metadata, pdf_path}
    """
    # Determine filename from URL
    filename = url.split("/")[-1]
    if not filename.endswith(".pdf"):
        filename = "downloaded.pdf"
    pdf_path = os.path.join(dest_dir, filename)
    _download_file(url, pdf_path)
    logger.info(f"Downloaded PDF from URL: {pdf_path}")
    return {"metadata": {}, "pdf_path": pdf_path}


def add_paper_from_source(source: str, repo, dest_dir: Optional[str] = None) -> int:
    """Add a paper from path, URL, or DOI.

    1. Determine source type (path, URL, DOI, arXiv ID)
    2. Fetch metadata + PDF if needed
    3. Create paper record with paper_key
    4. Add paper_files entry

    Returns:
        paper_id
    """
    if dest_dir is None:
        from ..paths import get_data_dir
        dest_dir = os.path.join(str(get_data_dir()), "downloads")
    os.makedirs(dest_dir, exist_ok=True)

    source = source.strip()

    # Case 1: Local file path
    if os.path.exists(source):
        pdf_path = os.path.abspath(source)
        metadata = {}
    # Case 2: DOI
    elif _detect_doi(source):
        doi = _detect_doi(source)
        result = fetch_by_doi(doi, dest_dir)
        metadata = result["metadata"]
        pdf_path = result.get("pdf_path")
        if not pdf_path:
            raise RuntimeError(f"Could not download PDF for DOI {doi}. "
                             f"Metadata fetched but no PDF URL available.")
    # Case 3: arXiv ID
    elif _detect_arxiv_id(source):
        arxiv_id = _detect_arxiv_id(source)
        result = fetch_by_arxiv(arxiv_id, dest_dir)
        metadata = result["metadata"]
        pdf_path = result["pdf_path"]
    # Case 4: URL
    elif source.startswith("http://") or source.startswith("https://"):
        result = fetch_by_url(source, dest_dir)
        metadata = result["metadata"]
        pdf_path = result["pdf_path"]
    else:
        raise RuntimeError(f"Cannot determine source type for: {source}")

    if not pdf_path or not os.path.exists(pdf_path):
        raise RuntimeError(f"PDF file not available after fetch: {pdf_path}")

    # Compute hash
    sha256 = _compute_sha256(pdf_path)

    # Check if paper already exists by hash
    if hasattr(repo, "find_file_by_hash"):
        existing = repo.find_file_by_hash(sha256)
        if existing:
            pf = existing[0]
            logger.info(f"Paper already exists (hash match): {pf.paper_id}")
            # Add this path as an additional file
            repo.add_paper_file(PaperFile(paper_id=pf.paper_id, path=pdf_path,
                               file_role="duplicate", sha256=sha256))
            return pf.paper_id

    # Generate paper_key
    paper_key = _generate_paper_key(metadata, pdf_path)

    # Check if paper exists by DOI
    if metadata.get("doi") and hasattr(repo, "get_paper_by_doi"):
        existing = repo.get_paper_by_doi(metadata["doi"])
        if existing:
            repo.add_paper_file(PaperFile(paper_id=existing.id, path=pdf_path,
                               file_role="publisher" if not metadata.get("arxiv_id") else "arxiv",
                               sha256=sha256))
            return existing.id

    # Create new paper record
    paper = Paper(
        paper_key=paper_key,
        doi=metadata.get("doi"),
        arxiv_id=metadata.get("arxiv_id"),
        title=metadata.get("title"),
        authors_text=metadata.get("authors"),
        year=metadata.get("year"),
        journal=metadata.get("journal"),
        abstract=metadata.get("abstract"),
    )
    paper_id = repo.upsert_paper(paper)

    # Add file record
    file_role = "publisher"
    if metadata.get("arxiv_id"):
        file_role = "arxiv"
    elif os.path.exists(source) and source != pdf_path:
        file_role = "local"
    repo.add_paper_file(PaperFile(paper_id=paper_id, path=pdf_path, file_role=file_role,
                       sha256=sha256, is_preferred=1))

    logger.info(f"Added paper {paper_id}: {paper_key} from {source}")
    return paper_id


def _generate_paper_key(metadata: dict, pdf_path: str) -> str:
    """Generate a semantic paper_key from metadata or filename."""
    if metadata.get("authors") and metadata.get("year"):
        first_author = metadata["authors"].split(";")[0].split(",")[0].strip()
        # Extract last name
        parts = first_author.split()
        last_name = parts[-1] if parts else first_author
        last_name = re.sub(r'[^a-zA-Z]', '', last_name)
        year = metadata["year"]
        # Keyword from title
        keyword = "paper"
        if metadata.get("title"):
            # Take first significant word
            words = re.findall(r'[a-zA-Z]+', metadata["title"])
            stop = {"the", "a", "an", "of", "for", "and", "in", "on", "with", "to", "from"}
            for w in words:
                if w.lower() not in stop and len(w) > 2:
                    keyword = w
                    break
        return f"{last_name}_{year}_{keyword}"
    # Fallback: use filename stem
    return Path(pdf_path).stem

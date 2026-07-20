"""Tests for paperdb.ingest.scanner — scan a test folder, verify paper_files entries."""
import os
import tempfile
import pytest
from paperdb.ingest.scanner import scan_folder, scan_mendeley
from paperdb.identity.hashing import clear_cache
from mock_repo import MockRepository

@pytest.fixture(autouse=True)
def clean_cache(tmp_path, monkeypatch):
    monkeypatch.setenv('PAPERDB_DATA', str(tmp_path))
    clear_cache()
    yield
    clear_cache()

@pytest.fixture
def repo():
    return MockRepository()

@pytest.fixture
def pdf_folder(tmp_path):
    """Create a temp folder with test PDFs."""
    folder = tmp_path / 'pdfs'
    folder.mkdir()
    (folder / 'paper1.pdf').write_bytes(b'%PDF-1.4\ncontent of paper 1\n%%EOF\n')
    (folder / 'paper2.pdf').write_bytes(b'%PDF-1.4\ncontent of paper 2\n%%EOF\n')
    subfolder = folder / 'sub'
    subfolder.mkdir()
    (subfolder / 'paper3.pdf').write_bytes(b'%PDF-1.4\ncontent of paper 3\n%%EOF\n')
    return str(folder)

def test_scan_folder_basic(repo, pdf_folder):
    """Scan folder, verify all PDFs are indexed."""
    results = scan_folder(pdf_folder, recursive=True, repo=repo)
    assert len(results) == 3
    for r in results:
        assert r['paper_id'] is not None
        assert os.path.exists(r['path'])
        assert r['matched_by'] in ('created', 'metadata', 'hash_moved', 'existing_path')

def test_scan_folder_non_recursive(repo, pdf_folder):
    """Non-recursive scan finds only top-level PDFs."""
    results = scan_folder(pdf_folder, recursive=False, repo=repo)
    assert len(results) == 2

def test_scan_folder_recursive(repo, pdf_folder):
    """Recursive scan finds all PDFs including subfolders."""
    results = scan_folder(pdf_folder, recursive=True, repo=repo)
    assert len(results) == 3

def test_scan_folder_creates_papers(repo, pdf_folder):
    """Scanning creates paper records for new PDFs."""
    scan_folder(pdf_folder, recursive=True, repo=repo)
    papers = repo.list_papers()
    assert len(papers) == 3

def test_scan_folder_adds_files(repo, pdf_folder):
    """Scanning adds paper_files entries."""
    scan_folder(pdf_folder, recursive=True, repo=repo)
    counts = repo.get_status_counts()
    assert counts['files'] == 3

def test_scan_folder_idempotent(repo, pdf_folder):
    """Scanning the same folder twice doesn't create duplicates."""
    scan_folder(pdf_folder, recursive=True, repo=repo)
    scan_folder(pdf_folder, recursive=True, repo=repo)
    papers = repo.list_papers()
    assert len(papers) == 3  # no new papers
    counts = repo.get_status_counts()
    assert counts['files'] == 3  # no new file entries

def test_scan_folder_requires_repo(pdf_folder):
    """Scan without repo raises ValueError."""
    with pytest.raises(ValueError):
        scan_folder(pdf_folder, repo=None)

def test_scan_folder_empty_folder(repo, tmp_path):
    """Scanning an empty folder returns empty list."""
    empty = tmp_path / 'empty'
    empty.mkdir()
    results = scan_folder(str(empty), repo=repo)
    assert results == []

def test_scan_folder_detects_moved_pdf(repo, tmp_path):
    """If a PDF is moved, scanner detects it by hash and adds new path."""
    # Create and index a PDF
    folder1 = tmp_path / 'folder1'
    folder1.mkdir()
    pdf = folder1 / 'test.pdf'
    pdf.write_bytes(b'%PDF-1.4\nunique content\n%%EOF\n')
    scan_folder(str(folder1), repo=repo)
    # Move the PDF
    folder2 = tmp_path / 'folder2'
    folder2.mkdir()
    new_path = folder2 / 'test.pdf'
    pdf.rename(new_path)
    # Re-scan new folder
    results = scan_folder(str(folder2), repo=repo)
    assert len(results) == 1
    assert results[0]['matched_by'] == 'hash_moved'
    assert results[0]['was_new'] is False
    # Paper count should not increase
    assert len(repo.list_papers()) == 1

def test_scan_mendeley_basic(repo, tmp_path):
    """Scan Mendeley BibTeX with PDF folder."""
    bib_content = """
@article{Test2020,
    title = {Test Mendeley Paper},
    author = {Test, Author},
    year = {2020},
    doi = {10.9999/test.2020.001},
    file = {:pdfs/test.pdf:pdf}
}
"""
    bib_path = tmp_path / 'library.bib'
    bib_path.write_text(bib_content)
    pdf_folder = tmp_path / 'pdfs'
    pdf_folder.mkdir()
    (pdf_folder / 'test.pdf').write_bytes(b'%PDF-1.4\ntest content\n%%EOF\n')
    results = scan_mendeley(str(bib_path), str(pdf_folder), repo=repo)
    assert len(results) == 1
    assert results[0]['was_new'] is True
    assert 'Test Mendeley Paper' in results[0]['title']

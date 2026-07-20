"""Tests for paperdb.identity.matching — paper_key generation, dedup by hash/DOI/metadata."""
import os
import tempfile
import pytest
from paperdb.identity.matching import (
    generate_paper_key, resolve_collisions, match_by_hash, match_by_doi,
    match_by_metadata, find_or_create_paper
)
from paperdb.identity.hashing import clear_cache
from .mock_repo import MockRepository

@pytest.fixture(autouse=True)
def clean_cache(tmp_path, monkeypatch):
    monkeypatch.setenv('PAPERDB_DATA', str(tmp_path))
    clear_cache()
    yield
    clear_cache()

@pytest.fixture
def repo():
    return MockRepository()

# --- paper_key generation ---

def test_generate_paper_key_basic():
    key = generate_paper_key('Macklin, Miles; Müller, Matthias', 2016, 'XPBD: Position-Based Simulation of Compliant Constrained Dynamics')
    assert key == 'Macklin_2016_XPBD'

def test_generate_paper_key_single_author():
    key = generate_paper_key('Smith, John', 2020, 'A Study on Neural Networks')
    assert key == 'Smith_2020_Study'

def test_generate_paper_key_no_year():
    key = generate_paper_key('Doe, Jane', None, 'Some Title')
    assert key == 'Doe_0000_Some'

def test_generate_paper_key_with_existing_stem():
    key = generate_paper_key('Macklin, Miles', 2016, 'XPBD', existing_stem='Macklin_2016_XPBD')
    assert key == 'Macklin_2016_XPBD'

def test_generate_paper_key_no_authors():
    key = generate_paper_key('', 2020, 'Untitled Work')
    assert 'Unknown' in key

def test_generate_paper_key_strips_special_chars():
    key = generate_paper_key("O'Brien, Sean", 2021, "L'équation mystère")
    assert "'" not in key
    assert 'é' not in key

# --- Collision resolution ---

def test_resolve_collisions_no_conflict(repo):
    assert resolve_collisions('Unique_2020_Key', repo) == 'Unique_2020_Key'

def test_resolve_collisions_with_conflict(repo):
    repo.upsert_paper(paper_key='Smith_2020_Study', doi=None, title='A Study', authors_text='Smith, John', year=2020)
    resolved = resolve_collisions('Smith_2020_Study', repo)
    assert resolved == 'Smith_2020_Study_2'

# --- match_by_hash ---

def test_match_by_hash_found(repo):
    pid = repo.upsert_paper(paper_key='Test_2020_Hash', title='Test', authors_text='Test', year=2020)
    repo.add_paper_file(paper_id=pid, path='/tmp/test.pdf', sha256='abc123')
    assert match_by_hash('abc123', repo) == pid

def test_match_by_hash_not_found(repo):
    assert match_by_hash('nonexistent', repo) is None

# --- match_by_doi ---

def test_match_by_doi_found(repo):
    pid = repo.upsert_paper(paper_key='Test_2020_DOI', doi='10.1103/physrevb.40.3979', title='Test', authors_text='Test', year=2020)
    assert match_by_doi('10.1103/PhysRevB.40.3979', repo) == pid

def test_match_by_doi_not_found(repo):
    assert match_by_doi('10.9999/nonexistent', repo) is None

def test_match_by_doi_none(repo):
    assert match_by_doi(None, repo) is None

# --- match_by_metadata ---

def test_match_by_metadata_exact_title(repo):
    pid = repo.upsert_paper(paper_key='Smith_2020_Study', title='A Study on Neural Networks', authors_text='Smith, John', year=2020)
    result = match_by_metadata('A Study on Neural Networks', 'Smith, John', 2020, repo)
    assert result == pid

def test_match_by_metadata_close_title(repo):
    pid = repo.upsert_paper(paper_key='Smith_2020_Study', title='A Study on Neural Networks', authors_text='Smith, John', year=2020)
    result = match_by_metadata('A Study on Neural Network', 'Smith, John', 2020, repo)
    assert result == pid

def test_match_by_metadata_no_match(repo):
    pid = repo.upsert_paper(paper_key='Smith_2020_Study', title='A Study on Neural Networks', authors_text='Smith, John', year=2020)
    result = match_by_metadata('Completely Different Title', 'Other, Author', 2021, repo)
    assert result is None

def test_match_by_metadata_no_title(repo):
    assert match_by_metadata(None, 'Author', 2020, repo) is None

# --- find_or_create_paper ---

def test_find_or_create_paper_new(repo):
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, mode='wb') as f:
        f.write(b'unique content for new paper')
        pdf_path = f.name
    try:
        pid, was_created = find_or_create_paper(pdf_path, repo, metadata={'title': 'Brand New Paper', 'authors': 'New, Author', 'year': 2024})
        assert was_created is True
        assert pid is not None
        paper = repo.get_paper(pid)
        assert paper['title'] == 'Brand New Paper'
    finally:
        os.unlink(pdf_path)

def test_find_or_create_paper_hash_match(repo):
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, mode='wb') as f:
        f.write(b'content for hash match test')
        pdf_path = f.name
    try:
        # First call creates the paper
        pid1, created1 = find_or_create_paper(pdf_path, repo, metadata={'title': 'Hash Test', 'authors': 'Test, Author', 'year': 2023})
        assert created1 is True
        # Second call should find by hash
        pid2, created2 = find_or_create_paper(pdf_path, repo, metadata={'title': 'Hash Test', 'authors': 'Test, Author', 'year': 2023})
        assert created2 is False
        assert pid1 == pid2
    finally:
        os.unlink(pdf_path)

def test_find_or_create_paper_doi_match(repo):
    # Pre-create a paper with a DOI
    pid_existing = repo.upsert_paper(paper_key='Known_2020_Paper', doi='10.1103/physrevb.40.3979', title='Known Paper', authors_text='Known, Author', year=2020)
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, mode='wb') as f:
        f.write(b'unique content for doi match')
        pdf_path = f.name
    try:
        pid, was_created = find_or_create_paper(pdf_path, repo, metadata={'doi': '10.1103/PhysRevB.40.3979', 'title': 'Known Paper', 'authors': 'Known, Author', 'year': 2020})
        assert was_created is False
        assert pid == pid_existing
    finally:
        os.unlink(pdf_path)

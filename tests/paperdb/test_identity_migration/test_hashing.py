"""Tests for paperdb.identity.hashing — lazy vs full, cache behavior."""
import os
import tempfile
import pytest
from paperdb.identity.hashing import compute_sha256, clear_cache, _load_cache, _get_cache_path

@pytest.fixture
def tmp_pdf():
    """Create a temporary PDF file with known content."""
    f = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, mode='wb')
    f.write(b'%PDF-1.4\nfake pdf content\n%%EOF\n')
    f.close()
    yield f.name
    os.unlink(f.name)

@pytest.fixture(autouse=True)
def clean_hash_cache(tmp_path, monkeypatch):
    """Use a temp directory for hash cache to avoid polluting real cache."""
    monkeypatch.setenv('PAPERDB_DATA', str(tmp_path))
    clear_cache()
    yield
    clear_cache()

def test_compute_sha256_full(tmp_pdf):
    """Full mode always computes."""
    sha = compute_sha256(tmp_pdf, lazy=False)
    assert isinstance(sha, str)
    assert len(sha) == 64  # SHA-256 hex

def test_compute_sha256_lazy(tmp_pdf):
    """Lazy mode returns same hash as full mode."""
    sha_full = compute_sha256(tmp_pdf, lazy=False)
    clear_cache()
    sha_lazy = compute_sha256(tmp_pdf, lazy=True)
    assert sha_full == sha_lazy

def test_cache_hit(tmp_pdf):
    """Lazy mode uses cache when size+mtime unchanged."""
    sha1 = compute_sha256(tmp_pdf, lazy=True)
    sha2 = compute_sha256(tmp_pdf, lazy=True)
    assert sha1 == sha2

def test_cache_invalidation_on_content_change(tmp_pdf):
    """Cache invalidated when file content changes (size/mtime change)."""
    sha1 = compute_sha256(tmp_pdf, lazy=True)
    # Modify file
    with open(tmp_pdf, 'wb') as f:
        f.write(b'%PDF-1.4\ndifferent content\n%%EOF\n')
    sha2 = compute_sha256(tmp_pdf, lazy=True)
    assert sha1 != sha2

def test_cache_persistence(tmp_pdf):
    """Cache is saved to disk and reloadable."""
    sha1 = compute_sha256(tmp_pdf, lazy=True)
    # Force reload from disk
    import paperdb.identity.hashing as h
    h._cache = None
    sha2 = compute_sha256(tmp_pdf, lazy=True)
    assert sha1 == sha2

def test_different_files_different_hashes():
    """Two different files have different hashes."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, mode='wb') as f1:
        f1.write(b'content A')
        f1_path = f1.name
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, mode='wb') as f2:
        f2.write(b'content B')
        f2_path = f2.name
    try:
        sha1 = compute_sha256(f1_path, lazy=False)
        sha2 = compute_sha256(f2_path, lazy=False)
        assert sha1 != sha2
    finally:
        os.unlink(f1_path)
        os.unlink(f2_path)

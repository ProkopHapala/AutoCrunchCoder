"""SHA-256 computation with lazy size+mtime caching.

Cache format: JSON file at $PAPERDB_DATA/.hash_cache.json (default ~/paperdb/).
{abspath: {"size": int, "mtime": float, "sha256": str}}

Lazy mode: if size+mtime match the cache, return cached hash without re-reading the file.
Full mode: always recompute (still updates cache).
"""

import hashlib
import json
import os
from pathlib import Path

_cache = None  # in-memory cache, loaded once per process

def _get_cache_path() -> str:
    data_dir = os.environ.get('PAPERDB_DATA', os.path.expanduser('~/paperdb'))
    return os.path.join(data_dir, '.hash_cache.json')

def _load_cache() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    cache_path = _get_cache_path()
    try:
        with open(cache_path, 'r') as f:
            _cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _cache = {}
    return _cache

def _save_cache():
    cache_path = _get_cache_path()
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    tmp = cache_path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(_cache, f, indent=2)
    os.replace(tmp, cache_path)  # atomic

def _compute_sha256_full(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def compute_sha256(path, lazy=True) -> str:
    """Compute SHA-256 of a file. If lazy=True, check size+mtime cache first."""
    abspath = os.path.abspath(path)
    st = os.stat(abspath)
    size, mtime = st.st_size, st.st_mtime

    cache = _load_cache()

    if lazy and abspath in cache:
        entry = cache[abspath]
        if entry.get('size') == size and entry.get('mtime') == mtime:
            return entry['sha256']

    sha = _compute_sha256_full(abspath)
    cache[abspath] = {'size': size, 'mtime': mtime, 'sha256': sha}
    _save_cache()
    return sha

def clear_cache():
    """Clear the in-memory and on-disk hash cache."""
    global _cache
    _cache = {}
    cache_path = _get_cache_path()
    if os.path.exists(cache_path):
        os.remove(cache_path)

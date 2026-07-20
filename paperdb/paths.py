"""Data directory resolution for paperdb.

Default: ~/paperdb/  (override via PAPERDB_DATA env var)
"""
import os
from pathlib import Path

def get_data_dir() -> Path:
    """Resolve the paperdb data directory from PAPERDB_DATA env or default ~/paperdb/."""
    d = os.environ.get("PAPERDB_DATA", os.path.join(os.path.expanduser("~"), "paperdb"))
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_db_path() -> Path:
    """Path to papers.db — override via PAPERDB_DB env var."""
    env = os.environ.get("PAPERDB_DB")
    if env: return Path(env)
    return get_data_dir() / "papers.db"

def get_papers_dir(data_dir: str | Path | None = None) -> Path:
    """Directory for .md/.json/.bib files, grouped by year."""
    p = (Path(data_dir).expanduser() if data_dir is not None else get_data_dir()) / "papers"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_legacy_dir(data_dir: str | Path | None = None) -> Path:
    """Directory for migrated legacy data."""
    p = (Path(data_dir).expanduser() if data_dir is not None else get_data_dir()) / "legacy"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_logs_dir(data_dir: str | Path | None = None) -> Path:
    """Directory for processing logs and migration reports."""
    p = (Path(data_dir).expanduser() if data_dir is not None else get_data_dir()) / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_reviews_dir(data_dir: str | Path | None = None) -> Path:
    """Directory for generated topical overviews."""
    p = (Path(data_dir).expanduser() if data_dir is not None else get_data_dir()) / "reviews"
    p.mkdir(parents=True, exist_ok=True)
    return p

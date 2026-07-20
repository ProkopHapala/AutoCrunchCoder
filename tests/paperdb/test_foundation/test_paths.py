"""Test data directory resolution, env var override."""
import os
import tempfile
from pathlib import Path
from paperdb.paths import get_data_dir, get_db_path, get_papers_dir, get_legacy_dir, get_logs_dir

def test_default_data_dir(monkeypatch):
    monkeypatch.delenv("PAPERDB_DATA", raising=False)
    monkeypatch.delenv("PAPERDB_DB", raising=False)
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("HOME", d)
        result = get_data_dir()
        assert "paperdb" in str(result)
        assert result.exists()

def test_env_override_data_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("PAPERDB_DATA", d)
        result = get_data_dir()
        assert str(result) == d

def test_env_override_db_path(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("PAPERDB_DB", os.path.join(d, "custom.db"))
        result = get_db_path()
        assert str(result) == os.path.join(d, "custom.db")

def test_papers_dir_created(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("PAPERDB_DATA", d)
        p = get_papers_dir()
        assert p.exists()
        assert p.name == "papers"

def test_legacy_dir_created(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("PAPERDB_DATA", d)
        p = get_legacy_dir()
        assert p.exists()
        assert p.name == "legacy"

def test_logs_dir_created(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("PAPERDB_DATA", d)
        p = get_logs_dir()
        assert p.exists()
        assert p.name == "logs"

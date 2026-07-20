"""Test CLI structure — verify commands exist, produce output, and delegate to PaperDB."""
import sys
import json
import pytest
from typer.testing import CliRunner

# conftest.py injects mock paperdb package before this import
from paperdb.cli import app

runner = CliRunner()

# ── Command existence ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("cmd", [
    "scan", "sync", "add", "ingest", "search", "context", "inspect", "get",
    "equations", "methods", "method", "tags", "related", "topic", "compare",
    "export", "reindex", "status", "mcp", "gui", "migrate",
])
def test_command_exists(cmd):
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert cmd in result.stdout, f"Command '{cmd}' not found in help output"

# ── Status ────────────────────────────────────────────────────────────────────
def test_status_human():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "895" in result.stdout

def test_status_json():
    result = runner.invoke(app, ["--json", "status"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["total_papers"] == 895

# ── Scan ──────────────────────────────────────────────────────────────────────
def test_scan():
    result = runner.invoke(app, ["scan", "/tmp/papers", "--recursive"])
    assert result.exit_code == 0
    assert "42" in result.stdout

def test_scan_json():
    result = runner.invoke(app, ["--json", "scan", "/tmp/papers"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["count"] == 42

# ── Inspect ───────────────────────────────────────────────────────────────────
def test_inspect():
    result = runner.invoke(app, ["inspect", "Macklin_2016_XPBD"])
    assert result.exit_code == 0
    assert "Macklin_2016_XPBD" in result.stdout

def test_inspect_json():
    result = runner.invoke(app, ["--json", "inspect", "Macklin_2016_XPBD"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["paper_key"] == "Macklin_2016_XPBD"

# ── Get ───────────────────────────────────────────────────────────────────────
def test_get_markdown():
    result = runner.invoke(app, ["get", "Macklin_2016_XPBD", "--markdown"])
    assert result.exit_code == 0
    assert "XPBD" in result.stdout

# ── Equations ─────────────────────────────────────────────────────────────────
def test_equations():
    result = runner.invoke(app, ["equations", "Macklin_2016_XPBD"])
    assert result.exit_code == 0
    assert "3.1" in result.stdout or "Compliance" in result.stdout

def test_equations_json():
    result = runner.invoke(app, ["--json", "equations", "Macklin_2016_XPBD"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 2
    assert data[0]["equation_number"] == "7"

# ── Tags ──────────────────────────────────────────────────────────────────────
def test_tags():
    result = runner.invoke(app, ["tags"])
    assert result.exit_code == 0
    assert "solver" in result.stdout

def test_tags_category():
    result = runner.invoke(app, ["tags", "--category", "solver"])
    assert result.exit_code == 0
    assert "position based dynamics" in result.stdout

def test_tags_json():
    result = runner.invoke(app, ["--json", "tags"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 5

# ── Topic ─────────────────────────────────────────────────────────────────────
def test_topic():
    result = runner.invoke(app, ["topic", "molecular force fields"])
    assert result.exit_code == 0
    assert "Topic Review" in result.stdout

def test_topic_out(tmp_path):
    out_file = tmp_path / "overview.md"
    result = runner.invoke(app, ["topic", "GPU collision", "--out", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    assert "Topic Review" in out_file.read_text()

# ── Export ────────────────────────────────────────────────────────────────────
def test_export_bibtex(tmp_path):
    out_file = tmp_path / "library.bib"
    result = runner.invoke(app, ["export", "--bibtex", "--out", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    assert "@inproceedings" in out_file.read_text() or "@article" in out_file.read_text()

# ── Context ───────────────────────────────────────────────────────────────────
def test_context_out(tmp_path):
    out_file = tmp_path / "context.md"
    result = runner.invoke(app, ["context", "XPBD constraint solving", "--out", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "Context Pack" in content

# ── Error handling ────────────────────────────────────────────────────────────
def test_ingest_no_args():
    result = runner.invoke(app, ["ingest"])
    assert result.exit_code == 1

def test_reindex_no_args():
    result = runner.invoke(app, ["reindex"])
    assert result.exit_code == 1

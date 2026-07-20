"""Test CLI search command with various flags — --explain, --json, --tag, --year."""
import sys
import json

from typer.testing import CliRunner

# conftest.py injects mock paperdb package before this import
from paperdb.cli import app

runner = CliRunner()

def test_search_basic():
    result = runner.invoke(app, ["search", "Gauss-Seidel XPBD"])
    assert result.exit_code == 0
    assert "Macklin_2016_XPBD" in result.stdout

def test_search_json():
    result = runner.invoke(app, ["--json", "search", "SIBFA"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 3
    assert data[0]["paper_key"] == "Macklin_2016_XPBD"

def test_search_explain():
    result = runner.invoke(app, ["search", "XPBD", "--explain"])
    assert result.exit_code == 0
    # With --explain, match_reason should appear in output
    assert "position based dynamics" in result.stdout or "Match Reason" in result.stdout

def test_search_explain_json():
    result = runner.invoke(app, ["--json", "search", "XPBD", "--explain"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # In explain mode, match_reason should be present
    assert any("match_reason" in r for r in data)

def test_search_limit():
    result = runner.invoke(app, ["--json", "search", "test", "--limit", "1"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1

def test_search_tag():
    result = runner.invoke(app, ["search", "test", "--tag", "solver:xpbd"])
    assert result.exit_code == 0

def test_search_year_range():
    result = runner.invoke(app, ["search", "test", "--year", "2015-2025"])
    assert result.exit_code == 0

def test_search_year_single():
    result = runner.invoke(app, ["search", "test", "--year", "2016"])
    assert result.exit_code == 0

def test_search_multiple_tags():
    result = runner.invoke(app, ["search", "test", "--tag", "solver:xpbd", "--tag", "domain:game_physics"])
    assert result.exit_code == 0

def test_search_excluded_tag():
    result = runner.invoke(app, ["search", "test", "--tag", "!solver:ewald"])
    assert result.exit_code == 0

# ── Context pack search ───────────────────────────────────────────────────────
def test_context_basic():
    result = runner.invoke(app, ["context", "stable GPU collision"])
    assert result.exit_code == 0
    assert "Context Pack" in result.stdout

def test_context_json():
    result = runner.invoke(app, ["--json", "context", "XPBD"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "content" in data

def test_context_budget():
    result = runner.invoke(app, ["context", "test", "--budget", "8000"])
    assert result.exit_code == 0

def test_context_include():
    result = runner.invoke(app, ["context", "test", "--include", "equations,methods"])
    assert result.exit_code == 0

def test_context_save_to_file(tmp_path):
    out = tmp_path / "ctx.md"
    result = runner.invoke(app, ["context", "XPBD", "--out", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert "Context Pack" in out.read_text()

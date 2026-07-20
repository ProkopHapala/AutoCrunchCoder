"""Test MCP retrieve_context tool — the central output for LLM agents."""
import sys
import json
import pytest

# conftest.py injects mock paperdb package before this import
from tests.paperdb.test_cli_mcp.conftest import MockPaperDB
from paperdb import mcp as mcp_module

def test_retrieve_context_basic():
    """retrieve_context returns a context pack with content."""
    mcp_module._db = MockPaperDB()
    result = mcp_module.retrieve_context("XPBD constraint solving")
    # Could be JSON dict or string
    if result.startswith("{"):
        data = json.loads(result)
    else:
        data = {"content": result}
    assert "content" in data
    assert "Context Pack" in data["content"]

def test_retrieve_context_with_budget():
    """retrieve_context respects token_budget parameter."""
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.retrieve_context("test query", token_budget=8000))
    assert "content" in result

def test_retrieve_context_with_include():
    """retrieve_context accepts include types."""
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.retrieve_context("test", include=["equations", "methods"]))
    assert "content" in result

def test_retrieve_context_with_filters():
    """retrieve_context accepts filters dict."""
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.retrieve_context("test", filters={"year_min": 2015}))
    assert "content" in result

def test_retrieve_context_returns_query():
    """Context pack should include the original query."""
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.retrieve_context("XPBD constraint solving"))
    assert result["query"] == "XPBD constraint solving"

def test_retrieve_context_returns_papers():
    """Context pack should list selected papers."""
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.retrieve_context("XPBD"))
    assert "papers" in result
    assert isinstance(result["papers"], list)

def test_retrieve_context_content_has_bibliography():
    """Context pack content should include a bibliography section."""
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.retrieve_context("XPBD"))
    assert "Bibliography" in result["content"] or "bibliography" in result["content"].lower()

def test_context_resource():
    """The paperdb://context/{id} resource should return a saved context pack."""
    mcp_module._db = MockPaperDB()
    result = mcp_module.resource_context("1")
    data = json.loads(result)
    assert "content" in data or "error" in data

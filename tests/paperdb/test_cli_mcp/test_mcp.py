"""Test MCP server — verify tool schemas, read-only enforcement, and tool behavior."""
import sys
import json
import asyncio
import pytest

# conftest.py injects mock paperdb package before this import
from tests.paperdb.test_cli_mcp.conftest import MockPaperDB
from paperdb import mcp as mcp_module

# ── Tool existence ────────────────────────────────────────────────────────────
DISCOVERY_TOOLS = ["search_papers", "find_methods", "find_equations", "compare_methods", "build_topic_review"]
INSPECTION_TOOLS = ["get_paper", "get_paper_markdown", "get_paper_methods", "get_paper_equations", "get_related_papers", "explain_paper_match"]
CONTEXT_TOOLS = ["retrieve_context"]
TAXONOMY_TOOLS = ["list_tags", "list_tag_aliases"]
MUTATING_TOOLS = ["ingest_pdf", "reprocess_document", "merge_tags"]

def _get_tool_names():
    """Get registered tool names from FastMCP (async API)."""
    tools = asyncio.run(mcp_module.mcp.list_tools())
    return [t.name for t in tools]

@pytest.mark.parametrize("tool_name", DISCOVERY_TOOLS + INSPECTION_TOOLS + CONTEXT_TOOLS + TAXONOMY_TOOLS + MUTATING_TOOLS)
def test_tool_registered(tool_name):
    """Verify all tools from §14 are registered with the MCP server."""
    names = _get_tool_names()
    assert tool_name in names, f"MCP tool '{tool_name}' not registered. Available: {names}"

# ── Read-only enforcement ─────────────────────────────────────────────────────
def test_mutating_tools_blocked_by_default():
    """Mutating tools must raise PermissionError when allow_mutations is False."""
    mcp_module._allow_mutations = False
    with pytest.raises(PermissionError):
        mcp_module.ingest_pdf("/tmp/test.pdf")
    with pytest.raises(PermissionError):
        mcp_module.reprocess_document("Macklin_2016_XPBD")
    with pytest.raises(PermissionError):
        mcp_module.merge_tags("DFT", "density functional theory")

def test_mutating_tools_allowed_with_flag():
    """Mutating tools work when allow_mutations is True."""
    mcp_module._allow_mutations = True
    try:
        result = mcp_module.ingest_pdf("/tmp/test.pdf")
        data = json.loads(result)
        assert "result" in data
    finally:
        mcp_module._allow_mutations = False  # reset

# ── Discovery tool behavior ───────────────────────────────────────────────────
def test_search_papers():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.search_papers("XPBD"))
    assert len(result) == 3
    assert result[0]["paper_key"] == "Macklin_2016_XPBD"

def test_search_papers_with_tags():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.search_papers("test", required_tags=["solver"]))
    assert len(result) == 3

def test_find_methods():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.find_methods("GPU collision detection"))
    assert isinstance(result, list)
    assert len(result) > 0

def test_find_equations():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.find_equations("constraint compliance"))
    assert isinstance(result, list)
    assert len(result) > 0
    assert "equations" in result[0]

def test_compare_methods():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.compare_methods("GPU collision", ["spatial_structure", "complexity"]))
    assert "axes" in result
    assert "spatial_structure" in result["axes"]

def test_build_topic_review():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.build_topic_review("molecular force fields"))
    assert "topic" in result
    assert result["topic"] == "molecular force fields"

# ── Inspection tool behavior ──────────────────────────────────────────────────
def test_get_paper():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.get_paper("Macklin_2016_XPBD"))
    assert result["paper_key"] == "Macklin_2016_XPBD"
    assert result["title"].startswith("XPBD")

def test_get_paper_markdown():
    mcp_module._db = MockPaperDB()
    result = mcp_module.get_paper_markdown("Macklin_2016_XPBD")
    assert "XPBD" in result

def test_get_paper_methods():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.get_paper_methods("Macklin_2016_XPBD"))
    assert len(result) == 1
    assert result[0]["name"] == "XPBD constraint update"

def test_get_paper_equations():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.get_paper_equations("Macklin_2016_XPBD"))
    assert len(result) == 2
    assert result[0]["equation_number"] == "7"

def test_get_related_papers():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.get_related_papers("Macklin_2016_XPBD"))
    assert len(result) > 0

def test_explain_paper_match():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.explain_paper_match("Macklin_2016_XPBD", "XPBD"))
    assert result["paper_key"] == "Macklin_2016_XPBD"
    assert "match_reason" in result

# ── Taxonomy tools ────────────────────────────────────────────────────────────
def test_list_tags():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.list_tags())
    assert len(result) == 5

def test_list_tags_category():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.list_tags(category="solver"))
    assert all(t["category"] == "solver" for t in result)

def test_list_tag_aliases():
    mcp_module._db = MockPaperDB()
    result = json.loads(mcp_module.list_tag_aliases("DFT"))
    assert "aliases" in result

# ── Resource existence ────────────────────────────────────────────────────────
def test_resources_registered():
    """Verify resources from §14 are registered."""
    resources = asyncio.run(mcp_module.mcp.list_resources())
    templates = asyncio.run(mcp_module.mcp.list_resource_templates())
    total = len(resources) + len(templates)
    assert total > 0, "No MCP resources registered"

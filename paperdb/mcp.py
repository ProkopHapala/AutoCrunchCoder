"""MCP server for paperdb — read-only by default, thin wrapper over PaperDB API.

Transport modes:
  stdio  — for IDE-integrated agents (Cursor, Claude Desktop, etc.)
  sse    — for remote/web-based agents (Devin, OpenCode, etc.)

Mutating tools are opt-in via --allow-mutations.
"""
import json as _json
import os
from typing import Optional

from fastmcp import FastMCP

# ── Global state ──────────────────────────────────────────────────────────────
_db = None
_allow_mutations = False

def _get_db():
    """Get or create the PaperDB instance (lazy)."""
    global _db
    if _db is None:
        from paperdb import PaperDB
        data_dir = os.environ.get("PAPERDB_DATA")
        db_path = os.environ.get("PAPERDB_DB")
        _db = PaperDB(data_dir=data_dir, db_path=db_path)
    return _db

def _check_mutations():
    """Raise if mutations are not allowed."""
    if not _allow_mutations:
        raise PermissionError("Mutating tools require --allow-mutations flag. Server is read-only by default.")

# ── MCP server ────────────────────────────────────────────────────────────────
mcp = FastMCP("paperdb")

# ── Discovery tools (scientific tasks) ────────────────────────────────────────
@mcp.tool()
def search_papers(
    query: str,
    required_tags: Optional[list[str]] = None,
    preferred_tags: Optional[list[str]] = None,
    excluded_tags: Optional[list[str]] = None,
    year_range: Optional[list[int]] = None,
    limit: int = 20,
) -> str:
    """Search papers with FTS + tag filter and explainable ranking. Returns papers + match reasons."""
    db = _get_db()
    yr = tuple(year_range) if year_range else None
    results = db.search(query, required_tags=required_tags, preferred_tags=preferred_tags, excluded_tags=excluded_tags, year_range=yr, limit=limit, explain=True)
    return _json.dumps(results, default=str)

@mcp.tool()
def find_methods(problem: str, constraints: Optional[str] = None, limit: int = 20) -> str:
    """Find methods across papers matching a scientific problem. E.g. 'short-range interaction search on GPU, avoid atomics'."""
    db = _get_db()
    results = db.search(problem, required_tags=["method"], limit=limit, explain=True)
    enriched = []
    for r in (results if isinstance(results, list) else []):
        pk = r.get("paper_key", r.get("id"))
        if pk and hasattr(db, "get_methods"):
            r["methods"] = db.get_methods(pk)
        enriched.append(r)
    return _json.dumps(enriched, default=str)

@mcp.tool()
def find_equations(concept: str, variables: Optional[list[str]] = None, tags: Optional[list[str]] = None, limit: int = 30) -> str:
    """Find equations across papers matching a concept. E.g. 'constraint compliance update', 'Ewald summation for 2D periodicity'."""
    db = _get_db()
    results = db.search(concept, required_tags=tags, limit=limit, explain=True)
    enriched = []
    for r in (results if isinstance(results, list) else []):
        pk = r.get("paper_key", r.get("id"))
        if pk and hasattr(db, "get_equations"):
            r["equations"] = db.get_equations(pk)
        enriched.append(r)
    return _json.dumps(enriched, default=str)

@mcp.tool()
def compare_methods(problem: str, comparison_axes: list[str], constraints: Optional[str] = None, max_papers: int = 20) -> str:
    """Compare methods across papers along specified axes (spatial_structure, complexity, synchronization, etc.). Returns comparison matrix."""
    db = _get_db()
    if hasattr(db, "compare_methods"):
        result = db.compare_methods(problem, comparison_axes, constraints=constraints, max_papers=max_papers)
    else:
        results = db.search(problem, limit=max_papers, explain=True)
        result = {"problem": problem, "axes": comparison_axes, "papers": results, "matrix": "not yet implemented"}
    return _json.dumps(result, default=str)

@mcp.tool()
def build_topic_review(topic: str, focus: Optional[str] = None, constraints: Optional[str] = None, max_papers: int = 30) -> str:
    """Multi-step: interpret query → find papers → retrieve method cards → compare → synthesize. Returns evidence-backed review."""
    db = _get_db()
    if hasattr(db, "build_topic_review"):
        result = db.build_topic_review(topic, focus=focus, constraints=constraints, max_papers=max_papers)
    else:
        results = db.search(topic, limit=max_papers, explain=True)
        result = {"topic": topic, "focus": focus, "papers": results, "review": "not yet implemented"}
    return _json.dumps(result, default=str)

# ── Inspection tools ──────────────────────────────────────────────────────────
@mcp.tool()
def get_paper(paper_id_or_key_or_doi: str) -> str:
    """Full metadata + summary + tags + processing status for a paper."""
    db = _get_db()
    result = db.get_paper(paper_id_or_key_or_doi)
    return _json.dumps(result, default=str)

@mcp.tool()
def get_paper_markdown(paper_id: str) -> str:
    """Full markdown (summary + source text) for a paper."""
    db = _get_db()
    return db.get_markdown(paper_id)

@mcp.tool()
def get_paper_methods(paper_id: str) -> str:
    """All method cards for a paper with evidence links."""
    db = _get_db()
    result = db.get_methods(paper_id)
    return _json.dumps(result, default=str)

@mcp.tool()
def get_paper_equations(paper_id: str) -> str:
    """All equations with source coordinates (latex_raw, latex_normalized, page, section)."""
    db = _get_db()
    result = db.get_equations(paper_id)
    return _json.dumps(result, default=str)

@mcp.tool()
def get_related_papers(paper_id: str, limit: int = 5) -> str:
    """Papers sharing tags with the given paper."""
    db = _get_db()
    if hasattr(db, "get_related"):
        result = db.get_related(paper_id, limit=limit)
        # Serialize SearchResult-like dicts
        if isinstance(result, list):
            result = [_json.loads(_json.dumps(r, default=str)) if not isinstance(r, dict) else r for r in result]
    else:
        result = db.search("", limit=limit)
    return _json.dumps(result, default=str)

@mcp.tool()
def explain_paper_match(paper_id: str, query: str) -> str:
    """Explain why this paper matched the query — shows scoring breakdown."""
    db = _get_db()
    results = db.search(query, limit=50, explain=True)
    for r in (results if isinstance(results, list) else []):
        if str(r.get("paper_key", r.get("id"))) == str(paper_id):
            return _json.dumps(r, default=str)
    return _json.dumps({"paper_id": paper_id, "match": "not found in search results"})

# ── Context pack tool ─────────────────────────────────────────────────────────
@mcp.tool()
def retrieve_context(query: str, token_budget: int = 24000, include: Optional[list[str]] = None, filters: Optional[dict] = None) -> str:
    """Assemble a compact, evidence-bearing context package: select papers (stage A) → retrieve relevant units (stage B) → format with comparison matrix + bibliography."""
    db = _get_db()
    result = db.retrieve_context(query, token_budget=token_budget, include=include, filters=filters)
    if isinstance(result, dict):
        return _json.dumps(result, default=str)
    return str(result)

# ── Taxonomy tools ────────────────────────────────────────────────────────────
@mcp.tool()
def list_tags(category: Optional[str] = None) -> str:
    """All tags, optionally filtered by category."""
    db = _get_db()
    result = db.list_tags(category=category)
    return _json.dumps(result, default=str)

@mcp.tool()
def list_tag_aliases(tag_name: str) -> str:
    """All aliases mapping to a canonical tag."""
    db = _get_db()
    if hasattr(db, "get_tag_aliases"):
        result = db.get_tag_aliases(tag_name)
    else:
        result = {"tag": tag_name, "aliases": "not yet implemented"}
    return _json.dumps(result, default=str)

# ── Mutating tools (opt-in, NOT enabled by default) ───────────────────────────
@mcp.tool()
def ingest_pdf(path_or_url: str, tags: Optional[list[str]] = None) -> str:
    """Add a paper from local path or URL (arXiv, DOI, etc.). Requires --allow-mutations."""
    _check_mutations()
    db = _get_db()
    result = db.add_paper(path_or_url) if hasattr(db, "add_paper") else "add_paper not yet implemented"
    return _json.dumps({"result": result}, default=str)

@mcp.tool()
def reprocess_document(paper_id: str, operations: Optional[list[str]] = None) -> str:
    """Re-run a specific operation (convert, summarize, tag, etc.). Requires --allow-mutations."""
    _check_mutations()
    db = _get_db()
    result = db.ingest_paper(paper_id, operations=operations) if hasattr(db, "ingest_paper") else "ingest_paper not yet implemented"
    return _json.dumps({"result": result}, default=str)

@mcp.tool()
def merge_tags(canonical: str, alias: str) -> str:
    """Merge tag alias into canonical. Requires --allow-mutations."""
    _check_mutations()
    db = _get_db()
    result = db.merge_tags(canonical, alias) if hasattr(db, "merge_tags") else "merge_tags not yet implemented"
    return _json.dumps({"result": result}, default=str)

# ── Resources ─────────────────────────────────────────────────────────────────
@mcp.resource("paperdb://paper/{paper_key}")
def resource_paper(paper_key: str) -> str:
    """Paper metadata + summary."""
    db = _get_db()
    result = db.get_paper(paper_key)
    return _json.dumps(result, default=str)

@mcp.resource("paperdb://paper/{paper_key}/markdown")
def resource_paper_markdown(paper_key: str) -> str:
    """Full markdown for a paper."""
    db = _get_db()
    return db.get_markdown(paper_key)

@mcp.resource("paperdb://paper/{paper_key}/json")
def resource_paper_json(paper_key: str) -> str:
    """Structured JSON for a paper."""
    db = _get_db()
    result = db.get_paper(paper_key)
    return _json.dumps(result, default=str)

@mcp.resource("paperdb://paper/{paper_key}/bib")
def resource_paper_bib(paper_key: str) -> str:
    """BibTeX for a paper."""
    db = _get_db()
    p = db.get_paper(paper_key)
    if isinstance(p, dict):
        return p.get("bibtex", "")
    return str(p)

@mcp.resource("paperdb://tags")
def resource_tags() -> str:
    """All tags grouped by category."""
    db = _get_db()
    result = db.list_tags()
    return _json.dumps(result, default=str)

@mcp.resource("paperdb://context/{context_id}")
def resource_context(context_id: str) -> str:
    """Saved context pack by ID."""
    db = _get_db()
    if hasattr(db, "get_context_pack"):
        result = db.get_context_pack(int(context_id))
    else:
        result = {"error": f"context pack {context_id} not yet implemented"}
    return _json.dumps(result, default=str)

# ── Server runner ─────────────────────────────────────────────────────────────
def run_server(transport: str = "stdio", port: int = 8000, allow_mutations: bool = False, db_path: str = None, data_dir: str = None):
    """Start the MCP server with the specified transport."""
    global _allow_mutations
    _allow_mutations = allow_mutations
    if db_path:
        os.environ["PAPERDB_DB"] = db_path
    if data_dir:
        os.environ["PAPERDB_DATA"] = data_dir
    if transport == "sse":
        mcp.run(transport="sse", port=port)
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="paperdb MCP server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--allow-mutations", action="store_true")
    args = parser.parse_args()
    run_server(transport=args.transport, port=args.port, allow_mutations=args.allow_mutations)

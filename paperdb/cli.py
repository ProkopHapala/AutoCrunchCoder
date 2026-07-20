"""Typer CLI for paperdb — thin wrapper over PaperDB API.

No SQL, no parsing logic. All commands delegate to PaperDB methods.
"""
import json as _json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="paperdb", help="Scientific paper compiler and retrieval service", no_args_is_help=True)
console = Console()

# ── Global state ──────────────────────────────────────────────────────────────
_state = {"data_dir": None, "db_path": None, "llm_config": None, "json": False}

def get_db() -> "PaperDB":
    """Create a PaperDB instance using global state (lazy import)."""
    from paperdb import PaperDB
    return PaperDB(data_dir=_state["data_dir"], db_path=_state["db_path"])

# ── Output helpers ────────────────────────────────────────────────────────────
def _out(data, table=None):
    """Output data as JSON or human-readable (rich table)."""
    if _state["json"]:
        print(_json.dumps(data, indent=2, default=str))
    elif table is not None:
        console.print(table)
    else:
        console.print(data)

def _papers_table(results, explain=False):
    """Format search results as a rich table."""
    t = Table(show_header=True, header_style="bold")
    t.add_column("Score", justify="right")
    t.add_column("Paper Key")
    t.add_column("Title")
    t.add_column("Year")
    if explain:
        t.add_column("Match Reason")
    for r in results:
        row = [str(r.get("score", "")), r.get("paper_key", ""), r.get("title", "")[:60], str(r.get("year", ""))]
        if explain:
            row.append(r.get("match_reason", ""))
        t.add_row(*row)
    return t

# ── Global callback ───────────────────────────────────────────────────────────
@app.callback()
def main_callback(
    data_dir: Optional[str] = typer.Option(None, "--data-dir", help="Override data directory (PAPERDB_DATA)"),
    db_path: Optional[str] = typer.Option(None, "--db-path", help="Override DB path (PAPERDB_DB)"),
    llm_config: Optional[str] = typer.Option(None, "--llm-config", help="LLM config key from config/LLMs.toml"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Scientific paper compiler and retrieval service."""
    _state["data_dir"] = data_dir or os.environ.get("PAPERDB_DATA")
    _state["db_path"] = db_path or os.environ.get("PAPERDB_DB")
    _state["llm_config"] = llm_config or os.environ.get("PAPERDB_LLM")
    _state["json"] = json_output

# ── Scanning & ingestion ─────────────────────────────────────────────────────
@app.command()
def scan(folder: str, recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Scan recursively")):
    """Scan a folder for PDFs and index them in-place."""
    db = get_db()
    count = db.scan_folder(folder, recursive=recursive)
    _out(f"Scanned {folder}: {count} PDFs indexed" if not _state["json"] else {"folder": folder, "count": count})

@app.command()
def sync(folder: Optional[str] = typer.Option(None, "--folder", help="Specific folder to sync")):
    """Sync: scan watched folders and process new/changed papers."""
    db = get_db()
    result = db.scan_folder(folder, recursive=True) if folder else db.sync()
    _out(f"Sync complete: {result}" if not _state["json"] else {"result": result})

@app.command()
def add(path_or_url_or_doi: str):
    """Add a single paper from local path, URL, or DOI."""
    db = get_db()
    result = db.add_paper(path_or_url_or_doi)
    _out(f"Added: {result}" if not _state["json"] else {"result": result})

@app.command()
def ingest(
    all_papers: bool = typer.Option(False, "--all", help="Ingest all indexed but unprocessed papers"),
    folder: Optional[str] = typer.Option(None, "--folder", help="Ingest papers from a specific folder"),
    paper: Optional[str] = typer.Option(None, "--paper", help="Ingest a single paper by key"),
):
    """Ingest (convert + summarize + tag + extract) papers."""
    db = get_db()
    if paper:
        result = db.ingest_paper(paper)
    elif folder:
        result = db.ingest_folder(folder)
    elif all_papers:
        result = db.ingest_all()
    else:
        console.print("[red]Must specify --all, --folder, or --paper[/red]")
        raise typer.Exit(1)
    _out(f"Ingest complete: {result}" if not _state["json"] else {"result": result})

# ── Search ────────────────────────────────────────────────────────────────────
@app.command()
def search(
    query: str,
    tag: Optional[list[str]] = typer.Option(None, "--tag", help="Filter by tag (e.g. solver:xpbd or domain:game_physics)"),
    year: Optional[str] = typer.Option(None, "--year", help="Year range (e.g. 2015-2025 or 2020)"),
    explain: bool = typer.Option(False, "--explain", help="Show scoring breakdown"),
    limit: int = typer.Option(20, "--limit", help="Max results"),
):
    """Search papers with explainable ranking."""
    db = get_db()
    required_tags = [t for t in (tag or []) if not t.startswith("!")]
    excluded_tags = [t[1:] for t in (tag or []) if t.startswith("!")]
    year_range = _parse_year_range(year)
    results = db.search(query, required_tags=required_tags or None, excluded_tags=excluded_tags or None, year_range=year_range, limit=limit, explain=explain)
    if _state["json"]:
        _out(results)
    else:
        t = _papers_table(results, explain=explain)
        _out(None, table=t)

def _parse_year_range(s: Optional[str]):
    """Parse '2015-2025' or '2020' into (start, end) tuple."""
    if not s: return None
    if "-" in s:
        parts = s.split("-", 1)
        return (int(parts[0]), int(parts[1]))
    y = int(s)
    return (y, y)

@app.command()
def context(
    query: str,
    budget: int = typer.Option(24000, "--budget", help="Token budget for context pack"),
    include: Optional[str] = typer.Option(None, "--include", help="Types to include (equations,methods,assumptions)"),
    out: Optional[str] = typer.Option(None, "--out", help="Write context pack to file"),
    save: bool = typer.Option(False, "--save", help="Save context pack to DB"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Assemble a compact, evidence-bearing context pack for an LLM agent."""
    db = get_db()
    include_types = include.split(",") if include else None
    result = db.retrieve_context(query, token_budget=budget, include=include_types)
    content = result if isinstance(result, str) else result.get("content", str(result))
    if out:
        Path(out).write_text(content, encoding="utf-8")
        _out(f"Context pack written to {out}" if not (json_output or _state["json"]) else {"out": out, "chars": len(content)})
    elif json_output or _state["json"]:
        _out(result if isinstance(result, dict) else {"content": content})
    else:
        console.print(content)

# ── Inspection ────────────────────────────────────────────────────────────────
@app.command()
def inspect(paper_key: str):
    """Show full metadata + tags + processing status for a paper."""
    db = get_db()
    paper = db.get_paper(paper_key)
    if _state["json"]:
        _out(paper)
    else:
        if paper:
            paper_dict = paper if isinstance(paper, dict) else paper.model_dump() if hasattr(paper, 'model_dump') else vars(paper)
            for k, v in paper_dict.items():
                console.print(f"[bold]{k}:[/bold] {v}")
        else:
            console.print("[red]Not found[/red]")

@app.command()
def get(
    paper_key: str,
    markdown: bool = typer.Option(False, "--markdown", help="Print full markdown"),
    json_fmt: bool = typer.Option(False, "--json", help="Print structured JSON"),
    bib: bool = typer.Option(False, "--bib", help="Print BibTeX"),
    all_fmt: bool = typer.Option(False, "--all", help="Print all formats"),
):
    """Get paper content in various formats."""
    db = get_db()
    if all_fmt or (not markdown and not json_fmt and not bib):
        all_fmt = True
    if all_fmt or markdown:
        md = db.get_markdown(paper_key)
        console.print(md) if not _state["json"] else _out({"markdown": md})
    if all_fmt or json_fmt:
        j = db.get_paper(paper_key)
        if _state["json"]:
            _out(j)
        else:
            console.print(_json.dumps(j, indent=2, default=str) if j else "Not found")
    if all_fmt or bib:
        p = db.get_paper(paper_key)
        bibtext = ""
        if p:
            bib_path = getattr(p, 'bibtex_path', None) if not isinstance(p, dict) else p.get('bibtex_path')
            if bib_path:
                try:
                    bibtext = Path(bib_path).read_text(encoding='utf-8')
                except Exception:
                    pass
        console.print(bibtext)

@app.command()
def equations(paper_key: str):
    """List extracted equations with source coordinates."""
    db = get_db()
    result = db.get_equations(paper_key)
    if _state["json"]:
        _out(result)
    else:
        t = Table(show_header=True, header_style="bold")
        t.add_column("#"); t.add_column("LaTeX"); t.add_column("Section"); t.add_column("Page")
        eqs = result if isinstance(result, list) else [result]
        for eq in eqs:
            t.add_row(str(eq.get("equation_number", "")), (eq.get("latex_raw") or eq.get("latex_normalized", ""))[:50], eq.get("section_path", ""), str(eq.get("page_number", "")))
        _out(None, table=t)

@app.command()
def methods(query: str, limit: int = typer.Option(20, "--limit", help="Max results")):
    """Find methods across papers matching a topic."""
    db = get_db()
    results = db.search(query, limit=limit)
    if _state["json"]:
        _out(results)
    else:
        t = _papers_table(results)
        _out(None, table=t)

@app.command()
def method(paper_key: str, name: Optional[str] = typer.Option(None, "--name", help="Method name to show")):
    """Show a method card with evidence links."""
    db = get_db()
    result = db.get_methods(paper_key)
    if _state["json"]:
        _out(result)
    else:
        ms = result if isinstance(result, list) else [result]
        if name:
            ms = [m for m in ms if name.lower() in (m.get("name", "")).lower()]
        for m in ms:
            console.print(f"[bold]{m.get('name', '')}[/bold] ({m.get('method_type', '')})")
            console.print(f"  Purpose: {m.get('purpose', '')}")
            console.print(f"  Confidence: {m.get('confidence', '')}")
            console.print()

# ── Tags ──────────────────────────────────────────────────────────────────────
@app.command()
def tags(
    category: Optional[str] = typer.Option(None, "--category", help="Filter by tag category"),
    merge: Optional[list[str]] = typer.Option(None, "--merge", help="Merge two tags (canonical alias)"),
):
    """List tags or merge tag aliases."""
    db = get_db()
    if merge:
        if len(merge) != 2:
            console.print("[red]--merge requires exactly two tag names[/red]")
            raise typer.Exit(1)
        result = db.merge_tags(merge[0], merge[1])
        _out(f"Merged: {result}" if not _state["json"] else {"result": result})
    else:
        result = db.list_tags(category=category)
        if _state["json"]:
            _out(result)
        else:
            t = Table(show_header=True, header_style="bold")
            t.add_column("Category"); t.add_column("Tag"); t.add_column("Count")
            tag_list = result if isinstance(result, list) else []
            for tag in tag_list:
                if isinstance(tag, dict):
                    t.add_row(tag.get("category", ""), tag.get("canonical_name", tag.get("name", "")), str(tag.get("count", "")))
                else:
                    t.add_row("", str(tag), "")
            _out(None, table=t)

@app.command()
def related(paper_key: str, limit: int = typer.Option(5, "--limit", help="Max results")):
    """Find papers sharing tags with the given paper."""
    db = get_db()
    result = db.get_related(paper_key, limit=limit) if hasattr(db, "get_related") else db.search("", limit=limit)
    if _state["json"]:
        _out(result)
    else:
        t = _papers_table(result if isinstance(result, list) else [])
        _out(None, table=t)

# ── Topical overviews ─────────────────────────────────────────────────────────
@app.command()
def topic(
    topic_name: str,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    out: Optional[str] = typer.Option(None, "--out", help="Write overview to file"),
):
    """Generate a topical review document comparing methods across papers."""
    db = get_db()
    result = db.build_topic_review(topic_name) if hasattr(db, "build_topic_review") else {"content": f"Topic review for '{topic_name}' — not yet implemented"}
    content = result.get("content", str(result)) if isinstance(result, dict) else str(result)
    if out:
        Path(out).write_text(content, encoding="utf-8")
        _out(f"Topic overview written to {out}" if not (json_output or _state["json"]) else {"out": out})
    elif json_output or _state["json"]:
        _out(result)
    else:
        console.print(content)

@app.command()
def compare(topic_name: str, axes: str = typer.Option(..., "--axes", help="Comparison axes (comma-separated)")):
    """Compare methods across papers along specified axes."""
    db = get_db()
    axes_list = axes.split(",")
    result = db.compare_methods(topic_name, axes_list) if hasattr(db, "compare_methods") else {"content": f"Comparison for '{topic_name}' — not yet implemented"}
    if _state["json"]:
        _out(result)
    else:
        content = result.get("content", str(result)) if isinstance(result, dict) else str(result)
        console.print(content)

# ── Export ────────────────────────────────────────────────────────────────────
@app.command()
def export(
    bibtex: bool = typer.Option(False, "--bibtex", help="Export as BibTeX"),
    out: Optional[str] = typer.Option(None, "--out", help="Write to file"),
):
    """Export the library."""
    db = get_db()
    result = db.export_bibtex() if hasattr(db, "export_bibtex") else ""
    if out:
        Path(out).write_text(result, encoding="utf-8")
        _out(f"Exported to {out}" if not _state["json"] else {"out": out, "chars": len(result)})
    else:
        console.print(result)

# ── Re-processing ─────────────────────────────────────────────────────────────
@app.command()
def reindex(
    re_summarize: bool = typer.Option(False, "--re-summarize", help="Re-run summarization"),
    re_tag: bool = typer.Option(False, "--re-tag", help="Re-run tag extraction"),
    re_extract_equations: bool = typer.Option(False, "--re-extract-equations", help="Re-run equation extraction"),
    llm_config: Optional[str] = typer.Option(None, "--llm-config", help="LLM config key"),
):
    """Re-process papers with updated settings."""
    db = get_db()
    operations = []
    if re_summarize: operations.append("summarize")
    if re_tag: operations.append("tag")
    if re_extract_equations: operations.append("equations")
    if not operations:
        console.print("[red]Must specify at least one --re-* flag[/red]")
        raise typer.Exit(1)
    result = db.reindex(operations, llm_config=llm_config or _state["llm_config"]) if hasattr(db, "reindex") else "reindex not yet implemented"
    _out(f"Reindex complete: {result}" if not _state["json"] else {"result": result, "operations": operations})

# ── Status ────────────────────────────────────────────────────────────────────
@app.command()
def status(
    missing: Optional[str] = typer.Option(None, "--missing", help="List papers missing a field (bibtex, summary, etc.)"),
    needs_reprocessing: bool = typer.Option(False, "--needs-reprocessing", help="List papers needing reprocessing"),
):
    """Show database statistics and processing status."""
    db = get_db()
    result = db.status()
    if _state["json"]:
        _out(result)
    else:
        if isinstance(result, dict):
            t = Table(show_header=True, header_style="bold")
            t.add_column("Metric"); t.add_column("Value")
            for k, v in result.items():
                t.add_row(k, str(v))
            _out(None, table=t)
        else:
            console.print(result)

# ── Server modes ──────────────────────────────────────────────────────────────
@app.command()
def mcp(
    transport: str = typer.Option("stdio", "--transport", help="Transport mode: stdio or sse"),
    port: int = typer.Option(8000, "--port", help="Port for SSE transport"),
    allow_mutations: bool = typer.Option(False, "--allow-mutations", help="Enable mutating tools"),
):
    """Start the MCP server for coding agent integration."""
    from paperdb.mcp import run_server
    run_server(transport=transport, port=port, allow_mutations=allow_mutations, db_path=_state["db_path"], data_dir=_state["data_dir"])

@app.command()
def gui():
    """Launch the GUI (not yet implemented)."""
    console.print("[yellow]GUI not yet implemented. Use 'paperdb search' or 'paperdb mcp' instead.[/yellow]")

# ── Migration ─────────────────────────────────────────────────────────────────
@app.command()
def migrate(
    from_db: Optional[str] = typer.Option(None, "--from", help="Source database path to migrate from"),
    from_mendeley: Optional[str] = typer.Option(None, "--from-mendeley", help="Mendeley BibTeX file to import"),
):
    """Import existing data from legacy databases or Mendeley BibTeX."""
    db = get_db()
    if from_db:
        result = db.migrate_from_db(from_db) if hasattr(db, "migrate_from_db") else f"Migration from {from_db} not yet implemented"
    elif from_mendeley:
        result = db.migrate_from_mendeley(from_mendeley) if hasattr(db, "migrate_from_mendeley") else f"Mendeley import from {from_mendeley} not yet implemented"
    else:
        console.print("[red]Must specify --from or --from-mendeley[/red]")
        raise typer.Exit(1)
    _out(f"Migration complete: {result}" if not _state["json"] else {"result": result})

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    app()

if __name__ == "__main__":
    main()

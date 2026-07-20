"""Context pack assembly with two-stage retrieval."""

from dataclasses import dataclass, field
from typing import Optional
from .fts import fts_search, fts_search_for_papers, SearchUnit
from .ranking import rank_papers, SearchResult, search


@dataclass
class ContextPack:
    query: str = ""
    filters_json: str = ""
    selected_units_json: str = ""
    content: str = ""
    output_path: Optional[str] = None
    token_estimate: int = 0
    paper_count: int = 0


def assemble_context_pack(query, repo, token_budget=24000, include=None, filters=None):
    """Two-stage retrieval + context pack assembly.

    1. Search papers (stage A) — use ranking.rank_papers()
    2. Select top N papers within token budget
    3. For each paper, retrieve relevant search units (stage B)
    4. Assemble context pack markdown
    5. Estimate token count (rough: chars/4)
    6. Truncate to token budget
    7. Return ContextPack (does NOT save to DB — caller decides)
    """
    include = include or ["summary", "equations", "methods", "assumptions", "sections"]
    filters = filters or {}

    # Stage A: search and rank papers
    fts_results = fts_search(query, repo, limit=500)
    results = rank_papers(
        query, fts_results, repo,
        required_tags=filters.get('required_tags'),
        preferred_tags=filters.get('preferred_tags'),
        excluded_tags=filters.get('excluded_tags'),
        year_range=filters.get('year_range'),
        explain=True
    )

    if not results:
        return ContextPack(query=query, content=f"# Context pack: {query}\n\nNo papers found.\n")

    # Stage B: for each paper, retrieve relevant search units
    paper_ids = [r.paper.id for r in results]
    stage_b_units = fts_search_for_papers(query, paper_ids, repo, limit=200)

    # Group stage B units by paper_id
    units_by_paper = {}
    for u in stage_b_units:
        units_by_paper.setdefault(u['paper_id'], []).append(u)

    # Assemble context pack
    sections = []
    sections.append(f"# Context pack: {query}\n")

    # Build per-paper sections within token budget
    selected_papers = []
    selected_units_info = []
    total_chars = 0
    max_chars = token_budget * 4  # rough: 4 chars per token

    # Header overhead
    header = f"# Context pack: {query}\n\n## Papers ({{N}} selected)\n\n"
    total_chars += len(header)

    for idx, result in enumerate(results, 1):
        paper = result.paper
        paper_section = _format_paper_section(idx, result, units_by_paper.get(paper.id, []),
                                               include, repo)
        section_chars = len(paper_section)

        if total_chars + section_chars > max_chars:
            break

        sections.append(paper_section)
        selected_papers.append(paper)
        selected_units_info.extend(units_by_paper.get(paper.id, []))
        total_chars += section_chars

    # Update header with actual count
    header = f"# Context pack: {query}\n\n## Papers ({len(selected_papers)} selected)\n\n"
    sections[0] = header

    # Comparison matrix
    if len(selected_papers) > 1:
        matrix = _build_comparison_matrix(selected_papers, results, repo)
        sections.append(matrix)
        total_chars += len(matrix)

    # Bibliography
    bib = _build_bibliography(selected_papers, repo)
    sections.append(bib)
    total_chars += len(bib)

    content = '\n'.join(sections)

    # Truncate if over budget
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[... truncated due to token budget ...]\n"

    import json
    return ContextPack(
        query=query,
        filters_json=json.dumps(filters),
        selected_units_json=json.dumps([u['unit_id'] for u in selected_units_info]),
        content=content,
        token_estimate=len(content) // 4,
        paper_count=len(selected_papers)
    )


def _format_paper_section(idx, result, units, include, repo):
    """Format a single paper's section in the context pack."""
    paper = result.paper
    lines = []
    lines.append(f"### {idx}. {paper.paper_key}\n")

    # Score breakdown
    breakdown_str = ", ".join(f"{k}: {v}" for k, v in result.breakdown.items())
    lines.append(f"**Score**: {result.score} ({breakdown_str})\n")

    # Summary
    if "summary" in include:
        summary = _get_active_summary(paper.id, repo)
        if summary:
            lines.append(f"**Summary**: {summary[:500]}...\n" if len(summary) > 500 else f"**Summary**: {summary}\n")

    # Key equations
    if "equations" in include:
        eq_units = [u for u in units if u.get('unit_type') == 'equation']
        if eq_units:
            lines.append("**Key equations**:")
            for eq in eq_units[:5]:
                lines.append(f"  - `{eq['content'].strip()}`")
            lines.append("")

    # Methods
    if "methods" in include:
        method_units = [u for u in units if u.get('unit_type') == 'method']
        if method_units:
            lines.append("**Methods**:")
            for m in method_units[:3]:
                content_preview = m['content'][:200].replace('\n', ' ')
                lines.append(f"  - {content_preview}")
            lines.append("")

    # Relevant sections
    if "sections" in include:
        section_units = [u for u in units if u.get('unit_type') in ('section', 'paragraph')]
        if section_units:
            lines.append("**Relevant sections**:")
            for s in section_units[:5]:
                content_preview = s['content'][:200].replace('\n', ' ')
                lines.append(f"  - [{s.get('section_path', '')}] {content_preview}")
            lines.append("")

    # Assumptions (from method cards if available)
    if "assumptions" in include:
        methods = _get_methods_for_paper(paper.id, repo)
        for m in methods[:2]:
            if m.get('card_json'):
                import json
                try:
                    card = json.loads(m['card_json'])
                    if card.get('assumptions'):
                        lines.append(f"**Assumptions** ({m.get('name', '')}):")
                        for a in card['assumptions'][:3]:
                            lines.append(f"  - {a}")
                        lines.append("")
                except (json.JSONDecodeError, TypeError):
                    pass

    lines.append("")
    return '\n'.join(lines)


def _build_comparison_matrix(papers, results, repo):
    """Build a comparison matrix table across selected papers."""
    lines = []
    lines.append("## Comparison matrix\n")
    lines.append("| Paper | Method | Complexity | Year | Score |")
    lines.append("|-------|--------|------------|------|-------|")

    for paper, result in zip(papers, results):
        methods = _get_methods_for_paper(paper.id, repo)
        method_name = methods[0]['name'] if methods else 'N/A'
        complexity = methods[0].get('complexity', 'N/A') if methods else 'N/A'
        year = paper.year or 'N/A'
        lines.append(f"| {paper.paper_key} | {method_name} | {complexity} | {year} | {result.score} |")

    lines.append("")
    return '\n'.join(lines)


def _build_bibliography(papers, repo):
    """Build BibTeX bibliography section."""
    lines = []
    lines.append("## Bibliography\n")
    for paper in papers:
        bib = _get_bibtex(paper.id, repo)
        if bib:
            lines.append(bib)
            lines.append("")
        else:
            # Generate minimal BibTeX from metadata
            key = paper.paper_key or f"paper_{paper.id}"
            title = paper.title or 'Unknown'
            authors = paper.authors_text or ''
            year = paper.year or ''
            lines.append(f"@article{{{key},")
            lines.append(f"  title = {{{title}}},")
            if authors:
                lines.append(f"  author = {{{authors}}},")
            if year:
                lines.append(f"  year = {{{year}}},")
            lines.append("}")
            lines.append("")
    return '\n'.join(lines)


# --- DB helper functions (use repo) ---

def _get_active_summary(paper_id, repo):
    """Get active summary content for a paper."""
    sql = "SELECT content FROM summaries WHERE paper_id = ? AND is_active = 1 ORDER BY timestamp DESC LIMIT 1"
    row = repo.conn.execute(sql, (paper_id,)).fetchone()
    return row[0] if row else None


def _get_methods_for_paper(paper_id, repo):
    """Get method cards for a paper. Returns list of dicts."""
    sql = "SELECT id, name, method_type, purpose, complexity, confidence, card_json, source_passages_json FROM methods WHERE paper_id = ?"
    rows = repo.conn.execute(sql, (paper_id,)).fetchall()
    return [dict(r) for r in rows]


def _get_bibtex(paper_id, repo):
    """Get BibTeX text for a paper from bibtex_path or DB."""
    # Check if paper has bibtex_path
    sql = "SELECT bibtex_path FROM papers WHERE id = ?"
    row = repo.conn.execute(sql, (paper_id,)).fetchone()
    if row and row[0]:
        import os
        if os.path.exists(row[0]):
            with open(row[0], 'r') as f:
                return f.read().strip()
    return None

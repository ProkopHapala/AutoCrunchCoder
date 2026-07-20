"""Topical overviews: query → papers → method cards → comparison → synthesis.

This is the "review paper for LLMs" feature — generates overview documents
comparing methods across papers. Evidence-backed: every claim in the review
links back to specific papers and passages.
"""

import json
from typing import Optional

TOPIC_REVIEW_PROMPT = """You are an expert computational scientist writing a topical review for other scientists and LLM coding agents.

Write a structured review comparing the methods found across the selected papers.
Every claim must reference the specific paper it comes from (use [paper_key] or [N] notation).

Format:
## Overview
Brief introduction to the topic and why it matters.

## Methods Compared
For each paper, describe the key method and its approach.

## Comparison
Compare methods along the specified axes. Use a table format.

## Key Equations
List the most important equations across papers with their sources.

## Recommendations
Which method is best suited for which use case? What are the trade-offs?

## Gaps
What's missing from the literature? What would be needed next?

Rules:
- Be evidence-backed: every claim references a specific paper.
- Be technically precise.
- Do not invent information not present in the papers.
- Use LaTeX for equations."""

INTERPRET_QUERY_PROMPT = """You are an expert computational scientist. Interpret the following research query and extract structured search parameters.

Return JSON:
{
  "search_terms": ["list of text search terms for FTS"],
  "required_tags": [["category", "tag_name"], ...],
  "preferred_tags": [["category", "tag_name"], ...],
  "comparison_axes": ["list of axes to compare methods along"]
}

Rules:
- search_terms: terms for full-text search
- required_tags: tags that MUST match (high relevance)
- preferred_tags: tags that are nice to have
- comparison_axes: dimensions to compare methods (e.g. "spatial_structure", "complexity", "synchronization")"""

def build_topic_review(topic: str, repo, db=None, focus=None, constraints=None,
                       max_papers=30, llm_config=None, comparison_axes=None) -> dict:
    """Multi-step topical overview generation.

    Steps:
    1. Interpret query → search terms + relevant tags
    2. Find papers: db.search(topic, limit=max_papers)
    3. Retrieve method cards for each paper
    4. Build comparison matrix along relevant axes
    5. Synthesize evidence-backed review using LLM
    6. Store in topics + topic_papers + topic_overviews tables

    Args:
        topic: Research topic/query string.
        repo: Repository for storing results.
        db: PaperDB instance with search() method. If None, creates one.
        focus: Optional focus subtopic to narrow the review.
        constraints: Optional dict of constraints (year_range, tags, etc.).
        max_papers: Maximum papers to include.
        llm_config: LLM template key or None for default.

    Returns:
        Dict with 'content' (review markdown), 'topic_id', 'papers_used', 'comparison_matrix'.
    """
    from paperdb.config import make_agent, response_text

    if db is None:
        from paperdb import PaperDB
        db = PaperDB()

    agent = make_agent(llm_config)

    # Step 1: Interpret query
    agent.set_system_prompt(INTERPRET_QUERY_PROMPT)
    query_prompt = f"Topic: {topic}\nFocus: {focus or 'general'}\nConstraints: {json.dumps(constraints or {})}\n\nExtract search parameters."
    response = agent.query(query_prompt, response_format={"type": "json_object"})
    raw_text = response_text(agent, response)

    search_params = _parse_json(raw_text)
    if not isinstance(search_params, dict): raise ValueError("Topic query interpretation must be a JSON object")

    search_terms = search_params.get('search_terms', [topic])
    if not search_terms:
        search_terms = [topic]
    comparison_axes = comparison_axes or search_params.get('comparison_axes', [])
    if not comparison_axes:
        comparison_axes = ['complexity', 'accuracy', 'scalability']

    # Step 2: apply interpreted tags and caller constraints to real retrieval.
    search_query = ' '.join(search_terms)
    constraints = constraints or {}
    papers = db.search(search_query,
                       required_tags=[*search_params.get('required_tags', []), *constraints.get('required_tags', [])] or None,
                       preferred_tags=[*search_params.get('preferred_tags', []), *constraints.get('preferred_tags', [])] or None,
                       excluded_tags=constraints.get('excluded_tags'), year_range=constraints.get('year_range'),
                       limit=max_papers, explain=True)
    papers = [_paper_record(paper) for paper in papers]

    if not papers:
        print(f"[topic_reviews] No papers found for topic '{topic}'")
        return {'content': f'No papers found for topic: {topic}', 'topic_id': None, 'papers_used': [], 'comparison_matrix': {}}

    # Step 3: Retrieve method cards for each paper
    all_methods = []
    paper_method_map = {}
    for p in papers:
        pid = p.get('id')
        if not pid: continue
        methods = repo.get_methods(pid, method_type='reconstructed_method')
        if not methods: methods = repo.get_methods(pid)
        paper_method_map[pid] = methods
        all_methods.extend(methods)

    # Step 4: Build comparison matrix
    comparison_matrix = build_comparison_matrix(papers, all_methods, comparison_axes, repo)

    # Step 5: Synthesize review
    agent.set_system_prompt(TOPIC_REVIEW_PROMPT)

    paper_summaries = []
    for i, p in enumerate(papers):
        pid = p.get('id')
        method_descs = []
        for method in paper_method_map.get(pid, [])[:3]:
            m = method if isinstance(method, dict) else method.model_dump()
            passages = json.loads(m.get('source_passages_json') or '[]')
            method_descs.append(f"  - {m.get('name', 'unknown')}: {m.get('purpose', '')}\n    Evidence: {json.dumps(passages[:5], ensure_ascii=False)}")
        equations = repo.get_equations_for_paper(pid)[:8]
        equation_descs = []
        for equation in equations:
            eq = equation if isinstance(equation, dict) else equation.model_dump()
            equation_descs.append(f"Eq. {eq.get('equation_number') or '?'} page {eq.get('page_number') or '?'} section {eq.get('section_path') or '?'}: {eq.get('latex_raw') or ''}")
        paper_summaries.append(f"[{i+1}] {p.get('paper_key', '?')} ({p.get('year', '?')}): {p.get('title', '?')}\n  Essence: {p.get('essence', 'N/A')}\n  Methods:\n{chr(10).join(method_descs) if method_descs else '  No method cards extracted'}\n  Equations:\n{chr(10).join(equation_descs) if equation_descs else '  No equations extracted'}")

    comparison_table = _format_comparison_matrix(comparison_matrix)

    review_prompt = f"""Topic: {topic}
Focus: {focus or 'general'}

Selected papers ({len(papers)}):
{''.join(paper_summaries)}

Comparison matrix:
{comparison_table}

Comparison axes: {', '.join(comparison_axes)}

Write a comprehensive topical review. Use [N] to reference paper N from the list above."""

    response = agent.query(review_prompt)
    review_content = response_text(agent, response)

    # Step 6: Store the evidence-bearing review and paper associations.
    topic_id = repo.add_topic(topic, description=focus or '')
    for i, paper in enumerate(papers):
        if paper.get('id'):
            repo.add_topic_paper(topic_id=topic_id, paper_id=paper['id'], relevance=f"Matched search: {search_query}", match_score=1.0 / (i + 1))
    repo.add_topic_overview(topic_id=topic_id, content=review_content, original_query=topic,
                            filters_json=json.dumps({'focus': focus, 'constraints': constraints, 'search_params': search_params}),
                            comparison_matrix_json=json.dumps(comparison_matrix), model_name=getattr(agent, 'model_name', 'unknown'),
                            prompt_version='v1', is_active=1)

    return {
        'content': review_content,
        'topic_id': topic_id,
        'papers_used': papers,
        'comparison_matrix': comparison_matrix,
    }

def _paper_record(value) -> dict:
    """Normalize PaperDB search results, including the facade's nested paper object."""
    if isinstance(value, dict):
        paper = dict(value.get('paper') or value)
        for key in ('id', 'paper_key', 'title', 'year', 'essence', 'abstract'):
            if key not in paper and key in value: paper[key] = value[key]
        return paper
    return value.model_dump() if hasattr(value, 'model_dump') else vars(value)

def build_comparison_matrix(papers: list, methods: list, axes: list, repo) -> dict:
    """Build a comparison matrix across papers along specified axes.

    Args:
        papers: List of paper dicts/objects.
        methods: List of method dicts/objects.
        axes: List of axis names (e.g. "spatial_structure", "complexity").
        repo: Repository for fetching additional data.

    Returns:
        {'axes': [...], 'papers': [...], 'matrix': [[...]]}
    """
    paper_keys = []
    for p in papers:
        p = p if isinstance(p, dict) else {'id': getattr(p, 'id', None), 'paper_key': getattr(p, 'paper_key', '')}
        paper_keys.append(p.get('paper_key', str(p.get('id', '?'))))

    # Build matrix: for each paper, extract values for each axis from method cards
    matrix = []
    for p in papers:
        p = p if isinstance(p, dict) else {'id': getattr(p, 'id', None)}
        pid = p.get('id')
        row = []
        for axis in axes:
            value = _extract_axis_value(pid, axis, methods, repo)
            row.append(value)
        matrix.append(row)

    return {'axes': axes, 'papers': paper_keys, 'matrix': matrix}

def _extract_axis_value(paper_id: int, axis: str, methods: list, repo) -> str:
    """Extract a comparison value for a specific axis from a paper's method cards."""
    paper_methods = [m for m in methods if _get_method_field(m, 'paper_id') == paper_id]
    for m in paper_methods:
        card_json = _get_method_field(m, 'card_json', '{}')
        if isinstance(card_json, str):
            card = json.loads(card_json)
        else:
            card = card_json

        # Map common axes to card fields
        axis_lower = axis.lower()
        if axis_lower in card:
            val = card[axis_lower]
            return str(val) if val is not None else 'N/A'
        if axis_lower == 'complexity':
            c = _get_method_field(m, 'complexity', '')
            return c or card.get('complexity', 'N/A')
        if axis_lower == 'parallelization':
            return str(card.get('parallelization', 'N/A'))
        if axis_lower == 'limitations':
            lims = card.get('limitations', [])
            return '; '.join(lims) if lims else 'N/A'
        if axis_lower == 'assumptions':
            assumptions = card.get('assumptions', [])
            return '; '.join(assumptions) if assumptions else 'N/A'

    return 'N/A'

def _get_method_field(method, field, default=None):
    """Get a field from a method dict or object."""
    if isinstance(method, dict):
        return method.get(field, default)
    return getattr(method, field, default)

def _format_comparison_matrix(matrix: dict) -> str:
    """Format comparison matrix as markdown table."""
    axes = matrix.get('axes', [])
    papers = matrix.get('papers', [])
    data = matrix.get('matrix', [])

    if not papers or not axes:
        return "No comparison data available."

    # Header
    header = "| Paper | " + " | ".join(axes) + " |"
    separator = "|---" * (len(axes) + 1) + "|"
    lines = [header, separator]

    for i, paper in enumerate(papers):
        row = data[i] if i < len(data) else []
        cells = [paper] + [str(row[j]) if j < len(row) else 'N/A' for j in range(len(axes))]
        lines.append("| " + " | ".join(cells) + " |")

    return '\n'.join(lines)

def _parse_json(text: str) -> dict:
    """Parse JSON from LLM response, handling code fences."""
    import re
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        text = text[start:end+1]
    return json.loads(text)

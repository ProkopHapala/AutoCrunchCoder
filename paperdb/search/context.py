'''Evidence-bearing context-pack assembly.'''

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .fts import fts_search_for_papers
from .ranking import _split_query, search


@dataclass
class ContextPack:
    id: Optional[int] = None
    query: str = ''
    filters_json: str = ''
    selected_units_json: str = ''
    content: str = ''
    output_path: Optional[str] = None
    token_estimate: int = 0
    paper_count: int = 0


def _dict(value):
    if isinstance(value, dict):
        return value
    if hasattr(value, 'model_dump'):
        return value.model_dump()
    return vars(value)


def _excerpt(text, limit=1600):
    '''Return a bounded excerpt at a paragraph/line boundary.'''
    text = (text or '').strip()
    if len(text) <= limit:
        return text
    cut = max(text.rfind('\n\n', 0, limit), text.rfind('\n', 0, limit), text.rfind('. ', 0, limit))
    if cut < limit // 2:
        cut = limit
    return text[:cut].rstrip() + '\n[excerpt continues in source artifact]'


def assemble_context_pack(query, repo, token_budget=24000, include=None, filters=None):
    include = include or ['summary', 'equations', 'methods', 'assumptions', 'sections']
    filters = filters or {}
    results = search(query, repo, required_tags=filters.get('required_tags'),
                     preferred_tags=filters.get('preferred_tags'), excluded_tags=filters.get('excluded_tags'),
                     year_range=filters.get('year_range'), limit=500, explain=True)
    if not results:
        return ContextPack(query=query, filters_json=json.dumps(filters), content=f'# Context pack: {query}\n\nNo papers found.\n')

    text_query, _ = _split_query(query)
    paper_ids = [result.paper.id for result in results]
    stage_b = fts_search_for_papers(text_query, paper_ids, repo, limit=500) if text_query else []
    units_by_paper = {}
    for unit in stage_b:
        units_by_paper.setdefault(unit['paper_id'], []).append(unit)

    max_chars = max(256, token_budget * 4)
    header = f'# Context pack: {query}\n\n'
    parts, selected, selected_units = [header], [], []
    used = len(header)
    for index, result in enumerate(results, 1):
        remaining = max_chars - used
        section, included_unit_ids = _format_paper_section(index, result, units_by_paper.get(result.paper.id, []), include, repo, remaining)
        if not section or len(section) > remaining:
            continue
        parts.append(section)
        selected.append(result)
        selected_units.extend(included_unit_ids)
        used += len(section)

    if len(selected) > 1:
        matrix = _build_comparison_matrix(selected, repo)
        if used + len(matrix) <= max_chars:
            parts.append(matrix); used += len(matrix)
    bibliography = _build_bibliography([result.paper for result in selected])
    if used + len(bibliography) <= max_chars:
        parts.append(bibliography); used += len(bibliography)

    content = '\n'.join(parts)
    return ContextPack(query=query, filters_json=json.dumps(filters),
                       selected_units_json=json.dumps(selected_units),
                       content=content, token_estimate=(len(content) + 3) // 4, paper_count=len(selected))


def _format_paper_section(index, result, units, include, repo, max_chars):
    paper = result.paper
    breakdown = ', '.join(f'{key}: {value}' for key, value in result.breakdown.items())
    base = f'## {index}. {paper.paper_key}\n\n**Title**: {paper.title or "Unknown"}\n\n**Year**: {paper.year or "Unknown"}\n\n**Score**: {result.score} ({breakdown})\n\n'
    if len(base) > max_chars:
        return '', []
    blocks = [base]
    used = len(base)
    evidence_added = False
    included_unit_ids = []

    def add(block):
        nonlocal used, evidence_added
        if block and used + len(block) <= max_chars:
            blocks.append(block); used += len(block); evidence_added = True
            return True
        return False

    if 'summary' in include:
        summary = repo.get_active_summary(paper.id)
        if summary and summary.content:
            add(f'### Scientific summary\n\n{summary.content.strip()}\n\n')

    if 'equations' in include:
        lines = []
        for equation in repo.get_equations_for_paper(paper.id)[:8]:
            eq = _dict(equation)
            location = ', '.join(part for part in [f"page {eq.get('page_number')}" if eq.get('page_number') is not None else '', eq.get('section_path') or '', f"parser {eq.get('parser')}" if eq.get('parser') else '', f"run {eq.get('run_id')}" if eq.get('run_id') else ''] if part)
            lines.append(f"- Eq. {eq.get('equation_number') or '?'} ({location or 'location unavailable'}):\n\n  ```latex\n  {_excerpt(eq.get('latex_raw'), 1200)}\n  ```")
            variables = repo.get_variables_for_equation(eq['id']) if eq.get('id') else []
            for variable in variables:
                var = _dict(variable)
                lines.append(f"  - `{var.get('symbol')}` — {var.get('meaning')} (page {var.get('source_page') or '?'})")
        if lines:
            add('### Equations and source coordinates\n\n' + '\n'.join(lines) + '\n\n')

    methods = repo.get_methods_for_paper(paper.id) if ('methods' in include or 'assumptions' in include) else []
    if methods:
        lines = []
        for method in methods[:5]:
            m = _dict(method)
            card = json.loads(m.get('card_json') or '{}')
            passages = json.loads(m.get('source_passages_json') or '[]')
            lines.append(f"- **{m.get('name') or 'Unnamed'}** [{m.get('method_type') or 'unknown'}, confidence {m.get('confidence')}] — {m.get('purpose') or ''}")
            if 'methods' in include:
                for field in ('inputs', 'outputs', 'initialization', 'steps', 'boundary_conditions', 'convergence', 'parallelization', 'limitations'):
                    value = card.get(field)
                    if value:
                        lines.append(f"  - {field}: {value}")
            if 'assumptions' in include and card.get('assumptions'):
                lines.append(f"  - assumptions: {card['assumptions']}")
            if card.get('field_evidence'):
                lines.append(f"  - field evidence indexes: {card['field_evidence']}")
            for passage_index, passage in enumerate(passages[:5]):
                passage = passage if isinstance(passage, dict) else {'text': str(passage)}
                location = ', '.join(str(value) for value in [passage.get('section'), f"page {passage.get('page')}" if passage.get('page') is not None else None] if value)
                lines.append(f"  - evidence[{passage_index}] ({location or 'location unavailable'}): {_excerpt(passage.get('text'), 900)}")
        add('### Method cards and evidence\n\n' + '\n'.join(lines) + '\n\n')

    if 'sections' in include:
        relevant_units = [u for u in units if u.get('unit_type') in ('section', 'paragraph')][:8]
        lines = []
        for unit in relevant_units:
            location = ', '.join(part for part in [unit.get('section_path') or '', f"pages {unit.get('page_from')}-{unit.get('page_to')}" if unit.get('page_from') else ''] if part)
            lines.append(f"- [{location or 'section'}; unit {unit.get('unit_id')}] {_excerpt(unit.get('content'), 1400)}")
        if lines and add('### Relevant source passages\n\n' + '\n\n'.join(lines) + '\n\n'):
            included_unit_ids.extend(unit['unit_id'] for unit in relevant_units)

    if 'markdown' in include and paper.markdown_path and Path(paper.markdown_path).exists():
        markdown = Path(paper.markdown_path).read_text(encoding='utf-8')
        add(f'### Full compiled Markdown\n\n{markdown}\n\n')
    return (''.join(blocks), included_unit_ids) if evidence_added or not include else ('', [])


def _build_comparison_matrix(results, repo):
    lines = ['## Comparison matrix\n', '| Paper | Method | Complexity | Year | Score |', '|---|---|---|---|---|']
    for result in results:
        paper = result.paper
        methods = repo.get_methods_for_paper(paper.id)
        method = _dict(methods[0]) if methods else {}
        lines.append(f"| {paper.paper_key} | {method.get('name', 'N/A')} | {method.get('complexity') or 'N/A'} | {paper.year or 'N/A'} | {result.score} |")
    return '\n'.join(lines) + '\n\n'


def _build_bibliography(papers):
    lines = ['## Bibliography\n']
    for paper in papers:
        if paper.bibtex_path and Path(paper.bibtex_path).exists():
            lines.append(Path(paper.bibtex_path).read_text(encoding='utf-8').strip())
        else:
            lines.append(f"@article{{{paper.paper_key or f'paper_{paper.id}'},\n  title = {{{paper.title or 'Unknown'}}},\n  author = {{{paper.authors_text or ''}}},\n  year = {{{paper.year or ''}}},\n}}")
    return '\n\n'.join(lines) + '\n'

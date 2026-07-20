"""FTS5 full-text search on search_units and markdown-to-search-units splitting."""

import re
from dataclasses import dataclass, field
from typing import Optional

# --- SearchUnit (duck-typed; matches paperdb.db.models.SearchUnit from Task 1) ---

@dataclass
class SearchUnit:
    id: Optional[int] = None
    paper_id: int = 0
    run_id: Optional[int] = None
    unit_type: str = ""          # 'summary' | 'section' | 'paragraph' | 'equation' | 'method'
    source_type: str = ""        # 'section' | 'equation' | 'method' | 'summary'
    source_id: Optional[int] = None
    section_path: str = ""
    page_from: Optional[int] = None
    page_to: Optional[int] = None
    content: str = ""


# --- FTS5 search ---

def _sanitize_fts_query(query):
    """Sanitize a query string for FTS5 MATCH.
    Wraps terms in double quotes to prevent FTS5 syntax errors with hyphens, etc.
    Multiple words become an AND query of quoted terms.
    """
    terms = query.strip().split()
    if not terms:
        return '""'
    return ' '.join(f'"{t}"' for t in terms)


def fts_search(query, repo, limit=100):
    """Execute FTS5 query on search_units_fts.
    Returns list of dicts: {unit_id, paper_id, content, section_path, rank, unit_type, source_type, source_id}.
    Uses BM25 ranking from FTS5 (lower rank = better match).
    """
    fts_query = _sanitize_fts_query(query)
    sql = """
        SELECT su.id AS unit_id, su.paper_id, su.content, su.section_path,
               su.unit_type, su.source_type, su.source_id,
               bm25(search_units_fts) AS rank
        FROM search_units_fts
        JOIN search_units su ON su.id = search_units_fts.rowid
        WHERE search_units_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    rows = repo.conn.execute(sql, (fts_query, limit)).fetchall()
    return [dict(r) for r in rows]


def fts_search_for_papers(query, paper_ids, repo, limit=100):
    """FTS5 search restricted to a set of paper_ids (used in Stage B of two-stage retrieval)."""
    if not paper_ids:
        return []
    fts_query = _sanitize_fts_query(query)
    placeholders = ",".join("?" * len(paper_ids))
    sql = f"""
        SELECT su.id AS unit_id, su.paper_id, su.content, su.section_path,
               su.unit_type, su.source_type, su.source_id,
               bm25(search_units_fts) AS rank
        FROM search_units_fts
        JOIN search_units su ON su.id = search_units_fts.rowid
        WHERE search_units_fts MATCH ? AND su.paper_id IN ({placeholders})
        ORDER BY rank
        LIMIT ?
    """
    params = [fts_query] + list(paper_ids) + [limit]
    rows = repo.conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# --- Markdown to search units ---

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
_EQUATION_RE = re.compile(r'^\$\$(.+?)\$\$$', re.DOTALL)
_FRONTMATTER_DELIM = '---'


def build_search_units_from_markdown(paper_id, markdown_text, run_id, repo):
    """Split markdown into search units by headings/equations/paragraphs.
    Types: 'summary', 'section', 'paragraph', 'equation', 'method'.
    Store via repo.replace_search_units() (transactional delete+insert, FTS triggers auto-sync).
    Returns list of created SearchUnit objects.
    """
    units = _split_markdown_to_units(paper_id, markdown_text, run_id)
    repo.replace_search_units(paper_id, units)
    return units


def _split_markdown_to_units(paper_id, markdown_text, run_id):
    """Parse markdown text and produce SearchUnit list."""
    lines = markdown_text.split('\n')
    units = []

    # Skip YAML front matter
    i = 0
    if lines and lines[0].strip() == _FRONTMATTER_DELIM:
        i = 1
        while i < len(lines) and lines[i].strip() != _FRONTMATTER_DELIM:
            i += 1
        i += 1  # skip closing delimiter

    in_summary = False
    in_source_text = False
    current_section_path = ""
    current_level = 0
    section_content = []
    section_start_line = 0

    def flush_section():
        """Emit a section unit from accumulated content."""
        nonlocal section_content
        text = '\n'.join(section_content).strip()
        if not text:
            section_content = []
            return
        is_method = 'method' in current_section_path.lower()
        if in_summary and current_section_path:
            unit_type = 'summary'
            source_type = 'summary'
        elif is_method:
            unit_type = 'method'
            source_type = 'method'
        else:
            unit_type = 'section'
            source_type = 'section'
        units.append(SearchUnit(
            paper_id=paper_id, run_id=run_id, unit_type=unit_type,
            source_type=source_type, section_path=current_section_path,
            content=text
        ))
        # Also split into paragraphs
        _split_paragraphs(units, paper_id, run_id, current_section_path, text, in_summary)
        section_content = []

    def flush_equation(eq_text, section_path, line_num):
        units.append(SearchUnit(
            paper_id=paper_id, run_id=run_id, unit_type='equation',
            source_type='equation', section_path=section_path,
            content=eq_text.strip()
        ))

    while i < len(lines):
        line = lines[i]

        # Check for heading
        m = _HEADING_RE.match(line)
        if m:
            # Flush previous section
            flush_section()
            level = len(m.group(1))
            heading_text = m.group(2).strip()
            # Track summary vs source text sections
            if 'generated scientific summary' in heading_text.lower():
                in_summary = True
                in_source_text = False
                current_section_path = ""
                current_level = level
                i += 1
                continue
            elif 'extracted source text' in heading_text.lower():
                in_summary = False
                in_source_text = True
                current_section_path = ""
                current_level = level
                i += 1
                continue
            # Build section path
            if level <= current_level:
                # Go up — just use heading text as path
                current_section_path = heading_text
            else:
                if current_section_path:
                    current_section_path = f"{current_section_path} > {heading_text}"
                else:
                    current_section_path = heading_text
            current_level = level
            section_start_line = i
            i += 1
            continue

        # Check for equation block $$...$$
        stripped = line.strip()
        if stripped.startswith('$$'):
            if stripped.endswith('$$') and len(stripped) > 4:
                # Single-line equation
                flush_section()
                flush_equation(stripped, current_section_path, i)
                i += 1
                continue
            else:
                # Multi-line equation block
                flush_section()
                eq_lines = [line]
                i += 1
                while i < len(lines) and '$$' not in lines[i]:
                    eq_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    eq_lines.append(lines[i])
                    i += 1
                flush_equation('\n'.join(eq_lines), current_section_path, i)
                continue

        section_content.append(line)
        i += 1

    # Flush last section
    flush_section()

    return units


def _split_paragraphs(units, paper_id, run_id, section_path, text, in_summary):
    """Split section text into paragraph-level search units."""
    paragraphs = re.split(r'\n\s*\n', text)
    for para in paragraphs:
        para = para.strip()
        if len(para) < 20:  # skip very short fragments
            continue
        is_method = 'method' in section_path.lower()
        if in_summary:
            unit_type = 'summary'
            source_type = 'summary'
        elif is_method:
            unit_type = 'method'
            source_type = 'method'
        else:
            unit_type = 'paragraph'
            source_type = 'section'
        units.append(SearchUnit(
            paper_id=paper_id, run_id=run_id, unit_type=unit_type,
            source_type=source_type, section_path=section_path,
            content=para
        ))

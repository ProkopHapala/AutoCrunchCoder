"""Equation extraction with source coordinates.

Extracts equations from Docling structured output and stores them via the repository.
Key principles (§18 D10):
- Source fidelity: store both latex_raw (what parser extracted) and latex_normalized
  (cleaned up) — never overwrite raw.
- Variable definitions as separate evidence records with source location.
- Equation extraction and paper classification are separate concerns.
"""
import re, json, logging
from typing import Optional

from ..db.models import Equation, EquationVariable

logger = logging.getLogger(__name__)

# Patterns for extracting variable definitions from surrounding text
_VAR_DEF_PATTERNS = [
    # "where x is the position", "where E is the energy" — stop at comma, semicolon, period, or " and <var> is/denotes"
    re.compile(r'(?:where|let|with|and|,)\s+\\?([a-zA-Z][a-zA-Z0-9_]*)\s+(?:is|denotes?|represents?|stands for)\s+(.+?)(?=\s+and\s+\w+\s+(?:is|denotes?|represents?|stands for)|[,;.]|$)', re.IGNORECASE),
    # "x := position", "x = position"
    re.compile(r'\\?([a-zA-Z][a-zA-Z0-9_]*)\s*[:=]\s*(.+?)(?:[,;.]|$)'),
    # "$x$ — the position"
    re.compile(r'\$([a-zA-Z][a-zA-Z0-9_]*)\$\s*[—\-–:]\s*(.+?)(?:[,;.]|$)'),
]


def _normalize_latex(latex_raw: str) -> str:
    """Basic LaTeX normalization — strip trailing equation numbers, fix common issues."""
    s = latex_raw.strip()
    # Remove trailing equation numbers like (1), (2.3)
    s = re.sub(r'\s*\(\d+(?:\.\d+)*\)\s*$', '', s)
    # Remove surrounding $$ if present
    if s.startswith('$$') and s.endswith('$$'):
        s = s[2:-2].strip()
    # Remove surrounding $ if present (inline)
    if s.startswith('$') and s.endswith('$') and len(s) > 2:
        s = s[1:-1].strip()
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s)
    return s


def _extract_variable_defs(context_before: str, context_after: str, page: Optional[int]) -> list[dict]:
    """Extract variable definitions from surrounding text.
    Looks for patterns like "where x is the position" in context_after.
    """
    variables = []
    text = (context_after or "") + " " + (context_before or "")

    for pattern in _VAR_DEF_PATTERNS:
        for m in pattern.finditer(text):
            symbol = m.group(1).strip()
            meaning = m.group(2).strip().rstrip('.,;')
            if len(symbol) <= 20 and len(meaning) <= 200 and len(meaning) > 2:
                # Avoid false positives where symbol is a common word
                if symbol.lower() not in ('the', 'and', 'for', 'with', 'this', 'that', 'which', 'from', 'where'):
                    variables.append({
                        "symbol": symbol,
                        "meaning": meaning,
                        "source_page": page,
                        "source_context": m.group(0)[:200],
                    })
    # Deduplicate by symbol
    seen = set()
    unique = []
    for v in variables:
        if v["symbol"] not in seen:
            seen.add(v["symbol"])
            unique.append(v)
    return unique


def extract_equations(structured_json: dict, paper_id: int, run_id: int, repo) -> list:
    """Extract equations from Docling structured output and store via repository.

    Args:
        structured_json: normalized structured output from DoclingParser
        paper_id: paper ID in the database
        run_id: processing_run ID for this extraction run
        repo: Repository instance with upsert_equation() and add_variable() methods

    Returns:
        list of equation dicts that were stored
    """
    # Equations may come from structured_json['equations'] (from DoclingParser)
    # or from markdown text as fallback
    eq_items = structured_json.get("equations", [])
    if not eq_items:
        # Fallback: extract from markdown in structured_json
        md = structured_json.get("markdown", "")
        if md:
            eq_items = _extract_from_markdown(md, structured_json.get("sections", []))

    stored = []
    for eq in eq_items:
        latex_raw = eq.get("latex_raw", "")
        if not latex_raw or len(latex_raw) < 3:
            continue

        latex_normalized = eq.get("latex_normalized") or _normalize_latex(latex_raw)

        eq_obj = Equation(
            paper_id=paper_id,
            run_id=run_id,
            latex_raw=latex_raw,
            latex_normalized=latex_normalized,
            equation_number=eq.get("equation_number"),
            section_path=eq.get("section_path"),
            page_number=eq.get("page_number"),
            bbox_json=eq.get("bbox_json"),
            context_before=eq.get("context_before"),
            context_after=eq.get("context_after"),
            parser=eq.get("parser", "docling"),
            confidence=eq.get("confidence"),
            verification_status="unverified",
        )

        eq_id = repo.upsert_equation(eq_obj)
        stored.append({"id": eq_id, "paper_id": paper_id, "run_id": run_id,
                       "latex_raw": latex_raw, "latex_normalized": latex_normalized,
                       "equation_number": eq.get("equation_number")})

        # Extract and store variable definitions
        variables = _extract_variable_defs(
            eq.get("context_before", ""),
            eq.get("context_after", ""),
            eq.get("page_number"),
        )
        for var in variables:
            repo.add_variable(EquationVariable(equation_id=eq_id, **var))

    logger.info(f"Extracted {len(stored)} equations for paper_id={paper_id}")
    return stored


def _extract_from_markdown(md_text: str, sections: list[dict]) -> list[dict]:
    """Fallback: extract equations from markdown $$...$$ blocks with section context."""
    equations = []
    current_section = ""

    lines = md_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # Track current section from headings
        heading_match = re.match(r'^#{1,6}\s+(.+)$', line)
        if heading_match:
            current_section = heading_match.group(1)
            i += 1
            continue

        # Display equations: $$...$$ (may span multiple lines)
        if "$$" in line:
            # Single-line $$...$$
            if line.count("$$") >= 2:
                matches = re.findall(r'\$\$(.+?)\$\$', line, re.DOTALL)
                for m in matches:
                    latex = m.strip()
                    if len(latex) > 3:
                        eq_number = None
                        num_match = re.search(r'\((\d+(?:\.\d+)*)\)\s*$', latex)
                        if num_match:
                            eq_number = num_match.group(1)
                            latex = latex[:num_match.start()].strip()
                        context_before = lines[i-1] if i > 0 else ""
                        context_after = lines[i+1] if i+1 < len(lines) else ""
                        equations.append({
                            "latex_raw": latex,
                            "latex_normalized": None,
                            "equation_number": eq_number,
                            "section_path": current_section,
                            "page_number": None,
                            "bbox_json": None,
                            "context_before": context_before,
                            "context_after": context_after,
                            "parser": "markdown_regex",
                            "confidence": None,
                        })
            else:
                # Multi-line $$...$$
                block_lines = [line]
                j = i + 1
                while j < len(lines) and "$$" not in lines[j]:
                    block_lines.append(lines[j])
                    j += 1
                if j < len(lines):
                    block_lines.append(lines[j])
                    block_text = "\n".join(block_lines)
                    # Extract content between first $$ and last $$
                    start = block_text.find("$$") + 2
                    end = block_text.rfind("$$")
                    if start < end:
                        latex = block_text[start:end].strip()
                        if len(latex) > 3:
                            eq_number = None
                            num_match = re.search(r'\((\d+(?:\.\d+)*)\)\s*$', latex)
                            if num_match:
                                eq_number = num_match.group(1)
                                latex = latex[:num_match.start()].strip()
                            context_before = lines[i-1] if i > 0 else ""
                            context_after = lines[j+1] if j+1 < len(lines) else ""
                            equations.append({
                                "latex_raw": latex,
                                "latex_normalized": None,
                                "equation_number": eq_number,
                                "section_path": current_section,
                                "page_number": None,
                                "bbox_json": None,
                                "context_before": context_before,
                                "context_after": context_after,
                                "parser": "markdown_regex",
                                "confidence": None,
                            })
                    i = j
        i += 1

    return equations

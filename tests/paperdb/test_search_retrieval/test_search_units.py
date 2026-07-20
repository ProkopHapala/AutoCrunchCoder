"""Tests for markdown-to-search-units splitting and transactional replacement."""

import sys
import os

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from paperdb.search.fts import _split_markdown_to_units, build_search_units_from_markdown, fts_search, SearchUnit
from conftest import create_test_db, insert_test_paper


def test_search_units_section_types():
    """Sections are classified correctly (summary vs section vs method)."""
    md = """# Generated scientific summary

## Essence
Short summary text.

## Methods
The algorithm uses spatial hashing.

---

# Extracted source text

## Introduction
Intro text.

## Methods
Detailed method description.
"""
    units = _split_markdown_to_units(1, md, run_id=1)
    summary_units = [u for u in units if u.unit_type == 'summary']
    section_units = [u for u in units if u.unit_type == 'section']
    method_units = [u for u in units if u.unit_type == 'method']
    assert len(summary_units) > 0, "Should have summary units from generated summary section"
    assert len(section_units) > 0, "Should have section units from source text"
    assert len(method_units) > 0, "Should have method units from Methods sections"
    print(f"✓ test_search_units_section_types passed (summary={len(summary_units)}, section={len(section_units)}, method={len(method_units)})")


def test_search_units_section_path():
    """Section paths are built from heading hierarchy."""
    md = """# Title

## Methods
Content.

### Sub-method
More content.
"""
    units = _split_markdown_to_units(1, md, run_id=1)
    # Include method-type units since "Methods" section triggers method classification
    section_paths = [u.section_path for u in units if u.unit_type in ('section', 'paragraph', 'method')]
    paths_str = '|'.join(section_paths)
    assert "Methods" in paths_str, f"Expected 'Methods' in paths: {section_paths}"
    # Sub-method should have nested path
    has_nested = any("Sub-method" in p for p in section_paths)
    assert has_nested, f"Expected nested section path, got: {section_paths}"
    print(f"✓ test_search_units_section_path passed (paths: {set(section_paths)})")


def test_search_units_multiline_equation():
    """Multi-line equation blocks are captured as single units."""
    md = """# Test

## Methods
Some text.

$$
E = \\sum_{i} \\frac{1}{2} k_i (r_i - r_{i,0})^2
$$

More text.
"""
    units = _split_markdown_to_units(1, md, run_id=1)
    eq_units = [u for u in units if u.unit_type == 'equation']
    assert len(eq_units) == 1, f"Expected 1 equation, got {len(eq_units)}"
    assert "\\sum" in eq_units[0].content
    print(f"✓ test_search_units_multiline_equation passed")


def test_search_units_paragraph_splitting():
    """Sections are split into paragraph-level units."""
    md = """# Test

## Introduction
First paragraph with enough text to pass the minimum length check here.

Second paragraph also has sufficient text for the minimum length filter.

Short.
"""
    units = _split_markdown_to_units(1, md, run_id=1)
    para_units = [u for u in units if u.unit_type == 'paragraph']
    # Should have 2 paragraphs (the "Short." one is too short)
    assert len(para_units) >= 2, f"Expected >= 2 paragraphs, got {len(para_units)}"
    # Verify short paragraph is excluded
    for u in para_units:
        assert len(u.content) >= 20, f"Short paragraph should be excluded: '{u.content}'"
    print(f"✓ test_search_units_paragraph_splitting passed ({len(para_units)} paragraphs)")


def test_search_units_empty_markdown():
    """Empty markdown produces no units."""
    units = _split_markdown_to_units(1, "", run_id=1)
    assert len(units) == 0
    print("✓ test_search_units_empty_markdown passed")


def test_search_units_only_frontmatter():
    """Markdown with only frontmatter produces no units."""
    md = """---
paper_id: 42
title: Test
---
"""
    units = _split_markdown_to_units(1, md, run_id=1)
    assert len(units) == 0
    print("✓ test_search_units_only_frontmatter passed")


def test_replace_search_units_idempotent():
    """Replacing search units multiple times doesn't create duplicates."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="Test")
    units = [SearchUnit(paper_id=pid, unit_type='section', source_type='section', content="test content")]
    repo.replace_search_units(pid, units)
    assert len(repo.get_search_units_for_paper(pid)) == 1
    repo.replace_search_units(pid, units)
    assert len(repo.get_search_units_for_paper(pid)) == 1
    repo.replace_search_units(pid, units)
    assert len(repo.get_search_units_for_paper(pid)) == 1
    print("✓ test_replace_search_units_idempotent passed")


def test_search_units_fts_sync():
    """Search units are searchable via FTS5 after storage."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="Test")
    md = """# Test

## Introduction
Gauss-Seidel iterative solver for constraint satisfaction.
"""
    build_search_units_from_markdown(pid, md, run_id=1, repo=repo)
    results = fts_search("Gauss-Seidel", repo)
    assert len(results) >= 1
    assert "Gauss-Seidel" in results[0]['content']
    print("✓ test_search_units_fts_sync passed")


def test_search_units_different_papers_isolated():
    """Search units from different papers don't interfere."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2020", title="A")
    pid2 = insert_test_paper(repo, "B_2021", title="B")
    build_search_units_from_markdown(pid1, "# A\n\nAlpha content.", run_id=1, repo=repo)
    build_search_units_from_markdown(pid2, "# B\n\nBeta content.", run_id=1, repo=repo)
    # Replacing pid2's units should not affect pid1
    u1 = repo.get_search_units_for_paper(pid1)
    u2 = repo.get_search_units_for_paper(pid2)
    assert all("Alpha" in u['content'] for u in u1)
    assert all("Beta" in u['content'] for u in u2)
    # FTS should find both
    assert len(fts_search("Alpha", repo)) >= 1
    assert len(fts_search("Beta", repo)) >= 1
    print("✓ test_search_units_different_papers_isolated passed")


if __name__ == "__main__":
    test_search_units_section_types()
    test_search_units_section_path()
    test_search_units_multiline_equation()
    test_search_units_paragraph_splitting()
    test_search_units_empty_markdown()
    test_search_units_only_frontmatter()
    test_replace_search_units_idempotent()
    test_search_units_fts_sync()
    test_search_units_different_papers_isolated()
    print("\n✅ All search units tests passed!")

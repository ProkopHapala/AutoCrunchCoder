"""Tests for FTS5 search and markdown-to-search-units splitting."""

import sys
import os

# Add paperdb to path (Task 1 may not have installed package yet)
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from paperdb.search.fts import fts_search, fts_search_for_papers, build_search_units_from_markdown, SearchUnit, _split_markdown_to_units
from .conftest import create_test_db, insert_test_paper, insert_test_search_unit


def test_fts_basic_search():
    """Basic FTS5 search returns matching units."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020_Foo", title="Foo paper")
    insert_test_search_unit(repo, pid, 'section', 'section', "XPBD position based dynamics constraint solver", "Introduction")
    insert_test_search_unit(repo, pid, 'section', 'section', "Unrelated content about cooking recipes", "Background")
    results = fts_search("XPBD", repo)
    assert len(results) == 1
    assert results[0]['paper_id'] == pid
    assert "XPBD" in results[0]['content']
    print("✓ test_fts_basic_search passed")


def test_fts_multiple_papers():
    """FTS5 search across multiple papers."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2020", title="Paper A")
    pid2 = insert_test_paper(repo, "B_2021", title="Paper B")
    insert_test_search_unit(repo, pid1, 'section', 'section', "Ewald summation for periodic boundaries", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "Ewald summation with slab correction", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "Particle mesh Ewald", "Methods")
    results = fts_search("Ewald", repo)
    assert len(results) == 3
    paper_ids = {r['paper_id'] for r in results}
    assert pid1 in paper_ids
    assert pid2 in paper_ids
    print("✓ test_fts_multiple_papers passed")


def test_fts_for_papers_restricted():
    """fts_search_for_papers restricts to given paper_ids."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2020", title="Paper A")
    pid2 = insert_test_paper(repo, "B_2021", title="Paper B")
    insert_test_search_unit(repo, pid1, 'section', 'section', "Ewald summation", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "Ewald summation", "Methods")
    results = fts_search_for_papers("Ewald", [pid1], repo)
    assert len(results) == 1
    assert results[0]['paper_id'] == pid1
    print("✓ test_fts_for_papers_restricted passed")


def test_fts_trigger_sync_on_delete():
    """FTS index updates when search_units are deleted (via replace_search_units)."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="Test")
    insert_test_search_unit(repo, pid, 'section', 'section', "unique search term foobarbaz", "Intro")
    assert len(fts_search("foobarbaz", repo)) == 1

    # Replace search units — old one should be gone from FTS
    repo.replace_search_units(pid, [SearchUnit(paper_id=pid, unit_type='section', source_type='section', content="new content without the magic word")])
    assert len(fts_search("foobarbaz", repo)) == 0
    assert len(fts_search("new content", repo)) == 1
    print("✓ test_fts_trigger_sync_on_delete passed")


def test_fts_trigger_sync_on_update():
    """FTS index updates when search_units are updated."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="Test")
    insert_test_search_unit(repo, pid, 'section', 'section', "old content word", "Intro")
    assert len(fts_search("old content", repo)) == 1

    # Update via replace (delete + insert)
    repo.replace_search_units(pid, [SearchUnit(paper_id=pid, unit_type='section', source_type='section', content="updated content word")])
    assert len(fts_search("old content", repo)) == 0
    assert len(fts_search("updated content", repo)) == 1
    print("✓ test_fts_trigger_sync_on_update passed")


def test_split_markdown_basic():
    """Markdown splitting produces correct search units."""
    md = """---
title: Test Paper
---

# Generated scientific summary

## Essence
This paper presents a novel method for collision detection.

## Key equations
$$E = mc^2$$

## Methods
The algorithm uses spatial hashing.

---

# Extracted source text

## Introduction
We present a method for fast collision detection on GPU.

## Methods
The spatial hash grid is built in parallel.
"""
    units = _split_markdown_to_units(1, md, run_id=1)
    # Should have sections, paragraphs, and equation units
    types = [u.unit_type for u in units]
    assert 'equation' in types, f"Expected equation in {types}"
    assert 'summary' in types, f"Expected summary in {types}"
    assert 'section' in types or 'paragraph' in types, f"Expected section/paragraph in {types}"
    print(f"✓ test_split_markdown_basic passed ({len(units)} units, types: {set(types)})")


def test_split_markdown_equations():
    """Equation blocks are extracted as separate units."""
    md = """# Test

## Section A
Some text before equation.

$$F = ma$$

Some text after equation.

## Section B
$$E_k = \\frac{1}{2}mv^2$$
"""
    units = _split_markdown_to_units(1, md, run_id=1)
    eq_units = [u for u in units if u.unit_type == 'equation']
    assert len(eq_units) == 2, f"Expected 2 equations, got {len(eq_units)}"
    assert "F = ma" in eq_units[0].content
    print(f"✓ test_split_markdown_equations passed ({len(eq_units)} equations)")


def test_split_markdown_frontmatter_skipped():
    """YAML front matter is not included in search units."""
    md = """---
paper_id: 42
paper_key: Test_2020
doi: 10.1234/test
---

# Title
Content here.
"""
    units = _split_markdown_to_units(1, md, run_id=1)
    for u in units:
        assert "paper_id" not in u.content, "Front matter leaked into search unit"
        assert "paper_key" not in u.content, "Front matter leaked into search unit"
    print(f"✓ test_split_markdown_frontmatter_skipped passed ({len(units)} units)")


def test_build_search_units_from_markdown_stored():
    """build_search_units_from_markdown stores units via repo and FTS syncs."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="Test")
    md = """# Test

## Introduction
XPBD position based dynamics.
"""
    units = build_search_units_from_markdown(pid, md, run_id=1, repo=repo)
    assert len(units) > 0
    # Verify stored in DB
    db_units = repo.get_search_units_for_paper(pid)
    assert len(db_units) == len(units)
    # Verify FTS works
    results = fts_search("XPBD", repo)
    assert len(results) >= 1
    print(f"✓ test_build_search_units_from_markdown_stored passed ({len(units)} units stored)")


def test_replace_search_units_transactional():
    """replace_search_units deletes old and inserts new atomically."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="Test")
    # Initial units
    repo.replace_search_units(pid, [
        SearchUnit(paper_id=pid, unit_type='section', source_type='section', content="old content alpha"),
        SearchUnit(paper_id=pid, unit_type='section', source_type='section', content="old content beta"),
    ])
    assert len(repo.get_search_units_for_paper(pid)) == 2
    # Replace with new units
    repo.replace_search_units(pid, [
        SearchUnit(paper_id=pid, unit_type='section', source_type='section', content="new content gamma"),
    ])
    db_units = repo.get_search_units_for_paper(pid)
    assert len(db_units) == 1
    assert "new content gamma" in db_units[0]['content']
    # Old content should be gone from FTS
    assert len(fts_search("alpha", repo)) == 0
    assert len(fts_search("gamma", repo)) == 1
    print("✓ test_replace_search_units_transactional passed")


def test_structured_equation_and_method_units_are_indexed():
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Structured_2026", title="Structured")
    units = build_search_units_from_markdown(pid, "# Source\n\nplain text", 4, repo,
        equations=[{"id": 7, "latex_raw": "E = mc^2", "section_path": "Theory", "page_number": 3}],
        methods=[{"id": 9, "name": "relaxation solver", "purpose": "solve constraints", "card_json": "{}", "source_passages_json": "[]"}])
    equation = next(unit for unit in units if unit.source_type == "equation")
    method = next(unit for unit in units if unit.source_type == "method")
    assert (equation.source_id, equation.page_from, equation.page_to) == (7, 3, 3)
    assert method.source_id == 9
    assert fts_search("relaxation", repo)[0]["source_id"] == 9


if __name__ == "__main__":
    test_fts_basic_search()
    test_fts_multiple_papers()
    test_fts_for_papers_restricted()
    test_fts_trigger_sync_on_delete()
    test_fts_trigger_sync_on_update()
    test_split_markdown_basic()
    test_split_markdown_equations()
    test_split_markdown_frontmatter_skipped()
    test_build_search_units_from_markdown_stored()
    test_replace_search_units_transactional()
    print("\n✅ All FTS tests passed!")

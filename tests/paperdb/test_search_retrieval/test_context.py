"""Tests for context pack assembly."""

import sys
import os

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from paperdb.search.context import assemble_context_pack, ContextPack
from paperdb.search.fts import SearchUnit
from conftest import (create_test_db, insert_test_paper, insert_test_search_unit,
                      insert_test_summary, insert_test_method, insert_test_tag,
                      insert_test_paper_tag)


def test_context_pack_basic():
    """Basic context pack assembly with one paper."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Macklin_2016_XPBD", title="XPBD: Position-Based Simulation",
                            year=2016, abstract="Compliant constraint dynamics",
                            essence="XPBD method for position-based dynamics")
    insert_test_search_unit(repo, pid, 'section', 'section', "XPBD constraint solver with compliance", "Methods")
    insert_test_search_unit(repo, pid, 'equation', 'equation', "$$\\Delta x = \\lambda w C / \\alpha$$", "Methods")
    insert_test_summary(repo, pid, "XPBD extends PBD with compliant constraints for stable simulation.")
    pack = assemble_context_pack("XPBD", repo, token_budget=24000)
    assert pack.paper_count == 1
    assert "XPBD" in pack.content
    assert "Macklin_2016_XPBD" in pack.content
    assert pack.token_estimate > 0
    print(f"✓ test_context_pack_basic passed (papers={pack.paper_count}, tokens~{pack.token_estimate})")


def test_context_pack_multiple_papers():
    """Context pack with multiple papers includes comparison matrix."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2016_XPBD", title="XPBD method", year=2016, essence="XPBD")
    pid2 = insert_test_paper(repo, "B_2014_PBD", title="PBD method", year=2014, essence="PBD original")
    insert_test_search_unit(repo, pid1, 'section', 'section', "XPBD position based dynamics", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "PBD position based dynamics", "Methods")
    insert_test_method(repo, pid1, "XPBD solver", "O(n)")
    insert_test_method(repo, pid2, "PBD solver", "O(n)")
    pack = assemble_context_pack("position based dynamics", repo, token_budget=24000)
    assert pack.paper_count == 2
    assert "Comparison matrix" in pack.content
    assert "A_2016_XPBD" in pack.content
    assert "B_2014_PBD" in pack.content
    print(f"✓ test_context_pack_multiple_papers passed (papers={pack.paper_count}, has matrix)")


def test_context_pack_token_budget():
    """Token budget truncation works."""
    conn, repo = create_test_db()
    # Create many papers to exceed small budget
    for i in range(10):
        pid = insert_test_paper(repo, f"Paper_{i}_2020", title=f"Paper {i} about Ewald summation", year=2020)
        insert_test_search_unit(repo, pid, 'section', 'section', "Ewald summation " * 100, "Methods")
        insert_test_summary(repo, pid, "Summary " * 50)
    # Small budget — should truncate
    pack = assemble_context_pack("Ewald", repo, token_budget=500)  # 500 tokens = ~2000 chars
    assert pack.paper_count < 10  # not all papers should fit
    assert len(pack.content) <= 500 * 4 + 200  # budget + truncation message
    print(f"✓ test_context_pack_token_budget passed (papers={pack.paper_count}, chars={len(pack.content)})")


def test_context_pack_bibliography():
    """Context pack includes bibliography section."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Macklin_2016_XPBD", title="XPBD", year=2016,
                            authors_text="Macklin, Miles; Müller, Matthias")
    insert_test_search_unit(repo, pid, 'section', 'section', "XPBD method", "Methods")
    pack = assemble_context_pack("XPBD", repo, token_budget=24000)
    assert "## Bibliography" in pack.content
    assert "Macklin_2016_XPBD" in pack.content
    assert "Macklin" in pack.content
    print("✓ test_context_pack_bibliography passed")


def test_context_pack_no_results():
    """Context pack with no results returns empty pack."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="Unrelated")
    insert_test_search_unit(repo, pid, 'section', 'section', "completely unrelated content", "Methods")
    pack = assemble_context_pack("nonexistent query terms", repo, token_budget=24000)
    assert pack.paper_count == 0
    assert "No papers found" in pack.content
    print("✓ test_context_pack_no_results passed")


def test_context_pack_include_filter():
    """include parameter controls which content types appear."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="XPBD test", year=2020, essence="XPBD essence")
    insert_test_search_unit(repo, pid, 'section', 'section', "XPBD method description", "Methods")
    insert_test_search_unit(repo, pid, 'equation', 'equation', "$$F=ma$$", "Methods")
    insert_test_summary(repo, pid, "XPBD summary content")
    # Only include summary — no equations
    pack = assemble_context_pack("XPBD", repo, token_budget=24000, include=["summary"])
    assert "XPBD summary content" in pack.content
    # Equations should not be in the output when not included
    assert "$$F=ma$$" not in pack.content
    print("✓ test_context_pack_include_filter passed")


def test_context_pack_filters():
    """Context pack respects filters (year_range, tags)."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2010", title="Ewald old", year=2010)
    pid2 = insert_test_paper(repo, "B_2020", title="Ewald new", year=2020)
    insert_test_search_unit(repo, pid1, 'section', 'section', "Ewald summation", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "Ewald summation", "Methods")
    pack = assemble_context_pack("Ewald", repo, token_budget=24000,
                                 filters={'year_range': (2015, 2025)})
    assert pack.paper_count == 1
    assert "B_2020" in pack.content
    print("✓ test_context_pack_filters passed")


def test_context_pack_score_in_output():
    """Context pack includes score breakdown for each paper."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Macklin_2016_XPBD", title="XPBD method", year=2016)
    insert_test_search_unit(repo, pid, 'section', 'section', "XPBD position based dynamics", "Methods")
    pack = assemble_context_pack("XPBD", repo, token_budget=24000)
    assert "**Score**" in pack.content
    # Should have some score breakdown
    assert "title" in pack.content or "fts" in pack.content
    print("✓ test_context_pack_score_in_output passed")


if __name__ == "__main__":
    test_context_pack_basic()
    test_context_pack_multiple_papers()
    test_context_pack_token_budget()
    test_context_pack_bibliography()
    test_context_pack_no_results()
    test_context_pack_include_filter()
    test_context_pack_filters()
    test_context_pack_score_in_output()
    print("\n✅ All context pack tests passed!")

"""Tests for weighted ranking with explainable breakdown."""

import sys
import os

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from paperdb.search.ranking import rank_papers, search, SearchResult, SCORE_REQUIRED_TAG, SCORE_PREFERRED_TAG, SCORE_TITLE, SCORE_ABSTRACT, SCORE_FTS, SCORE_USER_TAG
from paperdb.search.fts import fts_search, SearchUnit
from conftest import (create_test_db, insert_test_paper, insert_test_search_unit,
                      insert_test_tag, insert_test_alias, insert_test_paper_tag)


def test_ranking_title_match():
    """Title match gives +5 score."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Macklin_2016_XPBD", title="XPBD: Position-Based Simulation of Compliant Constrained Dynamics")
    insert_test_search_unit(repo, pid, 'section', 'section', "XPBD constraint solver", "Methods")
    fts_results = fts_search("XPBD", repo)
    results = rank_papers("XPBD", fts_results, repo, explain=True)
    assert len(results) == 1
    assert results[0].paper.id == pid
    assert 'title' in results[0].breakdown
    assert results[0].breakdown['title'] == SCORE_TITLE
    print(f"✓ test_ranking_title_match passed (score={results[0].score}, breakdown={results[0].breakdown})")


def test_ranking_fts_match():
    """FTS match gives +1 per matching unit."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="Unrelated title")
    insert_test_search_unit(repo, pid, 'section', 'section', "Ewald summation method", "Methods")
    insert_test_search_unit(repo, pid, 'section', 'section', "Ewald slab correction", "Methods")
    fts_results = fts_search("Ewald", repo)
    results = rank_papers("Ewald", fts_results, repo, explain=True)
    assert len(results) == 1
    assert 'fts' in results[0].breakdown
    assert results[0].breakdown['fts'] == 2 * SCORE_FTS  # 2 matching units
    print(f"✓ test_ranking_fts_match passed (score={results[0].score}, breakdown={results[0].breakdown})")


def test_ranking_required_tags_filter():
    """Required tags act as AND filter — paper must have ALL."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2020", title="Paper A")
    pid2 = insert_test_paper(repo, "B_2021", title="Paper B")
    # Tags
    tid_solver = insert_test_tag(repo, "position based dynamics", "solver")
    tid_gpu = insert_test_tag(repo, "GPU", "implementation")
    tid_grid = insert_test_tag(repo, "uniform grid", "data_structure")
    # Paper A has solver + gpu
    insert_test_paper_tag(repo, pid1, tid_solver)
    insert_test_paper_tag(repo, pid1, tid_gpu)
    # Paper B has solver only
    insert_test_paper_tag(repo, pid2, tid_solver)
    # Both have FTS matches
    insert_test_search_unit(repo, pid1, 'section', 'section', "XPBD collision detection", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "XPBD collision detection", "Methods")
    # Search with required tags: solver + gpu — only paper A should match
    fts_results = fts_search("XPBD", repo)
    results = rank_papers("XPBD", fts_results, repo, required_tags=["position based dynamics", "GPU"], explain=True)
    assert len(results) == 1
    assert results[0].paper.id == pid1
    assert 'required_tags' in results[0].breakdown
    print(f"✓ test_ranking_required_tags_filter passed (only paper A matched)")


def test_ranking_preferred_tags_boost():
    """Preferred tags give +4 per matching tag."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2020", title="Paper A")
    pid2 = insert_test_paper(repo, "B_2021", title="Paper B")
    tid_gpu = insert_test_tag(repo, "GPU", "implementation")
    tid_grid = insert_test_tag(repo, "uniform grid", "data_structure")
    # Paper A has GPU + grid, Paper B has neither
    insert_test_paper_tag(repo, pid1, tid_gpu)
    insert_test_paper_tag(repo, pid1, tid_grid)
    # Both have same FTS match
    insert_test_search_unit(repo, pid1, 'section', 'section', "collision detection", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "collision detection", "Methods")
    fts_results = fts_search("collision", repo)
    results = rank_papers("collision", fts_results, repo, preferred_tags=["GPU", "uniform grid"], explain=True)
    assert len(results) == 2
    # Paper A should rank higher due to preferred tag boost
    assert results[0].paper.id == pid1
    assert results[0].breakdown.get('preferred_tags') == 2 * SCORE_PREFERRED_TAG
    # Paper B should have no preferred tag boost
    assert 'preferred_tags' not in results[1].breakdown
    print(f"✓ test_ranking_preferred_tags_boost passed (A score={results[0].score}, B score={results[1].score})")


def test_ranking_excluded_tags_filter():
    """Excluded tags remove papers from results."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2020", title="Paper A")
    pid2 = insert_test_paper(repo, "B_2021", title="Paper B")
    tid_old = insert_test_tag(repo, "deprecated method", "method")
    insert_test_paper_tag(repo, pid2, tid_old)
    insert_test_search_unit(repo, pid1, 'section', 'section', "Ewald summation", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "Ewald summation", "Methods")
    fts_results = fts_search("Ewald", repo)
    results = rank_papers("Ewald", fts_results, repo, excluded_tags=["deprecated method"])
    assert len(results) == 1
    assert results[0].paper.id == pid1
    print("✓ test_ranking_excluded_tags_filter passed")


def test_ranking_year_range_filter():
    """Year range filters papers."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2010", title="Paper A", year=2010)
    pid2 = insert_test_paper(repo, "B_2020", title="Paper B", year=2020)
    insert_test_search_unit(repo, pid1, 'section', 'section', "Ewald summation", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "Ewald summation", "Methods")
    fts_results = fts_search("Ewald", repo)
    results = rank_papers("Ewald", fts_results, repo, year_range=(2015, 2025))
    assert len(results) == 1
    assert results[0].paper.id == pid2
    print("✓ test_ranking_year_range_filter passed")


def test_ranking_tag_alias_resolution():
    """Tag aliases are resolved during search (DFT → density functional theory)."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="DFT paper")
    tid = insert_test_tag(repo, "density functional theory", "method")
    insert_test_alias(repo, tid, "DFT")
    insert_test_paper_tag(repo, pid, tid)
    insert_test_search_unit(repo, pid, 'section', 'section', "quantum chemistry calculation", "Methods")
    # Search using alias "DFT" as preferred tag
    fts_results = fts_search("quantum", repo)
    results = rank_papers("quantum", fts_results, repo, preferred_tags=["DFT"], explain=True)
    assert len(results) == 1
    assert results[0].breakdown.get('preferred_tags') == SCORE_PREFERRED_TAG
    print("✓ test_ranking_tag_alias_resolution passed")


def test_ranking_user_tag_boost():
    """User-assigned tags give +6 per tag."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2020", title="Paper A")
    pid2 = insert_test_paper(repo, "B_2021", title="Paper B")
    tid = insert_test_tag(repo, "force field", "method")
    # Paper A has user-assigned tag, Paper B has LLM-assigned
    insert_test_paper_tag(repo, pid1, tid, source='user')
    insert_test_paper_tag(repo, pid2, tid, source='llm')
    insert_test_search_unit(repo, pid1, 'section', 'section', "molecular dynamics", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "molecular dynamics", "Methods")
    fts_results = fts_search("molecular", repo)
    results = rank_papers("molecular", fts_results, repo, explain=True)
    # Paper A should have user_tag boost
    a_result = [r for r in results if r.paper.id == pid1][0]
    b_result = [r for r in results if r.paper.id == pid2][0]
    assert a_result.breakdown.get('user_tags') == SCORE_USER_TAG
    assert 'user_tags' not in b_result.breakdown
    assert a_result.score > b_result.score
    print(f"✓ test_ranking_user_tag_boost passed (A={a_result.score}, B={b_result.score})")


def test_ranking_abstract_match():
    """Abstract/essence match gives +2."""
    conn, repo = create_test_db()
    pid = insert_test_paper(repo, "Test_2020", title="Unrelated title", abstract="This paper discusses Ewald summation methods.")
    insert_test_search_unit(repo, pid, 'section', 'section', "some content", "Methods")
    fts_results = fts_search("some", repo)
    results = rank_papers("Ewald", fts_results, repo, explain=True)
    # Paper should match via abstract even though FTS query "Ewald" didn't match FTS content "some"
    # Actually fts_search("Ewald") won't match "some content", so we need to test differently
    # Let's search with the term that's in both FTS and abstract
    fts_results2 = fts_search("content", repo)
    results2 = rank_papers("Ewald", fts_results2, repo, explain=True)
    # Paper should be candidate (from FTS "content") and get abstract boost for "Ewald"
    assert len(results2) == 1
    assert 'abstract' in results2[0].breakdown
    assert results2[0].breakdown['abstract'] == SCORE_ABSTRACT
    print(f"✓ test_ranking_abstract_match passed (score={results2[0].score})")


def test_search_convenience_function():
    """search() convenience function combines FTS + ranking with limit."""
    conn, repo = create_test_db()
    for i in range(5):
        pid = insert_test_paper(repo, f"Paper_{i}_2020", title=f"Paper {i}")
        insert_test_search_unit(repo, pid, 'section', 'section', "Ewald summation", "Methods")
    results = search("Ewald", repo, limit=3)
    assert len(results) == 3
    print(f"✓ test_search_convenience_function passed (3 of 5 returned)")


def test_ranking_sort_order():
    """Results are sorted by score descending."""
    conn, repo = create_test_db()
    pid1 = insert_test_paper(repo, "A_2020", title="Ewald method paper")  # title match
    pid2 = insert_test_paper(repo, "B_2021", title="Unrelated")           # no title match
    insert_test_search_unit(repo, pid1, 'section', 'section', "Ewald summation", "Methods")
    insert_test_search_unit(repo, pid2, 'section', 'section', "Ewald summation", "Methods")
    fts_results = fts_search("Ewald", repo)
    results = rank_papers("Ewald", fts_results, repo, explain=True)
    assert results[0].score >= results[1].score
    assert results[0].paper.id == pid1  # title match gives higher score
    print(f"✓ test_ranking_sort_order passed (sorted: {results[0].score} >= {results[1].score})")


if __name__ == "__main__":
    test_ranking_title_match()
    test_ranking_fts_match()
    test_ranking_required_tags_filter()
    test_ranking_preferred_tags_boost()
    test_ranking_excluded_tags_filter()
    test_ranking_year_range_filter()
    test_ranking_tag_alias_resolution()
    test_ranking_user_tag_boost()
    test_ranking_abstract_match()
    test_search_convenience_function()
    test_ranking_sort_order()
    print("\n✅ All ranking tests passed!")

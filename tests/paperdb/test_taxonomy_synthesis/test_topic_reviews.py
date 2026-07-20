"""Test topic review generation (mock search + LLM), comparison matrix."""

import json
import pytest
from unittest.mock import patch, MagicMock
from tests.paperdb.test_taxonomy_synthesis.conftest import make_mock_repo, MockAgent

MOCK_INTERPRET_RESPONSE = json.dumps({
    "search_terms": ["XPBD", "position based dynamics", "constraint solving"],
    "required_tags": [["solver", "position based dynamics"]],
    "preferred_tags": [["domain", "game physics"]],
    "comparison_axes": ["complexity", "parallelization", "accuracy"]
})

MOCK_REVIEW_RESPONSE = """## Overview
This review compares position-based dynamics methods for constraint solving.

## Methods Compared
[1] Macklin 2016: XPBD method with compliance.

## Comparison
| Paper | complexity | parallelization | accuracy |
|---|---|---|---|
| Macklin 2016 | O(n*c) | Gauss-Seidel | medium |

## Recommendations
XPBD is best for interactive simulations.

## Gaps
No GPU-parallel version exists yet."""

def _setup_papers(repo):
    """Set up test papers with methods in the repo."""
    p1 = repo.add_paper("Macklin_2016_XPBD", title="XPBD", year=2016, essence="Position-based dynamics with compliance")
    p2 = repo.add_paper("Muller_2007_PBD", title="PBD", year=2007, essence="Position-based dynamics")

    run_id = repo.create_processing_run(p1, operation='methods')
    repo.add_method(p1, run_id=run_id, name="XPBD", method_type='reconstructed_method',
                    purpose="constraint solving", complexity="O(n*c)",
                    card_json=json.dumps({"parallelization": "Gauss-Seidel", "limitations": ["sequential"]}),
                    source_passages_json='[]')

    run_id2 = repo.create_processing_run(p2, operation='methods')
    repo.add_method(p2, run_id=run_id2, name="PBD", method_type='reconstructed_method',
                    purpose="constraint solving", complexity="O(n*c)",
                    card_json=json.dumps({"parallelization": "Gauss-Seidel", "limitations": ["stiffness issues"]}),
                    source_passages_json='[]')

    return [p1, p2]

class MockPaperDB:
    """Mock PaperDB with search() that returns papers from repo."""
    def __init__(self, repo, paper_ids):
        self.repo = repo
        self.paper_ids = paper_ids

    def search(self, query, limit=30):
        results = []
        for pid in self.paper_ids[:limit]:
            p = self.repo.get_paper(pid)
            if p:
                results.append(p)
        return results

def test_build_topic_review_basic():
    """Test that build_topic_review generates a review and stores it."""
    from paperdb.synthesis import topic_reviews

    repo = make_mock_repo()
    paper_ids = _setup_papers(repo)
    mock_db = MockPaperDB(repo, paper_ids)

    mock_agent = MockAgent(responses=[MOCK_INTERPRET_RESPONSE, MOCK_REVIEW_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        result = topic_reviews.build_topic_review("XPBD constraint solving", repo, db=mock_db)

    assert 'content' in result
    assert "Overview" in result['content']
    assert result['topic_id'] is not None
    assert len(result['papers_used']) == 2

def test_build_topic_review_stores_topic():
    """Test that topic is stored in topics table."""
    from paperdb.synthesis import topic_reviews

    repo = make_mock_repo()
    paper_ids = _setup_papers(repo)
    mock_db = MockPaperDB(repo, paper_ids)

    mock_agent = MockAgent(responses=[MOCK_INTERPRET_RESPONSE, MOCK_REVIEW_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        result = topic_reviews.build_topic_review("XPBD constraint solving", repo, db=mock_db)

    # Check topic was stored
    topics = repo.conn.execute("SELECT * FROM topics").fetchall()
    assert len(topics) == 1
    assert topics[0]['name'] == "XPBD constraint solving"

    # Check topic_papers
    tp = repo.conn.execute("SELECT * FROM topic_papers").fetchall()
    assert len(tp) == 2

    # Check topic_overview
    ov = repo.conn.execute("SELECT * FROM topic_overviews").fetchall()
    assert len(ov) == 1
    assert ov[0]['is_active'] == 1

def test_build_comparison_matrix():
    """Test that comparison matrix is built correctly."""
    from paperdb.synthesis import topic_reviews

    repo = make_mock_repo()
    paper_ids = _setup_papers(repo)

    papers = [repo.get_paper(pid) for pid in paper_ids]
    methods = []
    for pid in paper_ids:
        methods.extend(repo.get_methods(pid))

    axes = ["complexity", "parallelization", "limitations"]
    matrix = topic_reviews.build_comparison_matrix(papers, methods, axes, repo)

    assert matrix['axes'] == axes
    assert len(matrix['papers']) == 2
    assert len(matrix['matrix']) == 2
    assert len(matrix['matrix'][0]) == 3

    # Check that complexity values are extracted
    assert matrix['matrix'][0][0] == "O(n*c)"  # complexity for first paper

def test_build_comparison_matrix_empty():
    """Test comparison matrix with no methods."""
    from paperdb.synthesis import topic_reviews

    repo = make_mock_repo()
    p1 = repo.add_paper("Empty_2020")
    papers = [repo.get_paper(p1)]

    matrix = topic_reviews.build_comparison_matrix(papers, [], ["complexity"], repo)
    assert matrix['matrix'][0][0] == "N/A"

def test_build_topic_review_no_papers():
    """Test that build_topic_review handles no results gracefully."""
    from paperdb.synthesis import topic_reviews

    repo = make_mock_repo()
    mock_db = MockPaperDB(repo, [])

    mock_agent = MockAgent(responses=[MOCK_INTERPRET_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        result = topic_reviews.build_topic_review("nonexistent topic", repo, db=mock_db)

    assert "No papers found" in result['content']
    assert result['topic_id'] is None
    assert len(result['papers_used']) == 0

def test_build_topic_review_comparison_matrix_in_result():
    """Test that comparison matrix is included in the result."""
    from paperdb.synthesis import topic_reviews

    repo = make_mock_repo()
    paper_ids = _setup_papers(repo)
    mock_db = MockPaperDB(repo, paper_ids)

    mock_agent = MockAgent(responses=[MOCK_INTERPRET_RESPONSE, MOCK_REVIEW_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        result = topic_reviews.build_topic_review("XPBD", repo, db=mock_db)

    assert 'comparison_matrix' in result
    assert 'axes' in result['comparison_matrix']
    assert 'papers' in result['comparison_matrix']
    assert 'matrix' in result['comparison_matrix']

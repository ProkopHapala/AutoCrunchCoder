"""Test method reconstruction, card_json structure, evidence links."""

import json
import pytest
from unittest.mock import patch
from tests.paperdb.test_taxonomy_synthesis.conftest import make_mock_repo, MockAgent

MOCK_RECONSTRUCT_RESPONSE = json.dumps({
    "name": "XPBD constraint update",
    "purpose": "Update particle positions to satisfy compliant constraints",
    "assumptions": ["quasi-static approximation", "small mass ratio"],
    "state_variables": ["positions", "velocities", "constraint multipliers"],
    "inputs": ["positions", "inverse masses", "compliance"],
    "outputs": ["updated positions", "updated multipliers"],
    "initialization": "Set lambda = 0 for all constraints",
    "steps": ["1. Compute constraint violation", "2. Update multiplier with compliance", "3. Update positions"],
    "boundary_conditions": None,
    "convergence": "Fixed iteration count",
    "parallelization": "Gauss-Seidel requires careful ordering on GPU",
    "limitations": ["Stiff constraints require many iterations", "Gauss-Seidel is sequential"],
    "complexity": "O(n*c) where n=particles, c=constraints",
    "confidence": 0.85,
    "source_passages": [{"page": 4, "section": "3.1", "text": "We update the multiplier..."}]
})

def test_reconstruct_method_basic():
    """Test that reconstruct_method creates a reconstructed_method card."""
    from paperdb.synthesis import method_cards

    repo = make_mock_repo()
    paper_id = repo.add_paper("Macklin_2016_XPBD", title="XPBD")
    run_id = repo.create_processing_run(paper_id, operation='methods')

    # Add a source_algorithm method (as Task 5 would)
    repo.add_method(paper_id, run_id=run_id, name="XPBD update",
                    method_type='source_algorithm', purpose="constraint update",
                    card_json=json.dumps({"steps": ["compute violation", "update lambda", "update x"]}),
                    source_passages_json=json.dumps([{"page": 4, "section": "3.1", "text": "We update..."}]))

    mock_agent = MockAgent(responses=[MOCK_RECONSTRUCT_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        results = method_cards.reconstruct_method(paper_id, run_id, repo)

    assert len(results) == 1
    assert results[0]['name'] == "XPBD constraint update"
    assert results[0]['confidence'] == 0.85

    # Check it was stored as reconstructed_method
    methods = repo.get_methods(paper_id, method_type='reconstructed_method')
    assert len(methods) == 1
    assert methods[0]['name'] == "XPBD constraint update"

def test_reconstruct_method_card_json_structure():
    """Test that card_json contains expected fields."""
    from paperdb.synthesis import method_cards

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_Card")
    run_id = repo.create_processing_run(paper_id, operation='methods')

    repo.add_method(paper_id, run_id=run_id, name="source method",
                    method_type='source_algorithm', purpose="test",
                    card_json='{}', source_passages_json='[]')

    mock_agent = MockAgent(responses=[MOCK_RECONSTRUCT_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        results = method_cards.reconstruct_method(paper_id, run_id, repo)

    methods = repo.get_methods(paper_id, method_type='reconstructed_method')
    card = json.loads(methods[0]['card_json'])

    # Check required fields per spec
    assert 'assumptions' in card
    assert 'state_variables' in card
    assert 'inputs' in card
    assert 'outputs' in card
    assert 'initialization' in card
    assert 'steps' in card
    assert 'boundary_conditions' in card
    assert 'convergence' in card
    assert 'parallelization' in card
    assert 'limitations' in card

def test_reconstruct_method_source_passages():
    """Test that source_passages_json contains evidence references."""
    from paperdb.synthesis import method_cards

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_Ev")
    run_id = repo.create_processing_run(paper_id, operation='methods')

    repo.add_method(paper_id, run_id=run_id, name="source",
                    method_type='source_algorithm', purpose="test",
                    card_json='{}', source_passages_json='[]')

    mock_agent = MockAgent(responses=[MOCK_RECONSTRUCT_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        results = method_cards.reconstruct_method(paper_id, run_id, repo)

    methods = repo.get_methods(paper_id, method_type='reconstructed_method')
    passages = json.loads(methods[0]['source_passages_json'])
    assert len(passages) > 0
    assert 'text' in passages[0]  # has source text reference

def test_reconstruct_method_no_source_methods():
    """Test that reconstruct_method returns empty list when no source_algorithm methods exist."""
    from paperdb.synthesis import method_cards

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_None")
    run_id = repo.create_processing_run(paper_id, operation='methods')

    mock_agent = MockAgent(responses=[])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        results = method_cards.reconstruct_method(paper_id, run_id, repo)

    assert len(results) == 0

def test_reconstruct_method_links_equations():
    """Test that equations are linked to the reconstructed method."""
    from paperdb.synthesis import method_cards

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_Eq")
    run_id = repo.create_processing_run(paper_id, operation='methods')

    # Add source method
    repo.add_method(paper_id, run_id=run_id, name="source",
                    method_type='source_algorithm', purpose="test",
                    card_json='{}', source_passages_json='[]')

    # Add an equation
    repo.conn.execute("INSERT INTO equations (paper_id, run_id, latex_raw, section_path) VALUES (?, ?, ?, ?)",
                      (paper_id, run_id, "$$x_{n+1} = x_n + \\alpha r_n$$", "3.1"))
    repo.conn.commit()

    mock_agent = MockAgent(responses=[MOCK_RECONSTRUCT_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        results = method_cards.reconstruct_method(paper_id, run_id, repo)

    # Check method_equations junction
    links = repo.conn.execute("SELECT * FROM method_equations").fetchall()
    assert len(links) > 0

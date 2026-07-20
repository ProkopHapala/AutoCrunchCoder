"""Test tag extraction from sample markdown, verify categories, raw_name preservation."""

import json
import pytest
from unittest.mock import patch, MagicMock
from .conftest import make_mock_repo, MockAgent

SAMPLE_MD = """# XPBD: Position-Based Simulation of Compliant Constrained Dynamics

## Abstract
We present a position-based dynamics method for simulating compliant constraints.

## Introduction
XPBD extends PBD by introducing compliance parameters...

## Method
The constraint update uses a Gauss-Seidel iteration over constraint pairs.
We use a uniform grid for broad-phase collision detection on GPU.
"""

MOCK_TAG_RESPONSE = json.dumps({
    "domain": ["game physics", "computational mechanics"],
    "physical_system": ["deformable bodies"],
    "phenomenon": [],
    "model_or_theory": ["constrained dynamics"],
    "method": ["position based dynamics"],
    "solver": ["gauss-seidel"],
    "data_structure": ["uniform grid"],
    "discretization": [],
    "task": ["constraint solving", "collision detection"],
    "implementation": ["GPU"],
    "software": [],
    "material_or_molecule": [],
    "user": [],
})

def test_extract_tags_basic():
    """Test that extract_tags stores tags with correct categories and raw_name."""
    from paperdb.taxonomy import extraction

    repo = make_mock_repo()
    paper_id = repo.add_paper("Macklin_2016_XPBD", title="XPBD")
    run_id = repo.create_processing_run(paper_id, operation='tag', backend='llm')

    mock_agent = MockAgent(responses=[MOCK_TAG_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        results = extraction.extract_tags(SAMPLE_MD, paper_id, run_id, repo)

    assert len(results) > 0
    # Check that tags were stored
    all_tags = repo.get_all_tags()
    tag_names = [t['canonical_name'] for t in all_tags]
    assert 'game physics' in tag_names
    assert 'gauss-seidel' in tag_names
    assert 'uniform grid' in tag_names

def test_extract_tags_preserves_raw_name():
    """Test that raw_name is preserved in paper_tags."""
    from paperdb.taxonomy import extraction

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_Foo")
    run_id = repo.create_processing_run(paper_id, operation='tag')

    mock_agent = MockAgent(responses=[MOCK_TAG_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        results = extraction.extract_tags(SAMPLE_MD, paper_id, run_id, repo)

    # Check raw_name preservation — at least some paper_tags should have raw_name
    paper_tags = repo.conn.execute("SELECT * FROM paper_tags WHERE paper_id=?", (paper_id,)).fetchall()
    assert len(paper_tags) > 0
    for pt in paper_tags:
        assert pt['raw_name'] is not None  # raw_name must be preserved

def test_extract_tags_empty_categories():
    """Test that empty categories are harmless — no tags created for them."""
    from paperdb.taxonomy import extraction

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_Empty")
    run_id = repo.create_processing_run(paper_id, operation='tag')

    empty_response = json.dumps({cat: [] for cat in extraction.TAG_CATEGORIES})
    mock_agent = MockAgent(responses=[empty_response])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        results = extraction.extract_tags(SAMPLE_MD, paper_id, run_id, repo)

    assert len(results) == 0  # no tags extracted
    all_tags = repo.get_all_tags()
    assert len(all_tags) == 0  # no tags created

def test_extract_tags_stores_source_and_run_id():
    """Test that source='llm' and run_id are stored correctly."""
    from paperdb.taxonomy import extraction

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_RunID")
    run_id = repo.create_processing_run(paper_id, operation='tag')

    mock_agent = MockAgent(responses=[MOCK_TAG_RESPONSE])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        results = extraction.extract_tags(SAMPLE_MD, paper_id, run_id, repo)

    paper_tags = repo.conn.execute("SELECT * FROM paper_tags WHERE paper_id=?", (paper_id,)).fetchall()
    for pt in paper_tags:
        assert pt['source'] == 'llm'
        assert pt['run_id'] == run_id

def test_tag_categories_list():
    """Test that TAG_CATEGORIES contains all 13 extended categories."""
    from paperdb.taxonomy import extraction

    expected = {
        "domain", "physical_system", "phenomenon", "model_or_theory",
        "method", "solver", "data_structure", "discretization",
        "task", "implementation", "software", "material_or_molecule", "user",
    }
    assert set(extraction.TAG_CATEGORIES) == expected
    assert len(extraction.TAG_CATEGORIES) == 13

"""Test summary generation (mock LLM), versioning, deactivation."""

import pytest
from unittest.mock import patch
from tests.paperdb.test_taxonomy_synthesis.conftest import make_mock_repo, MockAgent

SAMPLE_MD = """# Test Paper: A Method for Something

## Abstract
We present a novel method for solving problems.

## Introduction
This paper introduces...

## Method
The algorithm uses iterative refinement...
"""

MOCK_SUMMARY = """## Essence
This paper presents a novel method for solving problems using iterative refinement.

## Key equations
$$x_{n+1} = x_n + \\alpha r_n$$

## Methods
Iterative refinement with relaxation parameter.

## Relevance
Useful for constraint solving in real-time simulations."""

def test_generate_summary_basic():
    """Test that generate_summary stores a summary."""
    from paperdb.synthesis import summaries

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_Sum")
    run_id = repo.create_processing_run(paper_id, operation='summarize', backend='llm')

    mock_agent = MockAgent(responses=[MOCK_SUMMARY])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        result = summaries.generate_summary(SAMPLE_MD, paper_id, run_id, repo)

    assert "Essence" in result
    assert "Key equations" in result

    # Check it was stored
    active = repo.get_active_summary(paper_id)
    assert active is not None
    assert active['content'] == MOCK_SUMMARY
    assert active['is_active'] == 1

def test_generate_summary_versioning():
    """Test that generating a new summary deactivates old one (keeps history)."""
    from paperdb.synthesis import summaries

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_Ver")
    run_id1 = repo.create_processing_run(paper_id, operation='summarize')
    run_id2 = repo.create_processing_run(paper_id, operation='summarize')

    mock_agent = MockAgent(responses=[MOCK_SUMMARY, "## Essence\nNew version of summary."])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        summaries.generate_summary(SAMPLE_MD, paper_id, run_id1, repo)
        summaries.generate_summary(SAMPLE_MD, paper_id, run_id2, repo)

    history = repo.get_summary_history(paper_id)
    assert len(history) == 2  # both versions kept

    # Only one should be active
    active = repo.get_active_summary(paper_id)
    assert active is not None
    assert active['is_active'] == 1
    assert "New version" in active['content']

    # Old one should be deactivated
    inactive = [s for s in history if s['is_active'] == 0]
    assert len(inactive) == 1

def test_generate_summary_prompt_version():
    """Test that prompt_version is stored correctly."""
    from paperdb.synthesis import summaries

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_PV")
    run_id = repo.create_processing_run(paper_id, operation='summarize')

    mock_agent = MockAgent(responses=[MOCK_SUMMARY])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        summaries.generate_summary(SAMPLE_MD, paper_id, run_id, repo, prompt_version="v1")

    active = repo.get_active_summary(paper_id)
    assert active['prompt_version'] == "v1"

def test_generate_summary_unknown_prompt_raises():
    """Test that unknown prompt_version raises ValueError."""
    from paperdb.synthesis import summaries

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_Err")
    run_id = repo.create_processing_run(paper_id, operation='summarize')

    mock_agent = MockAgent(responses=[MOCK_SUMMARY])

    with patch('paperdb.config.make_agent', return_value=mock_agent):
        with pytest.raises(ValueError, match="Unknown prompt_version"):
            summaries.generate_summary(SAMPLE_MD, paper_id, run_id, repo, prompt_version="v99")

def test_format_summary_section():
    """Test that format_summary_section produces correct markdown structure."""
    from paperdb.synthesis import summaries

    formatted = summaries.format_summary_section("## Essence\nTest summary.", prompt_version="v1")

    assert "# Generated scientific summary" in formatted
    assert "> This section was generated from the paper and is not source text." in formatted
    assert "## Essence" in formatted
    assert "# Extracted source text" in formatted
    assert "Prompt version: v1" in formatted

def test_get_summary_history_empty():
    """Test that get_summary_history returns empty list for paper with no summaries."""
    from paperdb.synthesis import summaries

    repo = make_mock_repo()
    paper_id = repo.add_paper("Test_2020_Empty")
    history = summaries.get_summary_history(paper_id, repo)
    assert len(history) == 0

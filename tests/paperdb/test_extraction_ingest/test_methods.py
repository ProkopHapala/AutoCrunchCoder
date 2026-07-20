"""Test method card extraction — card_json structure, method_equations links."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from paperdb.extract.methods import extract_methods, _extract_source_algorithms
from paperdb.db.models import Method


class MockRepo:
    def __init__(self):
        self.methods = []
        self.links = []
        self._m_id = 0

    def upsert_method(self, m: Method) -> int:
        self._m_id += 1
        m.id = self._m_id
        self.methods.append(m)
        return self._m_id

    def link_method_equation(self, method_id, equation_id, role):
        self.links.append({"method_id": method_id, "equation_id": equation_id, "role": role})


def test_extract_source_algorithms():
    md = """# Methods

## Algorithm 1: Gradient Descent

1. Initialize x_0
2. Compute gradient g = ∇f(x)
3. Update x = x - α * g
4. Repeat until convergence

Some other text.
"""
    methods = _extract_source_algorithms(md)
    assert len(methods) == 1
    assert "Gradient Descent" in methods[0]["name"]
    assert methods[0]["method_type"] == "source_algorithm"
    assert len(methods[0]["steps"]) == 4
    assert methods[0]["confidence"] == 0.9


def test_extract_methods_no_llm():
    """Test method extraction without LLM — only source_algorithm from regex."""
    repo = MockRepo()
    md = """# Paper

## Algorithm 1: Merge Sort

1. Split array in half
2. Recursively sort each half
3. Merge sorted halves
"""
    methods = extract_methods(md, [], paper_id=1, run_id=1, repo=repo, llm_config=None)
    assert len(methods) == 1
    assert methods[0]["method_type"] == "source_algorithm"
    # Check card_json is valid JSON
    card = json.loads(repo.methods[0].card_json)
    assert "steps" in card
    assert len(card["steps"]) == 3


def test_extract_methods_card_json_structure():
    repo = MockRepo()
    md = """# Algorithm 1: Quick Sort

1. Pick pivot
2. Partition array
3. Recurse on sub-arrays
"""
    methods = extract_methods(md, [], paper_id=1, run_id=1, repo=repo, llm_config=None)
    assert len(methods) == 1
    card = json.loads(repo.methods[0].card_json)
    # Verify all expected fields exist
    for field in ["assumptions", "state_variables", "inputs", "outputs",
                  "initialization", "steps", "boundary_conditions",
                  "convergence", "parallelization", "limitations"]:
        assert field in card
    # Source passages should be valid JSON
    passages = json.loads(repo.methods[0].source_passages_json)
    assert isinstance(passages, list)


def test_extract_methods_equation_links():
    repo = MockRepo()
    equations = [
        {"id": 1, "equation_number": "1", "latex_raw": "F = ma"},
        {"id": 2, "equation_number": "2", "latex_raw": "E = mc^2"},
    ]
    md = """# Algorithm 1: Newton's Method

1. Compute force using Eq (1)
2. Update position
"""
    methods = extract_methods(md, equations, paper_id=1, run_id=1, repo=repo, llm_config=None)
    # Source algorithms don't have equation_refs by default, so no links
    # This test verifies the linking mechanism doesn't crash
    assert len(methods) == 1


if __name__ == "__main__":
    test_extract_source_algorithms()
    test_extract_methods_no_llm()
    test_extract_methods_card_json_structure()
    test_extract_methods_equation_links()
    print("All method extraction tests passed!")

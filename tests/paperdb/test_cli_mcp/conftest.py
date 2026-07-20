"""Mock PaperDB for testing CLI and MCP without the real implementation.

This mock implements the interface contract from Task 1's spec.
It is used by injecting it into sys.modules before importing paperdb.cli / paperdb.mcp.
"""
import sys
import types
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock

# ── Inject mock paperdb package ───────────────────────────────────────────────
# paperdb/__init__.py (Task 1) may not exist yet. We create a mock package
# with __path__ pointing to the real paperdb/ directory so that submodule
# imports (paperdb.cli, paperdb.mcp) work correctly.
_PAPERDB_DIR = str(Path(__file__).resolve().parents[3] / "paperdb")

# Legacy tests replaced sys.modules["paperdb"] globally, which poisoned unrelated
# integration tests. The autouse fixture below patches only CLI/MCP boundaries.

# Test data
MOCK_PAPERS = [
    {"paper_key": "Macklin_2016_XPBD", "id": 1, "title": "XPBD: Position-Based Simulation of Compliant Constrained Dynamics", "year": 2016, "doi": "10.1145/2994258.2994272", "authors_text": "Macklin, Miles; Müller, Matthias", "essence": "Position-based dynamics with compliance for constraint solving", "score": 28, "match_reason": "solver: position based dynamics; math_class: constrained dynamics; title: XPBD", "bibtex": "@inproceedings{Macklin2016,\n  title={XPBD},\n  author={Macklin, Miles},\n  year={2016}\n}"},
    {"paper_key": "Smith_2020_SIBFA", "id": 2, "title": "SIBFA: Sum of Interactions Between Fragments Ab initio", "year": 2020, "doi": "10.1021/ct200123", "authors_text": "Smith, John", "essence": "Fragment-based force field with ab initio parametrization", "score": 22, "match_reason": "solver: SIBFA; domain: computational chemistry", "bibtex": "@article{Smith2020,\n  title={SIBFA},\n  author={Smith, John},\n  year={2020}\n}"},
    {"paper_key": "Jones_2018_Ewald", "id": 3, "title": "Ewald summation for 2D periodicity", "year": 2018, "doi": "10.1103/PhysRevB.97.123", "authors_text": "Jones, Mary", "essence": "Ewald summation method for 2D periodic systems", "score": 18, "match_reason": "solver: Ewald; domain: electrostatics", "bibtex": "@article{Jones2018,\n  title={Ewald summation},\n  author={Jones, Mary},\n  year={2018}\n}"},
]

MOCK_TAGS = [
    {"id": 1, "canonical_name": "position based dynamics", "category": "solver", "count": 5},
    {"id": 2, "canonical_name": "constrained dynamics", "category": "math_class", "count": 3},
    {"id": 3, "canonical_name": "game physics", "category": "domain", "count": 12},
    {"id": 4, "canonical_name": "SIBFA", "category": "solver", "count": 2},
    {"id": 5, "canonical_name": "Ewald", "category": "solver", "count": 8},
]

MOCK_EQUATIONS = [
    {"id": 1, "equation_number": "7", "latex_raw": "\\Delta \\lambda = \\frac{C(\\mathbf{x})}{\\tilde{w} + \\alpha_t / \\Delta t^2}", "latex_normalized": "\\Delta \\lambda = \\frac{C(\\mathbf{x})}{\\tilde{w} + \\alpha_t / \\Delta t^2}", "section_path": "3.1 Compliance", "page_number": 4, "context_before": "The constraint multiplier update is", "context_after": "where alpha is compliance"},
    {"id": 2, "equation_number": "8", "latex_raw": "\\mathbf{x}_{new} = \\mathbf{x} + \\Delta \\lambda \\cdot w \\cdot \\nabla C", "latex_normalized": "\\mathbf{x}_{new} = \\mathbf{x} + \\Delta \\lambda \\cdot w \\cdot \\nabla C", "section_path": "3.1 Compliance", "page_number": 4, "context_before": "Position update follows as", "context_after": "This is the XPBD update step"},
]

MOCK_METHODS = [
    {"id": 1, "name": "XPBD constraint update", "method_type": "reconstructed_method", "purpose": "Solve compliant constraints in position-based dynamics", "confidence": 0.9, "card_json": "{}", "source_passages_json": "[]"},
]

MOCK_STATUS = {"total_papers": 895, "with_markdown": 869, "with_summary": 373, "with_tags": 895, "with_equations": 169, "with_bibtex": 764}

MOCK_CONTEXT = {
    "content": "# Context Pack\n\nQuery: XPBD constraint solving\n\n## Paper 1: Macklin_2016_XPBD\n- Score: 28\n- Why: solver: position based dynamics\n\n## Bibliography\n- Macklin et al. 2016",
    "query": "XPBD constraint solving",
    "papers": ["Macklin_2016_XPBD"],
}

class MockPaperDB:
    """Mock implementation of the PaperDB API for testing."""
    def __init__(self, data_dir=None, db_path=None):
        self.data_dir = data_dir
        self.db_path = db_path
        self._papers = {p["paper_key"]: p for p in MOCK_PAPERS}
        self._papers_by_id = {p["id"]: p for p in MOCK_PAPERS}
        self._papers_by_doi = {p["doi"]: p for p in MOCK_PAPERS}

    def scan_folder(self, path, recursive=True):
        return [{"path": f"{path}/{i}.pdf"} for i in range(42)]

    def sync(self, folder, llm_config=None):
        return {"scanned": 42, "new": 5, "folder": folder}

    def add_paper(self, path_or_url_or_doi, dest_dir=None):
        return {"paper_key": "New_2024_Test", "status": "added"}

    def ingest_paper(self, paper_id, operations=None, llm_config=None):
        return {"paper_key": paper_id, "status": "ingested", "operations": operations or ["convert", "summarize", "tag"]}

    def ingest_folder(self, folder, llm_config=None):
        return {"folder": folder, "ingested": 10}

    def ingest_all(self, llm_config=None):
        return {"ingested": 42}

    def search(self, query, required_tags=None, preferred_tags=None, excluded_tags=None, year_range=None, limit=20, explain=False):
        import copy
        results = copy.deepcopy(MOCK_PAPERS[:limit])
        if not explain:
            for r in results:
                r.pop("match_reason", None)
        return results

    def retrieve_context(self, query, token_budget=24000, include=None, filters=None, save=False):
        result = dict(MOCK_CONTEXT)
        if save: result["id"] = 1
        return result

    def get_paper(self, id_or_key_or_doi):
        if id_or_key_or_doi in self._papers: return dict(self._papers[id_or_key_or_doi])
        try: return dict(self._papers_by_id[int(id_or_key_or_doi)])
        except (ValueError, KeyError): pass
        if id_or_key_or_doi in self._papers_by_doi: return dict(self._papers_by_doi[id_or_key_or_doi])
        return {"error": f"Paper '{id_or_key_or_doi}' not found"}

    def describe_paper(self, paper_id):
        result = self.get_paper(paper_id)
        result.update({"files": [], "tags": self.get_tags(paper_id), "summary": self.get_summary(paper_id), "processing_runs": []})
        return result

    def get_json(self, paper_id):
        return self.get_paper(paper_id)

    def get_bibtex(self, paper_id):
        return self.get_paper(paper_id).get("bibtex", "")

    def get_markdown(self, paper_id):
        p = self.get_paper(paper_id)
        return f"# {p.get('title', 'Unknown')}\n\n## Essence\n{p.get('essence', '')}\n\n## Source text\n..."

    def get_equations(self, paper_id):
        return list(MOCK_EQUATIONS)

    def get_methods(self, paper_id):
        return list(MOCK_METHODS)

    def get_equation_variables(self, equation_id):
        return [{"equation_id": equation_id, "symbol": "lambda", "meaning": "constraint multiplier"}]

    def get_tags(self, paper_id):
        return [t for t in MOCK_TAGS[:3]]

    def get_summary(self, paper_id):
        p = self.get_paper(paper_id)
        return f"## Essence\n{p.get('essence', '')}"

    def list_tags(self, category=None):
        if category:
            return [t for t in MOCK_TAGS if t["category"] == category]
        return list(MOCK_TAGS)

    def get_related(self, paper_id, limit=5):
        return list(MOCK_PAPERS[1:1+limit])

    def merge_tags(self, canonical, alias):
        return {"merged": alias, "into": canonical}

    def status(self, missing=None, needs_reprocessing=False):
        return dict(MOCK_STATUS)

    def build_topic_review(self, topic, focus=None, constraints=None, max_papers=30, llm_config=None):
        return {"topic": topic, "content": f"# Topic Review: {topic}\n\n## Papers\n- Macklin 2016 XPBD\n\n## Comparison\n| Method | Complexity |\n|--------|------------|\n| XPBD   | O(n)       |", "papers": ["Macklin_2016_XPBD"]}

    def compare_methods(self, problem, axes, constraints=None, max_papers=20):
        return {"problem": problem, "axes": axes, "matrix": "not yet implemented", "papers": MOCK_PAPERS[:max_papers]}

    def export_bibtex(self):
        return "\n".join(p["bibtex"] for p in MOCK_PAPERS)

    def reindex(self, operations, llm_config=None):
        return {"operations": operations, "llm_config": llm_config, "count": 42}

    def get_tag_aliases(self, tag_name):
        return {"tag": tag_name, "aliases": [tag_name.lower(), tag_name.upper()]}

    def add_user_tags(self, paper_id, tags):
        return None

    def get_context_pack(self, context_id):
        return dict(MOCK_CONTEXT)

@pytest.fixture(autouse=True)
def patch_paperdb_boundaries(monkeypatch):
    import paperdb.cli as cli_module
    import paperdb.mcp as mcp_module
    monkeypatch.setattr(cli_module, "get_db", lambda: MockPaperDB())
    mcp_module._db = MockPaperDB()

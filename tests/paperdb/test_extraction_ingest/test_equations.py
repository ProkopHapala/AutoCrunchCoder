"""Test equation extraction — latex_raw vs latex_normalized, variable definitions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from paperdb.extract.equations import extract_equations, _normalize_latex, _extract_variable_defs, _extract_from_markdown
from paperdb.db.models import Equation, EquationVariable


class MockRepo:
    def __init__(self):
        self.equations = []
        self.variables = []
        self._eq_id = 0
        self._var_id = 0

    def upsert_equation(self, eq: Equation) -> int:
        self._eq_id += 1
        eq.id = self._eq_id
        self.equations.append(eq)
        return self._eq_id

    def add_variable(self, var: EquationVariable) -> int:
        self._var_id += 1
        var.id = self._var_id
        self.variables.append(var)
        return self._var_id


def test_normalize_latex():
    assert _normalize_latex("$$E = mc^2$$") == "E = mc^2"
    assert _normalize_latex("E = mc^2 (1)") == "E = mc^2"
    assert _normalize_latex("  $$  F = ma  $$  ") == "F = ma"
    assert _normalize_latex("$x = 1$") == "x = 1"


def test_extract_variable_defs():
    vars = _extract_variable_defs("", "where E is the total energy and m is the mass", 3)
    assert len(vars) >= 2
    symbols = [v["symbol"] for v in vars]
    assert "E" in symbols
    assert "m" in symbols
    # Check source page
    for v in vars:
        assert v["source_page"] == 3


def test_extract_variable_defs_dollar_notation():
    vars = _extract_variable_defs("", "$T$ — the temperature", 5)
    assert len(vars) >= 1
    assert vars[0]["symbol"] == "T"
    assert "temperature" in vars[0]["meaning"].lower()


def test_extract_from_markdown_single_line():
    md = """# Introduction

Some text here.

$$E = mc^2$$

More text.
"""
    eqs = _extract_from_markdown(md, [])
    assert len(eqs) == 1
    assert "E = mc^2" in eqs[0]["latex_raw"]
    assert eqs[0]["section_path"] == "Introduction"


def test_extract_from_markdown_with_number():
    md = """# Methods

$$F = ma (1)$$

Next paragraph.
"""
    eqs = _extract_from_markdown(md, [])
    assert len(eqs) == 1
    assert eqs[0]["equation_number"] == "1"
    assert "F = ma" in eqs[0]["latex_raw"]


def test_extract_from_markdown_multiline():
    md = """# Theory

$$
\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}
$$

End.
"""
    eqs = _extract_from_markdown(md, [])
    assert len(eqs) == 1
    assert "int" in eqs[0]["latex_raw"]


def test_extract_equations_with_repo():
    repo = MockRepo()
    structured = {
        "equations": [
            {"latex_raw": "E = mc^2", "equation_number": "1", "section_path": "Intro",
             "page_number": 3, "context_before": "As shown in", "context_after": "where E is the energy",
             "parser": "docling"},
            {"latex_raw": "F = ma", "equation_number": "2", "section_path": "Methods",
             "page_number": 5, "context_before": "Newton's law:", "context_after": "",
             "parser": "docling"},
        ],
        "markdown": "",
        "sections": [],
    }
    eqs = extract_equations(structured, paper_id=1, run_id=10, repo=repo)
    assert len(eqs) == 2
    assert len(repo.equations) == 2
    # Check that latex_normalized was set
    assert repo.equations[0].latex_normalized == "E = mc^2"
    assert repo.equations[0].verification_status == "unverified"
    # Check variable extraction for first equation
    assert len(repo.variables) >= 1  # "E is the energy"
    var_symbols = [v.symbol for v in repo.variables]
    assert "E" in var_symbols


def test_extract_equations_empty():
    repo = MockRepo()
    structured = {"equations": [], "markdown": "", "sections": []}
    eqs = extract_equations(structured, paper_id=1, run_id=1, repo=repo)
    assert eqs == []


if __name__ == "__main__":
    test_normalize_latex()
    test_extract_variable_defs()
    test_extract_variable_defs_dollar_notation()
    test_extract_from_markdown_single_line()
    test_extract_from_markdown_with_number()
    test_extract_from_markdown_multiline()
    test_extract_equations_with_repo()
    test_extract_equations_empty()
    print("All equation extraction tests passed!")

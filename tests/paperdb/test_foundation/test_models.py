"""Test Pydantic model validation."""
import pytest
from pydantic import ValidationError
from paperdb.db.models import *

def test_paper_required_field():
    p = Paper(paper_key="Test_2020_Foo")
    assert p.paper_key == "Test_2020_Foo"
    assert p.id is None
    assert p.year is None

def test_paper_missing_required():
    with pytest.raises(ValidationError):
        Paper()  # paper_key is required

def test_paper_file_required():
    pf = PaperFile(paper_id=1, path="/test.pdf")
    assert pf.paper_id == 1
    assert pf.path == "/test.pdf"
    assert pf.is_preferred == 0
    assert pf.exists_now == 1

def test_equation_model():
    eq = Equation(paper_id=1, latex_raw="E=mc^2", page_number=5)
    assert eq.latex_raw == "E=mc^2"
    assert eq.page_number == 5
    assert eq.verification_status is None

def test_tag_model():
    t = Tag(canonical_name="DFT", category="method")
    assert t.canonical_name == "DFT"
    assert t.category == "method"

def test_search_result_default():
    sr = SearchResult(paper=Paper(paper_key="Test_2020_Foo"))
    assert sr.score == 0.0
    assert sr.match_reasons == []

def test_processing_run_defaults():
    r = ProcessingRun(paper_id=1, operation="convert")
    assert r.status == "pending"
    assert r.backend is None

def test_method_model():
    m = Method(paper_id=1, name="XPBD", method_type="source_algorithm")
    assert m.name == "XPBD"
    assert m.card_json is None

def test_summary_model():
    s = Summary(paper_id=1, content="test summary")
    assert s.is_active == 1
    assert s.content == "test summary"

def test_context_pack_model():
    cp = ContextPack(query="test query")
    assert cp.query == "test query"
    assert cp.content is None

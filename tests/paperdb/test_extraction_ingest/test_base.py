"""Test base parser interface and ExtractionResult."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from paperdb.extract.base import BaseParser, ExtractionResult


def test_extraction_result_defaults():
    r = ExtractionResult(markdown="# Test", structured_json={"a": 1})
    assert r.markdown == "# Test"
    assert r.structured_json == {"a": 1}
    assert r.equations == []
    assert r.sections == []
    assert r.tables == []
    assert r.metadata == {}


def test_extraction_result_to_dict():
    r = ExtractionResult(markdown="hello", structured_json={}, equations=[{"latex": "E=mc^2"}])
    d = r.to_dict()
    assert d["markdown"] == "hello"
    assert d["equations"] == [{"latex": "E=mc^2"}]


def test_base_parser_is_abstract():
    try:
        BaseParser()
        assert False, "Should not instantiate abstract class"
    except TypeError:
        pass


def test_base_parser_subclass():
    class DummyParser(BaseParser):
        @property
        def backend_name(self): return "dummy"
        def parse(self, pdf_path, keep_debug=False):
            return ExtractionResult(markdown="dummy", structured_json={})

    p = DummyParser()
    assert p.backend_name == "dummy"
    r = p.parse("fake.pdf")
    assert r.markdown == "dummy"


if __name__ == "__main__":
    test_extraction_result_defaults()
    test_extraction_result_to_dict()
    test_base_parser_is_abstract()
    test_base_parser_subclass()
    print("All base parser tests passed!")

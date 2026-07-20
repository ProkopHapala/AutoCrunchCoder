"""Test fetch — CrossRef/arXiv lookup, DOI detection, PDF download (mocked)."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from paperdb.ingest.fetch import _normalize_doi, _detect_doi, _detect_arxiv_id, _generate_paper_key


def test_normalize_doi():
    assert _normalize_doi("10.1103/PhysRevB.40.3979") == "10.1103/physrevb.40.3979"
    assert _normalize_doi("https://doi.org/10.1103/PhysRevB.40.3979") == "10.1103/physrevb.40.3979"
    assert _normalize_doi("doi: 10.1103/PhysRevB.40.3979") == "10.1103/physrevb.40.3979"
    assert _normalize_doi("https://dx.doi.org/10.1145/2994258.2994272") == "10.1145/2994258.2994272"


def test_detect_doi():
    assert _detect_doi("10.1103/PhysRevB.40.3979") == "10.1103/physrevb.40.3979"
    assert _detect_doi("https://doi.org/10.1145/2994258.2994272") == "10.1145/2994258.2994272"
    assert _detect_doi("not a doi") is None
    assert _detect_doi("https://arxiv.org/abs/2401.02058") is None


def test_detect_arxiv_id():
    assert _detect_arxiv_id("2401.02058") == "2401.02058"
    assert _detect_arxiv_id("2401.02058v1") == "2401.02058v1"
    assert _detect_arxiv_id("https://arxiv.org/abs/2401.02058") == "2401.02058"
    assert _detect_arxiv_id("https://arxiv.org/pdf/2401.02058") == "2401.02058"
    assert _detect_arxiv_id("hep-th/9901001") == "hep-th/9901001"
    assert _detect_arxiv_id("not an arxiv id") is None


def test_generate_paper_key_from_metadata():
    metadata = {"authors": "Macklin, Miles; Müller, Matthias", "year": 2016, "title": "XPBD: Position-Based Simulation of Compliant Constrained Dynamics"}
    key = _generate_paper_key(metadata, "/fake/path.pdf")
    assert "Macklin" in key or "Müller" in key  # May use last name
    assert "2016" in key


def test_generate_paper_key_from_filename():
    metadata = {}
    key = _generate_paper_key(metadata, "/fake/path/Macklin_2016_XPBD.pdf")
    assert key == "Macklin_2016_XPBD"


def test_generate_paper_key_stops_common_words():
    metadata = {"authors": "Doe, John", "year": 2020, "title": "The Study of A Method For Computing"}
    key = _generate_paper_key(metadata, "/fake/path.pdf")
    assert "Doe" in key
    assert "2020" in key
    # Should not use "The" as keyword
    assert "The" not in key


if __name__ == "__main__":
    test_normalize_doi()
    test_detect_doi()
    test_detect_arxiv_id()
    test_generate_paper_key_from_metadata()
    test_generate_paper_key_from_filename()
    test_generate_paper_key_stops_common_words()
    print("All fetch tests passed!")

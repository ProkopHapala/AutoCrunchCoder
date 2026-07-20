"""Tests for paperdb.identity.metadata — DOI normalization, BibTeX parsing, CrossRef mock."""
import pytest
from paperdb.identity.metadata import normalize_doi, parse_bibtex

# --- DOI normalization ---

def test_normalize_doi_basic():
    assert normalize_doi('10.1103/PhysRevB.40.3979') == '10.1103/physrevb.40.3979'

def test_normalize_doi_strip_prefix():
    assert normalize_doi('https://doi.org/10.1103/PhysRevB.40.3979') == '10.1103/physrevb.40.3979'

def test_normalize_doi_strip_doi_prefix():
    assert normalize_doi('doi:10.1103/PhysRevB.40.3979') == '10.1103/physrevb.40.3979'

def test_normalize_doi_strip_http():
    assert normalize_doi('http://doi.org/10.1103/PhysRevB.40.3979') == '10.1103/physrevb.40.3979'

def test_normalize_doi_none():
    assert normalize_doi(None) is None

def test_normalize_doi_empty():
    assert normalize_doi('') is None

def test_normalize_doi_whitespace():
    assert normalize_doi('  10.1103/PhysRevB.40.3979  ') == '10.1103/physrevb.40.3979'

# --- BibTeX parsing ---

BIBTEX_SAMPLE = """
@article{Macklin2016,
    title = {XPBD: Position-Based Simulation of Compliant Constrained Dynamics},
    author = {Macklin, Miles and M{\"u}ller, Matthias},
    year = {2016},
    doi = {10.1145/2994258.2994272},
    journal = {Proceedings of Motion in Games},
    keywords = {position based dynamics, constraints},
    abstract = {We present a modification of the position based dynamics method...}
}

@inproceedings{Smith2020,
    title = {A Study on Neural Networks},
    author = {Smith, John},
    year = {2020},
    doi = {10.9999/test.2020.001}
}
"""

def test_parse_bibtex_count():
    entries = parse_bibtex(BIBTEX_SAMPLE)
    assert len(entries) == 2

def test_parse_bibtex_fields():
    entries = parse_bibtex(BIBTEX_SAMPLE)
    e = entries[0]
    assert 'XPBD' in e['title']
    assert 'Macklin' in e['authors']
    assert e['year'] == 2016
    assert e['doi'] == '10.1145/2994258.2994272'
    assert e['entry_id'] == 'Macklin2016'

def test_parse_bibtex_latex_decode():
    entries = parse_bibtex(BIBTEX_SAMPLE)
    e = entries[0]
    # LaTeX-encoded ü should be decoded
    assert 'Müller' in e['authors'] or 'Muller' in e['authors']

def test_parse_bibtex_empty():
    entries = parse_bibtex('')
    assert entries == []

def test_parse_bibtex_mendeley_file_field():
    bib = """
@article{Test2020,
    title = {Test Paper},
    author = {Test, Author},
    year = {2020},
    file = {:/home/user/papers/test.pdf:pdf}
}
"""
    entries = parse_bibtex(bib)
    e = entries[0]
    assert e['pdf_path'] == '/home/user/papers/test.pdf'

# --- CrossRef / arXiv (mocked) ---

def test_crossref_lookup_mock(monkeypatch):
    """Mock CrossRef API response."""
    from paperdb.identity import metadata as meta_mod

    class MockResponse:
        status_code = 200
        def json(self):
            return {'message': {
                'title': ['Test Paper'],
                'author': [{'family': 'Test', 'given': 'Author'}],
                'published-print': {'date-parts': [[2020]]},
                'container-title': ['Test Journal'],
                'abstract': 'Test abstract',
            }}
        def raise_for_status(self):
            pass

    def mock_get(url, **kwargs):
        return MockResponse()

    monkeypatch.setattr(meta_mod.requests, 'get', mock_get)
    result = meta_mod.crossref_lookup('10.9999/test.2020.001')
    assert result['title'] == 'Test Paper'
    assert result['year'] == 2020
    assert 'Test' in result['authors']

def test_arxiv_lookup_mock(monkeypatch):
    """Mock arXiv API response."""
    from paperdb.identity import metadata as meta_mod

    ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Test arXiv Paper</title>
    <author><name>John Smith</name></author>
    <published>2023-01-15T00:00:00Z</published>
    <summary>Test abstract content</summary>
    <link title="pdf" href="http://arxiv.org/pdf/2301.12345"/>
  </entry>
</feed>"""

    class MockResponse:
        status_code = 200
        text = ARXIV_XML
        def raise_for_status(self):
            pass

    def mock_get(url, **kwargs):
        return MockResponse()

    monkeypatch.setattr(meta_mod.requests, 'get', mock_get)
    result = meta_mod.arxiv_lookup('2301.12345')
    assert 'Test arXiv Paper' in result['title']
    assert result['year'] == 2023
    assert 'Smith' in result['authors']
    assert result['pdf_url'] == 'http://arxiv.org/pdf/2301.12345'

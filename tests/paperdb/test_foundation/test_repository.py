"""Test repository CRUD for each table, transactional search unit replacement."""
import sqlite3
import tempfile
import os
from paperdb.db.connection import get_connection, init_schema, close_connection
from paperdb.db.repository import Repository
from paperdb.db.models import *

def _setup():
    close_connection()
    d = tempfile.mkdtemp()
    conn = get_connection(os.path.join(d, "test.db"))
    init_schema(conn)
    repo = Repository(conn)
    # create a base paper
    pid = repo.upsert_paper(Paper(paper_key="Macklin_2016_XPBD", title="XPBD", year=2016))
    return conn, repo, pid

def test_upsert_paper_insert():
    conn, repo, pid = _setup()
    assert pid is not None and pid > 0
    p = repo.get_paper(pid)
    assert p.paper_key == "Macklin_2016_XPBD"
    assert p.title == "XPBD"
    conn.close()

def test_upsert_paper_update():
    conn, repo, pid = _setup()
    repo.upsert_paper(Paper(paper_key="Macklin_2016_XPBD", title="XPBD: Position-Based Simulation", year=2016, doi="10.1145/2994258.2994272"))
    p = repo.get_paper_by_key("Macklin_2016_XPBD")
    assert p.title == "XPBD: Position-Based Simulation"
    assert p.doi == "10.1145/2994258.2994272"
    assert p.id == pid  # same ID — it was an update
    conn.close()

def test_get_paper_by_doi():
    conn, repo, pid = _setup()
    repo.upsert_paper(Paper(paper_key="Macklin_2016_XPBD", doi="10.1145/2994258.2994272"))
    p = repo.get_paper_by_doi("10.1145/2994258.2994272")
    assert p is not None
    assert p.paper_key == "Macklin_2016_XPBD"
    conn.close()

def test_list_papers():
    conn, repo, pid = _setup()
    repo.upsert_paper(Paper(paper_key="Author_2019_Foo"))
    repo.upsert_paper(Paper(paper_key="Author_2020_Bar"))
    papers = repo.list_papers(limit=10)
    assert len(papers) == 3
    conn.close()

def test_add_and_get_files():
    conn, repo, pid = _setup()
    fid = repo.add_paper_file(PaperFile(paper_id=pid, path="/home/test/paper.pdf", file_role="publisher", sha256="abc123"))
    files = repo.get_files_for_paper(pid)
    assert len(files) == 1
    assert files[0].path == "/home/test/paper.pdf"
    assert files[0].sha256 == "abc123"
    conn.close()

def test_set_preferred_file():
    conn, repo, pid = _setup()
    f1 = repo.add_paper_file(PaperFile(paper_id=pid, path="/a.pdf", is_preferred=1))
    f2 = repo.add_paper_file(PaperFile(paper_id=pid, path="/b.pdf", is_preferred=0))
    repo.set_preferred_file(pid, f2)
    files = repo.get_files_for_paper(pid)
    preferred = [f for f in files if f.is_preferred]
    assert len(preferred) == 1
    assert preferred[0].id == f2
    conn.close()

def test_find_file_by_hash():
    conn, repo, pid = _setup()
    repo.add_paper_file(PaperFile(paper_id=pid, path="/a.pdf", sha256="hash123"))
    found = repo.find_file_by_hash("hash123")
    assert len(found) == 1
    assert found[0].path == "/a.pdf"
    conn.close()

def test_replace_search_units():
    conn, repo, pid = _setup()
    units = [SearchUnit(paper_id=pid, content="section A", section_path="1"), SearchUnit(paper_id=pid, content="section B", section_path="2")]
    repo.replace_search_units(pid, units)
    assert len(repo.get_search_units_for_paper(pid)) == 2
    # replace with different set
    units2 = [SearchUnit(paper_id=pid, content="section C", section_path="3")]
    repo.replace_search_units(pid, units2)
    result = repo.get_search_units_for_paper(pid)
    assert len(result) == 1
    assert result[0].content == "section C"
    conn.close()

def test_processing_runs():
    conn, repo, pid = _setup()
    run_id = repo.start_run(ProcessingRun(paper_id=pid, operation="convert", backend="docling"))
    assert run_id > 0
    repo.finish_run(run_id, status="ok", message="done")
    run = repo.get_current_run(pid, "convert")
    assert run is not None
    assert run.status == "ok"
    assert run.message == "done"
    conn.close()

def test_tags_and_aliases():
    conn, repo, pid = _setup()
    tag_id = repo.upsert_tag(Tag(canonical_name="DFT", category="method"))
    repo.add_alias(tag_id, "density functional theory")
    repo.add_alias(tag_id, "DFT")
    resolved = repo.resolve_alias("density functional theory")
    assert resolved is not None
    assert resolved.canonical_name == "DFT"
    repo.add_paper_tag(PaperTag(paper_id=pid, tag_id=tag_id, source="llm", confidence=0.9, raw_name="DFT"))
    tags = repo.get_tags_for_paper(pid)
    assert len(tags) == 1
    assert tags[0].canonical_name == "DFT"
    conn.close()

def test_equations_and_variables():
    conn, repo, pid = _setup()
    eq_id = repo.upsert_equation(Equation(paper_id=pid, latex_raw="E = mc^2", equation_number="1", page_number=5))
    assert eq_id > 0
    repo.add_variable(EquationVariable(equation_id=eq_id, symbol="E", meaning="energy"))
    eqs = repo.get_equations_for_paper(pid)
    assert len(eqs) == 1
    assert eqs[0].latex_raw == "E = mc^2"
    vars_ = repo.get_variables_for_equation(eq_id)
    assert len(vars_) == 1
    assert vars_[0].symbol == "E"
    conn.close()

def test_methods_and_link():
    conn, repo, pid = _setup()
    eq_id = repo.upsert_equation(Equation(paper_id=pid, latex_raw="F = ma"))
    m_id = repo.upsert_method(Method(paper_id=pid, name="Newton", method_type="source_algorithm"))
    repo.link_method_equation(m_id, eq_id, "core")
    methods = repo.get_methods_for_paper(pid)
    assert len(methods) == 1
    assert methods[0].name == "Newton"
    conn.close()

def test_summaries():
    conn, repo, pid = _setup()
    repo.add_summary(Summary(paper_id=pid, content="Summary v1", model_name="llama-8b"))
    repo.add_summary(Summary(paper_id=pid, content="Summary v2", model_name="gemini-flash"))
    active = repo.get_active_summary(pid)
    assert active.content == "Summary v2"
    all_s = repo.list_summaries(pid)
    assert len(all_s) == 2
    conn.close()

def test_context_packs():
    conn, repo, pid = _setup()
    cp_id = repo.save_context_pack(ContextPack(query="GPU collision", content="context pack text"))
    cp = repo.get_context_pack(cp_id)
    assert cp is not None
    assert cp.query == "GPU collision"
    conn.close()

def test_topics():
    conn, repo, pid = _setup()
    tid = repo.upsert_topic(Topic(name="molecular force fields", description="FF methods"))
    repo.add_topic_paper(TopicPaper(topic_id=tid, paper_id=pid, relevance="core method"))
    t = repo.get_topic_by_name("molecular force fields")
    assert t is not None
    tp = repo.get_topic_papers(tid)
    assert len(tp) == 1
    conn.close()

def test_citations():
    conn, repo, pid = _setup()
    repo.add_citation(Citation(citing_paper_id=pid, cited_doi="10.1234/test", cited_title="Referenced Paper"))
    cites = repo.get_citations_for_paper(pid)
    assert len(cites) == 1
    assert cites[0].cited_doi == "10.1234/test"
    conn.close()

def test_status_counts():
    conn, repo, pid = _setup()
    repo.add_paper_file(PaperFile(paper_id=pid, path="/a.pdf"))
    repo.upsert_tag(Tag(canonical_name="DFT", category="method"))
    counts = repo.get_status_counts()
    assert counts["papers"] == 1
    assert counts["files"] == 1
    assert counts["tags"] == 1
    conn.close()

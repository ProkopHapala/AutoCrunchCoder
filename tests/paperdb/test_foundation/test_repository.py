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

def test_summary_visibility_changes_only_after_successful_run():
    from paperdb.ingest.jobs import finish_job
    conn, repo, pid = _setup()
    repo.add_summary(paper_id=pid, content="Last successful", model_name="baseline")
    failed_run = repo.start_run(paper_id=pid, operation="summarize", backend="llm", config_hash="failed")
    repo.add_summary(paper_id=pid, run_id=failed_run, content="Unverified", model_name="candidate")
    assert repo.get_active_summary(pid).content == "Last successful"
    finish_job(failed_run, "failed", repo)
    assert repo.get_active_summary(pid).content == "Last successful"
    successful_run = repo.start_run(paper_id=pid, operation="summarize", backend="llm", config_hash="ok")
    repo.add_summary(paper_id=pid, run_id=successful_run, content="New successful", model_name="candidate")
    assert repo.get_active_summary(pid).content == "Last successful"
    finish_job(successful_run, "ok", repo)
    assert repo.get_active_summary(pid).content == "New successful"
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


def test_active_tag_run_refresh_and_assertion_history():
    from paperdb.ingest.jobs import finish_job
    conn, repo, pid = _setup()
    old_tag = repo.upsert_tag(canonical_name="old method", category="method")
    new_tag = repo.upsert_tag(canonical_name="new method", category="method")
    run1 = repo.start_run(paper_id=pid, operation="tag", backend="llm", config_hash="a")
    repo.add_paper_tag(paper_id=pid, tag_id=old_tag, source="llm", run_id=run1, raw_name="Old Method")
    assert repo.get_tags_for_paper(pid) == []
    finish_job(run1, "ok", repo)
    assert [tag.canonical_name for tag in repo.get_tags_for_paper(pid)] == ["old method"]
    run2 = repo.start_run(paper_id=pid, operation="tag", backend="llm", config_hash="b")
    repo.add_paper_tag(paper_id=pid, tag_id=new_tag, source="llm", run_id=run2, raw_name="New Method")
    assert [tag.canonical_name for tag in repo.get_tags_for_paper(pid)] == ["old method"]
    finish_job(run2, "ok", repo)
    assert [tag.canonical_name for tag in repo.get_tags_for_paper(pid)] == ["new method"]
    assert conn.execute("SELECT COUNT(*) FROM tag_assertions WHERE paper_id=?", (pid,)).fetchone()[0] == 2
    conn.close()


def test_merge_tags_preserves_raw_assertions_real_repository():
    from paperdb.taxonomy.aliases import merge_tags
    conn, repo, pid = _setup()
    canonical = repo.upsert_tag(canonical_name="density functional theory", category="method")
    alias = repo.upsert_tag(canonical_name="DFT", category="method")
    repo.add_paper_tag(paper_id=pid, tag_id=alias, source="user", raw_name="DFT", confidence=1.0)
    merge_tags(canonical, alias, repo)
    assertion = conn.execute("SELECT tag_id, raw_name FROM tag_assertions WHERE paper_id=?", (pid,)).fetchone()
    assert assertion["tag_id"] == canonical
    assert assertion["raw_name"] == "DFT"
    assert repo.get_tag_by_id(alias) is None
    conn.close()


def test_real_saved_context_and_cli_json(tmp_path):
    import json
    from typer.testing import CliRunner
    from paperdb import PaperDB
    from paperdb.cli import app
    data_dir = tmp_path / "paperdb"
    db = PaperDB(data_dir=str(data_dir))
    pid = db.upsert_paper(Paper(paper_key="Evidence_2026_Context", title="Scientific evidence"))
    db.repo.add_search_unit(SearchUnit(paper_id=pid, unit_type="section", source_type="section", section_path="Methods", content="scientific evidence method details"))
    pack = db.retrieve_context("scientific evidence", save=True)
    assert pack.id is not None and pack.paper_count == 1
    db.close()
    reopened = PaperDB(data_dir=str(data_dir))
    assert reopened.get_context_pack(pack.id).content == pack.content
    reopened.close()
    result = CliRunner().invoke(app, ["--data-dir", str(data_dir), "--json", "context", "scientific evidence", "--save"])
    assert result.exit_code == 0, result.exception
    payload = json.loads(result.stdout)
    assert payload["id"] is not None
    assert payload["paper_count"] == 1

"""Test ingest pipeline — skip-if-equivalent logic, atomic file writes, orchestration."""
import sys, os, json, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from paperdb.ingest.pipeline import _atomic_write, _atomic_write_json, _config_hash, _generate_bib_file, _generate_json_file
from paperdb.ingest.jobs import find_equivalent_run, run_job, finish_job, ingest_batch
from paperdb.db.models import Paper, PaperFile, ProcessingRun, Tag, Method, Equation


class MockRepo:
    """Mock repository for testing pipeline logic without a real database."""
    def __init__(self):
        self.papers = {1: Paper(id=1, paper_key="Test_2020_Paper", year=2020, doi="10.1234/test",
                          title="Test Paper", authors_text="Test Author", markdown_path=None)}
        self.files = {1: [PaperFile(id=1, paper_id=1, path="/fake/test.pdf", sha256="abc123", is_preferred=1)]}
        self.runs = {}
        self._run_id = 0
        self.equations = []
        self.methods = []

    def get_paper(self, pid): return self.papers.get(pid)
    def get_files_for_paper(self, pid): return self.files.get(pid, [])
    def update_paper_paths(self, pid, **kwargs):
        if pid in self.papers:
            p = self.papers[pid]
            for k, v in kwargs.items():
                setattr(p, k, v)
    def start_run(self, run: ProcessingRun) -> int:
        self._run_id += 1
        run.id = self._run_id
        run.status = "running"
        self.runs[self._run_id] = run
        return self._run_id
    def finish_run(self, run_id, status="ok", message=None, output_path=None):
        if run_id in self.runs:
            self.runs[run_id].status = status
            self.runs[run_id].message = message
            self.runs[run_id].output_path = output_path
    def get_runs_for_paper(self, paper_id):
        return [r for r in self.runs.values() if r.paper_id == paper_id]
    def find_equivalent_run(self, paper_id, operation, config_hash, input_sha256=None):
        return None  # No equivalent runs in mock
    def supersede_run(self, run_id, new_run_id):
        if run_id in self.runs:
            self.runs[run_id].status = "superseded"
            self.runs[run_id].supersedes_run_id = new_run_id
    def upsert_equation(self, eq): return 1
    def add_variable(self, var): return 1
    def upsert_method(self, m): return 1
    def link_method_equation(self, **kwargs): pass
    def get_equations_for_paper(self, pid): return self.equations
    def get_methods_for_paper(self, pid): return self.methods
    def get_tags_for_paper(self, pid): return []


def test_atomic_write():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        path = f.name
    try:
        _atomic_write(path, "hello world")
        assert open(path).read() == "hello world"
    finally:
        os.unlink(path)


def test_atomic_write_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        _atomic_write_json(path, {"key": "value", "num": 42})
        data = json.loads(open(path).read())
        assert data["key"] == "value"
        assert data["num"] == 42
    finally:
        os.unlink(path)


def test_atomic_write_empty_fails():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        path = f.name
    try:
        try:
            _atomic_write(path, "")
            assert False, "Should raise on empty content"
        except RuntimeError:
            pass
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_config_hash():
    h1 = _config_hash({"a": 1, "b": 2})
    h2 = _config_hash({"b": 2, "a": 1})  # Same content, different order
    h3 = _config_hash({"a": 1, "b": 3})
    assert h1 == h2  # Order-independent
    assert h1 != h3  # Different content
    assert _config_hash(None) == ""
    assert _config_hash({}) == ""  # empty dict is falsy


def test_generate_bib_file():
    with tempfile.TemporaryDirectory() as d:
        bib_path = os.path.join(d, "test.bib")
        paper = Paper(id=1, paper_key="Test_2020", title="Test Paper",
                 authors_text="John Doe", year=2020, journal="Nature",
                 doi="10.1234/test")
        _generate_bib_file(paper, bib_path)
        content = open(bib_path).read()
        assert "@article{Test_2020," in content
        assert "Test Paper" in content
        assert "John Doe" in content
        assert "2020" in content
        assert "10.1234/test" in content


def test_generate_json_file():
    repo = MockRepo()
    with tempfile.TemporaryDirectory() as d:
        json_path = os.path.join(d, "test.json")
        paper = Paper(id=1, paper_key="Test_2020", doi="10.1234/test",
                 arxiv_id=None, title="Test", authors_text="Author",
                 year=2020, journal="Nature")
        equations = [{"equation_number": "1", "latex_raw": "E=mc^2", "latex_normalized": "E=mc^2",
                      "section_path": "Intro", "page_number": 3}]
        _generate_json_file(paper, equations, repo, json_path)
        data = json.loads(open(json_path).read())
        assert data["paper_id"] == 1
        assert data["paper_key"] == "Test_2020"
        assert len(data["equations"]) == 1
        assert data["equations"][0]["latex_raw"] == "E=mc^2"


def test_find_equivalent_run_no_method():
    """If repo doesn't have find_equivalent_run, return None."""
    class NoMethodRepo:
        pass
    repo = NoMethodRepo()
    result = find_equivalent_run(1, "convert", "abc", "docling", "hash", None, None, repo)
    assert result is None


def test_run_job_creates_run():
    repo = MockRepo()
    run_id = run_job(1, "convert", "docling", {"backend": "docling"}, repo)
    assert run_id is not None
    assert repo.runs[run_id].status == "running"
    assert repo.runs[run_id].operation == "convert"


def test_finish_job_ok():
    repo = MockRepo()
    run_id = run_job(1, "convert", "docling", {}, repo)
    finish_job(run_id, "ok", repo)
    assert repo.runs[run_id].status == "ok"


def test_finish_job_failed():
    repo = MockRepo()
    run_id = run_job(1, "convert", "docling", {}, repo)
    finish_job(run_id, "failed", repo, message="test error")
    assert repo.runs[run_id].status == "failed"
    assert repo.runs[run_id].message == "test error"


if __name__ == "__main__":
    test_atomic_write()
    test_atomic_write_json()
    test_atomic_write_empty_fails()
    test_config_hash()
    test_generate_bib_file()
    test_generate_json_file()
    test_find_equivalent_run_no_method()
    test_run_job_creates_run()
    test_finish_job_ok()
    test_finish_job_failed()
    print("All pipeline tests passed!")

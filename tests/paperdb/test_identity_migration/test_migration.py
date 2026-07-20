"""Tests for paperdb.ingest.migration — migrate a small test DB, verify paper count, search units, report."""
import os
import sqlite3
import tempfile
import pytest
from paperdb.ingest.migration import migrate_legacy, _apply_tag_consolidation, _normalize_tag_name
from paperdb.identity.hashing import clear_cache
from mock_repo import MockRepository

@pytest.fixture(autouse=True)
def clean_cache(tmp_path, monkeypatch):
    monkeypatch.setenv('PAPERDB_DATA', str(tmp_path))
    clear_cache()
    yield
    clear_cache()

def _create_legacy_db(db_path: str, n_papers: int = 3):
    """Create a small legacy consolidated.db for testing."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_pdf_path TEXT,
            stem TEXT UNIQUE,
            doi TEXT,
            bibtex_ok INTEGER,
            bibtex_path TEXT,
            bibtex_error TEXT,
            bibtex_text TEXT,
            title TEXT,
            authors TEXT,
            year TEXT,
            journal TEXT,
            keywords TEXT,
            shadow_md_path TEXT,
            shadow_pdf_path TEXT,
            rename_target_md TEXT,
            rename_target_pdf TEXT,
            md_path TEXT,
            timestamp TEXT,
            essence TEXT,
            run_name TEXT
        );
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            category TEXT
        );
        CREATE TABLE article_tags (
            article_id TEXT,
            tag_id INTEGER,
            UNIQUE(article_id, tag_id)
        );
    """)
    for i in range(n_papers):
        conn.execute("""INSERT INTO papers (stem, doi, title, authors, year, journal, essence, run_name, bibtex_text)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (f'Test{i}_2020_Paper{i}', f'10.9999/test.2020.{i:03d}', f'Test Paper {i}', f'Test, Author{i}', '2020',
             'Test Journal', f'Essence of paper {i}', '20260223_195058', f'@article{{Test{i}, title={{Test Paper {i}}}, year={{2020}}}}'))
    # Add tags
    conn.execute("INSERT INTO tags (name, category) VALUES ('DFT', 'domain')")
    conn.execute("INSERT INTO tags (name, category) VALUES ('density functional theory', 'domain')")
    conn.execute("INSERT INTO tags (name, category) VALUES ('molecular dynamics', 'domain')")
    # Link tags to papers
    conn.execute("INSERT INTO article_tags (article_id, tag_id) VALUES ('Test0_2020_Paper0', 1)")
    conn.execute("INSERT INTO article_tags (article_id, tag_id) VALUES ('Test0_2020_Paper0', 2)")
    conn.execute("INSERT INTO article_tags (article_id, tag_id) VALUES ('Test1_2020_Paper1', 3)")
    conn.commit()
    conn.close()

def _create_legacy_markdown(legacy_dir: str, n_papers: int = 3):
    """Create legacy markdown and summary files."""
    run_dir = os.path.join(legacy_dir, '20260223_195058')
    md_dir = os.path.join(run_dir, 'markdown')
    summary_dir = os.path.join(run_dir, 'summaries')
    os.makedirs(md_dir, exist_ok=True)
    os.makedirs(summary_dir, exist_ok=True)
    for i in range(n_papers):
        stem = f'Test{i}_2020_Paper{i}'
        with open(os.path.join(md_dir, f'{stem}.md'), 'w') as f:
            f.write(f'# Test Paper {i}\n\n## Introduction\n\nThis is test paper {i}.\n\n## Methods\n\nSome methods.\n')
        with open(os.path.join(summary_dir, f'{stem}.md'), 'w') as f:
            f.write(f'## Essence\n\nEssence of paper {i}.\n\n## Key Equations\n\nE = mc^2\n')

@pytest.fixture
def legacy_setup(tmp_path):
    """Create a complete legacy setup with DB + markdown."""
    legacy_dir = tmp_path / 'legacy'
    legacy_dir.mkdir()
    db_path = str(legacy_dir / 'consolidated.db')
    _create_legacy_db(db_path, n_papers=3)
    _create_legacy_markdown(str(legacy_dir), n_papers=3)
    data_dir = tmp_path / 'paperdb_data'
    data_dir.mkdir()
    return str(legacy_dir), str(data_dir)

def test_migrate_legacy_basic(legacy_setup):
    """Migrate a small test DB, verify paper count."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    result = migrate_legacy(legacy_dir, repo, data_dir)
    assert result['papers_migrated'] == 3
    assert result['papers_failed'] == 0
    papers = repo.list_papers()
    assert len(papers) == 3

def test_migrate_legacy_paper_keys(legacy_setup):
    """Verify paper_keys are generated correctly."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    migrate_legacy(legacy_dir, repo, data_dir)
    papers = repo.list_papers()
    for p in papers:
        assert p['paper_key'] is not None
        assert 'Test' in p['paper_key']
        assert '2020' in p['paper_key']

def test_migrate_legacy_dois(legacy_setup):
    """Verify DOIs are normalized."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    migrate_legacy(legacy_dir, repo, data_dir)
    papers = repo.list_papers()
    for p in papers:
        if p['doi']:
            assert p['doi'] == p['doi'].lower()
            assert not p['doi'].startswith('https://')

def test_migrate_legacy_tags(legacy_setup):
    """Verify tags are imported and consolidated."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    migrate_legacy(legacy_dir, repo, data_dir)
    counts = repo.get_status_counts()
    # DFT and density functional theory should be consolidated into one
    assert counts['tags'] < 3  # fewer than original 3 tags

def test_migrate_legacy_processing_runs(legacy_setup):
    """Verify processing_runs are created for markdown and summary migration."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    migrate_legacy(legacy_dir, repo, data_dir)
    cur = repo.conn.execute("SELECT COUNT(*) as n FROM processing_runs WHERE operation = 'migrate_markdown'")
    assert cur.fetchone()['n'] == 3
    cur = repo.conn.execute("SELECT COUNT(*) as n FROM processing_runs WHERE operation = 'migrate_summary'")
    assert cur.fetchone()['n'] == 3

def test_migrate_legacy_search_units(legacy_setup):
    """Verify search_units are built from migrated markdown."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    migrate_legacy(legacy_dir, repo, data_dir)
    cur = repo.conn.execute("SELECT COUNT(*) as n FROM search_units")
    assert cur.fetchone()['n'] > 0

def test_migrate_legacy_bundles(legacy_setup):
    """Verify .md/.json/.bib bundles are generated."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    migrate_legacy(legacy_dir, repo, data_dir)
    papers_dir = os.path.join(data_dir, 'papers', '2020')
    assert os.path.isdir(papers_dir)
    md_files = [f for f in os.listdir(papers_dir) if f.endswith('.md')]
    json_files = [f for f in os.listdir(papers_dir) if f.endswith('.json')]
    assert len(md_files) == 3
    assert len(json_files) == 3

def test_migrate_legacy_report(legacy_setup):
    """Verify migration report is produced."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    result = migrate_legacy(legacy_dir, repo, data_dir)
    assert os.path.exists(result['report_path'])
    with open(result['report_path'], 'r') as f:
        report = f.read()
    assert 'Migration Report' in report
    assert 'Papers migrated' in report

def test_migrate_legacy_copies_db(legacy_setup):
    """Verify consolidated.db is copied to legacy/ (non-destructive)."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    migrate_legacy(legacy_dir, repo, data_dir)
    copied_db = os.path.join(data_dir, 'legacy', 'consolidated.db')
    assert os.path.exists(copied_db)

def test_migrate_legacy_needs_reprocessing(legacy_setup):
    """Verify papers with pdfminer backend or missing summaries are flagged."""
    legacy_dir, data_dir = legacy_setup
    repo = MockRepository()
    result = migrate_legacy(legacy_dir, repo, data_dir)
    # Our test markdown is from docling (inferred from run dir), so should not need reprocessing
    # unless summaries are missing
    assert isinstance(result['needs_reprocessing'], list)

def test_tag_consolidation():
    """Test tag consolidation rules."""
    tags = [
        {'name': 'DFT', 'category': 'domain'},
        {'name': 'density functional theory', 'category': 'domain'},
        {'name': 'machine learning', 'category': 'domain'},
        {'name': 'neural networks', 'category': 'domain'},
    ]
    consolidated, aliases = _apply_tag_consolidation(tags)
    # DFT and density functional theory should merge
    names = [t['name'] for t in consolidated]
    assert 'density functional theory (dft)' in names
    # neural networks should merge into machine learning
    assert 'machine learning' in names
    # Should have fewer tags than original
    assert len(consolidated) < len(tags)

def test_normalize_tag_name():
    assert _normalize_tag_name('DFT') == 'dft'
    assert _normalize_tag_name('Density Functional Theory (DFT)') == 'density functional theory dft'
    assert _normalize_tag_name('') == ''

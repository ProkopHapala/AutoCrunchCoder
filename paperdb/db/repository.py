"""Repository — ALL SQL queries live here. Single place for database access.

Repository(connection) provides CRUD for every table in the schema.
"""
import sqlite3
from typing import Any, Optional
from paperdb.db.models import *
from paperdb.db.connection import db_transaction

class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def _executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        return self.conn.executemany(sql, params_list)

    def _fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, params).fetchone()

    def _fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    # ── Papers ──────────────────────────────────────────────────────────

    def upsert_paper(self, paper: Paper | None = None, **kwargs) -> int:
        """Insert or update a paper by paper_key. Returns the paper ID.
        Accepts either a Paper object or keyword arguments."""
        if paper is None:
            paper = Paper(**kwargs)
        row = self._fetchone("SELECT id FROM papers WHERE doi = ?", (paper.doi,)) if paper.doi else None
        if row is None: row = self._fetchone("SELECT id FROM papers WHERE paper_key = ?", (paper.paper_key,))
        if row:
            self._execute("""UPDATE papers SET doi=COALESCE(?,doi), arxiv_id=COALESCE(?,arxiv_id), title=COALESCE(?,title),
                authors_text=COALESCE(?,authors_text), year=COALESCE(?,year), journal=COALESCE(?,journal),
                abstract=COALESCE(?,abstract), keywords=COALESCE(?,keywords), essence=COALESCE(?,essence),
                markdown_path=COALESCE(?,markdown_path), json_path=COALESCE(?,json_path), bibtex_path=COALESCE(?,bibtex_path), updated_at=CURRENT_TIMESTAMP
                WHERE id=?""",
                (paper.doi, paper.arxiv_id, paper.title, paper.authors_text, paper.year, paper.journal,
                 paper.abstract, paper.keywords, paper.essence, paper.markdown_path, paper.json_path, paper.bibtex_path, row["id"]))
            return row["id"]
        cur = self._execute("""INSERT INTO papers (paper_key, doi, arxiv_id, title, authors_text, year, journal,
            abstract, keywords, essence, markdown_path, json_path, bibtex_path)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (paper.paper_key, paper.doi, paper.arxiv_id, paper.title, paper.authors_text, paper.year, paper.journal,
             paper.abstract, paper.keywords, paper.essence, paper.markdown_path, paper.json_path, paper.bibtex_path))
        return cur.lastrowid

    def get_paper(self, paper_id: int) -> Paper | None:
        row = self._fetchone("SELECT * FROM papers WHERE id = ?", (paper_id,))
        return Paper(**dict(row)) if row else None

    def get_paper_by_key(self, key: str) -> Paper | None:
        row = self._fetchone("SELECT * FROM papers WHERE paper_key = ?", (key,))
        return Paper(**dict(row)) if row else None

    def get_paper_by_doi(self, doi: str) -> Paper | None:
        row = self._fetchone("SELECT * FROM papers WHERE doi = ?", (doi,))
        return Paper(**dict(row)) if row else None

    def list_papers(self, limit: int = 100, offset: int = 0) -> list[Paper]:
        rows = self._fetchall("SELECT * FROM papers ORDER BY id LIMIT ? OFFSET ?", (limit, offset))
        return [Paper(**dict(r)) for r in rows]

    def update_paper_paths(self, paper_id: int = None, markdown_path: str | None = None, json_path: str | None = None, bibtex_path: str | None = None, **kwargs):
        parts, params = [], []
        if markdown_path is not None: parts.append("markdown_path=?"); params.append(markdown_path)
        if json_path is not None: parts.append("json_path=?"); params.append(json_path)
        if bibtex_path is not None: parts.append("bibtex_path=?"); params.append(bibtex_path)
        if not parts: return
        parts.append("updated_at=CURRENT_TIMESTAMP")
        params.append(paper_id)
        self._execute(f"UPDATE papers SET {', '.join(parts)} WHERE id=?", tuple(params))

    def set_paper_bibtex(self, paper_id: int, bibtex_text: str, bibtex_path: str | None = None):
        """Store BibTeX at an explicit artifact path and update the paper."""
        from pathlib import Path
        paper = self.get_paper(paper_id)
        if paper is None: raise ValueError(f"Paper {paper_id} not found")
        path = Path(bibtex_path or paper.bibtex_path) if (bibtex_path or paper.bibtex_path) else None
        if path is None: raise ValueError("set_paper_bibtex requires an explicit path for a paper without one")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(bibtex_text, encoding="utf-8")
        tmp.replace(path)
        self.update_paper_paths(paper_id=paper_id, bibtex_path=str(path))

    # ── Paper Files ─────────────────────────────────────────────────────

    def add_paper_file(self, pf: PaperFile | None = None, **kwargs) -> int:
        """Add a file record. Accepts PaperFile object or kwargs."""
        if pf is None:
            pf = PaperFile(**kwargs)
        cur = self._execute("""INSERT INTO paper_files (paper_id, path, file_role, version_label, file_size, modified_time, sha256, exists_now, is_preferred)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (pf.paper_id, pf.path, pf.file_role, pf.version_label, pf.file_size, pf.modified_time, pf.sha256, pf.exists_now, pf.is_preferred))
        return cur.lastrowid

    def get_files_for_paper(self, paper_id: int) -> list[PaperFile]:
        rows = self._fetchall("SELECT * FROM paper_files WHERE paper_id = ? ORDER BY is_preferred DESC, id", (paper_id,))
        return [PaperFile(**dict(r)) for r in rows]

    def set_preferred_file(self, paper_id: int, file_id: int):
        self._execute("UPDATE paper_files SET is_preferred=0 WHERE paper_id=? AND is_preferred=1", (paper_id,))
        self._execute("UPDATE paper_files SET is_preferred=1 WHERE paper_id=? AND id=?", (paper_id, file_id))

    def find_file_by_hash(self, sha256: str) -> list[PaperFile]:
        rows = self._fetchall("SELECT * FROM paper_files WHERE sha256 = ?", (sha256,))
        return [PaperFile(**dict(r)) for r in rows]

    def find_file_by_path(self, path: str) -> PaperFile | None:
        row = self._fetchone("SELECT * FROM paper_files WHERE path = ?", (path,))
        return PaperFile(**dict(row)) if row else None

    def touch_file(self, file_id: int, sha256: str | None = None, file_size: int | None = None, modified_time: float | None = None):
        """Mark a file present and refresh its observed identity."""
        self._execute("""UPDATE paper_files SET last_seen=CURRENT_TIMESTAMP, exists_now=1,
            sha256=COALESCE(?,sha256), file_size=COALESCE(?,file_size), modified_time=COALESCE(?,modified_time) WHERE id=?""",
            (sha256, file_size, modified_time, file_id))

    def move_file(self, file_id: int, path: str, file_size: int | None = None, modified_time: float | None = None):
        """Update a file path after hash-based move detection."""
        self._execute("""UPDATE paper_files SET path=?, file_size=COALESCE(?,file_size), modified_time=COALESCE(?,modified_time),
            exists_now=1, last_seen=CURRENT_TIMESTAMP WHERE id=?""", (path, file_size, modified_time, file_id))

    # ── Search Units ────────────────────────────────────────────────────

    def replace_search_units(self, paper_id: int, units: list):
        """Transactional delete+insert for search units of a paper.
        Accepts list of SearchUnit objects or list of dicts."""
        with db_transaction(self.conn):
            self._execute("DELETE FROM search_units WHERE paper_id = ?", (paper_id,))
            for u in units:
                if isinstance(u, dict):
                    u = SearchUnit(paper_id=paper_id, **{k: v for k, v in u.items() if k != 'paper_id'})
                self._execute("""INSERT INTO search_units (paper_id, run_id, unit_type, source_type, source_id, section_path, page_from, page_to, content)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (paper_id, u.run_id, u.unit_type, u.source_type, u.source_id, u.section_path, u.page_from, u.page_to, u.content))

    def get_search_units_for_paper(self, paper_id: int) -> list[SearchUnit]:
        rows = self._fetchall("SELECT * FROM search_units WHERE paper_id = ? ORDER BY id", (paper_id,))
        return [SearchUnit(**dict(r)) for r in rows]

    def add_search_unit(self, su: SearchUnit | None = None, **kwargs) -> int:
        if su is None:
            su = SearchUnit(**kwargs)
        cur = self._execute("""INSERT INTO search_units (paper_id, run_id, unit_type, source_type, source_id, section_path, page_from, page_to, content)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (su.paper_id, su.run_id, su.unit_type, su.source_type, su.source_id, su.section_path, su.page_from, su.page_to, su.content))
        return cur.lastrowid

    # ── Processing Runs ─────────────────────────────────────────────────

    def start_run(self, run: ProcessingRun | None = None, **kwargs) -> int:
        """Start a processing run. Accepts ProcessingRun object or kwargs.
        Status is set to 'running' regardless of input status."""
        if run is None:
            run = ProcessingRun(**kwargs)
        cur = self._execute("""INSERT INTO processing_runs (paper_id, operation, backend, backend_version, model_name, prompt_version,
            configuration_json, config_hash, source_file_id, input_sha256, output_path, supersedes_run_id, status, started_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (run.paper_id, run.operation, run.backend, run.backend_version, run.model_name, run.prompt_version,
             run.configuration_json, run.config_hash, run.source_file_id, run.input_sha256, run.output_path, run.supersedes_run_id, "running"))
        return cur.lastrowid

    def finish_run(self, run_id: int, status: str = "ok", message: str | None = None, output_path: str | None = None):
        self._execute("""UPDATE processing_runs SET status=?, message=?, output_path=COALESCE(?, output_path), finished_at=CURRENT_TIMESTAMP
            WHERE id=?""", (status, message, output_path, run_id))

    def get_current_run(self, paper_id: int, operation: str) -> ProcessingRun | None:
        """Get the newest active successful run for a paper and operation."""
        row = self._fetchone("SELECT * FROM processing_runs WHERE paper_id=? AND operation=? AND status='ok' ORDER BY id DESC LIMIT 1", (paper_id, operation))
        return ProcessingRun(**dict(row)) if row else None

    def supersede_run(self, run_id: int, new_run_id: int):
        """Mark the immediate predecessor superseded and link it from the new run."""
        self._execute("UPDATE processing_runs SET status='superseded' WHERE id=?", (run_id,))
        self._execute("UPDATE processing_runs SET supersedes_run_id=? WHERE id=?", (run_id, new_run_id))

    def mark_run_superseded(self, run_id: int):
        """Deactivate an older successful run without changing lineage on the new run."""
        self._execute("UPDATE processing_runs SET status='superseded' WHERE id=?", (run_id,))

    def find_equivalent_run(self, paper_id: int = None, operation: str = None, config_hash: str = None, input_sha256: str | None = None,
                            backend: str | None = None, model_name: str | None = None, prompt_version: str | None = None, **kwargs) -> ProcessingRun | None:
        """Find an existing successful run with identical input and processing configuration."""
        sql = """SELECT * FROM processing_runs WHERE paper_id=? AND operation=? AND config_hash=? AND status='ok'
            AND (? IS NULL OR input_sha256=?) AND (? IS NULL OR backend=?)
            AND (? IS NULL OR model_name=?) AND (? IS NULL OR prompt_version=?) ORDER BY id DESC LIMIT 1"""
        params = (paper_id, operation, config_hash, input_sha256, input_sha256, backend, backend, model_name, model_name, prompt_version, prompt_version)
        row = self._fetchone(sql, params)
        return ProcessingRun(**dict(row)) if row else None

    def get_runs_for_paper(self, paper_id: int) -> list[ProcessingRun]:
        rows = self._fetchall("SELECT * FROM processing_runs WHERE paper_id=? ORDER BY id DESC", (paper_id,))
        return [ProcessingRun(**dict(r)) for r in rows]

    def get_run_by_id(self, run_id: int) -> ProcessingRun | None:
        row = self._fetchone("SELECT * FROM processing_runs WHERE id=?", (run_id,))
        return ProcessingRun(**dict(row)) if row else None

    # ── Tags ────────────────────────────────────────────────────────────

    def upsert_tag(self, tag: Tag | None = None, **kwargs) -> int:
        """Insert or find a tag by canonical_name+category. Returns tag ID.
        Accepts Tag object or kwargs."""
        if tag is None:
            tag = Tag(**kwargs)
        row = self._fetchone("SELECT id FROM tags WHERE canonical_name=? AND category=?", (tag.canonical_name, tag.category))
        if row: return row["id"]
        cur = self._execute("INSERT INTO tags (canonical_name, category) VALUES (?,?)", (tag.canonical_name, tag.category))
        return cur.lastrowid

    def add_tag(self, canonical_name: str, category: str) -> int:
        """Convenience alias for upsert_tag with kwargs."""
        return self.upsert_tag(canonical_name=canonical_name, category=category)

    def add_alias(self, tag_id: int, alias: str, normalized_alias: str | None = None):
        if normalized_alias is None: normalized_alias = alias.lower().strip()
        self._execute("INSERT OR IGNORE INTO tag_aliases (tag_id, alias, normalized_alias) VALUES (?,?,?)", (tag_id, alias, normalized_alias))

    def add_tag_alias(self, tag_id: int, alias: str, normalized_alias: str | None = None):
        """Alias for add_alias — matches caller expectations in taxonomy/aliases.py."""
        self.add_alias(tag_id, alias, normalized_alias)

    def resolve_alias(self, normalized_alias: str) -> Tag | None:
        row = self._fetchone("""SELECT t.* FROM tags t JOIN tag_aliases a ON t.id = a.tag_id WHERE a.normalized_alias = ?""",
            (normalized_alias,))
        return Tag(**dict(row)) if row else None

    def get_tags_for_paper(self, paper_id: int) -> list[Tag]:
        rows = self._fetchall("""SELECT DISTINCT t.* FROM tags t JOIN paper_tags pt ON t.id = pt.tag_id WHERE pt.paper_id = ?""",
            (paper_id,))
        return [Tag(**dict(r)) for r in rows]

    def add_paper_tag(self, pt: PaperTag | None = None, **kwargs) -> None:
        """Add a paper-tag association. Accepts PaperTag object or kwargs."""
        if pt is None:
            pt = PaperTag(**kwargs)
        run = self.get_run_by_id(pt.run_id) if pt.source == "llm" and pt.run_id is not None else None
        visible = run is None or run.status == "ok"
        exists = self._fetchone("SELECT 1 FROM paper_tags WHERE paper_id=? AND tag_id=? AND IFNULL(source,'')=IFNULL(?, '')",
                                (pt.paper_id, pt.tag_id, pt.source))
        if visible and not exists:
            self._execute("""INSERT INTO paper_tags (paper_id, tag_id, source, run_id, confidence, raw_name)
                VALUES (?,?,?,?,?,?)""", (pt.paper_id, pt.tag_id, pt.source, pt.run_id, pt.confidence, pt.raw_name))
        self._execute("""INSERT OR IGNORE INTO tag_assertions (paper_id, tag_id, source, run_id, confidence, raw_name)
            VALUES (?,?,?,?,?,?)""", (pt.paper_id, pt.tag_id, pt.source, pt.run_id, pt.confidence, pt.raw_name))

    def refresh_paper_tags(self, paper_id: int):
        """Rebuild LLM canonical links from active assertions after a tag run succeeds."""
        with db_transaction(self.conn):
            self._execute("DELETE FROM paper_tags WHERE paper_id=? AND source='llm'", (paper_id,))
            self._execute("""INSERT INTO paper_tags (paper_id, tag_id, source, run_id, confidence, raw_name)
                SELECT a.paper_id, a.tag_id, a.source, MAX(a.run_id), MAX(a.confidence), MAX(a.raw_name)
                FROM tag_assertions a JOIN processing_runs r ON r.id=a.run_id
                WHERE a.paper_id=? AND a.source='llm' AND r.status='ok' GROUP BY a.paper_id, a.tag_id, a.source""", (paper_id,))

    def list_all_tags(self, category: str | None = None) -> list[Tag]:
        if category:
            rows = self._fetchall("SELECT * FROM tags WHERE category = ? ORDER BY canonical_name", (category,))
        else:
            rows = self._fetchall("SELECT * FROM tags ORDER BY category, canonical_name")
        return [Tag(**dict(r)) for r in rows]

    def get_all_tags(self) -> list[Tag]:
        """Alias for list_all_tags() — matches taxonomy/aliases.py expectations."""
        return self.list_all_tags()

    def get_tag_aliases(self, tag_id: int) -> list[TagAlias]:
        rows = self._fetchall("SELECT * FROM tag_aliases WHERE tag_id = ?", (tag_id,))
        return [TagAlias(**dict(r)) for r in rows]

    def get_tag_aliases_by_tag(self, tag_id: int) -> list[TagAlias]:
        """Alias for get_tag_aliases — matches taxonomy/aliases.py expectations."""
        return self.get_tag_aliases(tag_id)

    def get_tag_by_name(self, name: str, category: str | None = None) -> Tag | None:
        """Find tag by canonical_name, optionally filtered by category."""
        if category:
            row = self._fetchone("SELECT * FROM tags WHERE canonical_name=? AND category=?", (name, category))
        else:
            row = self._fetchone("SELECT * FROM tags WHERE canonical_name=?", (name,))
        return Tag(**dict(row)) if row else None

    def get_tag_by_name_any_category(self, name: str) -> Tag | None:
        """Find tag by canonical_name, any category."""
        return self.get_tag_by_name(name)

    def get_tag_by_id(self, tag_id: int) -> Tag | None:
        row = self._fetchone("SELECT * FROM tags WHERE id=?", (tag_id,))
        return Tag(**dict(row)) if row else None

    def get_tag_aliases_by_normalized(self, normalized_alias: str) -> list[dict]:
        """Find all tag_aliases matching a normalized alias. Returns list of dicts with tag info."""
        rows = self._fetchall("""SELECT a.*, t.canonical_name, t.category
            FROM tag_aliases a JOIN tags t ON a.tag_id = t.id
            WHERE a.normalized_alias = ?""", (normalized_alias,))
        return [dict(r) for r in rows]

    def get_paper_tags_by_tag(self, tag_id: int) -> list[PaperTag]:
        """Get all paper_tags for a given tag."""
        rows = self._fetchall("SELECT * FROM paper_tags WHERE tag_id=?", (tag_id,))
        return [PaperTag(**dict(r)) for r in rows]

    def delete_paper_tags_by_tag(self, tag_id: int):
        """Delete all canonical paper-tag links for a given tag."""
        self._execute("DELETE FROM paper_tags WHERE tag_id=?", (tag_id,))

    def move_tag_assertions(self, from_tag_id: int, to_tag_id: int):
        """Preserve every raw assertion while changing its canonical tag."""
        self._execute("UPDATE OR IGNORE tag_assertions SET tag_id=? WHERE tag_id=?", (to_tag_id, from_tag_id))
        self._execute("DELETE FROM tag_assertions WHERE tag_id=?", (from_tag_id,))

    def delete_tag_aliases_by_tag(self, tag_id: int):
        """Delete all tag_aliases for a given tag."""
        self._execute("DELETE FROM tag_aliases WHERE tag_id=?", (tag_id,))

    def delete_tag(self, tag_id: int):
        """Delete a tag."""
        self._execute("DELETE FROM tags WHERE id=?", (tag_id,))

    def get_paper_tag_count(self, tag_id: int) -> int:
        """Count how many papers use this tag."""
        row = self._fetchone("SELECT COUNT(*) as c FROM paper_tags WHERE tag_id=?", (tag_id,))
        return row["c"] if row else 0

    def count_tag_aliases(self) -> int:
        row = self._fetchone("SELECT COUNT(*) as c FROM tag_aliases")
        return row["c"] if row else 0

    def count_paper_tags(self) -> int:
        row = self._fetchone("SELECT COUNT(*) as c FROM paper_tags")
        return row["c"] if row else 0

    # ── Equations ───────────────────────────────────────────────────────

    def upsert_equation(self, eq: Equation | None = None, **kwargs) -> int:
        if eq is None:
            eq = Equation(**kwargs)
        cur = self._execute("""INSERT INTO equations (paper_id, run_id, latex_raw, latex_normalized, equation_number,
            section_path, page_number, bbox_json, context_before, context_after, parser, confidence, verification_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (eq.paper_id, eq.run_id, eq.latex_raw, eq.latex_normalized, eq.equation_number,
             eq.section_path, eq.page_number, eq.bbox_json, eq.context_before, eq.context_after, eq.parser, eq.confidence, eq.verification_status))
        return cur.lastrowid

    def get_equations_for_paper(self, paper_id: int, include_superseded: bool = False) -> list[Equation]:
        sql = """SELECT e.* FROM equations e LEFT JOIN processing_runs r ON r.id=e.run_id WHERE e.paper_id=?
            AND (? OR e.run_id IS NULL OR r.status='ok') ORDER BY e.id"""
        rows = self._fetchall(sql, (paper_id, int(include_superseded)))
        return [Equation(**dict(r)) for r in rows]

    def add_variable(self, var: EquationVariable | None = None, **kwargs) -> int:
        if var is None:
            var = EquationVariable(**kwargs)
        cur = self._execute("INSERT INTO equation_variables (equation_id, symbol, meaning, source_page, source_context) VALUES (?,?,?,?,?)",
            (var.equation_id, var.symbol, var.meaning, var.source_page, var.source_context))
        return cur.lastrowid

    def get_variables_for_equation(self, equation_id: int) -> list[EquationVariable]:
        rows = self._fetchall("SELECT * FROM equation_variables WHERE equation_id = ?", (equation_id,))
        return [EquationVariable(**dict(r)) for r in rows]

    # ── Methods ─────────────────────────────────────────────────────────

    def upsert_method(self, m: Method | None = None, **kwargs) -> int:
        if m is None:
            m = Method(**kwargs)
        cur = self._execute("""INSERT INTO methods (paper_id, run_id, name, method_type, purpose, complexity, confidence, card_json, source_passages_json)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (m.paper_id, m.run_id, m.name, m.method_type, m.purpose, m.complexity, m.confidence, m.card_json, m.source_passages_json))
        return cur.lastrowid

    def add_method(self, **kwargs) -> int:
        """Convenience alias for upsert_method with kwargs — matches synthesis/method_cards.py."""
        return self.upsert_method(**kwargs)

    def get_methods_for_paper(self, paper_id: int, include_superseded: bool = False) -> list[Method]:
        sql = """SELECT m.* FROM methods m LEFT JOIN processing_runs r ON r.id=m.run_id WHERE m.paper_id=?
            AND (? OR m.run_id IS NULL OR r.status='ok') ORDER BY m.id"""
        rows = self._fetchall(sql, (paper_id, int(include_superseded)))
        return [Method(**dict(r)) for r in rows]

    def get_methods(self, paper_id: int, method_type: str | None = None) -> list[Method]:
        """Get active methods for a paper, optionally filtered by method_type."""
        if method_type:
            rows = self._fetchall("""SELECT m.* FROM methods m LEFT JOIN processing_runs r ON r.id=m.run_id
                WHERE m.paper_id=? AND m.method_type=? AND (m.run_id IS NULL OR r.status='ok') ORDER BY m.id""", (paper_id, method_type))
        else:
            rows = self._fetchall("""SELECT m.* FROM methods m LEFT JOIN processing_runs r ON r.id=m.run_id
                WHERE m.paper_id=? AND (m.run_id IS NULL OR r.status='ok') ORDER BY m.id""", (paper_id,))
        return [Method(**dict(r)) for r in rows]

    def link_method_equation(self, method_id: int, equation_id: int, role: str):
        self._execute("INSERT OR IGNORE INTO method_equations (method_id, equation_id, role) VALUES (?,?,?)", (method_id, equation_id, role))

    # ── Summaries ───────────────────────────────────────────────────────

    def add_summary(self, s: Summary | None = None, **kwargs) -> int:
        """Stage a run-owned summary; expose it only after its run succeeds."""
        if s is None:
            s = Summary(**kwargs)
        run = self.get_run_by_id(s.run_id) if s.run_id is not None else None
        visible = run is None or run.status == "ok"
        if visible: self._execute("UPDATE summaries SET is_active=0 WHERE paper_id=? AND is_active=1", (s.paper_id,))
        cur = self._execute("""INSERT INTO summaries (paper_id, run_id, model_name, prompt_version, content, is_active)
            VALUES (?,?,?,?,?,?)""", (s.paper_id, s.run_id, s.model_name, s.prompt_version, s.content, int(visible)))
        return cur.lastrowid

    def refresh_active_summary(self, paper_id: int):
        """Atomically expose the newest summary backed by a successful run."""
        with db_transaction(self.conn):
            self._execute("UPDATE summaries SET is_active=0 WHERE paper_id=?", (paper_id,))
            self._execute("""UPDATE summaries SET is_active=1 WHERE id=(
                SELECT s.id FROM summaries s LEFT JOIN processing_runs r ON r.id=s.run_id
                WHERE s.paper_id=? AND (s.run_id IS NULL OR r.status='ok') ORDER BY s.id DESC LIMIT 1)""", (paper_id,))

    def get_active_summary(self, paper_id: int) -> Summary | None:
        row = self._fetchone("""SELECT s.* FROM summaries s LEFT JOIN processing_runs r ON r.id=s.run_id
            WHERE s.paper_id=? AND s.is_active=1 AND (s.run_id IS NULL OR r.status='ok') ORDER BY s.id DESC LIMIT 1""", (paper_id,))
        return Summary(**dict(row)) if row else None

    def list_summaries(self, paper_id: int) -> list[Summary]:
        rows = self._fetchall("SELECT * FROM summaries WHERE paper_id=? ORDER BY id DESC", (paper_id,))
        return [Summary(**dict(r)) for r in rows]

    def deactivate_summaries(self, paper_id: int):
        """Deactivate all active summaries for a paper."""
        self._execute("UPDATE summaries SET is_active=0 WHERE paper_id=? AND is_active=1", (paper_id,))

    def get_summary_history(self, paper_id: int) -> list[Summary]:
        """Get all summary versions for a paper (newest first). Alias for list_summaries."""
        return self.list_summaries(paper_id)

    # ── Context Packs ───────────────────────────────────────────────────

    def save_context_pack(self, cp: ContextPack | None = None, **kwargs) -> int:
        if cp is None:
            cp = ContextPack(**kwargs)
        cur = self._execute("""INSERT INTO context_packs (query, filters_json, selected_units_json, content, output_path)
            VALUES (?,?,?,?,?)""", (cp.query, cp.filters_json, cp.selected_units_json, cp.content, cp.output_path))
        return cur.lastrowid

    def get_context_pack(self, pack_id: int) -> ContextPack | None:
        row = self._fetchone("SELECT * FROM context_packs WHERE id = ?", (pack_id,))
        return ContextPack(**dict(row)) if row else None

    # ── Topics ──────────────────────────────────────────────────────────

    def upsert_topic(self, topic: Topic | None = None, **kwargs) -> int:
        if topic is None:
            topic = Topic(**kwargs)
        row = self._fetchone("SELECT id FROM topics WHERE name = ?", (topic.name,))
        if row:
            if topic.description: self._execute("UPDATE topics SET description=? WHERE id=?", (topic.description, row["id"]))
            return row["id"]
        cur = self._execute("INSERT INTO topics (name, description) VALUES (?,?)", (topic.name, topic.description))
        return cur.lastrowid

    def add_topic(self, name: str, description: str | None = None, **kwargs) -> int:
        """Convenience alias for upsert_topic — matches synthesis/topic_reviews.py."""
        return self.upsert_topic(name=name, description=description)

    def add_topic_paper(self, tp: TopicPaper | None = None, **kwargs) -> None:
        """Add topic-paper association. Accepts TopicPaper object or kwargs."""
        if tp is None:
            tp = TopicPaper(**kwargs)
        self._execute("INSERT OR IGNORE INTO topic_papers (topic_id, paper_id, relevance, match_score) VALUES (?,?,?,?)",
            (tp.topic_id, tp.paper_id, tp.relevance, tp.match_score))

    def save_topic_overview(self, to: TopicOverview | None = None, **kwargs) -> int:
        if to is None:
            to = TopicOverview(**kwargs)
        self._execute("UPDATE topic_overviews SET is_active=0 WHERE topic_id=? AND is_active=1", (to.topic_id,))
        cur = self._execute("""INSERT INTO topic_overviews (topic_id, content, original_query, filters_json, comparison_matrix_json, model_name, prompt_version, is_active)
            VALUES (?,?,?,?,?,?,?,1)""",
            (to.topic_id, to.content, to.original_query, to.filters_json, to.comparison_matrix_json, to.model_name, to.prompt_version))
        return cur.lastrowid

    def add_topic_overview(self, **kwargs) -> int:
        """Convenience alias for save_topic_overview — matches synthesis/topic_reviews.py."""
        return self.save_topic_overview(**kwargs)

    def get_topic(self, topic_id: int) -> Topic | None:
        row = self._fetchone("SELECT * FROM topics WHERE id = ?", (topic_id,))
        return Topic(**dict(row)) if row else None

    def get_topic_by_name(self, name: str) -> Topic | None:
        row = self._fetchone("SELECT * FROM topics WHERE name = ?", (name,))
        return Topic(**dict(row)) if row else None

    def get_topic_papers(self, topic_id: int) -> list[TopicPaper]:
        rows = self._fetchall("SELECT * FROM topic_papers WHERE topic_id = ?", (topic_id,))
        return [TopicPaper(**dict(r)) for r in rows]

    # ── Citations ───────────────────────────────────────────────────────

    def add_citation(self, c: Citation | None = None, **kwargs) -> None:
        if c is None:
            c = Citation(**kwargs)
        self._execute("INSERT OR IGNORE INTO citations (citing_paper_id, cited_doi, cited_title, matched_paper_id) VALUES (?,?,?,?)",
            (c.citing_paper_id, c.cited_doi, c.cited_title, c.matched_paper_id))

    def get_citations_for_paper(self, paper_id: int) -> list[Citation]:
        rows = self._fetchall("SELECT * FROM citations WHERE citing_paper_id = ?", (paper_id,))
        return [Citation(**dict(r)) for r in rows]

    # ── Stats ───────────────────────────────────────────────────────────

    def find_papers_missing(self, field: str) -> list[Paper]:
        """Return papers missing one supported compiled artifact or derived record."""
        queries = {
            "bibtex": "SELECT p.* FROM papers p WHERE p.bibtex_path IS NULL OR p.bibtex_path='' ORDER BY p.id",
            "markdown": "SELECT p.* FROM papers p WHERE p.markdown_path IS NULL OR p.markdown_path='' ORDER BY p.id",
            "json": "SELECT p.* FROM papers p WHERE p.json_path IS NULL OR p.json_path='' ORDER BY p.id",
            "summary": "SELECT p.* FROM papers p WHERE NOT EXISTS (SELECT 1 FROM summaries s WHERE s.paper_id=p.id AND s.is_active=1) ORDER BY p.id",
            "pdf": "SELECT p.* FROM papers p WHERE NOT EXISTS (SELECT 1 FROM paper_files f WHERE f.paper_id=p.id AND f.exists_now=1) ORDER BY p.id",
        }
        if field not in queries: raise ValueError(f"Unknown missing field '{field}'. Expected one of: {', '.join(queries)}")
        return [Paper(**dict(row)) for row in self._fetchall(queries[field])]

    def find_papers_needing_reprocessing(self) -> list[Paper]:
        """Return papers without conversion or whose latest run for an operation failed."""
        rows = self._fetchall("""SELECT p.* FROM papers p WHERE
            NOT EXISTS (SELECT 1 FROM processing_runs ok WHERE ok.paper_id=p.id AND ok.operation='convert' AND ok.status='ok')
            OR EXISTS (SELECT 1 FROM processing_runs failed WHERE failed.paper_id=p.id AND failed.status='failed'
                AND NOT EXISTS (SELECT 1 FROM processing_runs newer WHERE newer.paper_id=failed.paper_id
                    AND newer.operation=failed.operation AND newer.status='ok' AND newer.id>failed.id))
            ORDER BY p.id""")
        return [Paper(**dict(row)) for row in rows]

    def get_status_counts(self) -> dict:
        """Return counts for status dashboard."""
        counts = {}
        counts["papers"] = self._fetchone("SELECT COUNT(*) as c FROM papers")["c"]
        counts["files"] = self._fetchone("SELECT COUNT(*) as c FROM paper_files")["c"]
        counts["search_units"] = self._fetchone("SELECT COUNT(*) as c FROM search_units")["c"]
        counts["tags"] = self._fetchone("SELECT COUNT(*) as c FROM tags")["c"]
        counts["equations"] = self._fetchone("SELECT COUNT(*) as c FROM equations e LEFT JOIN processing_runs r ON r.id=e.run_id WHERE e.run_id IS NULL OR r.status='ok'")["c"]
        counts["methods"] = self._fetchone("SELECT COUNT(*) as c FROM methods m LEFT JOIN processing_runs r ON r.id=m.run_id WHERE m.run_id IS NULL OR r.status='ok'")["c"]
        counts["summaries"] = self._fetchone("SELECT COUNT(*) as c FROM summaries WHERE is_active=1")["c"]
        counts["runs"] = self._fetchone("SELECT COUNT(*) as c FROM processing_runs WHERE status='ok'")["c"]
        counts["topics"] = self._fetchone("SELECT COUNT(*) as c FROM topics")["c"]
        counts["context_packs"] = self._fetchone("SELECT COUNT(*) as c FROM context_packs")["c"]
        # papers with markdown
        counts["with_markdown"] = self._fetchone("SELECT COUNT(*) as c FROM papers WHERE markdown_path IS NOT NULL")["c"]
        counts["with_summary"] = self._fetchone("SELECT COUNT(*) as c FROM summaries WHERE is_active=1")["c"]
        counts["with_doi"] = self._fetchone("SELECT COUNT(*) as c FROM papers WHERE doi IS NOT NULL")["c"]
        return counts

"""PaperDB — stable public API facade for the paper knowledge base.

All CLI, MCP, GUI, and other modules go through this interface.
Architecture rule (D18): CLI/MCP/GUI → PaperDB API → repository/services.
"""
from __future__ import annotations
from typing import Optional
from pathlib import Path
from paperdb.db.connection import get_connection, init_schema, close_connection, db_transaction
from paperdb.db.repository import Repository
from paperdb.db.models import *
from paperdb.paths import get_data_dir, get_db_path

class PaperDB:
    def __init__(self, data_dir: str | None = None, db_path: str | None = None):
        self.data_dir = Path(data_dir).expanduser() if data_dir else get_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path).expanduser() if db_path else self.data_dir / "papers.db"
        self.papers_dir = self.data_dir / "papers"
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.conn = get_connection(self.db_path)
        self.repo = Repository(self.conn)
        init_schema(self.conn)

    # ── Papers ──────────────────────────────────────────────────────────

    def get_paper(self, id_or_key_or_doi: str | int) -> Paper | None:
        if isinstance(id_or_key_or_doi, int):
            return self.repo.get_paper(id_or_key_or_doi)
        p = self.repo.get_paper_by_key(id_or_key_or_doi)
        if p: return p
        p = self.repo.get_paper_by_doi(id_or_key_or_doi)
        if p: return p
        try: return self.repo.get_paper(int(id_or_key_or_doi))
        except ValueError: return None

    def describe_paper(self, id_or_key_or_doi: str | int) -> dict:
        """Return metadata plus derived knowledge and processing provenance."""
        paper = self.get_paper(id_or_key_or_doi)
        if paper is None: return {}
        result = to_serializable(paper)
        result.update({"files": to_serializable(self.repo.get_files_for_paper(paper.id)),
                       "tags": to_serializable(self.repo.get_tags_for_paper(paper.id)), "summary": self.get_summary(paper.id),
                       "processing_runs": to_serializable(self.repo.get_runs_for_paper(paper.id))})
        return result

    def list_papers(self, limit: int = 100, offset: int = 0) -> list[Paper]:
        return self.repo.list_papers(limit, offset)

    def upsert_paper(self, paper: Paper) -> int:
        return self.repo.upsert_paper(paper)

    # ── Files ───────────────────────────────────────────────────────────

    def add_file(self, paper_id: int, path: str, role: str | None = None, sha256: str | None = None,
                 file_size: int | None = None, modified_time: float | None = None) -> int:
        pf = PaperFile(paper_id=paper_id, path=path, file_role=role, sha256=sha256, file_size=file_size, modified_time=modified_time)
        return self.repo.add_paper_file(pf)

    def get_files(self, paper_id: int) -> list[PaperFile]:
        return self.repo.get_files_for_paper(paper_id)

    def set_preferred_file(self, paper_id: int, file_id: int):
        self.repo.set_preferred_file(paper_id, file_id)

    # ── Search (delegates to search/ module) ───────────────────────────

    def search(self, query: str, required_tags: list | None = None, preferred_tags: list | None = None,
               excluded_tags: list | None = None, year_range: tuple | None = None,
               limit: int = 20, explain: bool = False) -> list[dict]:
        from paperdb.search.ranking import search as _search
        results = _search(query, self.repo, required_tags=required_tags, preferred_tags=preferred_tags,
                          excluded_tags=excluded_tags, year_range=year_range, limit=limit, explain=explain)
        # Convert SearchResult dataclass objects to dicts for CLI/MCP consumers
        out = []
        for r in results:
            p = r.paper
            paper_dict = {
                'id': getattr(p, 'id', None),
                'paper_key': getattr(p, 'paper_key', ''),
                'title': getattr(p, 'title', ''),
                'year': getattr(p, 'year', None),
                'authors_text': getattr(p, 'authors_text', ''),
                'essence': getattr(p, 'essence', ''),
                'abstract': getattr(p, 'abstract', ''),
                'doi': getattr(p, 'doi', None),
            }
            out.append({
                'paper': paper_dict,
                'score': r.score,
                'breakdown': r.breakdown,
                'matching_units': r.matching_units if explain else [],
                # Flatten key fields for easy access by CLI/MCP
                'paper_key': paper_dict['paper_key'],
                'title': paper_dict['title'],
                'year': paper_dict['year'],
                'id': paper_dict['id'],
            })
        return out

    def retrieve_context(self, query: str, token_budget: int = 24000, include: list | None = None,
                         filters: dict | None = None, save: bool = False):
        from paperdb.search.context import assemble_context_pack
        pack = assemble_context_pack(query, self.repo, token_budget=token_budget, include=include, filters=filters)
        if save: pack.id = self.repo.save_context_pack(query=pack.query, filters_json=pack.filters_json, selected_units_json=pack.selected_units_json, content=pack.content, output_path=pack.output_path)
        return pack

    # ── Processing (delegates to ingest/ module) ──────────────────────

    def scan_folder(self, path: str, recursive: bool = True):
        from paperdb.ingest.scanner import scan_folder as _scan
        return _scan(path, recursive=recursive, repo=self.repo)

    def ingest_paper(self, paper_id: int, operations: list | None = None, llm_config=None, force=False):
        from paperdb.ingest.pipeline import ingest_paper as _ingest
        # Accept paper_key string and resolve to ID
        if isinstance(paper_id, str):
            paper_id = self._resolve_paper_id(paper_id)
            if paper_id is None:
                return {"errors": [f"Paper not found"]}
        return _ingest(paper_id, self.repo, operations=operations, llm_config=llm_config, force=force, data_dir=str(self.papers_dir))

    def ingest_folder(self, folder: str, operations: list | None = None, llm_config=None, force=False):
        """Scan a folder for PDFs, index them, then ingest all newly indexed papers."""
        from paperdb.ingest.scanner import scan_folder as _scan
        from paperdb.ingest.jobs import ingest_batch as _batch
        count = _scan(folder, recursive=True, repo=self.repo)
        # Find all papers that have files but no successful runs
        all_papers = self.repo.list_papers(limit=100000)
        paper_ids = [p.id for p in all_papers]
        return _batch(paper_ids, self.repo, operations=operations, llm_config=llm_config, force=force, data_dir=str(self.papers_dir))

    def ingest_all(self, operations: list | None = None, llm_config=None, force=False):
        """Ingest all papers in the database that haven't been processed yet."""
        from paperdb.ingest.jobs import ingest_batch as _batch
        all_papers = self.repo.list_papers(limit=100000)
        paper_ids = [p.id for p in all_papers]
        return _batch(paper_ids, self.repo, operations=operations, llm_config=llm_config, force=force, data_dir=str(self.papers_dir))

    def sync(self, folder: str | None = None, llm_config=None):
        """Scan one explicit source folder and process new or changed papers."""
        if folder is None: raise ValueError("sync requires a source PDF folder; generated PaperDB artifacts are not source PDFs")
        self.scan_folder(folder, recursive=True)
        return self.ingest_all(llm_config=llm_config)

    def add_paper(self, path_or_url_or_doi: str, dest_dir: str | None = None):
        from paperdb.ingest.fetch import add_paper_from_source
        return add_paper_from_source(path_or_url_or_doi, self.repo, dest_dir=dest_dir, artifact_dir=str(self.papers_dir))

    def get_processing_status(self, paper_id: int) -> dict:
        """Return the newest recorded status for each operation."""
        status = {}
        for run in self.repo.get_runs_for_paper(paper_id): status.setdefault(run.operation, run.status)
        return status

    # ── Content access ──────────────────────────────────────────────────

    def _resolve_paper_id(self, id_or_key_or_doi: str | int) -> int | None:
        """Resolve a paper key, DOI, or numeric ID to a paper ID. Returns None if not found."""
        if isinstance(id_or_key_or_doi, int):
            return id_or_key_or_doi
        p = self.repo.get_paper_by_key(id_or_key_or_doi)
        if p: return p.id
        p = self.repo.get_paper_by_doi(id_or_key_or_doi)
        if p: return p.id
        # Maybe it's a numeric string
        try:
            return int(id_or_key_or_doi)
        except (ValueError, TypeError):
            return None

    def get_markdown(self, id_or_key_or_doi: str | int) -> str:
        pid = self._resolve_paper_id(id_or_key_or_doi)
        if pid is None: return ""
        p = self.repo.get_paper(pid)
        if not p or not p.markdown_path:
            return ""
        import pathlib
        mp = pathlib.Path(p.markdown_path)
        if not mp.exists():
            return ""
        return mp.read_text(encoding="utf-8")

    def get_json(self, id_or_key_or_doi: str | int) -> dict:
        pid = self._resolve_paper_id(id_or_key_or_doi)
        p = self.repo.get_paper(pid) if pid is not None else None
        if not p or not p.json_path or not Path(p.json_path).exists(): return {}
        import json
        return json.loads(Path(p.json_path).read_text(encoding="utf-8"))

    def get_bibtex(self, id_or_key_or_doi: str | int) -> str:
        pid = self._resolve_paper_id(id_or_key_or_doi)
        p = self.repo.get_paper(pid) if pid is not None else None
        if not p or not p.bibtex_path or not Path(p.bibtex_path).exists(): return ""
        return Path(p.bibtex_path).read_text(encoding="utf-8")

    def get_equations(self, id_or_key_or_doi: str | int) -> list[Equation]:
        pid = self._resolve_paper_id(id_or_key_or_doi)
        if pid is None: return []
        return self.repo.get_equations_for_paper(pid)

    def get_equation_variables(self, equation_id: int) -> list[EquationVariable]:
        return self.repo.get_variables_for_equation(equation_id)

    def get_methods(self, id_or_key_or_doi: str | int) -> list[Method]:
        pid = self._resolve_paper_id(id_or_key_or_doi)
        if pid is None: return []
        return self.repo.get_methods_for_paper(pid)

    def get_tags(self, paper_id: int) -> list[Tag]:
        return self.repo.get_tags_for_paper(paper_id)

    def get_summary(self, paper_id: int) -> str:
        s = self.repo.get_active_summary(paper_id)
        return s.content if s else ""

    # ── Taxonomy (delegates to taxonomy/ module) ──────────────────────

    def add_user_tags(self, paper_id: int, tags: list[str]) -> None:
        """Attach explicit user assertions, accepting ``category:name`` syntax."""
        if self.repo.get_paper(paper_id) is None: raise ValueError(f"Paper {paper_id} not found")
        for value in tags:
            category, name = value.split(':', 1) if ':' in value else ('user', value)
            canonical = name.strip().replace('_', ' ')
            tag_id = self.repo.upsert_tag(canonical_name=canonical, category=category.strip())
            self.repo.add_alias(tag_id=tag_id, alias=name, normalized_alias=name.lower().strip())
            self.repo.add_paper_tag(paper_id=paper_id, tag_id=tag_id, source='user', raw_name=value, confidence=1.0)

    def list_tags(self, category: str | None = None) -> list[Tag]:
        return self.repo.list_all_tags(category)

    def merge_tags(self, canonical: str, alias: str):
        from paperdb.taxonomy.aliases import merge_tags as _merge
        # Resolve canonical and alias to tag_ids
        canon_tag = self.repo.get_tag_by_name(canonical) or self.repo.resolve_alias(canonical.lower().strip())
        alias_tag = self.repo.get_tag_by_name(alias) or self.repo.resolve_alias(alias.lower().strip())
        if canon_tag is None or alias_tag is None:
            raise ValueError(f"Could not resolve tags: canonical='{canonical}', alias='{alias}'")
        _merge(canon_tag.id, alias_tag.id, self.repo)
        return f"Merged '{alias}' into '{canonical}'"

    # ── Synthesis (delegates to synthesis/ module) ────────────────────

    def get_tag_aliases(self, tag_name: str) -> list[TagAlias]:
        tag = self.repo.get_tag_by_name(tag_name) or self.repo.resolve_alias(tag_name.lower().strip())
        return self.repo.get_tag_aliases(tag.id) if tag else []

    def get_context_pack(self, context_id: int) -> ContextPack | None:
        return self.repo.get_context_pack(context_id)

    def build_topic_review(self, topic: str, focus: str | None = None, constraints: dict | None = None,
                           max_papers: int = 30, llm_config=None):
        from paperdb.synthesis.topic_reviews import build_topic_review as _build
        return _build(topic, self.repo, db=self, focus=focus, constraints=constraints,
                      max_papers=max_papers, llm_config=llm_config)

    def compare_methods(self, topic: str, axes: list[str], constraints: dict | None = None, max_papers: int = 20, llm_config=None):
        from paperdb.synthesis.topic_reviews import build_topic_review
        return build_topic_review(topic, self.repo, db=self, constraints=constraints, max_papers=max_papers, llm_config=llm_config, comparison_axes=axes)

    def get_related(self, id_or_key_or_doi: str | int, limit: int = 5) -> list[dict]:
        pid = self._resolve_paper_id(id_or_key_or_doi)
        if pid is None: return []
        tags = self.repo.get_tags_for_paper(pid)
        if not tags:
            return []
        tag_names = [f"{t.category}:{t.canonical_name}" for t in tags]
        results = self.search("", preferred_tags=tag_names, limit=limit + 1)
        return [r for r in results if r.get('id') != pid][:limit]

    def export_bibtex(self) -> str:
        import pathlib
        parts = []
        for p in self.repo.list_papers(limit=10000):
            if p.bibtex_path and pathlib.Path(p.bibtex_path).exists():
                parts.append(pathlib.Path(p.bibtex_path).read_text(encoding='utf-8'))
            else:
                key = p.paper_key or f"paper_{p.id}"
                parts.append(f"@article{{{key},\n  title = {{{p.title or ''}}},\n  author = {{{p.authors_text or ''}}},\n  year = {{{p.year or ''}}},\n}}\n")
        return '\n'.join(parts)

    def reindex(self, operations: list, llm_config=None, force=True):
        """Re-run specific operations on all papers."""
        from paperdb.ingest.jobs import ingest_batch as _batch
        all_papers = self.repo.list_papers(limit=100000)
        paper_ids = [p.id for p in all_papers]
        return _batch(paper_ids, self.repo, operations=operations, llm_config=llm_config, force=force, data_dir=str(self.papers_dir))

    # ── Status ──────────────────────────────────────────────────────────

    def status(self, missing: str | None = None, needs_reprocessing: bool = False) -> dict:
        result = self.repo.get_status_counts()
        if missing: result["missing"] = to_serializable(self.repo.find_papers_missing(missing))
        if needs_reprocessing: result["needs_reprocessing"] = to_serializable(self.repo.find_papers_needing_reprocessing())
        return result

    # ── Migration ───────────────────────────────────────────────────────

    def migrate_from_db(self, legacy_db_path: str):
        from paperdb.ingest.migration import migrate_legacy
        return migrate_legacy(legacy_db_path, self.repo, str(self.data_dir))

    def migrate_from_mendeley(self, bibtex_path: str):
        from paperdb.ingest.scanner import scan_mendeley
        return scan_mendeley(bibtex_path, str(self.papers_dir), repo=self.repo)

    # ── Cleanup ─────────────────────────────────────────────────────────

    def close(self):
        close_connection(self.conn)

"""Durable, independently resumable PDF ingestion pipeline."""
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

from .jobs import find_equivalent_run, finish_job, run_job, _model_name
from ..db.models import to_serializable
from ..extract.base import ExtractionResult
from ..extract.docling_backend import DoclingParser
from ..extract.equations import extract_equations
from ..extract.methods import extract_methods
from ..synthesis.summaries import compile_markdown, source_markdown

logger = logging.getLogger(__name__)
DEFAULT_OPERATIONS = ["convert", "equations", "methods", "summarize", "tag", "files", "search_units"]


def _compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""): h.update(chunk)
    return h.hexdigest()


def _atomic_write(path: str, content: str) -> None:
    """Atomically replace a non-empty UTF-8 artifact in its target directory."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    if tmp.stat().st_size == 0:
        tmp.unlink()
        raise RuntimeError(f"Atomic write failed: empty content for {path}")
    os.replace(tmp, target)


def _atomic_write_json(path: str, obj: dict) -> None:
    _atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _config_hash(config: Optional[dict]) -> str:
    if not config: return ""
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]


def _equivalent(paper_id, operation, input_hash, backend, config, llm_config, prompt_version, repo, force):
    if force: return None
    return find_equivalent_run(paper_id, operation, input_hash, backend, _config_hash(config),
                               _model_name(llm_config), prompt_version, repo)


def _load_extraction(json_path: str, markdown: str) -> ExtractionResult | None:
    if not os.path.exists(json_path): return None
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    extraction = data.get("extraction")
    if not extraction: return None
    structured = dict(extraction.get("structured_json", {}))
    if extraction.get("metadata", {}).get("backend") == "markdown_fallback": structured["markdown"] = markdown
    return ExtractionResult(markdown=markdown,
                            structured_json=structured,
                            equations=extraction.get("equations", []),
                            sections=extraction.get("sections", []),
                            tables=extraction.get("tables", []),
                            metadata=extraction.get("metadata", {}))


def ingest_paper(paper_id: int, repo, operations=None, llm_config=None, force=False,
                 data_dir: Optional[str] = None, keep_debug: bool = False) -> dict:
    """Run requested operations using persisted artifacts from prior operations."""
    ops = operations or list(DEFAULT_OPERATIONS)
    result = {"paper_id": paper_id, "operations_run": [], "operations_skipped": [], "errors": []}
    paper = repo.get_paper(paper_id)
    if not paper:
        result["errors"].append(f"Paper {paper_id} not found")
        return result
    files = repo.get_files_for_paper(paper_id)
    preferred = next((f for f in files if f.is_preferred), files[0] if files else None)
    preferred_available = preferred is not None and os.path.exists(preferred.path)
    source_file_id = preferred.id if preferred_available else None
    input_hash = (preferred.sha256 or _compute_sha256(preferred.path)) if preferred_available else ""
    data_dir = data_dir or str(__import__("paperdb.paths", fromlist=["get_papers_dir"]).get_papers_dir())
    out_dir = os.path.join(data_dir, str(paper.year or "unknown"))
    base = f"{paper.paper_key or f'p{paper_id:04d}'}__p{paper_id:04d}"
    md_path = os.path.join(out_dir, base + ".md")
    json_path = os.path.join(out_dir, base + ".json")
    bib_path = os.path.join(out_dir, base + ".bib")

    markdown = Path(paper.markdown_path).read_text(encoding="utf-8", errors="replace") if paper.markdown_path and os.path.exists(paper.markdown_path) else ""
    source_text = source_markdown(markdown)
    extraction = _load_extraction(paper.json_path, source_text) if paper.json_path else None

    if "convert" in ops and not preferred_available:
        detail = f"PDF not found on disk: {preferred.path}" if preferred else f"No PDF file found for paper {paper_id}"
        result["errors"].append(f"convert: {detail}")

    if "convert" in ops and preferred_available:
        config = {"backend": "docling"}
        existing = _equivalent(paper_id, "convert", input_hash, "docling", config, False, None, repo, force)
        if existing and source_text and extraction:
            result["operations_skipped"].append("convert")
        else:
            run_id = run_job(paper_id, "convert", "docling", config, repo, llm_config=False, input_sha256=input_hash, source_file_id=source_file_id, prompt_version=None)
            try:
                parser = DoclingParser(debug_dir=os.path.join(Path(data_dir).parent, "logs", "debug") if keep_debug else None)
                extraction = parser.parse(preferred.path, keep_debug=keep_debug)
                source_text = extraction.markdown
                active_summary = repo.get_active_summary(paper_id)
                markdown = compile_markdown(source_text, active_summary.content if active_summary else None,
                                            active_summary.prompt_version if active_summary else "v1")
                _atomic_write(md_path, markdown)
                paper.markdown_path = md_path
                paper.json_path = json_path
                repo.update_paper_paths(paper_id=paper_id, markdown_path=md_path, json_path=json_path)
                _generate_json_file(paper, repo.get_equations_for_paper(paper_id), repo, json_path, extraction)
                finish_job(run_id, "ok", repo, output_path=md_path)
                result["operations_run"].append("convert")
            except Exception as exc:
                finish_job(run_id, "failed", repo, message=str(exc))
                result["errors"].append(f"convert: {exc}")
                logger.error("Convert failed for paper %s: %s", paper_id, exc, exc_info=True)
                return result

    if not source_text and paper.markdown_path and os.path.exists(paper.markdown_path):
        markdown = Path(paper.markdown_path).read_text(encoding="utf-8", errors="replace")
        source_text = source_markdown(markdown)
    if extraction is None and source_text:
        extraction = ExtractionResult(markdown=source_text, structured_json={"markdown": source_text}, metadata={"backend": "markdown_fallback"})

    source_hash = hashlib.sha256(source_text.encode()).hexdigest() if source_text else ""
    extraction_hash = hashlib.sha256(json.dumps(to_serializable(extraction), sort_keys=True, default=str).encode()).hexdigest() if extraction else ""
    equations = repo.get_equations_for_paper(paper_id)
    if "equations" in ops:
        if extraction is None:
            result["errors"].append("equations: no persisted conversion artifact or Markdown source")
        else:
            config = {"parser": extraction.metadata.get("backend", "docling")}
            existing = _equivalent(paper_id, "equations", extraction_hash, "docling", config, False, None, repo, force)
            if existing:
                result["operations_skipped"].append("equations")
            else:
                run_id = run_job(paper_id, "equations", "docling", config, repo, llm_config=False, input_sha256=extraction_hash, source_file_id=source_file_id, prompt_version=None)
                try:
                    structured = dict(extraction.structured_json)
                    structured.update({"equations": extraction.equations, "markdown": source_text})
                    extract_equations(structured, paper_id, run_id, repo)
                    finish_job(run_id, "ok", repo)
                    equations = repo.get_equations_for_paper(paper_id)
                    result["operations_run"].append("equations")
                except Exception as exc:
                    finish_job(run_id, "failed", repo, message=str(exc))
                    result["errors"].append(f"equations: {exc}")

    methods_input_hash = hashlib.sha256((source_hash + json.dumps(to_serializable(equations), sort_keys=True, default=str)).encode()).hexdigest()
    if "methods" in ops:
        if not source_text:
            result["errors"].append("methods: no Markdown source")
        else:
            model = _model_name(llm_config)
            backend = "llm" if llm_config is not False else "regex"
            config = {"llm": model or "default", "prompt_version": "v1"}
            existing = _equivalent(paper_id, "methods", methods_input_hash, backend, config, llm_config, "v1", repo, force)
            if existing:
                result["operations_skipped"].append("methods")
            else:
                run_id = run_job(paper_id, "methods", backend, config, repo, llm_config, methods_input_hash, source_file_id)
                try:
                    extract_methods(source_text, to_serializable(equations), paper_id, run_id, repo, llm_config)
                    finish_job(run_id, "ok", repo)
                    result["operations_run"].append("methods")
                except Exception as exc:
                    finish_job(run_id, "failed", repo, message=str(exc))
                    result["errors"].append(f"methods: {exc}")

    if "summarize" in ops:
        if not source_text:
            result["errors"].append("summarize: no Markdown source")
        else:
            from ..synthesis.summaries import generate_summary
            config = {"llm": _model_name(llm_config) or "default", "prompt_version": "v1"}
            existing = _equivalent(paper_id, "summarize", source_hash, "llm", config, llm_config, "v1", repo, force)
            if existing:
                result["operations_skipped"].append("summarize")
            else:
                run_id = run_job(paper_id, "summarize", "llm", config, repo, llm_config, source_hash, source_file_id)
                try:
                    summary = generate_summary(source_text, paper_id, run_id, repo, llm_config)
                    markdown = compile_markdown(source_text, summary)
                    _atomic_write(md_path, markdown)
                    paper.markdown_path = md_path
                    repo.update_paper_paths(paper_id=paper_id, markdown_path=md_path)
                    finish_job(run_id, "ok", repo, output_path=md_path)
                    result["operations_run"].append("summarize")
                except Exception as exc:
                    finish_job(run_id, "failed", repo, message=str(exc))
                    result["errors"].append(f"summarize: {exc}")

    if "tag" in ops:
        if not source_text:
            result["errors"].append("tag: no Markdown source")
        else:
            from ..taxonomy.extraction import extract_tags
            config = {"llm": _model_name(llm_config) or "default", "prompt_version": "v1"}
            existing = _equivalent(paper_id, "tag", source_hash, "llm", config, llm_config, "v1", repo, force)
            if existing:
                result["operations_skipped"].append("tag")
            else:
                run_id = run_job(paper_id, "tag", "llm", config, repo, llm_config, source_hash, source_file_id)
                try:
                    extract_tags(source_text, paper_id, run_id, repo, llm_config)
                    finish_job(run_id, "ok", repo)
                    result["operations_run"].append("tag")
                except Exception as exc:
                    finish_job(run_id, "failed", repo, message=str(exc))
                    result["errors"].append(f"tag: {exc}")

    structured_changed = any(operation in result["operations_run"] for operation in ("convert", "equations", "methods", "summarize"))
    if "search_units" in ops or structured_changed:
        if not markdown:
            result["errors"].append("search_units: no compiled Markdown")
        else:
            from ..search.fts import build_search_units_from_markdown
            active_equations = repo.get_equations_for_paper(paper_id)
            active_methods = repo.get_methods_for_paper(paper_id)
            search_payload = markdown + json.dumps(to_serializable(active_equations), sort_keys=True, default=str) + json.dumps(to_serializable(active_methods), sort_keys=True, default=str)
            search_hash = hashlib.sha256(search_payload.encode()).hexdigest()
            config = {"splitter": "markdown_and_structured_v2"}
            existing = _equivalent(paper_id, "search_units", search_hash, "internal", config, False, None, repo, force)
            if existing:
                if "search_units" in ops: result["operations_skipped"].append("search_units")
            else:
                run_id = run_job(paper_id, "search_units", "internal", config, repo, llm_config=False, input_sha256=search_hash, prompt_version=None)
                try:
                    build_search_units_from_markdown(paper_id, markdown, run_id, repo, equations=active_equations, methods=active_methods)
                    finish_job(run_id, "ok", repo)
                    result["operations_run"].append("search_units")
                except Exception as exc:
                    finish_job(run_id, "failed", repo, message=str(exc))
                    result["errors"].append(f"search_units: {exc}")

    artifacts_missing = not os.path.exists(json_path) or not os.path.exists(bib_path)
    knowledge_changed = bool(result["operations_run"])
    if "files" in ops or knowledge_changed:
        if force or artifacts_missing or knowledge_changed:
            try:
                paper = repo.get_paper(paper_id)
                _generate_json_file(paper, repo.get_equations_for_paper(paper_id), repo, json_path, extraction)
                _generate_bib_file(paper, bib_path)
                repo.update_paper_paths(paper_id=paper_id, json_path=json_path, bibtex_path=bib_path)
                if "files" in ops: result["operations_run"].append("files")
            except Exception as exc:
                result["errors"].append(f"files: {exc}")
        elif "files" in ops:
            result["operations_skipped"].append("files")
    return result


def _generate_json_file(paper, equations: list, repo, json_path: str, extraction: ExtractionResult | None = None) -> None:
    """Generate the structured companion while preserving conversion evidence."""
    existing = {}
    if os.path.exists(json_path):
        existing = json.loads(Path(json_path).read_text(encoding="utf-8"))
    tags = repo.get_tags_for_paper(paper.id)
    tag_map = {}
    for tag in tags: tag_map.setdefault(tag.category, []).append(tag.canonical_name)
    methods = repo.get_methods_for_paper(paper.id)
    obj = {
        "paper_id": paper.id, "paper_key": paper.paper_key,
        "identifiers": {"doi": paper.doi, "arxiv_id": paper.arxiv_id},
        "title": paper.title, "authors": paper.authors_text, "year": paper.year, "journal": paper.journal,
        "tags": tag_map, "equations": to_serializable(equations), "methods": to_serializable(methods),
        "summary": to_serializable(repo.get_active_summary(paper.id)),
        "processing_runs": to_serializable(repo.get_runs_for_paper(paper.id)),
        "extraction": existing.get("extraction"),
    }
    if extraction is not None:
        obj["extraction"] = {"structured_json": extraction.structured_json, "equations": extraction.equations,
                             "sections": extraction.sections, "tables": extraction.tables, "metadata": extraction.metadata}
    _atomic_write_json(json_path, obj)


def _generate_bib_file(paper, bib_path: str) -> None:
    """Preserve imported BibTeX; generate a minimal record only when none exists."""
    if paper.bibtex_path and os.path.exists(paper.bibtex_path):
        if os.path.abspath(paper.bibtex_path) == os.path.abspath(bib_path): return
        _atomic_write(bib_path, Path(paper.bibtex_path).read_text(encoding="utf-8"))
        return
    key = paper.paper_key or f"p{paper.id:04d}"
    fields = [f"  title = {{{paper.title}}}," if paper.title else "",
              f"  author = {{{paper.authors_text}}}," if paper.authors_text else "",
              f"  year = {{{paper.year}}}," if paper.year else "",
              f"  journal = {{{paper.journal}}}," if paper.journal else "",
              f"  doi = {{{paper.doi}}}," if paper.doi else "",
              f"  eprint = {{{paper.arxiv_id}}}," if paper.arxiv_id else ""]
    _atomic_write(bib_path, "@article{" + key + ",\n" + "\n".join(f for f in fields if f) + "\n}\n")

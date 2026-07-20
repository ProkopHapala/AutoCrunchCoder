"""Ingest pipeline — orchestrates full paper ingestion.

Orchestrates: convert → extract equations → extract methods → summarize → tag →
generate .json/.bib → build search units.

Skip logic: operations with an equivalent successful processing_run are skipped
(same operation + input_sha256 + backend + config_hash + model + prompt).
Use force=True to re-run regardless.

If Task 6 modules (taxonomy.extraction, synthesis.summaries) are not available,
those steps are skipped with a warning. The pipeline still works for
convert + equation extraction without LLM steps.
"""
import os, json, hashlib, logging, tempfile
from pathlib import Path
from typing import Optional

from .jobs import find_equivalent_run, run_job
from ..extract.docling_backend import DoclingParser
from ..extract.equations import extract_equations
from ..extract.methods import extract_methods

logger = logging.getLogger(__name__)

# Default operations in order
DEFAULT_OPERATIONS = ["convert", "equations", "methods", "summarize", "tag", "files", "search_units"]


def _compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write(path: str, content: str) -> None:
    """Write file atomically: temp → validate → rename."""
    tmp = path + ".tmp"
    Path(tmp).write_text(content)
    # Validate: file is non-empty
    if os.path.getsize(tmp) == 0:
        os.unlink(tmp)
        raise RuntimeError(f"Atomic write failed: empty content for {path}")
    os.replace(tmp, path)


def _atomic_write_json(path: str, obj: dict) -> None:
    _atomic_write(path, json.dumps(obj, indent=2, default=str))


def _config_hash(config: Optional[dict]) -> str:
    if not config:
        return ""
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]


def ingest_paper(paper_id: int, repo, operations=None, llm_config=None, force=False,
                 data_dir: Optional[str] = None, keep_debug: bool = False) -> dict:
    """Orchestrate full ingestion for a single paper.

    Args:
        paper_id: paper ID in the database
        repo: Repository instance
        operations: list of operation names to run (default: all)
        llm_config: dict with 'template_name' for LLM-based steps, or None
        force: if True, re-run all operations regardless of existing runs
        data_dir: paperdb data directory (for writing .md/.json/.bib)
        keep_debug: save raw parser debug output

    Returns:
        {paper_id, operations_run, operations_skipped, errors}
    """
    ops = operations or list(DEFAULT_OPERATIONS)
    result = {"paper_id": paper_id, "operations_run": [], "operations_skipped": [], "errors": []}

    # Get paper record
    paper = repo.get_paper(paper_id)
    if not paper:
        result["errors"].append(f"Paper {paper_id} not found")
        return result

    # Get preferred PDF file
    files = repo.get_files_for_paper(paper_id)
    preferred = [f for f in files if f.is_preferred]
    pdf_file = preferred[0] if preferred else (files[0] if files else None)
    if not pdf_file:
        result["errors"].append(f"No PDF file found for paper {paper_id}")
        return result

    pdf_path = pdf_file.path
    if not os.path.exists(pdf_path):
        result["errors"].append(f"PDF not found on disk: {pdf_path}")
        return result

    input_sha256 = pdf_file.sha256 or _compute_sha256(pdf_path)

    # Determine output paths
    if data_dir is None:
        from ..paths import get_papers_dir
        data_dir = str(get_papers_dir())
    year = paper.year or "unknown"
    paper_key = paper.paper_key or f"p{paper_id:04d}"
    out_dir = os.path.join(data_dir, str(year))
    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, f"{paper_key}__p{paper_id:04d}.md")
    json_path = os.path.join(out_dir, f"{paper_key}__p{paper_id:04d}.json")
    bib_path = os.path.join(out_dir, f"{paper_key}__p{paper_id:04d}.bib")

    # Step 1: Convert
    extraction_result = None
    markdown_text = None
    if "convert" in ops:
        cfg_hash = _config_hash({"backend": "docling"})
        existing = None if force else find_equivalent_run(
            paper_id, "convert", input_sha256, "docling", cfg_hash, None, None, repo)
        if existing:
            result["operations_skipped"].append("convert")
            # Load existing markdown
            if paper.markdown_path and os.path.exists(paper.markdown_path):
                markdown_text = Path(paper.markdown_path).read_text(errors="replace")
        else:
            run_id = run_job(paper_id, "convert", "docling", {"backend": "docling"}, repo, llm_config)
            try:
                parser = DoclingParser(debug_dir=os.path.join(data_dir, "..", "logs", "debug") if keep_debug else None)
                extraction_result = parser.parse(pdf_path, keep_debug=keep_debug)
                markdown_text = extraction_result.markdown
                _atomic_write(md_path, markdown_text)
                repo.update_paper_paths(paper_id, markdown_path=md_path)
                repo.finish_run(run_id, status="ok", output_path=md_path)
                result["operations_run"].append("convert")
            except Exception as e:
                repo.finish_run(run_id, status="failed", message=str(e))
                result["errors"].append(f"convert: {e}")
                logger.error(f"Convert failed for paper {paper_id}: {e}", exc_info=True)
                return result  # Can't proceed without markdown

    # Step 2: Extract equations
    equations = []
    if "equations" in ops and extraction_result:
        cfg_hash = _config_hash({"parser": "docling"})
        existing = None if force else find_equivalent_run(
            paper_id, "equations", input_sha256, "docling", cfg_hash, None, None, repo)
        if existing:
            result["operations_skipped"].append("equations")
            equations = repo.get_equations_for_paper(paper_id)
        else:
            run_id = run_job(paper_id, "equations", "docling", {"parser": "docling"}, repo, llm_config)
            try:
                structured = extraction_result.structured_json
                structured["equations"] = extraction_result.equations
                structured["markdown"] = extraction_result.markdown
                equations = extract_equations(structured, paper_id, run_id, repo)
                repo.finish_run(run_id, status="ok")
                result["operations_run"].append("equations")
            except Exception as e:
                repo.finish_run(run_id, status="failed", message=str(e))
                result["errors"].append(f"equations: {e}")
                logger.error(f"Equation extraction failed for paper {paper_id}: {e}", exc_info=True)

    # Step 3: Extract methods
    if "methods" in ops and markdown_text:
        model = llm_config.get("template_name") if llm_config else None
        cfg_hash = _config_hash({"llm": model})
        existing = None if force else find_equivalent_run(
            paper_id, "methods", input_sha256, "llm" if model else "regex", cfg_hash, model, "v1", repo)
        if existing:
            result["operations_skipped"].append("methods")
        else:
            run_id = run_job(paper_id, "methods", "llm" if model else "regex",
                             {"llm": model}, repo, llm_config)
            try:
                extract_methods(markdown_text, equations, paper_id, run_id, repo, llm_config)
                repo.finish_run(run_id, status="ok")
                result["operations_run"].append("methods")
            except Exception as e:
                repo.finish_run(run_id, status="failed", message=str(e))
                result["errors"].append(f"methods: {e}")
                logger.error(f"Method extraction failed for paper {paper_id}: {e}", exc_info=True)

    # Step 4: Summarize (Task 6 — optional)
    if "summarize" in ops:
        try:
            from ..synthesis.summaries import generate_summary
            model = llm_config.get("template_name") if llm_config else None
            cfg_hash = _config_hash({"llm": model})
            existing = None if force else find_equivalent_run(
                paper_id, "summarize", input_sha256, "llm", cfg_hash, model, "v1", repo)
            if existing:
                result["operations_skipped"].append("summarize")
            else:
                run_id = run_job(paper_id, "summarize", "llm", {"llm": model}, repo, llm_config)
                try:
                    summary = generate_summary(markdown_text or "", paper_id, run_id, repo, llm_config)
                    repo.finish_run(run_id, status="ok")
                    result["operations_run"].append("summarize")
                except Exception as e:
                    repo.finish_run(run_id, status="failed", message=str(e))
                    result["errors"].append(f"summarize: {e}")
        except ImportError:
            logger.info("synthesis.summaries not available — skipping summarize step")

    # Step 5: Tag extraction (Task 6 — optional)
    if "tag" in ops:
        try:
            from ..taxonomy.extraction import extract_tags
            model = llm_config.get("template_name") if llm_config else None
            cfg_hash = _config_hash({"llm": model})
            existing = None if force else find_equivalent_run(
                paper_id, "tag", input_sha256, "llm", cfg_hash, model, "v1", repo)
            if existing:
                result["operations_skipped"].append("tag")
            else:
                run_id = run_job(paper_id, "tag", "llm", {"llm": model}, repo, llm_config)
                try:
                    extract_tags(markdown_text or "", paper_id, run_id, repo, llm_config)
                    repo.finish_run(run_id, status="ok")
                    result["operations_run"].append("tag")
                except Exception as e:
                    repo.finish_run(run_id, status="failed", message=str(e))
                    result["errors"].append(f"tag: {e}")
        except ImportError:
            logger.info("taxonomy.extraction not available — skipping tag step")

    # Step 6: Generate .json and .bib files
    if "files" in ops:
        try:
            _generate_json_file(paper, equations, repo, json_path)
            repo.update_paper_paths(paper_id, json_path=json_path)
            _generate_bib_file(paper, bib_path)
            repo.update_paper_paths(paper_id, bibtex_path=bib_path)
            result["operations_run"].append("files")
        except Exception as e:
            result["errors"].append(f"files: {e}")
            logger.error(f"File generation failed for paper {paper_id}: {e}", exc_info=True)

    # Step 7: Build search units (Task 3 — optional)
    if "search_units" in ops and markdown_text:
        try:
            from ..search.fts import build_search_units_from_markdown
            run_id = run_job(paper_id, "search_units", "internal", {}, repo, llm_config)
            try:
                build_search_units_from_markdown(paper_id, markdown_text, run_id, repo)
                repo.finish_run(run_id, status="ok")
                result["operations_run"].append("search_units")
            except Exception as e:
                repo.finish_run(run_id, status="failed", message=str(e))
                result["errors"].append(f"search_units: {e}")
        except ImportError:
            logger.info("search.fts not available — skipping search_units step")

    return result


def _generate_json_file(paper, equations: list, repo, json_path: str) -> None:
    """Generate the structured JSON companion file."""
    tags = repo.get_tags_for_paper(paper.id) if hasattr(repo, "get_tags_for_paper") else []
    methods = repo.get_methods_for_paper(paper.id) if hasattr(repo, "get_methods_for_paper") else []

    obj = {
        "paper_id": paper.id,
        "paper_key": paper.paper_key,
        "identifiers": {"doi": paper.doi, "arxiv_id": paper.arxiv_id},
        "title": paper.title,
        "authors": paper.authors_text,
        "year": paper.year,
        "journal": paper.journal,
        "conversion": {"backend": "docling", "status": "ok"},
        "tags": {},
        "equations": [
            {"number": e.get("equation_number"), "latex_raw": e.get("latex_raw"),
             "latex_normalized": e.get("latex_normalized"), "section": e.get("section_path"),
             "page": e.get("page_number")}
            for e in equations
        ],
        "methods": [
            {"name": m.name, "type": m.method_type, "confidence": m.confidence}
            for m in methods
        ],
    }
    _atomic_write_json(json_path, obj)


def _generate_bib_file(paper, bib_path: str) -> None:
    """Generate BibTeX file from paper metadata."""
    key = paper.paper_key or f"p{paper.id:04d}"
    bib = f"@article{{{key},\n"
    if paper.title: bib += f'  title = {{{paper.title}}},\n'
    if paper.authors_text: bib += f'  author = {{{paper.authors_text}}},\n'
    if paper.year: bib += f'  year = {{{paper.year}}},\n'
    if paper.journal: bib += f'  journal = {{{paper.journal}}},\n'
    if paper.doi: bib += f'  doi = {{{paper.doi}}},\n'
    if paper.arxiv_id: bib += f'  eprint = {{{paper.arxiv_id}}},\n'
    bib += "}\n"
    _atomic_write(bib_path, bib)

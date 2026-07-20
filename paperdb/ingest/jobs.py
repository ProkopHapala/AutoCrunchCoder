"""Incremental job execution — skip if equivalent run exists.

Processing state is tracked via the processing_runs table (§18 D15).
Instead of boolean flags, we check for equivalent successful runs:
same operation + input_sha256 + backend/version + config_hash + model + prompt_version.
When a new run succeeds, prior runs for that operation are superseded.
"""
import json, hashlib, logging
from typing import Optional

from ..db.models import ProcessingRun

logger = logging.getLogger(__name__)


def find_equivalent_run(paper_id: int, operation: str, input_sha256: str,
                        backend: str, config_hash: str, model: Optional[str],
                        prompt_version: Optional[str], repo) -> Optional[int]:
    """Check if an equivalent successful processing_run exists.

    Matches on: operation + config_hash + input_sha256 (via Repository API).
    Status must be 'ok'. Returns run_id if found, None otherwise.
    """
    if not hasattr(repo, "find_equivalent_run"):
        return None
    run = repo.find_equivalent_run(
        paper_id=paper_id,
        operation=operation,
        config_hash=config_hash,
        input_sha256=input_sha256,
    )
    return run.id if run else None


def run_job(paper_id: int, operation: str, backend: str, config: dict,
            repo, llm_config: Optional[dict] = None) -> int:
    """Create a processing_run with status='running' and return its ID.

    The caller is responsible for executing the operation and calling finish_run().
    On success: caller calls repo.finish_run(run_id, status='ok') — this supersedes
    prior runs for this operation. On failure: caller calls
    repo.finish_run(run_id, status='failed', message=...).
    """
    model = llm_config.get("template_name") if llm_config else None
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]

    run = ProcessingRun(
        paper_id=paper_id,
        operation=operation,
        backend=backend,
        model_name=model,
        prompt_version="v1",
        configuration_json=json.dumps(config),
        config_hash=config_hash,
    )
    run_id = repo.start_run(run)
    logger.info(f"Started run {run_id}: paper={paper_id} op={operation} backend={backend}")
    return run_id


def finish_job(run_id: int, status: str, repo, message: Optional[str] = None,
               output_path: Optional[str] = None) -> None:
    """Finish a processing run and supersede prior runs if successful."""
    repo.finish_run(run_id, status=status, message=message, output_path=output_path)
    if status == "ok":
        # Get the run to find paper_id and operation
        current = repo.get_run_by_id(run_id) if hasattr(repo, "get_run_by_id") else None
        if current:
            # Supersede prior successful runs for the same paper+operation
            runs = repo.get_runs_for_paper(current.paper_id) if hasattr(repo, "get_runs_for_paper") else []
            for r in runs:
                if r.id != run_id and r.operation == current.operation and r.status == "ok":
                    repo.supersede_run(r.id, run_id)
    logger.info(f"Finished run {run_id}: status={status}")


def ingest_batch(paper_ids: list, repo, operations=None, llm_config=None,
                 force=False, data_dir=None) -> dict:
    """Process multiple papers. Skip papers with all operations already done.

    Returns:
        {processed, skipped, failed, details}
    """
    from .pipeline import ingest_paper, DEFAULT_OPERATIONS

    ops = operations or list(DEFAULT_OPERATIONS)
    result = {"processed": 0, "skipped": 0, "failed": 0, "details": []}

    for pid in paper_ids:
        # Check if all operations have equivalent runs
        if not force:
            all_done = True
            paper = repo.get_paper(pid)
            if not paper:
                result["failed"] += 1
                result["details"].append({"paper_id": pid, "error": "not found"})
                continue

            files = repo.get_files_for_paper(pid)
            if not files:
                result["failed"] += 1
                result["details"].append({"paper_id": pid, "error": "no files"})
                continue

            input_sha256 = files[0].sha256 or ""
            for op in ops:
                if op in ("files", "search_units"):
                    continue  # These are always re-generated
                cfg_hash = hashlib.sha256(json.dumps({"backend": "docling"}, sort_keys=True).encode()).hexdigest()[:16]
                existing = find_equivalent_run(pid, op, input_sha256, "docling", cfg_hash, None, None, repo)
                if not existing:
                    all_done = False
                    break

            if all_done:
                result["skipped"] += 1
                result["details"].append({"paper_id": pid, "status": "skipped"})
                continue

        try:
            r = ingest_paper(pid, repo, operations=ops, llm_config=llm_config,
                             force=force, data_dir=data_dir)
            if r["errors"]:
                result["failed"] += 1
            else:
                result["processed"] += 1
            result["details"].append(r)
        except Exception as e:
            result["failed"] += 1
            result["details"].append({"paper_id": pid, "error": str(e)})
            logger.error(f"Batch ingest failed for paper {pid}: {e}", exc_info=True)

    return result

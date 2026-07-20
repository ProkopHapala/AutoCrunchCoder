"""Incremental processing jobs backed by durable processing-run provenance."""
import hashlib
import json
import logging
from typing import Optional

from ..db.models import ProcessingRun

logger = logging.getLogger(__name__)


def _model_name(llm_config) -> Optional[str]:
    """Resolve the actual configured model, including the default template."""
    if llm_config is False: return None
    from paperdb.config import get_llm_config
    key = llm_config.get("template_name") if isinstance(llm_config, dict) else llm_config
    return get_llm_config(key).get("model_name", key)


def find_equivalent_run(paper_id: int, operation: str, input_sha256: str,
                        backend: str, config_hash: str, model: Optional[str],
                        prompt_version: Optional[str], repo) -> Optional[int]:
    """Return a successful run only when every reproducibility input matches."""
    run = repo.find_equivalent_run(paper_id=paper_id, operation=operation, config_hash=config_hash,
                                   input_sha256=input_sha256, backend=backend, model_name=model,
                                   prompt_version=prompt_version)
    return run.id if run else None


def run_job(paper_id: int, operation: str, backend: str, config: dict,
            repo, llm_config=None, input_sha256: Optional[str] = None,
            source_file_id: Optional[int] = None, prompt_version: Optional[str] = "v1",
            backend_version: Optional[str] = None) -> int:
    """Create a running processing record containing all equivalence inputs."""
    model = _model_name(llm_config)
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]
    run = ProcessingRun(paper_id=paper_id, operation=operation, backend=backend,
                        backend_version=backend_version, model_name=model,
                        prompt_version=prompt_version, configuration_json=json.dumps(config, sort_keys=True),
                        config_hash=config_hash, input_sha256=input_sha256, source_file_id=source_file_id)
    run_id = repo.start_run(run)
    logger.info("Started run %s: paper=%s op=%s backend=%s", run_id, paper_id, operation, backend)
    return run_id


def finish_job(run_id: int, status: str, repo, message: Optional[str] = None,
               output_path: Optional[str] = None) -> None:
    """Finish a run and supersede the newest prior successful equivalent operation."""
    repo.finish_run(run_id, status=status, message=message, output_path=output_path)
    if status == "ok":
        current = repo.get_run_by_id(run_id)
        priors = [r for r in repo.get_runs_for_paper(current.paper_id)
                  if r.id != run_id and r.operation == current.operation and r.status == "ok"]
        if priors:
            repo.supersede_run(priors[0].id, run_id)
            for prior in priors[1:]: repo.mark_run_superseded(prior.id)
        if current.operation == "tag": repo.refresh_paper_tags(current.paper_id)
        if current.operation == "summarize": repo.refresh_active_summary(current.paper_id)
    logger.info("Finished run %s: status=%s", run_id, status)


def ingest_batch(paper_ids: list, repo, operations=None, llm_config=None,
                 force=False, data_dir=None) -> dict:
    """Process papers and classify a no-op pipeline result as skipped."""
    from .pipeline import ingest_paper, DEFAULT_OPERATIONS
    ops = operations or list(DEFAULT_OPERATIONS)
    result = {"processed": 0, "skipped": 0, "failed": 0, "details": []}
    for pid in paper_ids:
        try:
            detail = ingest_paper(pid, repo, operations=ops, llm_config=llm_config,
                                  force=force, data_dir=data_dir)
            if detail["errors"]: result["failed"] += 1
            elif detail["operations_run"]: result["processed"] += 1
            else: result["skipped"] += 1
            result["details"].append(detail)
        except Exception as exc:
            result["failed"] += 1
            result["details"].append({"paper_id": pid, "error": str(exc)})
            logger.error("Batch ingest failed for paper %s: %s", pid, exc, exc_info=True)
    return result

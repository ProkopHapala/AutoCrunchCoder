"""Method card extraction — source_algorithm vs reconstructed_method.

Extracts method cards from markdown + equations. Two types (§18 D9):
- source_algorithm: verbatim algorithm steps extracted from the paper text
- reconstructed_method: LLM interpretation that combines multiple passages

Every reconstructed field refers back to source passages — lets coding agent
distinguish "paper says this" from "model inferred this".

Uses pyCruncher.Agent for LLM-based reconstruction.
"""
import json, re, logging
from typing import Optional

from ..db.models import Method

logger = logging.getLogger(__name__)

# Prompt for LLM-based method reconstruction
_RECONSTRUCT_PROMPT = """You are a scientific method extraction assistant. Given the markdown text of a scientific paper and a list of extracted equations, identify the main computational methods/algorithms described in the paper.

For each method, produce a JSON array of method cards with the following structure:
[
  {
    "name": "short method name",
    "purpose": "what this method does",
    "method_type": "source_algorithm" or "reconstructed_method",
    "assumptions": ["assumption 1", ...],
    "state_variables": ["variable 1", ...],
    "inputs": ["input 1", ...],
    "outputs": ["output 1", ...],
    "initialization": ["step 1", ...],
    "steps": ["step 1", ...],
    "boundary_conditions": ["condition 1", ...],
    "convergence": "convergence criterion if applicable",
    "parallelization": "parallelization strategy if applicable",
    "limitations": ["limitation 1", ...],
    "complexity": "time/space complexity if stated",
    "source_passages": [{"page": null, "section": "section name", "text": "relevant passage excerpt"}],
    "equation_refs": [equation_number, ...],
    "confidence": 0.0-1.0
  }
]

Rules:
- Use "source_algorithm" when the paper explicitly describes algorithm steps (e.g., numbered steps, pseudocode).
- Use "reconstructed_method" when you infer the algorithm from multiple passages.
- Every field should be grounded in the paper text. Include source_passages for each method.
- Reference equations by their equation_number if known.
- Be conservative with confidence: 0.9+ for explicit algorithms, 0.5-0.8 for reconstructions.
- Return ONLY the JSON array, no other text.

Paper markdown (first 12000 chars):
---
{markdown}
---

Extracted equations:
{equations_text}

Extract all methods you can identify. Return a JSON array."""


def extract_methods(markdown: str, equations: list, paper_id: int, run_id: int,
                    repo, llm_config: Optional[dict] = None) -> list:
    """Extract method cards from markdown + equations.

    Args:
        markdown: full paper markdown text
        equations: list of equation dicts (from extract_equations)
        paper_id: paper ID in the database
        run_id: processing_run ID for this extraction run
        repo: Repository instance with upsert_method() and link_method_equation()
        llm_config: dict with 'template_name' for pyCruncher.Agent, or None to skip LLM

    Returns:
        list of method dicts that were stored
    """
    # First: try to extract source_algorithm (verbatim) from markdown
    source_methods = _extract_source_algorithms(markdown)

    # Then: use LLM for reconstructed_method if config provided
    reconstructed_methods = []
    if llm_config and llm_config.get("template_name"):
        reconstructed_methods = _llm_reconstruct_methods(markdown, equations, llm_config)
    else:
        logger.info("No LLM config provided — skipping reconstructed_method extraction")

    all_methods = source_methods + reconstructed_methods
    stored = []

    for m in all_methods:
        card_json = {
            "assumptions": m.get("assumptions", []),
            "state_variables": m.get("state_variables", []),
            "inputs": m.get("inputs", []),
            "outputs": m.get("outputs", []),
            "initialization": m.get("initialization", []),
            "steps": m.get("steps", []),
            "boundary_conditions": m.get("boundary_conditions", []),
            "convergence": m.get("convergence"),
            "parallelization": m.get("parallelization"),
            "limitations": m.get("limitations", []),
        }

        source_passages = m.get("source_passages", [])

        method_obj = Method(
            paper_id=paper_id,
            run_id=run_id,
            name=m.get("name", "unnamed"),
            method_type=m.get("method_type", "reconstructed_method"),
            purpose=m.get("purpose"),
            complexity=m.get("complexity"),
            confidence=m.get("confidence", 0.5),
            card_json=json.dumps(card_json),
            source_passages_json=json.dumps(source_passages),
        )

        method_id = repo.upsert_method(method_obj)
        stored.append({"id": method_id, "name": method_obj.name,
                       "method_type": method_obj.method_type})

        # Link equations to this method
        eq_refs = m.get("equation_refs", [])
        if eq_refs and equations:
            # Match equation_refs (numbers) to stored equations
            for eq in equations:
                eq_num = eq.get("equation_number")
                if eq_num and str(eq_num) in [str(r) for r in eq_refs]:
                    role = "core"  # default role
                    repo.link_method_equation(method_id=method_id, equation_id=eq["id"], role=role)

    logger.info(f"Extracted {len(stored)} methods for paper_id={paper_id} "
                f"({len(source_methods)} source, {len(reconstructed_methods)} reconstructed)")
    return stored


def _extract_source_algorithms(markdown: str) -> list[dict]:
    """Extract verbatim algorithm descriptions from markdown.
    Looks for patterns like "Algorithm 1:", numbered steps, pseudocode blocks.
    """
    methods = []
    lines = markdown.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect "Algorithm N:" headers
        algo_match = re.match(r'^#+\s*(?:Algorithm\s+)?(\d+)[:.\s]+(.+)$', line, re.IGNORECASE)
        if not algo_match:
            algo_match = re.match(r'^\*\*Algorithm\s+(\d+)[:.\s]*(.+)\*\*$', line, re.IGNORECASE)
        if algo_match:
            algo_num = algo_match.group(1)
            algo_name = algo_match.group(2).strip().rstrip(":")
            # Collect following lines until next heading or blank section
            steps = []
            passages = []
            j = i + 1
            current_section = ""
            while j < len(lines) and j < i + 100:
                l = lines[j]
                heading = re.match(r'^#{1,6}\s+', l)
                if heading:
                    break
                # Numbered steps: "1. ...", "Step 1: ..."
                step_match = re.match(r'^(?:Step\s+)?(\d+)[.):\s]+(.+)$', l, re.IGNORECASE)
                if step_match:
                    steps.append(l.strip())
                elif l.strip() and not l.strip().startswith("```"):
                    passages.append(l.strip())
                j += 1

            if steps:
                methods.append({
                    "name": f"Algorithm {algo_num}: {algo_name}",
                    "purpose": algo_name,
                    "method_type": "source_algorithm",
                    "steps": steps,
                    "assumptions": [],
                    "state_variables": [],
                    "inputs": [],
                    "outputs": [],
                    "initialization": [],
                    "boundary_conditions": [],
                    "convergence": None,
                    "parallelization": None,
                    "limitations": [],
                    "complexity": None,
                    "source_passages": [{"page": None, "section": "", "text": "\n".join(passages[:10])}],
                    "equation_refs": [],
                    "confidence": 0.9,
                })
            i = j
        i += 1
    return methods


def _llm_reconstruct_methods(markdown: str, equations: list, llm_config: dict) -> list[dict]:
    """Use pyCruncher.Agent to reconstruct method cards from paper text."""
    try:
        from pyCruncher.AgentOpenAI import AgentOpenAI
    except ImportError:
        try:
            from pyCruncher.AgentDeepSeek import AgentDeepSeek as AgentOpenAI
        except ImportError:
            logger.warning("No Agent implementation available — skipping LLM reconstruction")
            return []

    template_name = llm_config.get("template_name", "lm-llama-8b")
    try:
        agent = AgentOpenAI(template_name)
    except Exception as e:
        logger.warning(f"Failed to create LLM agent ({template_name}): {e}")
        return []

    # Prepare equations text
    eq_lines = []
    for eq in equations:
        num = eq.get("equation_number", "?")
        latex = eq.get("latex_raw", eq.get("latex_normalized", ""))
        section = eq.get("section_path", "")
        eq_lines.append(f"Eq ({num}) [{section}]: {latex[:200]}")
    equations_text = "\n".join(eq_lines[:50]) if eq_lines else "(no equations extracted)"

    # Truncate markdown for context window
    md_trunc = markdown[:12000]

    prompt = _RECONSTRUCT_PROMPT.format(markdown=md_trunc, equations_text=equations_text)

    try:
        response = agent.query(prompt=prompt, bHistory=False)
        text = agent.get_response_text(response) if hasattr(agent, 'get_response_text') else str(response)
    except Exception as e:
        logger.warning(f"LLM query failed: {e}")
        return []

    # Parse JSON from response — may be wrapped in ```json blocks
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        methods = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM method JSON: {e}\nRaw: {text[:500]}")
        return []

    if not isinstance(methods, list):
        methods = [methods]

    return methods

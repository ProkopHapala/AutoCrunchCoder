"""Method card construction with evidence links.

Handles reconstruction and enrichment — building `reconstructed_method` cards
from multiple passages using LLM. Task 5's `extract/methods.py` does the initial
extraction from Docling structured output; this module synthesizes coherent
method descriptions from those source_algorithm cards + paper text.

Key principle (§18 D9): Every reconstructed field refers back to source passages
— lets coding agent distinguish "paper says this" from "model inferred this".
"""

import json
from typing import Optional

RECONSTRUCT_PROMPT = """You are an expert computational scientist. Reconstruct a coherent method card from the following source algorithm extractions and paper text.

The source_algorithm cards are verbatim extractions from the paper. Your job is to synthesize them into a single coherent reconstructed_method card.

Return JSON with these fields:
{
  "name": "descriptive method name",
  "purpose": "what this method computes or solves",
  "assumptions": ["list of assumptions"],
  "state_variables": ["list of state variables"],
  "inputs": ["list of inputs"],
  "outputs": ["list of outputs"],
  "initialization": "initialization steps",
  "steps": ["ordered list of algorithm steps"],
  "boundary_conditions": "boundary conditions if applicable",
  "convergence": "convergence criteria if applicable",
  "parallelization": "parallelization strategy if mentioned",
  "limitations": ["list of limitations"],
  "complexity": "computational complexity if stated",
  "confidence": 0.0-1.0 self-reported confidence,
  "source_passages": [{"page": null, "section": null, "text": "relevant passage from paper"}]
}

Rules:
- Only include information present in the paper. Do NOT invent.
- For each field, cite the source passage it came from in source_passages.
- If a field cannot be determined from the paper, use null or empty list.
- confidence reflects how completely the method could be reconstructed."""

def reconstruct_method(paper_id: int, run_id: int, repo, llm_config=None) -> list:
    """Build reconstructed_method cards from source_algorithm cards + paper text.

    Args:
        paper_id: Paper ID in the database.
        run_id: Processing run ID for provenance tracking.
        repo: Repository with get_methods, add_method, link_method_equation methods.
        llm_config: LLM template key or None for default.

    Returns:
        List of reconstructed Method dicts.
    """
    from paperdb.config import make_agent

    # Read source_algorithm methods (from Task 5's extraction)
    try:
        source_methods = repo.get_methods(paper_id, method_type='source_algorithm')
    except Exception:
        source_methods = []

    if not source_methods:
        print(f"[method_cards] No source_algorithm methods for paper {paper_id}")
        return []

    # Read paper markdown for context
    try:
        paper = repo.get_paper(paper_id)
        paper = paper if isinstance(paper, dict) else {'markdown_path': getattr(paper, 'markdown_path', None)}
        md_path = paper.get('markdown_path')
    except Exception:
        md_path = None

    paper_text = ""
    if md_path:
        try:
            from pathlib import Path
            paper_text = Path(md_path).read_text(encoding='utf-8')[:30000]
        except Exception:
            pass

    # Read equations for this paper
    try:
        equations = repo.get_equations_for_paper(paper_id)
    except Exception:
        equations = []

    agent = make_agent(llm_config)
    agent.set_system_prompt(RECONSTRUCT_PROMPT)

    results = []
    for sm in source_methods:
        sm = sm if isinstance(sm, dict) else {
            'id': sm.id, 'name': sm.name, 'purpose': getattr(sm, 'purpose', ''),
            'card_json': getattr(sm, 'card_json', '{}'), 'source_passages_json': getattr(sm, 'source_passages_json', '[]')
        }

        # Build context for LLM
        source_card = sm.get('card_json', '{}')
        if isinstance(source_card, str):
            try:
                source_card = json.loads(source_card)
            except Exception:
                source_card = {}

        source_passages = sm.get('source_passages_json', '[]')
        if isinstance(source_passages, str):
            try:
                source_passages = json.loads(source_passages)
            except Exception:
                source_passages = []

        eq_text = ""
        for eq in equations[:10]:
            eq = eq if isinstance(eq, dict) else {'latex_raw': getattr(eq, 'latex_raw', ''), 'section_path': getattr(eq, 'section_path', '')}
            eq_text += f"  - {eq.get('latex_raw', '')} (section: {eq.get('section_path', '?')})\n"

        prompt = f"""Source algorithm card:
{json.dumps(source_card, indent=2)}

Source passages:
{json.dumps(source_passages, indent=2)}

Relevant equations:
{eq_text if eq_text else 'None extracted'}

Paper text (truncated):
{paper_text[:15000]}

Reconstruct a coherent method card from this information. Return JSON only."""

        response = agent.query(prompt, response_format={"type": "json_object"})
        raw_text = response.content if hasattr(response, 'content') else str(response)

        try:
            card = _parse_json(raw_text)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[method_cards] LLM returned invalid JSON for paper {paper_id}, method '{sm.get('name')}': {e}")
            continue

        # Extract fields
        name = card.get('name', sm.get('name', 'unknown'))
        purpose = card.get('purpose', '')
        complexity = card.get('complexity', '')
        confidence = card.get('confidence', 0.7)
        source_passages_out = card.get('source_passages', source_passages)

        # Store reconstructed method
        card_json = json.dumps({
            'assumptions': card.get('assumptions', []),
            'state_variables': card.get('state_variables', []),
            'inputs': card.get('inputs', []),
            'outputs': card.get('outputs', []),
            'initialization': card.get('initialization'),
            'steps': card.get('steps', []),
            'boundary_conditions': card.get('boundary_conditions'),
            'convergence': card.get('convergence'),
            'parallelization': card.get('parallelization'),
            'limitations': card.get('limitations', []),
        })
        source_passages_json = json.dumps(source_passages_out)

        try:
            method_id = repo.add_method(
                paper_id=paper_id, run_id=run_id, name=name,
                method_type='reconstructed_method', purpose=purpose,
                complexity=complexity, confidence=confidence,
                card_json=card_json, source_passages_json=source_passages_json,
            )
        except Exception as e:
            print(f"[method_cards] Failed to store reconstructed method for paper {paper_id}: {e}")
            continue

        # Link equations to this method
        for eq in equations:
            eq = eq if isinstance(eq, dict) else {'id': eq.id}
            eq_id = eq.get('id')
            if eq_id:
                try:
                    repo.link_method_equation(method_id, eq_id, role='core')
                except Exception:
                    pass

        results.append({
            'id': method_id, 'name': name, 'purpose': purpose,
            'confidence': confidence, 'card': card,
        })

    return results

def _parse_json(text: str) -> dict:
    """Parse JSON from LLM response, handling code fences."""
    import re
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        text = text[start:end+1]
    return json.loads(text)

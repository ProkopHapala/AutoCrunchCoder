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
  "source_passages": [{"page": null, "section": null, "text": "relevant passage from paper"}],
  "field_evidence": {"steps": [0], "assumptions": [1]},
  "equation_refs": ["equation number explicitly used by this method"]
}

Rules:
- Only include information present in the paper. Do NOT invent.
- For each populated field, list the zero-based source_passages indexes supporting it in field_evidence.
- Only list equations actually used by the method in equation_refs; use their equation_number.
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

    source_methods = repo.get_methods(paper_id, method_type='source_algorithm')

    if not source_methods:
        print(f"[method_cards] No source_algorithm methods for paper {paper_id}")
        return []

    paper = repo.get_paper(paper_id)
    md_path = paper.get('markdown_path') if isinstance(paper, dict) else getattr(paper, 'markdown_path', None)
    paper_text = ""
    if md_path:
        from pathlib import Path
        paper_text = Path(md_path).read_text(encoding='utf-8')

    equations = repo.get_equations_for_paper(paper_id)

    agent = make_agent(llm_config)
    agent.set_system_prompt(RECONSTRUCT_PROMPT)
    paper_limit = max(12000, agent.max_context_length * 3 - 24000) if agent.max_context_length else 12000
    paper_text = paper_text[:paper_limit]

    results = []
    for sm in source_methods:
        sm = sm if isinstance(sm, dict) else {
            'id': sm.id, 'name': sm.name, 'purpose': getattr(sm, 'purpose', ''),
            'card_json': getattr(sm, 'card_json', '{}'), 'source_passages_json': getattr(sm, 'source_passages_json', '[]')
        }

        # Build context for LLM
        source_card = sm.get('card_json', '{}')
        if isinstance(source_card, str):
            source_card = json.loads(source_card)

        source_passages = sm.get('source_passages_json', '[]')
        if isinstance(source_passages, str):
            source_passages = json.loads(source_passages)

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

Paper text (bounded by configured model context):
{paper_text}

Reconstruct a coherent method card from this information. Return JSON only."""

        response = agent.query(prompt, response_format={"type": "json_object"})
        raw_text = response.content if hasattr(response, 'content') else str(response)

        card = _parse_json(raw_text)
        if not isinstance(card, dict): raise ValueError(f"Method reconstruction for '{sm.get('name')}' must be a JSON object")

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
            'field_evidence': card.get('field_evidence', {}),
        })
        source_passages_json = json.dumps(source_passages_out)

        method_id = repo.add_method(
            paper_id=paper_id, run_id=run_id, name=name,
            method_type='reconstructed_method', purpose=purpose,
            complexity=complexity, confidence=confidence,
            card_json=card_json, source_passages_json=source_passages_json,
        )

        # Link only explicitly cited equations, never every equation in the paper.
        refs = {str(ref) for ref in card.get('equation_refs', [])}
        for eq in equations:
            eq_id = eq.get('id') if isinstance(eq, dict) else eq.id
            eq_num = eq.get('equation_number') if isinstance(eq, dict) else eq.equation_number
            if eq_id and eq_num is not None and str(eq_num) in refs:
                repo.link_method_equation(method_id=method_id, equation_id=eq_id, role='core')

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

"""LLM tag extraction with extended categories.

Uses pyCruncher.Agent to extract structured tags from paper markdown.
Extended categories per §18 D6:
  domain, physical_system, phenomenon, model_or_theory, method, solver,
  data_structure, discretization, task, implementation, software,
  material_or_molecule, user

Key principles:
- Provisional tags first — don't try to get it perfect.
- Preserve raw tag text in paper_tags.raw_name.
- Canonicalize via aliases.resolve_to_canonical().
- Empty categories are harmless; noisy invented tags are not.
"""

import json
import re
from typing import Optional

# Extended tag categories (§18 D6)
TAG_CATEGORIES = [
    "domain", "physical_system", "phenomenon", "model_or_theory",
    "method", "solver", "data_structure", "discretization",
    "task", "implementation", "software", "material_or_molecule", "user",
]

# Categories to emphasize initially (others populated when genuinely applicable)
PRIMARY_CATEGORIES = [
    "domain", "physical_system", "model_or_theory", "task",
    "method", "solver", "data_structure", "implementation", "software",
]

# JSON schema sent to LLM for structured tag extraction
TAG_SCHEMA = {
    "type": "object",
    "properties": {
        cat: {
            "type": "array",
            "items": {"type": "string"},
            "description": f"Tags for {cat}. Only include when genuinely applicable. Can be empty."
        }
        for cat in TAG_CATEGORIES
    },
    "required": TAG_CATEGORIES,
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are an expert computational scientist and taxonomist.
Extract structured tags from the given paper markdown.
Assign tags to these categories: domain, physical_system, phenomenon, model_or_theory, method, solver, data_structure, discretization, task, implementation, software, material_or_molecule, user.

Rules:
- Only assign a tag when it is genuinely applicable to the paper. Empty categories are fine.
- Do NOT invent tags. If a category doesn't apply, return an empty list.
- Use descriptive, specific tag names (e.g. "density functional theory" not "DFT").
- Keep tag names lowercase.
- 1-5 tags per category maximum. Quality over quantity.
- Return valid JSON only."""

def _parse_llm_json(text: str) -> dict:
    """Parse JSON from LLM response, handling code fences and extra text."""
    # Strip code fences if present
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    # Try to find JSON object
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        text = text[start:end+1]
    return json.loads(text)

def extract_tags(markdown: str, paper_id: int, run_id: int, repo, llm_config=None) -> list:
    """Extract tags from paper markdown using LLM.

    Args:
        markdown: Paper markdown text (summary + source text sections).
        paper_id: Paper ID in the database.
        run_id: Processing run ID for provenance tracking.
        repo: Repository object with add_tag, get_tag_by_name, add_paper_tag methods.
        llm_config: LLM template key (str) or config dict. If None, uses default from config.

    Returns:
        List of (tag_id, category, canonical_name, raw_name, confidence) tuples for stored tags.
    """
    from paperdb.config import make_agent
    from paperdb.taxonomy.aliases import resolve_to_canonical, normalize_alias

    agent = make_agent(llm_config)
    agent.set_system_prompt(SYSTEM_PROMPT)

    # Truncate markdown to fit context window
    max_chars = min(agent.max_context_length * 3 if agent.max_context_length else 12000, 50000)
    md_truncated = markdown[:max_chars]

    prompt = f"Extract structured tags from this paper. Return JSON with these keys: {', '.join(TAG_CATEGORIES)}.\n\nPaper markdown:\n{md_truncated}"

    response = agent.query(prompt, response_format={"type": "json_object"})
    raw_text = response.content if hasattr(response, 'content') else str(response)

    try:
        tags_dict = _parse_llm_json(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON for tag extraction: {e}\nRaw: {raw_text[:500]}")

    results = []
    for category in TAG_CATEGORIES:
        raw_tags = tags_dict.get(category, [])
        if not raw_tags:
            continue
        if not isinstance(raw_tags, list):
            raw_tags = [raw_tags]

        for raw_name in raw_tags:
            raw_name = str(raw_name).strip()
            if not raw_name:
                continue

            # Try to resolve to canonical tag(s) via aliases
            canonical_tags = resolve_to_canonical(raw_name, repo, category=category)
            if canonical_tags:
                # Use first match (or let ambiguity be — store all)
                for tag in canonical_tags:
                    _store_paper_tag(repo, paper_id, tag['id'], run_id, raw_name, source='llm', confidence=0.8)
                    results.append((tag['id'], category, tag['canonical_name'], raw_name, 0.8))
            else:
                # No existing canonical tag — create new one
                canonical_name = raw_name.lower().strip()
                tag_id = _get_or_create_tag(repo, canonical_name, category)
                if tag_id is not None:
                    _store_paper_tag(repo, paper_id, tag_id, run_id, raw_name, source='llm', confidence=0.7)
                    # Also add as alias
                    normalized = normalize_alias(raw_name)
                    try:
                        repo.add_tag_alias(tag_id, raw_name, normalized)
                    except Exception:
                        pass  # alias may already exist
                    results.append((tag_id, category, canonical_name, raw_name, 0.7))

    return results

def _get_or_create_tag(repo, canonical_name: str, category: str) -> Optional[int]:
    """Get existing tag or create new one. Returns tag_id."""
    try:
        existing = repo.get_tag_by_name(canonical_name, category)
        if existing:
            return existing['id'] if isinstance(existing, dict) else existing.id
    except Exception:
        pass
    try:
        return repo.add_tag(canonical_name, category)
    except Exception:
        # Maybe created concurrently — try fetching again
        try:
            existing = repo.get_tag_by_name(canonical_name, category)
            if existing:
                return existing['id'] if isinstance(existing, dict) else existing.id
        except Exception:
            pass
    return None

def _store_paper_tag(repo, paper_id: int, tag_id: int, run_id: int, raw_name: str, source: str, confidence: float):
    """Store a paper_tags assertion, preserving raw_name."""
    try:
        repo.add_paper_tag(paper_id, tag_id, source=source, run_id=run_id, confidence=confidence, raw_name=raw_name)
    except Exception as e:
        # PK conflict — paper_tag already exists for this (paper_id, tag_id, source, run_id)
        print(f"[extraction] paper_tag already exists: paper={paper_id} tag={tag_id} source={source} run={run_id}: {e}")

"""Versioned summaries via pyCruncher.Agent.

Summary structure: Essence, Key equations, Methods, Relevance.
Summaries are versioned — keep history. Deactivate old, don't delete.
The summary is embedded in the paper's .md file (in the "Generated scientific summary"
section, clearly separated from source text).
"""

from typing import Optional

SUMMARY_PROMPT_V1 = """You are an expert computational scientist. Generate a structured scientific summary of the following paper.

Format your response as markdown with these sections:

## Essence
1-2 sentences capturing the core contribution and significance.

## Key equations
List the most important equations in LaTeX. For each, briefly explain what it represents.
Only include equations that are central to the paper's contribution.

## Methods
Describe the main computational/numerical methods used. Be specific about:
- Algorithm type and key steps
- Numerical techniques
- Data structures
- Implementation details mentioned

## Relevance
Why this paper matters for computational science. What problems does it solve?
What can a coding agent learn from it for implementation?

Rules:
- Be concise but technically precise.
- Use LaTeX for all equations ($$...$$ or $...$).
- Do not invent information not present in the paper.
- If a section doesn't apply, write "N/A"."""

SUMMARY_PROMPTS = {"v1": SUMMARY_PROMPT_V1}

def generate_summary(markdown: str, paper_id: int, run_id: int, repo,
                     llm_config=None, prompt_version="v1") -> str:
    """Generate a scientific summary from paper markdown using LLM.

    Args:
        markdown: Paper markdown text.
        paper_id: Paper ID in the database.
        run_id: Processing run ID for provenance tracking.
        repo: Repository with add_summary, deactivate_summaries methods.
        llm_config: LLM template key or None for default.
        prompt_version: Version of the prompt template to use.

    Returns:
        Summary markdown text.
    """
    from paperdb.config import make_agent

    prompt_template = SUMMARY_PROMPTS.get(prompt_version)
    if prompt_template is None:
        raise ValueError(f"Unknown prompt_version '{prompt_version}'. Available: {list(SUMMARY_PROMPTS.keys())}")

    agent = make_agent(llm_config)
    agent.set_system_prompt(prompt_template)

    max_chars = min(agent.max_context_length * 3 if agent.max_context_length else 12000, 50000)
    md_truncated = markdown[:max_chars]

    response = agent.query(f"Summarize this paper:\n\n{md_truncated}")
    summary_text = response.content if hasattr(response, 'content') else str(response)

    # Deactivate previous active summaries (keep history — don't delete)
    try:
        repo.deactivate_summaries(paper_id)
    except Exception as e:
        print(f"[summaries] Warning: could not deactivate old summaries for paper {paper_id}: {e}")

    model_name = getattr(agent, 'model_name', 'unknown')
    try:
        repo.add_summary(paper_id, run_id=run_id, model_name=model_name,
                         prompt_version=prompt_version, content=summary_text, is_active=1)
    except Exception as e:
        raise RuntimeError(f"Failed to store summary for paper {paper_id}: {e}")

    return summary_text

def get_active_summary(paper_id: int, repo) -> Optional[dict]:
    """Get the active summary for a paper. Returns summary dict or None."""
    try:
        return repo.get_active_summary(paper_id)
    except Exception:
        return None

def get_summary_history(paper_id: int, repo) -> list:
    """Get all summary versions for a paper (newest first)."""
    try:
        return repo.get_summary_history(paper_id)
    except Exception:
        return []

def format_summary_section(summary_text: str, prompt_version: str = "v1") -> str:
    """Format summary for embedding in paper markdown.

    The summary is clearly separated from source text per §8.
    """
    return f"""# Generated scientific summary

> This section was generated from the paper and is not source text.
> Prompt version: {prompt_version}

{summary_text}

---

# Extracted source text
"""

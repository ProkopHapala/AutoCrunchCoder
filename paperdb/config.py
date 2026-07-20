"""LLM config loading via pyCruncher.Agent + config/LLMs.toml.

Provides get_llm_config(key) that returns the provider settings dict.
Default key from PAPERDB_LLM env var.
"""
import os
import toml
from pathlib import Path

def _get_llms_toml_path() -> Path:
    """Locate config/LLMs.toml relative to the AutoCrunchCoder repo root."""
    here = Path(__file__).resolve().parent  # paperdb/
    repo_root = here.parent  # AutoCrunchCoder/
    return repo_root / "config" / "LLMs.toml"

def load_all_templates() -> dict:
    """Load all templates from config/LLMs.toml."""
    path = _get_llms_toml_path()
    with open(path, "r") as f:
        return toml.load(f)

def get_llm_config(key: str | None = None) -> dict:
    """Return the provider settings dict for the given template key.

    If key is None, uses PAPERDB_LLM env var, falling back to the first template.
    """
    templates = load_all_templates()
    if key is None:
        key = os.environ.get("PAPERDB_LLM")
    if key is None:
        # fallback: first available template
        key = next(iter(templates))
    if key not in templates:
        available = ", ".join(templates.keys())
        raise ValueError(f"Unknown LLM template '{key}'. Available: {available}")
    return templates[key]

def make_agent(key: str | dict | None = None):
    """Create a pyCruncher Agent from an explicit or resolved-default template key."""
    if isinstance(key, dict):
        key = key.get("template_name")
        if not key: raise ValueError("LLM config dictionaries require 'template_name'")
    if key is None:
        templates = load_all_templates()
        key = os.environ.get("PAPERDB_LLM") or next(iter(templates))
    cfg = get_llm_config(key)
    provider = cfg.get("provider", "openai")
    # Import here to avoid circular deps and keep config.py lightweight
    if provider == "deepseek":
        from pyCruncher.AgentDeepSeek import AgentDeepSeek
        return AgentDeepSeek(key)
    elif provider == "google":
        from pyCruncher.AgentGoogle import AgentGoogle
        return AgentGoogle(key)
    elif provider == "anthropic":
        from pyCruncher.AgentAnthropic import AgentAnthropic
        return AgentAnthropic(key)
    else:
        from pyCruncher.AgentOpenAI import AgentOpenAI
        return AgentOpenAI(key)


def response_text(agent, response) -> str:
    """Normalize provider-specific response objects through the Agent interface."""
    return agent.get_response_text(response) if hasattr(agent, "get_response_text") else getattr(response, "content", str(response))

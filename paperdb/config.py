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

def make_agent(key: str | None = None):
    """Create a pyCruncher Agent instance for the given config key.

    Uses the provider field to determine which Agent subclass to instantiate.
    """
    cfg = get_llm_config(key)
    provider = cfg.get("provider", "openai")
    # Import here to avoid circular deps and keep config.py lightweight
    if provider == "deepseek":
        from pyCruncher.AgentDeepSeek import AgentDeepSeek
        return AgentDeepSeek(cfg.get("model_name", key))
    elif provider == "google":
        from pyCruncher.AgentGoogle import AgentGoogle
        return AgentGoogle(key)
    elif provider == "anthropic":
        from pyCruncher.AgentAnthropic import AgentAnthropic
        return AgentAnthropic(key)
    else:
        from pyCruncher.AgentOpenAI import AgentOpenAI
        return AgentOpenAI(key)

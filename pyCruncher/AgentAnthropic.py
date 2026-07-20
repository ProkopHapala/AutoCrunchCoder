"""
Anthropic Claude agent — minimal implementation of the Messages API.

This is the most basic agent: it sets up the `anthropic.Anthropic` client and
implements `query`/`stream`. Tool calling is not fully wired yet — the base
class interface is there but `extract_tool_call` needs provider-specific work.

Non-obvious things:
- Uses a hardcoded 8192 context length (should be read from the model profile).
- The import `from Agent import Agent` (not `.Agent`) suggests this file was
  written to be run standalone at some point.
"""

import os
from typing import Dict, Any, List, Generator
from Agent import Agent
import anthropic

class AnthropicAgent(Agent):
    def get_api_key(self) -> str:
        return os.environ.get("ANTHROPIC_API_KEY")

    def setup_client(self):
        return anthropic.Anthropic(api_key=self.api_key)

    def get_max_context_length(self) -> int:
        # Implement this method to return the maximum context length for Anthropic's model
        return 8192  # Assuming a maximum context length of 8192 tokens

    def query(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        response = self.client.messages.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
        return {
            "content": response.content[0].text,
            "usage": response.usage.output_tokens
        }

    def stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        try:
            with self.client.messages.stream(
                model=self.model_name,
                messages=messages,
                **kwargs
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"Error: {str(e)}"

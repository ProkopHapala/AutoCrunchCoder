"""
DeepSeek agent — adds FIM (fill-in-the-middle) and strict JSON mode on top of AgentOpenAI.

DeepSeek's coder models support prefix/suffix completion (`fim_completion`),
which is useful for code infilling tasks. The JSON helpers force
`response_format={'type': 'json_object'}` so structured extraction is reliable.

Non-obvious things:
- Math tools (numerical derivative, integral, expression evaluation) are
  imported here so they can be registered as callable tools in one place.
- `stream_json` accumulates the full response before parsing — partial JSON
  is not valid, so we yield chunks but only parse at the end.
"""

import json
from typing import List, Dict, Any, Optional, Generator, Tuple
from openai import OpenAI
from .AgentOpenAI import AgentOpenAI
from .tools import compute_numerical_derivative, compute_expression_steps, compute_integral, check_numerical_vs_analytical_derivative

class AgentDeepSeek(AgentOpenAI):
    
    def __init__(self, template_name: str = "deepseek-coder", base_url=None ):
        super().__init__(template_name, base_url=base_url )

    def fim_completion(self, prefix: str, suffix: str = "", max_tokens: int = 128) -> str:
        response = self.client.completions.create(
            model=self.model_name,
            prompt=prefix,
            suffix=suffix,
            max_tokens=max_tokens
        )
        return response.choices[0].text

    def query_json(self, prompt: str, system_prompt: str = "You are a helpful assistant. You strictly output JSON format.") -> Dict[str, Any]:
        self.set_system_prompt(system_prompt)
        response = self.query(prompt, response_format={'type': 'json_object'} )
        return json.loads(response)
    
    def stream_json(self, prompt: str, system_prompt: str = "You are a helpful assistant. You strictly output JSON format.") -> Generator[str, None, None]:
        self.set_system_prompt(system_prompt)
        content = ""
        for chunk in self.stream(prompt, response_format={'type': 'json_object'}):
            content += chunk
            yield chunk 
        self.answer_json = json.loads(content)  

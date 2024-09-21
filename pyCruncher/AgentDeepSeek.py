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

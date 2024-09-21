from typing import List, Dict, Any, Optional
from openai import OpenAI
from LMagent import BaseAgent

class DeepSeekAgent(BaseAgent):
    from tools import compute_numerical_derivative, compute_expression_steps, compute_integral, check_numerical_vs_analytical_derivative
    import json
    def __init__(self, template_name: str = "deepseek-chat", use_proxy: bool = False, config_format: str = 'yaml'):
        super().__init__(template_name, use_proxy, config_format)
        self.tools: List[Dict[str, Any]] = []

    def numerical_derivative(self, expr: str, var: str, point: float, h: float = 1e-5) -> float:
        return compute_numerical_derivative(expr, var, point, h)

    def evaluate_expression_steps(self, steps: List[Dict[str, str]]) -> Dict[str, Any]:
        return compute_expression_steps(steps)

    def compute_integral(self, expr: str, var: str, lower: float, upper: float) -> float:
        return compute_integral(expr, var, lower, upper)

    def compare_derivatives(self, expr: str, var: str, point: float, h: float = 1e-5, tolerance: float = 1e-6) -> Dict[str, Any]:
        return check_numerical_vs_analytical_derivative(expr, var, point, h, tolerance)

    def fim_completion(self, prefix: str, suffix: str = "", max_tokens: int = 128) -> str:
        response = self.client.completions.create(
            model=self.model_name,
            prompt=prefix,
            suffix=suffix,
            max_tokens=max_tokens
        )
        return response.choices[0].text

    def json_output(self, prompt: str, system_prompt: str = "You are a helpful assistant. Please provide output in JSON format.") -> Dict[str, Any]:
        self.set_system_prompt(system_prompt)
        response, _ = self.send_message(prompt, response_format={'type': 'json_object'})
        return json.loads(response)

    def add_tool(self, name: str, description: str, parameters: Dict[str, Any]) -> None:
        tool = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        self.tools.append(tool)

    def use_tool(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> Dict[str, Any]:
        self.set_system_prompt(system_prompt)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.history,
            tools=self.tools
        )
        return response.choices[0].message

    def stream_response(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> Generator[str, None, None]:
        self.set_system_prompt(system_prompt)
        self.history.append({"role": "user", "content": prompt})
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.history,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

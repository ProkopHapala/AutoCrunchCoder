import openai
from openai import OpenAI
import os
import requests
import json
import yaml
import toml

from deepseek_agent import DeepSeekAgent

class BaseAgent:
    def __init__(self, template_name: str, use_proxy: bool = False, config_format: str = 'yaml'):
        self.template_name = template_name
        self.use_proxy = use_proxy
        self.config_format = config_format
        self.load_keys()
        self.load_template()
        self.history: List[Dict[str, str]] = []
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.session = self.setup_session()

    def load_keys(self):
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        keys_path = os.path.join(config_dir, 'keys.toml')
        with open(keys_path, 'r') as file:
            self.keys = toml.load(file)

    def load_template(self):
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')

        if self.config_format == 'yaml':
            config_path = os.path.join(config_dir, 'LLMs.yaml')
            with open(config_path, 'r') as file:
                templates = yaml.safe_load(file)
        elif self.config_format == 'toml':
            config_path = os.path.join(config_dir, 'LLMs.toml')
            with open(config_path, 'r') as file:
                templates = toml.load(file)
        else:
            raise ValueError(f"Unsupported config format: {self.config_format}")

        template = templates.get(self.template_name)
        if not template:
            raise ValueError(f"Unknown template: {self.template_name}")

        self.model_name = template['model_name']
        self.api_key = self.keys.get(template['provider'])
        if not self.api_key:
            raise ValueError(f"API key not found for provider: {template['provider']}")
        self.base_url = template.get('base_url', "http://localhost:1234/v1")

    def setup_session(self) -> requests.Session:
        session = requests.Session()
        if self.use_proxy:
            proxy = {
                'http': 'socks5h://localhost:9870',
                'https': 'socks5h://localhost:9870',
            }
            session.proxies.update(proxy)
        return session

    def query_model(self, model_name: str) -> Dict[str, Any]:
        response = self.session.get(f"{self.client.base_url}/models/{model_name}")
        return response.json()

    def set_system_prompt(self, system_prompt: str) -> None:
        """Set the initial system prompt for the agent."""
        self.history = [{"role": "system", "content": system_prompt}]

    def send_message(self, user_input: str, **kwargs: Any) -> Tuple[str, int]:
        """Send a message to the model and get a response."""
        self.history.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.history,
            **kwargs
        )
        assistant_message = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": assistant_message})
        return assistant_message, response.usage.total_tokens

    def reset_history(self) -> None:
        self.history = []

from deepseek_agent import DeepSeekAgent
    def __init__(self, model_name, api_key=None, base_url="https://api.deepseek.com", use_proxy=False, key_file="./deepseek.key"):
        super().__init__(model_name, api_key, base_url, use_proxy, key_file)

    def get_response(self, prompt, system_prompt="You are a helpful assistant"):
        self.set_system_prompt(system_prompt)
        return self.send_message(prompt)

    def send_message_json(self, user_input, system_prompt="You are a helpful assistant", json_format=True):
        """Send a message to the model and get a JSON response."""
        self.set_system_prompt(system_prompt)
        kwargs = {'response_format': {'type': 'json_object'}} if json_format else {}
        response, ntok = self.send_message(user_input, **kwargs)
        try:
            return json.loads(response), ntok
        except json.JSONDecodeError:
            return response, ntok  # Return raw response if not valid JSON

    def stream_response(self, prompt, system_prompt="You are a helpful assistant"):
        self.set_system_prompt(system_prompt)
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.history,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

def remove_code_block_delimiters(text):
    lines = text.splitlines()
    cleaned_lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(cleaned_lines)

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

# Example usage
if __name__ == "__main__":
    from deepseek_agent import DeepSeekAgent

    # Demonstrate different templates with YAML and TOML configurations
    templates = ["deepseek-chat", "gpt-3.5-turbo", "local-llama"]
    config_formats = ['yaml', 'toml']

    for template in templates:
        for config_format in config_formats:
            print(f"\n{template.upper()} Agent ({config_format.upper()} config):")
            agent = DeepSeekAgent(template, config_format=config_format)

            # Basic message example
            response, _ = agent.send_message("Hello, what can you tell me about your capabilities?")
            print(f"Response: {response[:100]}...")  # Print first 100 characters

            # JSON output example (if supported)
            try:
                json_response = agent.json_output("List three famous scientists in JSON format")
                print(f"JSON Output: {json_response}")
            except AttributeError:
                print("JSON output not supported for this template")

            # Streaming example
            print("Streaming Response (first 3 chunks):")
            for i, chunk in enumerate(agent.stream_response("Count from 1 to 10")):
                if i < 3:
                    print(chunk, end='', flush=True)
                else:
                    print("...", end='', flush=True)
                    break
            print("\n")

            # Display API key information
            print(f"API Key for {template}: {'*' * len(agent.api_key) if agent.api_key else 'Not set or not required'}")

    # Example with GPT-3.5 agent
    agent_gpt = DeepSeekAgent("gpt-3.5-turbo", config_format='yaml')
    print("\nGPT-3.5 Agent:")
    json_response = agent_gpt.json_output("Give me information about the planet Mars in JSON format")
    print("JSON Output:", json_response)

    # Example with local model
    agent_local = DeepSeekAgent("local-llama", config_format='toml')
    print("\nLocal Model Agent:")
    print("Streaming Response:")
    for chunk in agent_local.stream_response("Tell me a short story about AI."):
        print(chunk, end='', flush=True)

    # Keeping one example of each feature with the DeepSeek agent
    print("\nAdditional DeepSeek Agent Features:")

    # Numerical Derivative
    derivative_result = agent_deepseek.numerical_derivative("x^2", "x", 2)
    print("Numerical Derivative Result:", derivative_result)

    # Expression Steps
    steps = [
        {"name": "a", "expression": "2 * 3"},
        {"name": "b", "expression": "a + 4"},
        {"name": "c", "expression": "b ^ 2"}
    ]
    steps_result = agent_deepseek.evaluate_expression_steps(steps)
    print("Expression Steps Result:", steps_result)

    # Integral
    integral_result = agent_deepseek.compute_integral("x^2", "x", 0, 1)
    print("Integral Result:", integral_result)

    # Compare Derivatives
    comparison_result = agent_deepseek.compare_derivatives("x^3", "x", 2)
    print("Derivative Comparison Result:", comparison_result)

    # FIM Completion
    fim_result = agent_deepseek.fim_completion("def fibonacci(n):", "    return fib(n-1) + fib(n-2)")
    print("FIM Completion Result:", fim_result)

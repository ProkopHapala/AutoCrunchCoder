import openai
from openai import OpenAI
import os
import requests
import json

class BaseAgent:
    def __init__(self, model_name, api_key=None, base_url="http://localhost:1234/v1", use_proxy=False, key_file="./deepseek.key"):
        self.model_name = model_name
        self.history = []
        self.api_key = api_key or self.read_api_key(key_file)
        self.base_url = base_url
        self.use_proxy = use_proxy

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.session = self.setup_session()

    @staticmethod
    def read_api_key(key_file):
        with open(key_file, "r") as f:
            return f.read().strip()

    def setup_session(self):
        session = requests.Session()
        if self.use_proxy:
            proxy = {
                'http': 'socks5h://localhost:9870',
                'https': 'socks5h://localhost:9870',
            }
            session.proxies.update(proxy)
        return session

    def query_model(self, model_name):
        response = self.session.get(f"{self.client.base_url}/models/{model_name}")
        return response.json()

    def set_system_prompt(self, system_prompt):
        """Set the initial system prompt for the agent."""
        self.history = [{"role": "system", "content": system_prompt}]

    def send_message(self, user_input, **kwargs):
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

    def reset_history(self):
        self.history = []

class DeepSeekAgent(BaseAgent):
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
    agent = DeepSeekAgent("deepseek-chat")
    response = agent.get_response("Hello, how are you?")
    print(response)

    json_response, tokens = agent.send_message_json("Give me a JSON object with your name and role.")
    print(json_response, tokens)

    for chunk in agent.stream_response("Tell me a short story."):
        print(chunk, end='', flush=True)

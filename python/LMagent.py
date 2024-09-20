import openai
from openai import OpenAI
import os
import requests
import json

class BaseAgent:
    def __init__(self, model_name, api_key=None, base_url="http://localhost:1234/v1", bProxy=False, key_file="./deepseek.key"):
        self.model_name = model_name
        self.history = []
        self.api_key = api_key
        self.base_url = base_url
        self.bProxy = bProxy
        self.key_file = key_file

        if self.api_key is None:
            with open(self.key_file, "r") as f:
                self.api_key = f.read().strip()

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.session = requests.Session()
        if self.bProxy:
            proxy = {
                'http': 'socks5h://localhost:9870',
                'https': 'socks5h://localhost:9870',
            }
            self.session.proxies.update(proxy)

    def query_model(self, model_name):
        response = self.session.get(f"{self.client.base_url}/models/{model_name}")
        return response.json()

    def set_system_prompt(self, system_prompt):
        """Set the initial system prompt for the agent."""
        self.history.append({"role": "system", "content": system_prompt})

    def send_message(self, user_input, user_args={}):
        """Send a message to the model and get a response."""
        self.history.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.history,
            messages=self.history, 
            **user_args
        )
        assistant_message = response.choices[0].message.content
        ntok = response.usage.completion_tokens
        self.history.append({"role": "assistant", "content": assistant_message})
        return assistant_message, ntok

    def reset_history(self):
        """Reset the conversation history."""
        self.history = []

class DeepSeekAgent(BaseAgent):
    def __init__(self, model_name, api_key=None, base_url="https://api.deepseek.com", bProxy=False, key_file="./deepseek.key"):
        super().__init__(model_name, api_key, base_url, bProxy, key_file)

    def get_response(self, prompt, system_prompt="You are a helpful assistant"):
    def send_message_json(self, user_input, system_prompt="You are a helpful assistant", json_format=True):
        """Send a message to the model and get a JSON response."""
        self.set_system_prompt(system_prompt)
        return self.send_message(prompt)
        if json_format:
            user_args = {
                'response_format': {
                    'type': 'json_object'
                }
            }
        else:
            user_args = {}
        response, ntok = self.send_message(user_input, user_args)
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            pass  # Handle the case where the response is not valid JSON
        return response, ntok

    def stream_response(self, prompt, system_prompt="You are a helpful assistant"):
class DeepSeekAgent(BaseAgent):
    def __init__(self, model_name, api_key=None, base_url="https://api.deepseek.com", bProxy=False, key_file="./deepseek.key"):
        super().__init__(model_name, api_key, base_url, bProxy, key_file)
    def get_response(self, prompt, system_prompt="You are a helpful assistant"):
        self.set_system_prompt(system_prompt)
        return self.send_message(prompt)

    def stream_response(self, prompt, system_prompt="You are a helpful assistant"):
        self.set_system_prompt(system_prompt)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.history,
            stream=True
        )
        for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                ch0 = chunk.choices[0]
                delta = ch0.delta
                content = delta.content if delta else ''
                if content:
                    yield content

def remove_code_block_delimiters(text):
    lines = text.splitlines()
    cleaned_lines = [line for line in lines if not line.strip().startswith("```")]
    cleaned_text = "\n".join(cleaned_lines)
    return cleaned_text

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()


    cleaned_lines = [line for line in lines if

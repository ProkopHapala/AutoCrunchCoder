import os
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

class Agent(ABC):
    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or self.get_api_key()
        self.client = self.setup_client()

    @abstractmethod
    def get_api_key(self) -> str:
        pass

    @abstractmethod
    def setup_client(self):
        pass

    @abstractmethod
    def send_message(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def stream_message(self, messages: List[Dict[str, str]], **kwargs):
        pass

class OpenAIAgent(Agent):
    def get_api_key(self) -> str:
        return os.environ.get("OPENAI_API_KEY")

    def setup_client(self):
        from openai import OpenAI
        return OpenAI(api_key=self.api_key)

    def send_message(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
        return {
            "content": response.choices[0].message.content,
            "usage": response.usage.total_tokens
        }

    def stream_message(self, messages: List[Dict[str, str]], **kwargs):
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            **kwargs
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

class AnthropicAgent(Agent):
    def get_api_key(self) -> str:
        return os.environ.get("ANTHROPIC_API_KEY")

    def setup_client(self):
        import anthropic
        return anthropic.Anthropic(api_key=self.api_key)

    def send_message(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        response = self.client.messages.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
        return {
            "content": response.content[0].text,
            "usage": response.usage.output_tokens
        }

    def stream_message(self, messages: List[Dict[str, str]], **kwargs):
        with self.client.messages.stream(
            model=self.model_name,
            messages=messages,
            **kwargs
        ) as stream:
            for text in stream.text_stream:
                yield text

class GoogleAIAgent(Agent):
    def get_api_key(self) -> str:
        return os.environ.get("GOOGLE_API_KEY")

    def setup_client(self):
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        return genai

    def send_message(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        model = self.client.GenerativeModel(self.model_name)
        response = model.generate_content([m["content"] for m in messages], **kwargs)
        return {
            "content": response.text,
            "usage": None  # Google AI doesn't provide token usage information
        }

    def stream_message(self, messages: List[Dict[str, str]], **kwargs):
        model = self.client.GenerativeModel(self.model_name)
        response = model.generate_content([m["content"] for m in messages], stream=True, **kwargs)
        for chunk in response:
            yield chunk.text

# Factory function to create agents based on provider
def create_agent(provider: str, model_name: str, api_key: Optional[str] = None) -> Agent:
    if provider == "openai":
        return OpenAIAgent(model_name, api_key)
    elif provider == "anthropic":
        return AnthropicAgent(model_name, api_key)
    elif provider == "google":
        return GoogleAIAgent(model_name, api_key)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

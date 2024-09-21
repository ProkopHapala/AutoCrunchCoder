import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator
import toml
#import yaml
class Agent(ABC):
    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or self.get_api_key()
        self.client = self.setup_client()
        self.history: List[Dict[str, str]] = []
        self.max_context_length = 4096

    def load_keys(self):
        """
        Load the API keys from a TOML file. This method will be used to
        retrieve API keys for various providers if not present in the environment variables.
        """
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        #keys_path = os.path.join(config_dir, 'providers.key')
        keys_path = 'providers.key'
        with open(keys_path, 'r') as file:
            self.keys = toml.load(file)['api_keys']
            
    def load_template(self):
        """
        Load the LLM template configuration from a YAML or TOML file. It also checks for
        the API key in environment variables first, falling back to the TOML file if not found.
        """
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')

        config_path = os.path.join(config_dir, 'LLMs.toml')
        with open(config_path, 'r') as file:    templates = toml.load(file)

        self.template  = templates.get(self.template_name)
        if not self.template : raise ValueError(f"Unknown template: {self.template_name}")
        self.base_url   = self.template.get('base_url', "http://localhost:1234/v1")   # Load the base URL for the API
        self.model_name = self.template['model_name']
        self.max_context_length = self.template.get('max_context_length')
        self.get_api_key()

    @abstractmethod
    def get_api_key(self) -> str:
        pass

    @abstractmethod
    def setup_client(self):
        pass

    @abstractmethod
    def query(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        pass

    def update_history(self, new_message: Dict[str, str]):
        """
        Append a new message to the history and trim it if the total token count exceeds
        the maximum context length.
        """
        self.history.append(new_message)
        self.trim_history_if_needed()

    def trim_history_if_needed(self):
        """
        Trims the conversation history to ensure the total token count stays within the model's maximum context length.
        Removes older messages if necessary.
        """
        while self.estimate_token_count(self.history) > self.max_context_length:
            self.history.pop(0)

    def estimate_token_count(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate the total token count for a list of messages.
        Subclasses should override this method to provide a provider-specific token count estimation.
        """
        return sum(len(msg['content']) for msg in messages)

    def reset_history(self) -> None:
        self.history = []

# def create_agent(provider: str, model_name: str, api_key: Optional[str] = None) -> Agent:
#     if provider == "openai":
#         return OpenAIAgent(model_name, api_key)
#     elif provider == "anthropic":
#         return AnthropicAgent(model_name, api_key)
#     elif provider == "google":
#         return GoogleAIAgent(model_name, api_key)
#     else:
#         raise ValueError(f"Unsupported provider: {provider}")

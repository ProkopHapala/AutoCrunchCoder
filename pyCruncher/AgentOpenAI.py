import openai
from openai import OpenAI
import os
import requests
import json
from typing import Dict, Any, List, Tuple, Generator
from .Agent import Agent
    
class AgentOpenAI(Agent):
    def __init__(self, template_name: str):
        self.system_prompt = "You are a helpful assistant."
        self.template_name = template_name
        self.load_keys()
        self.load_template()
        self.setup_client()
        self.history: List[Dict[str, str]] = []
        self.session = requests.Session()
        self.tools = {}

    def setup_client(self):
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_api_key(self):
        # --- get API key
        provider_key_var = self.template['api_key_var']  # Get the environment variable name for API key
        self.api_key = os.getenv(provider_key_var)  # Attempt to load API key from environment variable
        if not self.api_key:                        # If not found in environment variables, fall back to the keys file
            provider_name = provider_key_var.split('_')[0].lower()  # e.g., 'deepseek' from 'DEEPSEEK_API_KEY'
            self.api_key  = self.keys.get(provider_name)
            if not self.api_key:  raise ValueError(f"API key not found for provider: {provider_name}")

    def set_system_prompt(self, system_prompt: str) -> None:
        """Set the initial system prompt for the agent."""
        self.system_prompt = system_prompt
        self.history = [{"role": "system", "content": system_prompt}]

    def query(self, prompt: str, bHistory=False, **kwargs: Any) -> str:
        """
        Send a message to the model while keeping track of the conversation history.
        This is useful for multi-turn conversations.
        """
        if bHistory:
            self.update_history({"role": "user", "content": prompt})   # Append user input to conversation history
            messages = self.history
        else:
            messages = [{"role": "user", "content": prompt}]         # Create a one-off message (no history used)  
        response = self.client.chat.completions.create(                  # Make a request to the model with the entire conversation history
            model=self.model_name,
            messages=messages,
            #tools=self.tools,
            **kwargs
        )
        assistant_message = response.choices[0].message.content                                      # Extract assistant's message from the response
        if bHistory: self.history.append({"role": "assistant", "content": assistant_message})   # Append assistant's message to history for future context
        return assistant_message

    def stream(self, prompt: str, bHistory=False, **kwargs: Any) -> Generator[str, None, None]:
        """
        Stream the response from the model while maintaining conversation history.
        Useful for streaming multi-turn conversations.
        """
        if bHistory:
            self.update_history({"role": "user", "content": prompt})   # Append user input to conversation history
            messages = self.history
        else:
            messages = [{"role": "user", "content": prompt}]           # Create a one-off message (no history used)  
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            #tools=self.tools,
            stream=True,
            **kwargs
        )        
        assistant_message = ""  # To accumulate the streamed content
        for chunk in stream:    # Yield content chunks as they arrive in the stream
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                assistant_message += content
                yield content
        
        # After the stream is exhausted, append the assistant's message to the history
        if bHistory: self.history.append({"role": "assistant", "content": assistant_message})

    def add_tool(self, name: str, description: str, parameters: Dict[str, Any]) -> None:
        """
        Add a new tool to the agent's toolkit.
        A tool is a function that the agent can call to perform a specific task by call to some extrnal API provied by user or service provider.
        """
        tool = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        self.tools.append(tool)

    def use_tool(self, prompt: str ) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.history,
            tools=self.tools
        )
        return response.choices[0].message

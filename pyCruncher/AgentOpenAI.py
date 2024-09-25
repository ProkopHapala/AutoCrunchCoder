import openai
from openai import OpenAI
import os
import requests
import json
from typing import Tuple, List, Dict, Any, Optional, Generator, Callable, Optional
from .Agent import Agent
    
class AgentOpenAI(Agent):
    def __init__(self, template_name: str, base_url=None):
        super().__init__(template_name, base_url=base_url )
        self.session = requests.Session()

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

    def query(self, prompt: str=None, bHistory=False, messages=None, bTools=True, **kwargs: Any) -> str:
        """
        Send a message to the model while keeping track of the conversation history.
        This is useful for multi-turn conversations.
        """
        #print( "AgentOpenAI::query()", prompt )
        if messages is None:
            messages = []
        # else:
        #     print( "AgentOpenAI::query() messages=\n" )
        #     for i,msg in enumerate(messages): print( "message[%i]:\n" %i,  msg )
        if prompt is not None:
            if bHistory:
                user_message = {"role": "user", "content": prompt}
                self.update_history(user_message)   # Append user input to conversation history
                messages = self.history + messages
            else:
                messages.append( {"role": "user", "content": prompt} )           # Create a one-off message (no history used)  
        if bTools and (len(self.tools)>0):
            #print( "call_1.tools :", self.tools )
            response = self.client.chat.completions.create(  model=self.model_name,  messages=messages, tools=self.tools, temperature=self.temperature, **kwargs)
            #print( "call_1.response :", response.choices[0].message.content )
        else: 
            response = self.client.chat.completions.create(  model=self.model_name,  messages=messages,                   **kwargs)
        message = response.choices[0].message
        message = self.try_tool(message, messages, **kwargs)
        #content = message.content                                 # Extract assistant's message from the response
        if bHistory: self.history.append(message)   # Append assistant's message to history for future context
        return message

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
            temperature=self.temperature,
            #tools=self.tools,
            stream=True,
            **kwargs
        )        
        self.assistant_message = ""  # To accumulate the streamed content
        for chunk in stream:    # Yield content chunks as they arrive in the stream
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                self.assistant_message += content
                yield content
        
        # After the stream is exhausted, append the assistant's message to the history
        if bHistory: self.history.append({"role": "assistant", "content": self.assistant_message})

    def extract_tool_call(self, message: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Check and extract the function call details from the OpenAI response.
        """
        if message.tool_calls:
            return message.tool_calls
        return None


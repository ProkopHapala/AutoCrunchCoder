import os
from typing import Tuple, List, Dict, Any, Optional, Generator
from .Agent import Agent
import google.generativeai as genai
from google.generativeai.types import ContentType, FunctionDeclaration

class AgentGoogle(Agent):
    def __init__(self, template_name: str, base_url=None):
        """
        Initialize the AgentGoogle instance.
        
        :param template_name: Name of the template to use
        :param base_url: Base URL for the API (optional)
        """
        super().__init__(template_name, base_url=base_url)
        self.session = None  # Google API doesn't use a session object

    def get_api_key(self) -> str:
        """
        Retrieve the API key from environment variables or the keys file.
        
        :return: The API key as a string
        :raises ValueError: If the API key is not found
        """
        provider_key_var = self.template['api_key_var']
        self.api_key = os.getenv(provider_key_var)
        if not self.api_key:
            provider_name = provider_key_var.split('_')[0].lower()
            self.api_key = self.keys.get(provider_name)
        if not self.api_key:
            raise ValueError(f"API key not found for provider: {provider_name}")
        return self.api_key

    def setup_client(self):
        """Configure the Google Generative AI client with the API key."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def query(self, prompt: str = None, bHistory: bool = False, messages: List[Dict[str, str]] = None, bTools: bool = True, **kwargs: Any) -> Dict[str, Any]:
        """
        Send a query to the Google AI model.
        
        :param prompt: The prompt to send to the model
        :param bHistory: Whether to use conversation history
        :param messages: List of previous messages in the conversation
        :param bTools: Whether to use tool calling
        :param kwargs: Additional keyword arguments for generation config
        :return: The model's response
        """
        try:
            if messages is None:
                messages = []
            
            if prompt is not None:
                if bHistory:
                    user_message = {"role": "user", "parts": [prompt]}
                    self.update_history(user_message)
                    messages = self.history + messages
                else:
                    messages.append({"role": "user", "parts": [prompt]})
            
            generation_config = self.prepare_generation_config(**kwargs)
            
            if bTools and self.tools:
                tools = [FunctionDeclaration(**tool) for tool in self.tools]
                response = self.model.generate_content(messages, generation_config=generation_config, tools=tools)
            else:
                response = self.model.generate_content(messages, generation_config=generation_config)
            
            response = self.try_tool(response, messages, **kwargs)
            
            if bHistory:
                self.history.append({"role": "model", "parts": [response.text]})
            
            return response
        except Exception as e:
            print(f"An error occurred during query: {str(e)}")
            raise

    def stream(self, prompt: str, bHistory: bool = False, **kwargs: Any) -> Generator[str, None, None]:
        """
        Stream a response from the Google AI model.
        
        :param prompt: The prompt to send to the model
        :param bHistory: Whether to use conversation history
        :param kwargs: Additional keyword arguments for generation config
        :return: A generator yielding response chunks
        """
        try:
            if bHistory:
                self.update_history({"role": "user", "parts": [prompt]})
                messages = self.history
            else:
                messages = [{"role": "user", "parts": [prompt]}]
            
            generation_config = self.prepare_generation_config(**kwargs)
            
            stream = self.model.generate_content(messages, generation_config=generation_config, stream=True)
            
            assistant_message = ""
            for chunk in stream:
                if chunk.text:
                    assistant_message += chunk.text
                    yield chunk.text
            
            if bHistory:
                self.history.append({"role": "model", "parts": [assistant_message]})
        except Exception as e:
            print(f"An error occurred during streaming: {str(e)}")
            raise

    def extract_tool_call(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Extract tool call information from the model's response.
        
        :param response: The model's response
        :return: A list of tool call dictionaries, or None if no tool calls are present
        """
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    return [{
                        "id": "function",  # Google API doesn't provide an ID, so we use a placeholder
                        "function": {
                            "name": part.function_call.name,
                            "arguments": part.function_call.args
                        }
                    }]
        return None

    def prepare_generation_config(self, **kwargs: Any) -> genai.types.GenerationConfig:
        """
        Prepare the generation configuration for the model.
        
        :param kwargs: Keyword arguments for configuration options
        :return: A GenerationConfig object
        """
        config = genai.types.GenerationConfig(
            candidate_count=kwargs.get('candidate_count', 1),
            stop_sequences=kwargs.get('stop_sequences', []),
            max_output_tokens=kwargs.get('max_output_tokens', self.max_context_length),
            temperature=kwargs.get('temperature', self.temperature)
        )
        return config

    def set_system_prompt(self, system_prompt: str) -> None:
        """
        Set the system prompt for the conversation.
        
        :param system_prompt: The system prompt to set
        """
        self.system_prompt = system_prompt
        self.history = [{"role": "system", "parts": [system_prompt]}]

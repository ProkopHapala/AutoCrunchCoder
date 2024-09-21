import os
from typing import Dict, Any, List, Generator
from Agent import Agent
import google.generativeai as genai

class GoogleAIAgent(Agent):
    def get_api_key(self) -> str:
        return os.environ.get("GOOGLE_API_KEY")

    def setup_client(self):
        genai.configure(api_key=self.api_key)
        return genai

    def get_max_context_length(self) -> int:
        # Implement this method to return the maximum context length for Google's model
        return 8192  # Assuming a maximum context length of 8192 tokens

    def query(self, prompt: str=None, bHistory=False, messages=None, bTools=True, **kwargs: Any) -> str:
        model = self.client.GenerativeModel(self.model_name)
        response = model.generate_content([m["content"] for m in messages], **kwargs)
        return response.text

    def query(self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        model = self.client.GenerativeModel(self.model_name)
        messages = [m["content"] for m in messages]
        response = model.generate_content(messages=messages, functions=functions, **kwargs)
        response = self.call_tool(response, messages, **kwargs)
        return response.text

    def stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        model = self.client.GenerativeModel(self.model_name)
        response = model.generate_content([m["content"] for m in messages], stream=True, **kwargs)
        for chunk in response:
            yield chunk.text

    def extract_tool_call(self, response: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Check and extract the function call details from the Google response.
        """
        if response.get("function_call"):
            function_name = response["function_call"]["name"]
            function_args = response["function_call"]["arguments"]
            return function_name, function_args
        return None, None


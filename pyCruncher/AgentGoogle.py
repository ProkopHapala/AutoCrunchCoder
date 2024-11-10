import os
from typing import Tuple, List, Dict, Any, Optional, Generator, Callable
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration #, FunctionParam
from .Agent import Agent
from .ToolScheme import schema

class AgentGoogle(Agent):
    def __init__(self, template_name: str, base_url=None):
        """
        Initialize the AgentGoogle instance.
        
        :param template_name: Name of the template to use
        :param base_url: Base URL for the API (optional)
        """
        super().__init__(template_name, base_url=base_url)
        self.session = None  # Google API doesn't use a session object

    # def get_api_key(self) -> str:
    #     """
    #     Retrieve the API key from environment variables or the keys file.
        
    #     :return: The API key as a string
    #     :raises ValueError: If the API key is not found
    #     """
    #     provider_key_var = self.template['api_key_var']
    #     self.api_key = os.getenv(provider_key_var)
    #     if not self.api_key:
    #         provider_name = provider_key_var.split('_')[0].lower()
    #         self.api_key = self.keys.get(provider_name)
    #     if not self.api_key:
    #         raise ValueError(f"API key not found for provider: {provider_name}")
    #     return self.api_key

    def setup_client(self):
        """Configure the Google Generative AI client with the API key."""
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel( self.model_name  )

    def get_response_text(self, message):
        #return response.choices[0].message.content
        return message.text

    def query(self, prompt: str = None, bHistory: bool = False, messages: List[Dict[str, str]] = None, bTools: bool = True, **kwargs: Any) -> Dict[str, Any]:
        """
        Send a query to the model with optional tool calling.
        Since tools are already stored in the correct format, they can be passed directly.
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

            #print( "AgentGoogle.query().messages = ", messages )

            # Prepare generation config
            generation_config = self.prepare_generation_config(**kwargs)

            #print( "AgentGoogle.query().generation_config = ", generation_config )

            # Directly use self.tools if tools are enabled
            if bTools and self.tools:
                #print( "AgentGoogle.query().tools = ", self.tools )
                response = self.client.generate_content(messages, generation_config=generation_config, tools=self.tools )
            else:
                response = self.client.generate_content(messages, generation_config=generation_config)

            #print( "AgentGoogle.query().response(BEFORE TOOL CALL) = ", response )

            response = self.try_tool(response, messages, **kwargs)   # Try to invoke any tool calls if present
            
            #print( "AgentGoogle.query().response(AFTER TOOL CALL) = ", response )

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
            
            stream = self.client.generate_content(messages, generation_config=generation_config, stream=True)
            
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
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    return [{
                        "id": "function",
                        "function": {
                            "name": part.function_call.name,
                            "arguments": part.function_call.args
                        }
                    }]
        return None

    def try_tool(self, response, messages: List[Dict[str, str]], **kwargs):
        tool_calls = self.extract_tool_call(response)
        if tool_calls is not None:
            if len(tool_calls) > 0:
                # Extract and handle each tool call
                for tool_call in tool_calls:
                    name = tool_call['function']['name']
                    if name is not None and name in self.tool_callbacks:
                        args = tool_call['function']['arguments']
                        
                        # Call the registered tool (function) and get the result
                        result = self.call_function(name, args)
                        
                        # Append the result of the tool call (as text) to the messages
                        #messages.append({"role": "function", "name": name, "parts": [result]})
                        #messages.append({"role": "function", "parts": [result]})
                        messages.append({"role": "model", "parts": [result]})

                for i,message in enumerate(messages): print( f"AgentGoogle::try_tool().messages[{i}]: {messages}")

                # Continue with the updated query, using only the tool result in the messages
                response = self.query(prompt=None, messages=messages, bTools=False, **kwargs)
                
        return response


    def register_tool(self, func: Callable[[Dict[str, Any]], str], name=None, bOnlyRequired=False):
        """
        Register a user-defined tool (function) in the correct format compatible with Google's API.
        """
        
        #print("AgentGoogle::register_tool()")

        tool_schema = schema(func, bOnlyRequired=bOnlyRequired)
        tool_name = tool_schema['name'] if name is None else name

        #print("AgentGoogle::register_tool().tool_schema: ", tool_schema)

        # Prepare function parameters in the correct format for Google's schema
        function_params = {
            param_name: {
                "type": param_info['type'],  # Correctly set "type" field
                "description": param_info['description']
            }
            for param_name, param_info in tool_schema['parameters']['properties'].items()
        }

        # Adjust the format for Google's `Schema` object, including "type": "object"
        function_params_for_google = {
            "type": "object",  # Specify that the parameters schema is an object
            "properties": function_params,
            "required": tool_schema['parameters']['required']  # Only include `required` and `properties`
        }

        #print("AgentGoogle::register_tool().function_params_for_google: ", function_params_for_google)

        # Create the tool definition directly compatible with Google API
        tool = FunctionDeclaration(
            name=tool_name,
            description=tool_schema['description'],
            parameters=function_params_for_google  # Correctly formatted parameters for Google
        )

        #print( "AgentGoogle::register_tool().tool= ", tool )

        # Store the tool directly in the self.tools list in the format Google expects
        self.tools.append(tool)

        # Register the callback for the tool to be called when the model requests it
        self.tool_callbacks[tool_name] = func

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

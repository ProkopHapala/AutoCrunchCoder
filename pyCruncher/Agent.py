import os
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any, Optional, Generator, Callable, Optional
import toml
import json
#import yaml

from .ToolScheme import schema


class Agent(ABC):
    def __init__(self, template_name: str, base_url=None ):
        self.system_prompt = "You are a helpful assistant."
        #self.model_name = model_name
        #self.api_key = api_key or self.get_api_key()
        #self.client = self.setup_client()
        self.history: List[Dict[str, str]] = []
        self.max_context_length = 4096
        self.temperature=0.0
        #self.tools = set()
        self.tools = []
        self.tool_callbacks = dict()

        self.template_name = template_name
        #self.load_keys()
        self.keys = None
        self.load_template()
        if base_url is not None: self.base_url = base_url
        self.setup_client()

    def get_api_key(self):
        #print( "Agent::get_api_key()" )
        provider_key_var = self.template['api_key_var']  # Get the environment variable name for API key
        #print( "provider_key_var ", provider_key_var )
        if (provider_key_var == "any") or (provider_key_var is None):
            self.api_key = "any"
            return
        self.api_key = os.getenv(provider_key_var)  # Attempt to load API key from environment variable
        if not self.api_key:   # If not found in environment variables, fall back to the keys file
            if self.keys is None: self.load_keys()
            provider_name = provider_key_var.split('_')[0].lower()  # e.g., 'deepseek' from 'DEEPSEEK_API_KEY'
            print( f"API_KEY not found by getenv({provider_key_var}) => try keys.get({provider_name})" )   
            self.api_key  = self.keys.get(provider_name)
            if not self.api_key:  raise ValueError(f"API key not found for provider: {provider_name}")

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
        print(f"Loading TOML from: {config_path}")
        try:
            with open(config_path, 'r') as file:    
                content = file.read()
                print("#=============== File content:")
                print(content)
                print("#===============")
                templates = toml.loads(content)  # Use loads instead of load
                print("#=============== Templates loaded successfully!")
                print("Available templates:", list(templates.keys()))
        except Exception as e:
            print(f"Error loading TOML: {str(e)}")
            raise

        #for t in templates: print(t)
        self.template  = templates.get(self.template_name)
        if not self.template : 
            print( f"ERROR in Agent::load_template() not such template ({self.template_name}) ")
            print( "available templates are: " )
            for k in templates.keys(): print(k)
            print( "eventually edit LLMs.toml to add new one" )
            raise ValueError(f"Unknown template: {self.template_name}")
        self.base_url   = self.template.get('base_url', "http://localhost:1234/v1")   # Load the base URL for the API
        self.model_name = self.template['model_name']
        self.max_context_length = self.template.get('max_context_length')
        self.get_api_key()

    # @abstractmethod
    # def get_api_key(self) -> str:
    #     pass

    @abstractmethod
    def get_response_text(self, response):
        pass

    @abstractmethod
    def setup_client(self):
        pass

    @abstractmethod
    def query(self, prompt: str=None, bHistory=False, messages=None, bTools=True, **kwargs: Any) -> str:
        """
        Send a query to the model with optional function calling capabilities.
        """
        pass

    @abstractmethod
    def stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """
        Stream a response from the model with optional function calling capabilities.
        """
        pass

    def try_tool(self, message, messages: List[Dict[str, str]], **kwargs):
        tool_calls = self.extract_tool_call(message) 
        if tool_calls is not None:
            if len(tool_calls) > 0:
                #print( "Agent::try_tool().message:\n", message.content )
                messages.append(message)
                ndone = 0
                for tool_call in tool_calls:
                    #print("Agent::try_tool() INPUTS: tool_call=", tool_call)
                    name = tool_call.function.name  # Use dot notation to access the function name
                    if name is not None:
                        if name in self.tool_callbacks:
                            args = json.loads(tool_call.function.arguments)  # Use dot notation for arguments as well
                            #print("Agent::try_tool().call_function() ", name, "  args= ", args)
                            result = self.call_function(name, args)
                            #print("Agent::try_tool().result: ", result)
                            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})  # Access tool_call.id using dot notation
                            ndone += 1  # Increment the count correctly
                if ndone > 0:
                    message = self.query( prompt=None, messages=messages, bTools=False, **kwargs)
        return message

    @abstractmethod
    def extract_tool_call(self, message: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Check if the response contains a function call and extract the function name and arguments.
        Return (None, None) if no function call is present.
        """
        pass

    def call_function(self, name: str, args: Dict[str, Any]) -> str:
        """
        Dynamically dispatch the function based on the function name and arguments provided by the model.
        """
        if name in self.tool_callbacks:
            #print( "Agent::call_function().INPUT  ", name ,"  arguments= ", args  )
            out = self.tool_callbacks[name](**args)   
            #print( "Agent::call_function().OUTPUT ", out  )
            return out
        else:
            return f"Error: Function {name} is not available."

    def register_tool(self, func: Callable[[Dict[str, Any]], str], name=None, bOnlyRequired=False ):
        """
        Register a user-defined tool (function) that can be called by the model.
        """
        #schema( function=function, bOnlyRequired=bOnlyRequired )
        tool = schema(func, bOnlyRequired=bOnlyRequired )    
        #pprint.pprint(schema, indent=2,  width=1000  )
        if name is None:
            name = tool['name']
        else:
            tool['name'] = name
        #print(json.dumps(tool, indent=2))
        self.tools.append( { "type": "function", "function": tool } )
        self.tool_callbacks[name] = func

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

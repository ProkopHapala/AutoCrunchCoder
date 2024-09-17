import openai
from openai import OpenAI
import os
import requests 

def remove_code_block_delimiters(text):
    lines = text.splitlines()   # Split the text into lines
    cleaned_lines = [line for line in lines if not line.strip().startswith("```")]   # Filter out lines that contain just the code block delimiters
    cleaned_text = "\n".join(cleaned_lines)  # Join the remaining lines back into a single string
    return cleaned_text

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

# ====== These free functions works, but maybe should be integrated to Agent

def initAgent( base_url="https://api.deepseek.com", api_key=None, key_file="./deepseek.key" ):
    if api_key is None:
        with open(key_file, "r") as f: api_key = f.read().strip()
        print(api_key)
    agent = OpenAI(api_key=api_key, base_url=base_url )
    return agent

def get_response( prompt="Who are you?", system_prompt="You are a helpful assistant", agent=None  ):
    if agent is None:
        agent = initAgent( base_url="https://api.deepseek.com", key_file="./deepseek.key" )
    response = agent.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt },
            {"role": "user",   "content": prompt },
        ],
        stream=False
    )
    return response.choices[0].message.content

def stream_response( prompt="Who are you?", system_prompt="You are a helpful assistant", agent=None ):
    if agent is None:
        agent = initAgent( base_url="https://api.deepseek.com", key_file="./deepseek.key" )
    response = agent.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt },
            {"role": "user",   "content": prompt },
        ],
        stream=True  # Enable streaming
    )
    for chunk in response:
        # Print the raw chunk for debugging
        #print("DEBUG chunk:", chunk)  
        # Check if 'choices' exists and has content
        if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
            ch0 = chunk.choices[0]  # Access the first choice
            delta = ch0.delta  # Directly access delta
            content = delta.content if delta else ''  # Get content from delta
            #print("DEBUG choices[0]:", ch0)  
            #print("DEBUG delta:", delta)  
            #print("DEBUG content:", content)  
            if content:  # Only yield if content is not empty
                yield content  # Yield the content


class Agent:
    def __init__(self, model_name, api_key="any", base_url="http://localhost:1234/v1", bProxy=False ):
        #tunnel_port = 8888     # The port where your SSH tunnel forwards the requests
        #base_url = f"http://localhost:{tunnel_port}/v1"     # Set the base URL to use the SSH tunnel (local machine)
        #base_url = "http://10.26.201.142:1234/v1"

        #self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.history = []
       
        # Set the proxy settings for OpenAI client
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.session = requests.Session()
        if bProxy:
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
            **user_args
        )
        #assistant_message = response.choices[0].message['content']
        assistant_message = response.choices[0].message.content
        ntok  =  response.usage.completion_tokens
        self.history.append({"role": "assistant", "content": assistant_message})
        return assistant_message, ntok

    def reset_history(self):
        """Reset the conversation history."""
        self.history = []

# Example usage
if __name__ == "__main__":
    # Initialize the agent with a specific model
    agent = Agent(model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf")

    # Set the system prompt to guide the behavior of the assistant
    agent.set_system_prompt("You are a helpful assistant skilled in coding and providing detailed explanations.")

    # Interaction loop
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
        response = agent.send_message(user_input)
        print("LM Studio: " + response)

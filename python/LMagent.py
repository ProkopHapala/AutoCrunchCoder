import openai
from openai import OpenAI

class Agent:
    def __init__(self, model_name, api_key="any", base_url="http://localhost:1234/v1"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.history = []

    def set_system_prompt(self, system_prompt):
        """Set the initial system prompt for the agent."""
        self.history.append({"role": "system", "content": system_prompt})

    def send_message(self, user_input):
        """Send a message to the model and get a response."""
        self.history.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.history
        )
        #assistant_message = response.choices[0].message['content']
        assistant_message = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": assistant_message})
        return assistant_message

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

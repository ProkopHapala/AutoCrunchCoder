import sys
import os
import unittest
from google.generativeai import list_models
sys.path.append("../")
from pyCruncher.AgentGoogle import AgentGoogle

class TestAgentGoogle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Set up the AgentGoogle instance for all tests.
        Skips all tests if initialization fails.
        """
        try:
            cls.agent = AgentGoogle("gemini-1.5-flash")
        except ValueError as e:
            raise unittest.SkipTest(f"Failed to initialize AgentGoogle: {str(e)}")

    @classmethod
    def tearDownClass(cls):
        """
        Clean up after all tests have run.
        """
        # Add any necessary cleanup here, e.g., closing connections, deleting test data, etc.
        pass

    def test_query(self):
        """Test the basic query functionality."""
        prompt = "Write a C++ function to calculate energy and force from Lennard-Jones potential"
        response = self.agent.query(prompt)
        self.assertIsNotNone(response)
        self.assertTrue(len(response.text) > 0)
        self.assertIn("Lennard-Jones", response.text)
        print("Query response:")
        print(response.text)
        
    def test_stream(self):
        """Test the streaming functionality."""
        prompt = "Explain the concept of quantum entanglement in 50 words"
        stream = self.agent.stream(prompt)
        full_response = ""
        for chunk in stream:
            full_response += chunk
            print(chunk, end='', flush=True)
        self.assertTrue(len(full_response) > 0)
        self.assertLess(len(full_response.split()), 100)  # Roughly 50 words, allowing some flexibility
        print("\nFull streamed response:", full_response)
        
    def test_tool_calling(self):
        """Test the tool calling functionality."""
        def dummy_tool(x: int, y: int) -> int:
            return x + y
        
        self.agent.register_tool(dummy_tool)
        prompt = "Add the numbers 5 and 7 using the available tool"
        response = self.agent.query(prompt, bTools=True)
        self.assertIsNotNone(response)
        self.assertIn("12", response.text)  # The result of 5 + 7
        print("Tool calling response:")
        print(response.text)

    def test_history(self):
        """Test the conversation history functionality."""
        prompt1 = "What is the capital of France?"
        prompt2 = "What is its population?"
        
        response1 = self.agent.query(prompt1, bHistory=True)
        self.assertIn("Paris", response1.text)
        
        response2 = self.agent.query(prompt2, bHistory=True)
        self.assertIn("Paris", response2.text)
        self.assertIn("population", response2.text)
        
        print("History-based responses:")
        print("Response 1:", response1.text)
        print("Response 2:", response2.text)

    def test_error_handling(self):
        """Test error handling for invalid model names."""
        with self.assertRaises(ValueError):
            invalid_agent = AgentGoogle("invalid-model-name")

    def test_system_prompt(self):
        """Test the system prompt functionality."""
        system_prompt = "You are a helpful assistant specialized in physics."
        self.agent.set_system_prompt(system_prompt)
        response = self.agent.query("What is Newton's first law of motion?", bHistory=True)
        self.assertIn("Newton", response.text)
        self.assertIn("law", response.text)
        print("System prompt response:")
        print(response.text)

def test( bStream=False, prompt = "Write a C++ function to calculate energy and force from Lennard-Jones potential", model="gemini-flash" ):
    agent = AgentGoogle(model)
    print("Available models:", agent.client.models.list())
    print("user:  "+prompt+"\n\n")
    print("agent: "+"\n\n")
    if bStream:
        for chunk in agent.stream(prompt): print(chunk, flush=True, end="")
    else:
        result = agent.query(prompt)
        print(result)

def list_available_models():
        """List available models from Google Gemini API."""
        models = list_models()
        print("Available Models:")
        for i,model in enumerate(models):
            #print( f"model[{i}]: ", model  )
            print( f"model[{i}]: ", model.display_name  )
            #print(f"Model ID: {model['name']}, Model Display Name: {model['display_name']}")
        return models

if __name__ == "__main__":

    list_available_models()

    #test( bStream = True, model="gemini-flash" )
    test( bStream = True, model="gemini-pro-exp" )

    #unittest.main()

"""
How to run these tests:

1. Ensure you have the necessary dependencies installed:
   pip install google-generativeai unittest

2. Set up your Google API key:
   - Create a file named 'google.key' in the same directory as this test file
   - Add your Google API key to this file

3. Run the tests using the following command:
   python -m unittest test_GoogleAI.py

Note: These tests interact with the Google AI API and may incur costs. 
Make sure you understand the pricing and usage limits of your API key before running these tests.
It's recommended to monitor your usage and set up billing alerts to avoid unexpected charges.
"""

# Previous code (kept for reference)
"""
import google.generativeai as genai
import os

#genai.configure(api_key=os.environ["API_KEY"])
with open( 'google.key', "r") as f: api_key = f.read().strip()
print(api_key)

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content( "Write me C++ function which calculates energy and force from Lennard-Jones potential" )
print(response.text)
with open( 'test_GoogleAI_response.md', "w") as f: f.write(response.text)
"""

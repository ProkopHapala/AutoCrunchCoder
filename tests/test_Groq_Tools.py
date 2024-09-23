import sys
import os
import pprint
import json

sys.path.append("../")

from pyCruncher.AgentOpenAI import AgentOpenAI
from pyCruncher.tools import symbolic_derivative

def test( prompt = "What is the derivative of Lenard-Jones poential (use tool `symbolic_derivative`) ?" ):
    agent = AgentOpenAI("groq-llama-70b")
    agent.register_tool(symbolic_derivative, bOnlyRequired=True )
    print("User:  "+prompt+"\n")
    message = agent.query(prompt)
    print("Agent(final):\n", message.content)

if __name__ == "__main__":
    test()

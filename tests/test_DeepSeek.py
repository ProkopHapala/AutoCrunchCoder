import sys
import os

sys.path.append("../")
from pyCruncher.AgentDeepSeek import AgentDeepSeek

def test( bStream=False, prompt = "Write a C++ function to calculate energy and force from Lennard-Jones potential" ):
    agent = AgentDeepSeek()
    print("user:  "+prompt+"\n\n")
    print("agent: "+"\n\n")
    if bStream:
        for chunk in agent.stream(prompt): print(chunk, flush=True, end="")
    else:
        result = agent.query(prompt)
        print(result)

if __name__ == "__main__":
    test( bStream = True )
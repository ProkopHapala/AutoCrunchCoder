import sys
import os

sys.path.append("../")
from pyCruncher.AgentOpenAI import AgentOpenAI

"""
source ~/venvML/bin/activate
pip install openai
"""

prompt = """
Write OpenCL kernell to to solve n-body problem for n-particles with Lennard-Jones potential.
Use R_0, E_0 for position for minimum and energy at minimum. 
Try to optimize the performance by pre-calculating subespesion, and avoid using costly functions like `pow()`. 
Also use workgroup local memory to pre-load the particles to avoid global memory bottleneck.
"""

def test( model="lm-llama-8b", bStream=False ):
    agent = AgentOpenAI(model)
    print("Available models:", agent.client.models.list())
    print("user:  "+prompt+"\n\n")
    print("agent: "+"\n\n")
    if bStream:
        for chunk in agent.stream(prompt): print(chunk, flush=True, end="")
    else:
        result = agent.query(prompt)
        print(result)

if __name__ == "__main__":
    #test( model="lm-llama-8b",    bStream = True )
    test( model="fzu-Qwen25-32b", bStream = True )

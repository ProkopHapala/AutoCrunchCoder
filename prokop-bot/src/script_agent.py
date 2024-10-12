import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
parent_dir = os.path.dirname(parent_dir)
# print( "script_agent.py  os.getcwd(): ", os.getcwd() )
# print( "script_agent.py  parent_dir: ", parent_dir )

sys.path.append(parent_dir)
from pyCruncher.AgentDeepSeek import AgentDeepSeek
#from pyCruncher.AgentDeepSeek import AgentDeepSeek

def main(prompt):
    agent = AgentDeepSeek()
    result = agent.query(prompt)
    print(result.content)

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "No input provided"
    main(prompt)
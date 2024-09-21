import sys
import os
import pprint
import json

sys.path.append("../")

from pyCruncher.AgentDeepSeek import AgentDeepSeek
from pyCruncher.tools import symbolic_derivative

def test_math_tools():

    #schema = ts.schema(symbolic_derivative, bOnlyRequired=True )    
    #pprint.pprint(schema, indent=2,  width=1000  )
    #print(json.dumps(schema, indent=2))

    prompt = "What is the derivative of Lenard-Jones poential (use tool `symbolic_derivative`) ?"

    agent = AgentDeepSeek()
    agent.register_tool(symbolic_derivative, bOnlyRequired=True )

    print("User:  "+prompt+"\n")
    message = agent.query(prompt)
    print("Agent(final):\n", message.content)

    #result = symbolic_derivative( '4*epsilon*((sigma/r)^12 - (sigma/r)^6)', 'r' )
    #print( "symbolic_derivative().result:   ", result )


if __name__ == "__main__":
    test_math_tools()

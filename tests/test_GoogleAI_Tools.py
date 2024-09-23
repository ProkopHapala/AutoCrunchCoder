import sys
import os
import pprint
import json

sys.path.append("../")

#from pyCruncher.AgentDeepSeek import AgentDeepSeek
from pyCruncher.AgentGoogle import AgentGoogle
from pyCruncher.tools import symbolic_derivative

def test( prompt = "What is the derivative of Lenard-Jones poential (use tool `symbolic_derivative`) ?", model="gemini-flash" ):
    #schema = ts.schema(symbolic_derivative, bOnlyRequired=True )    
    #pprint.pprint(schema, indent=2,  width=1000  )
    #print(json.dumps(schema, indent=2))
    agent = AgentGoogle(model)
    #agent = AgentDeepSeek()
    agent.register_tool(symbolic_derivative, bOnlyRequired=True )
    print("User:  "+prompt+"\n")
    message = agent.query(prompt)

    #txt = ''.join(message.candidates[0].content.parts)

    # Extract the text from the first candidate's parts
    if message.candidates and message.candidates[0].content and message.candidates[0].content.parts:
        txt = ''.join([part.text for part in message.candidates[0].content.parts])
        print("Agent(final):\n", txt)
    else:
        print("No response received.")

    #print("Agent(final):\n", txt )
    #result = symbolic_derivative( '4*epsilon*((sigma/r)^12 - (sigma/r)^6)', 'r' )
    #print( "symbolic_derivative().result:   ", result )


if __name__ == "__main__":
    test()

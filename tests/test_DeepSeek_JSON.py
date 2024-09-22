import sys
import os

sys.path.append("../")

from pyCruncher.AgentDeepSeek import AgentDeepSeek

def test( bStream = False, prompt = "Give me information about the planet Mars." ):
    agent = AgentDeepSeek()
    post_prompt = " Output strictly JSON format."
    #prompt = "Provide a simple recipe for chocolate chip cookies."
    print("user:  "+prompt+"\n\n")
    print("agent: "+"\n\n")
    if bStream:
        for chunk in agent.stream_json(prompt+post_prompt): print(chunk, flush=True, end="")
    else:
        result = agent.query_json(prompt+post_prompt)
        print(result)
    print( "\n\nagent.json: ", agent.answer_json )

if __name__ == "__main__":
    test( bStream = True )

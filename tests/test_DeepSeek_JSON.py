import sys
import os

sys.path.append("../")

from pyCruncher.AgentDeepSeek import AgentDeepSeek

def test_json_output( bStream = False ):
    agent = AgentDeepSeek()

    post_prompt = " Output strictly JSON format."

    prompt = "Give me information about the planet Mars."
    #prompt = "Provide a simple recipe for chocolate chip cookies."

    print("user:  "+prompt+"\n\n")
    print("agent: "+prompt+"\n\n")
    if bStream:
        for chunk in agent.stream_json(prompt+post_prompt): print(chunk, flush=True, end="")
    else:
        result = agent.query_json(prompt+post_prompt)
        print(result)
    print( "\n\nagent.json: ", agent.answer_json )

if __name__ == "__main__":
    #test_json_output()
    test_json_output( bStream = True )

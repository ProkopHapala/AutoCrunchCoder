import sys
import os

sys.path.append("../")

from pyCruncher.AgentDeepSeek import AgentDeepSeek

def test_json_output( bStream = False ):
    agent = AgentDeepSeek("deepseek-coder")

    if bStream:

        prompt = "Give me information about the planet Mars in JSON format"
        print("JSON Output for Mars information:")
        for chunk in agent.stream_json(prompt): print(chunk, flush=True, end="")
        print( "agent.answer_json: ", agent.answer_json )

        prompt = "Provide a simple recipe for chocolate chip cookies in JSON format"
        print("\nJSON Output for chocolate chip cookie recipe:")
        for chunk in agent.stream_json(prompt): print(chunk, flush=True, end="")
        print( "agent.answer_json: ", agent.answer_json )

    else:

        # Test case 1: Get information about a planet
        prompt = "Give me information about the planet Mars in JSON format"
        result = agent.query_json(prompt)
        print("JSON Output for Mars information:")
        print(result)

        # Test case 2: Get a recipe in JSON format
        prompt = "Provide a simple recipe for chocolate chip cookies in JSON format"
        result = agent.query_json(prompt)
        print("\nJSON Output for chocolate chip cookie recipe:")
        print(result)

if __name__ == "__main__":
    #test_json_output()
    test_json_output( bStream = True )

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.deepseek_agent import DeepSeekAgent

def test_json_output():
    agent = DeepSeekAgent("deepseek-chat")

    # Test case 1: Get information about a planet
    prompt = "Give me information about the planet Mars in JSON format"
    result = agent.json_output(prompt)
    print("JSON Output for Mars information:")
    print(result)

    # Test case 2: Get a recipe in JSON format
    prompt = "Provide a simple recipe for chocolate chip cookies in JSON format"
    result = agent.json_output(prompt)
    print("\nJSON Output for chocolate chip cookie recipe:")
    print(result)

if __name__ == "__main__":
    test_json_output()

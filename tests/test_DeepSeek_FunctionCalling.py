import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.deepseek_agent import DeepSeekAgent

def get_weather(location):
    # This is a mock function. In a real scenario, you would call an actual weather API.
    return f"The weather in {location} is sunny and 25°C."

def test_function_calling():
    agent = DeepSeekAgent("deepseek-chat")

    # Add a tool for getting weather information
    agent.add_tool(
        name="get_weather",
        description="Get weather information for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and country, e.g. London, UK",
                }
            },
            "required": ["location"]
        }
    )

    # Test the function calling
    response = agent.use_tool("What's the weather like in Paris, France?")
    print("Function Calling Response:")
    print(response)

    # In a real scenario, you would then call the actual function based on the model's response
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call.function.name == "get_weather":
                location = tool_call.function.arguments["location"]
                weather_info = get_weather(location)
                print(f"\nActual weather information: {weather_info}")

if __name__ == "__main__":
    test_function_calling()

# DeepSeek API docs


## API call example

```python
from openai import OpenAI

client = OpenAI(api_key="<DeepSeek API Key>", base_url="https://api.deepseek.com")


response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)
```

## FIM Completion (Beta)

In FIM (Fill In the Middle) completion, users can provide a prefix and a suffix (optional), and the model will complete the content in between. FIM is commonly used for content completion、code completion.

#### Notice

The max tokens of FIM completion is 4K.
The user needs to set base_url=https://api.deepseek.com/beta to enable the Beta feature.

#### Sample Code

Below is a complete Python code example for FIM completion. In this example, we provide the beginning and the end of a function to calculate the Fibonacci sequence, allowing the model to complete the content in the middle.

```Python
from openai import OpenAI

client = OpenAI(
    api_key="<your api key>",
    base_url="https://api.deepseek.com/beta",
)

response = client.completions.create(
    model="deepseek-coder",
    prompt="def fib(a):",
    suffix="    return fib(a-1) + fib(a-2)",
    max_tokens=128
)
print(response.choices[0].text)
```


## JSON Output

In many scenarios, users need the model to output in strict JSON format to achieve structured output, facilitating subsequent parsing.

DeepSeek provides JSON Output to ensure the model outputs valid JSON strings.

#### Notice

To enable JSON Output, users should:

Set the response_format parameter to {'type': 'json_object'}.
Include the word "json" in the system or user prompt, and provide an example of the desired JSON format to guide the model in outputting valid JSON.
Set the max_tokens parameter reasonably to prevent the JSON string from being truncated midway.


#### Sample Code


Here is the complete Python code demonstrating the use of JSON Output:

```Python
import json
from openai import OpenAI

client = OpenAI(
    api_key="<your api key>",
    base_url="https://api.deepseek.com",
)

system_prompt = """
The user will provide some exam text. Please parse the "question" and "answer" and output them in JSON format. 

EXAMPLE INPUT: 
Which is the highest mountain in the world? Mount Everest.

EXAMPLE JSON OUTPUT:
{
    "question": "Which is the highest mountain in the world?",
    "answer": "Mount Everest"
}
"""

user_prompt = "Which is the longest river in the world? The Nile River."

messages = [{"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}]

response = client.chat.completions.create(
    model="deepseek-coder",
    messages=messages,
    response_format={
        'type': 'json_object'
    }
)

print(json.loads(response.choices[0].message.content))
```

The model will output:

```JSON
{
    "question": "Which is the longest river in the world?",
    "answer": "The Nile River"
}
```


## Function Calling

Function Calling allows the model to call external tools to enhance its capabilities.

## Sample Code

Here is an example of using Function Calling to get the current weather information of the user's location, demonstrated with complete Python code.

For the specific API format of Function Calling, please refer to the Chat Completion documentation.

```Python
from openai import OpenAI

def send_messages(messages):
    response = client.chat.completions.create(
        model="deepseek-coder",
        messages=messages,
        tools=tools
    )
    return response.choices[0].message

client = OpenAI(
    api_key="<your api key>",
    base_url="https://api.deepseek.com",
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather of an location, the user shoud supply a location first",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    }
                },
                "required": ["location"]
            },
        }
    },
]

messages = [{"role": "user", "content": "How's the weather in Hangzhou?"}]
message = send_messages(messages)
print(f"User>\t {messages[0]['content']}")

tool = message.tool_calls[0]
messages.append(message)

messages.append({"role": "tool", "tool_call_id": tool.id, "content": "24℃"})
message = send_messages(messages)
print(f"Model>\t {message.content}")
```

The execution flow of this example is as follows:

 * User: Asks about the current weather in Hangzhou
 * Model: Returns the function get_weather({location: 'Hangzhou'})
 * User: Calls the function get_weather({location: 'Hangzhou'}) and provides the result to the model
 * Model: Returns in natural language, "The current temperature in Hangzhou is 24°C."

Note: In the above code, the functionality of the get_weather function needs to be provided by the user. The model itself does not execute specific functions.
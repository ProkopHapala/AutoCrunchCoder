# Anthropic AI studio API docs

install
```
pip install anthropic
```

```
export ANTHROPIC_API_KEY=<YOUR_API_KEY>   
```

## API call example

```python
import anthropic

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="my_api_key",
)
message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude"}
    ]
)
print(message.content)
```
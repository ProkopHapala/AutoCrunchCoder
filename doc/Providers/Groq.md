# Groq API docs

## Instalation 

install
```
pip install groq
```

setup api key
```
export GROQ_API_KEY=<your-api-key-here>
```

## API call example

Performing a Chat Completion:

```Python
import os

from groq import Groq

client = Groq( api_key=os.environ.get("GROQ_API_KEY"), )

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Explain the importance of fast language models",
        }
    ],
    model="llama3-8b-8192",
)

print(chat_completion.choices[0].message.content)
```

Now that you have successfully received a chat completion, you can try out the other endpoints in the API.

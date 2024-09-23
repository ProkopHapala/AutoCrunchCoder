# OpenRouter API docs

## Instalation


setup api key
```
export OPENROUTER_API_KEY=<your-api-key-here>
```

## API call example

using OpenAI API

```python
import OpenAI from "openai"

const openai = new OpenAI({
  baseURL: "https://openrouter.ai/api/v1",
  apiKey: $OPENROUTER_API_KEY,
  defaultHeaders: {
    "HTTP-Referer": $YOUR_SITE_URL, // Optional, for including your app on openrouter.ai rankings.
    "X-Title": $YOUR_SITE_NAME, // Optional. Shows in rankings on openrouter.ai.
  }
})
async function main() {
  const completion = await openai.chat.completions.create({
    model: "openai/gpt-3.5-turbo",
    messages: [
      { role: "user", content: "Say this is a test" }
    ],
  })

  console.log(completion.choices[0].message)
}
main()
```

using just python requests and json

```Python
import requests
import json

response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": f"{YOUR_SITE_URL}", # Optional, for including your app on openrouter.ai rankings.
    "X-Title": f"{YOUR_APP_NAME}", # Optional. Shows in rankings on openrouter.ai.
  },
  data=json.dumps({
    "model": "openai/gpt-3.5-turbo", # Optional
    "messages": [
      { "role": "user", "content": "What is the meaning of life?" }
    ]

  })
)
```

Now that you have successfully received a chat completion, you can try out the other endpoints in the API.

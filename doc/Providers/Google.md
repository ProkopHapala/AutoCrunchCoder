# Google AI studio API docs

install
```
pip install -q -U google-generativeai
```

setup api key
```
export GOOGLE_API_KEY=<YOUR_API_KEY>
```

## API call example

```python
import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
with open( 'google.key', "r") as f: api_key = f.read().strip()
print(api_key)

genai.configure(api_key=api_key)


model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content( "Write me C++ function which calculates energy and force from Lennard-Jones potential" )
print(response.text)
with open( 'test_GoogleAI_response.md', "w") as f: f.write(response.text)
```
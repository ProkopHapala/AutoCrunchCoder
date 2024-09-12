import subprocess
import json

task="Please write me a C/C++ function which evaluates gaussian fuctions for array of n points"
with open("./deepseek.key", "r") as f: api_key = f.read()

def decode_json(response, fname='response_formated.md' ):
    try:
        response_json = json.loads(response)
        if "choices" in response_json:
            content = response_json["choices"][0]["message"]["content"]
            print(content)
            with open(fname, "w") as f: f.write(content)
        else:
            print("No 'choices' field in the response")
    except json.JSONDecodeError:
        print("Failed to decode JSON. Response may not be in valid JSON format.")

curl_message = f"""
curl -X POST https://api.deepseek.com/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer {api_key}" \\
  -d '{{ 
        "model": "deepseek-coder", 
        "messages": [
          {{"role": "system", "content": "You are a helpful assistant for programming scientific code."}}, 
          {{"role": "user", "content": "{task}"}}
        ], 
        "stream": false 
      }}'
"""

# ======= BODY

print( curl_message )
print( "==============" )

#with open("./response.txt", "r") as f: response = f.read()
result = subprocess.run(curl_message, shell=True, capture_output=True, text=True)

response = result.stdout
print("Response:",response )
with open("./response.txt", "w") as f: f.write(response)

print("Error (if any):", result.stderr)

print( "\n\n============== DECODE JSON ==============\n\n" )

decode_json(response)

print( "\n\n============== DONE ==============\n\n" )



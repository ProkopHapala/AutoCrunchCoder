from openai import OpenAI

def initAgent( base_url="https://api.deepseek.com", api_key=None, key_file="./deepseek.key" ):
    if api_key is None:
        with open(key_file, "r") as f: api_key = f.read().strip()
        print(api_key)
    agent = OpenAI(api_key=api_key, base_url=base_url )
    return agent

def get_response( prompt="Who are you?", system_prompt="You are a helpful assistant", agent=None  ):
    if agent is None:
        agent = initAgent( base_url="https://api.deepseek.com", key_file="./deepseek.key" )
    response = agent.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt },
            {"role": "user",   "content": prompt },
        ],
        stream=False
    )
    return response.choices[0].message.content

def stream_response( prompt="Who are you?", system_prompt="You are a helpful assistant", agent=None ):
    if agent is None:
        agent = initAgent( base_url="https://api.deepseek.com", key_file="./deepseek.key" )
    response = agent.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt },
            {"role": "user",   "content": prompt },
        ],
        stream=True  # Enable streaming
    )
    for chunk in response:
        # Print the raw chunk for debugging
        #print("DEBUG chunk:", chunk)  
        # Check if 'choices' exists and has content
        if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
            ch0 = chunk.choices[0]  # Access the first choice
            delta = ch0.delta  # Directly access delta
            content = delta.content if delta else ''  # Get content from delta
            #print("DEBUG choices[0]:", ch0)  
            #print("DEBUG delta:", delta)  
            #print("DEBUG content:", content)  
            if content:  # Only yield if content is not empty
                yield content  # Yield the content


#get_response( prompt="Write me C++ function which calculates energy and force from Lennard-Jones potential" )

for part in stream_response( prompt="Write me C++ function which calculates energy and force from Lennard-Jones potential" ):
    print(part, end='', flush=True)  # Print each part as it comes in
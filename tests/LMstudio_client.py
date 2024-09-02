#!/usr/bin/python

'''
Usage notes:

1) Activate Environement like this
>> source ~/venvML/bin/activate

2)In case of problems check the server status like this
>> curl http://localhost:1234/v1/models
'''

import openai
from openai import OpenAI

client = OpenAI(api_key="any", base_url="http://localhost:1234/v1")
def send_message(prompt):    
    response = client.chat.completions.create(
        #model="Phi-3.1-mini-128k-instruct-Q4_K_M.gguf",  # Your model name
        model="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        #model="QuantFactory/deepseek-math-7b-instruct-GGUF/deepseek-math-7b-instruct.Q4_0.gguf",
        messages=[{"role": "user", "content": prompt}]
        # messages=[
        #     {"role": "system", "content": system_prompt },
        #     {"role": "user",   "content": user_prompt   }
        # ]
    )
    return response.choices[0].message.content

while True:
    user_input = input("You: ")
    if user_input.lower() == 'exit':
        break
    response = send_message(user_input)
    print("LM Studio: " + response)

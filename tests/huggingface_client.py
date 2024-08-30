#!/usr/bin/python

'''
How To:
1) Actiavte environment
>> source ~/venvML/bin/activate
2) Run script
>> python huggingface_client.py

'''

#from huggingface_hub import InferenceClient,login
import huggingface_hub as hf

client = hf.InferenceClient(model="gpt2")  # Initialize the InferenceClient for a specific model

key = open("./huggingface.key","r").read(); print("key=",key)
hf.login(key)

response = client.text_generation("Once upon a time in a land far away,")   # Send a prompt to the model and get the response
print(response)

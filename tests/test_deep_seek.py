from openai import OpenAI

'''
Usage notes:
1) Activate Environement like this:
source ~/venvML/bin/activate
'''

import sys
sys.path.append('../python')
import LMagent as lm

with open("./deepseek.key", "r") as f: api_key = f.read()
print(api_key)

model="deepseek-chat"
#model="deepseek-coder"

coder = lm.Agent(model_name=model, api_key=api_key, base_url="https://api.deepseek.com" )
coder.set_system_prompt( lm.read_file( '../prompts/ImplementPotential/matematician_system_prompt.md' ) )
response = coder.send_message( lm.read_file( 'debug_promt_simplify.md' ) ); 

print(response)
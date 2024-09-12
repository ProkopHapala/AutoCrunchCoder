#!/usr/bin/python

'''
Usage notes:

1) Activate Environement like this
>> source ~/venvML/bin/activate

2)In case of problems check the server status like this
>> curl http://localhost:1234/v1/models
'''

import sys
sys.path.append('../python')
import LMagent 
#import Maxima

import time

models={
"codestral"     : "lmstudio-community/Codestral-22B-v0.1-GGUF/Codestral-22B-v0.1-Q4_K_M.gguf",
"mathstral"     : "lmstudio-community/mathstral-7B-v0.1-GGUF/mathstral-7B-v0.1-Q4_K_M.gguf",
"Qwen2_500M"    : "Qwen/Qwen2-0.5B-Instruct-GGUF/qwen2-0_5b-instruct-q4_0.gguf",
"deepseek2"     : "lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
"Llama3.1"      : "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
"Qwen2-Math"    : "lmstudio-community/Qwen2-Math-1.5B-Instruct-GGUF/Qwen2-Math-1.5B-Instruct-Q4_K_M.gguf",
"llava1.5"      : "second-state/Llava-v1.5-7B-GGUF/llava-v1.5-7b-Q4_0.gguf",
"internlm2.5"   : "internlm/internlm2_5-20b-chat-gguf/internlm2_5-20b-chat-q4_0.gguf",
"deepseek-math" : "QuantFactory/deepseek-math-7b-instruct-GGUF/deepseek-math-7b-instruct.Q4_0.gguf",
"Phi3.1m"       : "lmstudio-community/Phi-3.1-mini-128k-instruct-GGUF/Phi-3.1-mini-128k-instruct-Q4_K_M.gguf",
#"":"nomic-ai/nomic-embed-text-v1.5-GGUF/nomic-embed-text-v1.5.Q4_K_M.gguf"
}

system_prompt="""
You are a scientific programmer with deep knowledge of physics and mathematics and computer science.
You answer by concise code which you meticulously test and censider all possible edge cases.
You try to use you knowledge of mathematics to implement fast code with minimum overhead. 
You prefer to use simple data structures (plain arrays and pointers) and algorithms to maximize performance and readability.
You try to limit usage of pow(x,n). Instead use x*x and x*x*x etc.
You if costly functions like exp, log, sin, cos, tan are necessary, you try to precalculate the expression, store in variable and reuse it.
"""

prompt = """
program C/C++ function which evaluates energy and force for n-body system of particles using Lenard-Jones + coulomb potential. 
* The function has this format:
```C++
double evalLJ(int n, const Vec3d* apos, Vec3d* fapos, const Vec3d* REQ ){ ... return E; };
```
where 
* apos is array of positions
* fapos is array of forces
* REQ is array of parameters { R0i, E0i, Qi }, mix them as R0ij=R0i+R0j; E0ij=E0i*E0j; Qij=Qi*Qj;
* R0ij is equilibrium distance between particles i and j, 
* E0ij is energy at equilibrium distance, 
* Qi*Qj is product of charges of particles i and j.
* Optimize the evaluation of LJ by substitution u=(R0/r) and precalculating the powers efficiently by multiplication, avoid using pow(x,n).
"""
# * Optimize the evaluation of LJ by precalculating substitution invr=1/r; u=(R0*invr); u2=u*u; u6=u2*u2*u2; 

model="codestral"    
#model="mathstral"   
#model="Qwen2_500M"   # FAILED - infinite loop
#model="deepseek2"    
#model="Llama3.1"      
#model="Qwen2-Math"    
#model="llava1.5"      
#model="internlm2.5"   
#model="deepseek-math"  #  FAILED - infinite loop
#model="Phi3.1m"       

model_name = models[model]

args = {
    #'max_tokens': 50,  # Adjust the length of the output
    'n': 1,            # Generate only one completion
    'temperature': 0, 
    'top_p': 0.1,
    #'best_of': 1,      # Generate only one completion
    #"batch_size": 4096,
}

agent = LMagent.Agent(model_name=model_name)
agent.set_system_prompt( system_prompt )

T0 = time.perf_counter_ns()
response, ntok = agent.send_message( prompt, user_args=args ); 
T1 = time.perf_counter_ns()
nchar = len(response)
dT = (T1-T0)*1.e-6
#print("LM Studio: " + response)
with open("response_"+model+".md", "w") as f:f.write(response)

print("TIME [ms] ", dT, " ntokens ", ntok, " nchar ", nchar," : ", dT/ntok, " [ms/tok] ", dT/nchar, " [ms/char]")
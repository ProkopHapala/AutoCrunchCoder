#!/usr/bin/python

'''
Usage notes:

1) Activate Environement like this
>> source ~/venvML/bin/activate

2)In case of problems check the server status like this
>> curl http://localhost:1234/v1/models
'''


system_prompt_gpt="""
You are a scientific programmer within an automated development loop.

The user is a program that requires well-structured communication. Your responses must be precise and adhere strictly to the instructions provided.
User messages will include sections: _feedback_, _errors_, _task_, and _format_.
Your primary role is to generate code based on the _task_ provided.
Your responses must follow the exact _format_ specified by the user.
After your code is executed by the user, you will receive _feedback_, including any _errors_. 
If _errors_ occur, you are expected to iterate and attempt to fix them until the solution is correct.
your asnwers should be concise, just code, without comments, using short variable names.
"""

system_prompt_prokop="""
You are scientific programmer inside automatic development loop. 
The _user_ is a program. Therefore you must communicate with well structured messages, and precisely follow instructions. 
Your answer must be in specific _format_ as prescribed by _user_.
Mssages from _user_ will containt sections _feedback_,_errors_,_task_,_format_.
_user_ will give you _task_ and you must generate code to solve it.
Your answers will be automatically executed by _user_ checking for errors, and report back the result. 
If there are errors you try several iterations to fix them.
"""


import sys
sys.path.append('../python')
import LMagent 

agent = LMagent.Agent(model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf")
agent.set_system_prompt( system_prompt_gpt )

response = agent.send_message(
"""
_task_

In C++ Write a function: 
Vec4d Coulomb( Vec3d d_ij, Q_ij );
which calculates force and energy between two chaged particles. 
include "Vec3d.h" and "Vec4d.h" header files which implement classes Vec3d and Vec4d, do not reimplement them. 
Both Vec3d and Vec4d have functions dot(),norm(),norm2() and overloaded operators +,-,*, and +=,-=,*= ; 
Q_ij=Q_i*Q_j is product of charges of the two partices. 
d_ij=p_i-p_j is vector between the two particles.
the output Vec4d{ f.x,f.y,f.z,E } contains both force and energy.
"""    
)
print("LM Studio: " + response)

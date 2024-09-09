import sys
import os
import numpy as np
import matplotlib.pyplot as plt

sys.path.append('../python')
import LMagent as lm
import code_derivs as cd
import Maxima as ma


user_input = {
"Equation"   : " e0*( (r0/r)^12 -2*(r0/r)^6 ) - Kcoul*qq/r",
#"DOFs"       : ["r"],
#"Parameters" : ["e0", "r0", "Q" ],
"DOFs"       : [ "r # distance of atoms" ],
"Parameters" : [ "e0 # depth of Lenard-Jones minimum", "r0 # optimal distance for Lenard-Jones", "qq # product of atom charges" ],
"Constants"  : { "Kcoul":14.3996448915 },
"Includes"   : [ 
    "<math.h>", 
    '"Vec2d.h" // 2d vector math with +,-,* operators, dot(),norm() and complex multimpleation cmul(a,b)', 
    '"Vec3d.h" // 3d vector math with +,-,* operators, dot(),norm() ', 
    '"Vec4d.h" // 4d vector math with +,-,* operators, dot(),norm() and quaternion multimpleation qmul(a,b)',
],
}


#cd.makePrompt_understand( user_input )
#cd.makePrompt_code_first( user_input )

prompt_simplify = cd.makePrompt_simplify( user_input )

#prompt_code1 = makePrompt_code_first( user_input )

#DOFs = cd.remove_commens( user_input["DOFs"] );   print( "DOFs ", DOFs)
#out = ma.get_derivs( user_input["Equation"], DOFs )
#print( "\n\n".join(out) )

model_name="lmstudio-community/Codestral-22B-v0.1-GGUF/Codestral-22B-v0.1-Q4_K_M.gguf"
# GOOD: respect formatting, the output is valid Maxima code, and looks sensible, some expressions are correct
# BAD: some of the final expression are wrong, it does not actually simplify the expression much


#model_name="lmstudio-community/mathstral-7B-v0.1-GGUF/mathstral-7B-v0.1-Q4_K_M.gguf"
# GOOD: respect formatting, the output is valid Maxima code, and looks sensible.
# BAD:  the final expression is wrong (does not match the original expression)

#model_name="Qwen/Qwen2-0.5B-Instruct-GGUF/qwen2-0_5b-instruct-q4_0.gguf"
# BAD: does not get it at all - generates something  with si,sj for Lenard-Jones

#model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
# GOOD: renerate valid Maxima code, the final expression is sometimes correct (match the reference)
# BAD: the expression is not really efficient, it still use ^ 

#model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
# BAD: the output vary wildely, does not respect format, 

#model_name="lmstudio-community/Qwen2-Math-1.5B-Instruct-GGUF/Qwen2-Math-1.5B-Instruct-Q4_K_M.gguf"
# BAD: produce huge markdown, the expression does not make any sense

#model_name="second-state/Llava-v1.5-7B-GGUF/llava-v1.5-7b-Q4_0.gguf"
# BAD: it just copies the input to output
# GOOD: respect formatting, the output is valid Maxima code, and looks sensible.

#model_name="internlm/internlm2_5-20b-chat-gguf/internlm2_5-20b-chat-q4_0.gguf"
# GOOD: respect formatting, the output is valid Maxima code, and looks sensible.
# BAD: the output is just wrong, does not make much sense

#model_name="QuantFactory/deepseek-math-7b-instruct-GGUF/deepseek-math-7b-instruct.Q4_0.gguf"
# BAD: infinite loop, nonsense output

#model_name="lmstudio-community/Phi-3.1-mini-128k-instruct-GGUF/Phi-3.1-mini-128k-instruct-Q4_K_M.gguf"    
# BAD: does not resspect formatting, insert unnnecesary comments, expressions are wrong

# coder = lm.Agent(model_name=model_name)
# coder.set_system_prompt( lm.read_file( '../prompts/ImplementPotential/matematician_system_prompt.md' ) )
# response = coder.send_message( prompt_simplify ); 
# print("\n========\nResponse:\n\n" + response)
# cd.write_file( "response_simplify.md", response )



#elines,dlines = cd.formulasFromResponse( response, DOFs=['r'] )
#print(elines)
#print(dlines)

#flines = cd.formulasFromResponse( response, DOFs=['r'] )
#for k,v in flines.items(): print(k, "  :   ", v)

#response=cd.read_file( "response_simplify.md" )

response_prokop="""
```Maxima
inv_r     : 1/r;
u2        : r0*r0*inv_r*inv_r;
u6        : u2*u2*u2;
u12       : u6*u6;
E         :   e0*    ( u12 - 2*u6 ) - Kcoul*qq*inv_r;
dE_r      :  (e0*-12*( u12 -   u6 ) + Kcoul*qq*inv_r)*inv_r;
```
"""

response = response_prokop
#response = response_deepseek_25
#response = response_deepseek_coder_25
#response = response_Claude35sonet

cd.check_formulas( user_input, response )






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

#DOFs = cd.remove_commens( user_input["DOFs"] );   print( "DOFs ", DOFs)
#out = ma.get_derivs( user_input["Equation"], DOFs )
#print( "\n\n".join(out) )


#model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
#model_name="lmstudio-community/mathstral-7B-v0.1-GGUF/mathstral-7B-v0.1-Q4_K_M.gguf"
# model_name="lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
# coder = lm.Agent(model_name=model_name)
# coder.set_system_prompt( lm.read_file( '../prompts/ImplementPotential/matematician_system_prompt.md' ) )
# response = coder.send_message( prompt_simplify ); 
# print("\n========\nResponse:\n\n" + response)
# cd.write_file( "response_simplify.md", response )

response="""
```Maxima
/* pre-calculate sub-expressions */
r06       : r0*r0*r0;
r012      : r0*r0*r0*r0*r0*r0*r0;
inv_r     : 1/r;
Kcoulqq   : Kcoul*qq;
e0        : e0;
/* final formulas and the derivative */
E         : e0*(r012/inv_r^12 - (2*r06)/inv_r^6) - Kcoulqq/inv_r;
dE_r      : e0*((12*r06)/(inv_r^(7))-(12*r012)/(inv_r^(13))) + (Kcoulqq/(inv_r^2));
```
"""

response_="""
```Maxima
inv_r     : 1/r;
u2        : r0*r0*inv_r*inv_r;
u6        : u2*u2*u2;
u12       : u6*u6;
E         :   e0*    ( u12 - 2*u6 ) - Kcoul*qq*inv_r;
dE_r      :  (e0*-12*( u12 -   u6 ) + Kcoul*qq*inv_r)*inv_r;
```
"""

response_="""
/* pre-calculate sub-expressions */
r2          : r*r;
r3          : r2*r;
r6          : r3*r3;
r7          : r6*r;
r12         : r6*r6;
r13         : r12*r;
r0_6        : r0^6;
r0_12       : r0^12;
inv_r       : 1/r;
inv_r2      : 1/r2;
inv_r6      : 1/r6;
inv_r7      : 1/r7;
inv_r12     : 1/r12;
inv_r13     : 1/r13;

/* final energy expression */
E           : e0*(r0_12*inv_r12 - 2*r0_6*inv_r6) - (Kcoul*qq)*inv_r;

/* derivative of energy with respect to r */
dE_r        : e0*(12*r0_6*inv_r7 - 12*r0_12*inv_r13) + (Kcoul*qq)*inv_r2;
```
"""

#elines,dlines = cd.formulasFromResponse( response, DOFs=['r'] )
#print(elines)
#print(dlines)

#flines = cd.formulasFromResponse( response, DOFs=['r'] )
#for k,v in flines.items(): print(k, "  :   ", v)

cd.check_formulas( user_input, response )






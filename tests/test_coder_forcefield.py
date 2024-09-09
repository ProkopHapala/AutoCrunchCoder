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
cd.makePrompt_code_first( user_input )

#DOFs = cd.remove_commens( user_input["DOFs"] );   print( "DOFs ", DOFs)
#out = ma.get_derivs( user_input["Equation"], DOFs )
#print( "\n\n".join(out) )




'''
model_name="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
coder = lm.Agent(model_name=model_name)
coder.set_system_prompt( lm.read_file( '../prompts/coder_system_prompt.md' ) )
'''




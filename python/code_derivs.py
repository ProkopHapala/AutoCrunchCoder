import os
import Maxima as ma


def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
# save to file "math_response.md"
def write_file(file_path, txt):
    with open(file_path, 'w') as file:
        file.write(txt)

def remove_commens( lst, sep="#"):
    return [ s.split(sep)[0] for s in lst ]


def makePrompt_understand( user_input, fname="../prompts/ImplementPotential/understand.md" ):
    #print("makePrompt_understand()", os.getcwd() )
    template = read_file(fname)
    consts = [  ("%s = %s \n" %(k,v) ) for k,v in user_input["Constants"].items()   ]
    prompt = template.format(
        Equation=user_input["Equation"],
        DOFs="\n".join(user_input["DOFs"]),
        Parameters="\n".join(user_input["Parameters"]),
        Constants="\n".join(consts),
    )
    write_file("debug_promt_understand.md", prompt)
    return prompt



def makePrompt_code_first( user_input, fname="../prompts/ImplementPotential/code_first.md" ):
    #print("makePrompt_understand()", os.getcwd() )
    template = read_file(fname)
    DOFs     = remove_commens( user_input["DOFs"] );
    Formulas = "\n".join(ma.get_derivs ( user_input["Equation"], DOFs ))
    Includes = "\n".join( [ ("#include "+x) for x in user_input["Includes"] ] )
    print("####### Includes =", Includes)
    prompt = template.format(
        Formulas=Formulas,
        Includes=Includes,
    )
    write_file("debug_promt_code_first.md", prompt)
    return prompt

#out = ma.get_derivs( Eformula, DOFs+params )



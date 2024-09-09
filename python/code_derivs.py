import os
import Maxima as ma
import re

default_operation_costs = {
'^':20,
'/':3,
'*':1,
'+':1,
'-':1,
}

re_split_op = re.compile(r'[\+\-\*/^;$()]')

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
# save to file "math_response.md"
def write_file(file_path, txt):
    with open(file_path, 'w') as file:
        file.write(txt)

def remove_commens( lst, sep="#"):
    return [ s.split(sep)[0].strip() for s in lst ]

def makeFormulas( user_input ):
    DOFs     = remove_commens( user_input["DOFs"] );
    Formulas = ma.get_derivs ( user_input["Equation"], DOFs )
    user_input["Formulas"] = Formulas
    return Formulas

def getOrMakeFormulas( user_input ):
    if not "Formulas" in user_input:
        Formulas = makeFormulas( user_input )
    else:
        Formulas = user_input["Formulas"]
    return Formulas

def getOrMakeSymbols( user_input ):
    if not "Symbols" in user_input:
        DOFs     = remove_commens( user_input["DOFs"] );
        Consts   = remove_commens( user_input["Parameters"] );
        params   = remove_commens( user_input["Constants"] );
        symbols  = set( DOFs + Consts + params )
        user_input["Symbols"] = symbols
    else:
        symbols = user_input["Symbols"]
    return symbols

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
    Formulas = getOrMakeFormulas( user_input )
    Formulas_ = "\n".join( Formulas )
    Includes = "\n".join( [ ("#include "+x) for x in user_input["Includes"] ] )
    print("####### Includes =", Includes)
    prompt = template.format(
        Formulas=Formulas_,
        Includes=Includes,
    )
    write_file("debug_promt_code_first.md", prompt)
    return prompt

def makePrompt_simplify( user_input, fname="../prompts/ImplementPotential/simplify2.md" ):
    #print("makePrompt_understand()", os.getcwd() )
    template = read_file(fname)
    Formulas = getOrMakeFormulas( user_input )
    
    Formulas_ = "\n".join( [x+";" for x in Formulas] )
    prompt = template.format(
        Formulas=Formulas_,
    )
    write_file("debug_promt_simplify.md", prompt)
    return prompt

def count_operations( code ):
    """Count the number of divisions, multiplications, additions, and subtractions in an expression by iterating through characters."""
    ndiv = 0
    nmul = 0
    nadd = 0
    nsub = 0
    npow = 0
    for char in code:
        if char == '/':
            ndiv += 1
        elif char == '*':
            nmul += 1
        elif char == '+':
            nadd += 1
        elif char == '-':
            nsub += 1
        elif char == '^':
                npow += 1
    return ndiv, nmul, nadd, nsub, npow

def formulasFromResponse_bak(response, DOFs):
    lines = response.splitlines()
    energy_line = None
    derivative_lines = {}
    energy_pattern = re.compile(r'^\s*E\s*:')
    for line in lines:
        # Strip leading/trailing whitespaces
        line = line.strip()
        if energy_pattern.match(line):
            #energy_line = line
            energy_line = line.split(":")[1]
        for dof in DOFs:
            derivative_pattern = re.compile(r'^\s*dE_' + re.escape(dof) + r'\s*:')
            if derivative_pattern.match(line):
                #derivative_lines[dof] = line
                derivative_lines[dof] = line.split(":")[1]
    return energy_line, derivative_lines

def formulasFromResponse(response, DOFs):
    dofs = set(DOFs); 
    #print(dofs)
    lines = response.splitlines()
    subexprs = []
    flines = {}
    names = ['E'] + [ ("dE_"+x) for x in dofs ]
    for line in lines:
        line = line.strip()
        if line.startswith("E ") or line.startswith("E:" ):
            flines["E"] = line.split(":")[1]
        elif line.startswith("dE_"):
            l0,l1 = line.split(":")
            l0=l0.strip()
            dof = l0.split("_")[1]
            if dof in dofs:
                flines[l0] = l1
            else:
                print("ERROR unknown DOF(%s)" %dof, " on line ", line  )
        elif ( ':' in line) and ( (';' in line) or ('$' in line) ):
            for s in line.split(";"):
                s=s.strip()
                if len(s)>0:
                    subexprs.append(s)
    return flines, names, subexprs


def check_defined( names, flines, subexprs, symbols ):
    nErr=0
    defs = set( [ x.split(":")[0].strip() for x in subexprs ] )
    defs = defs | symbols
    for k in names:
        if not k in flines:
            print("ERROR: ", k, " not defined")
            nErr+=1
        expr = flines[k]
        vars = re_split_op.split( expr )
        #print(k, "=", expr, "vars=", vars)
        for v in vars:
            v = v.strip()
            if len(v)>0 and not v.isnumeric():
                if not v in defs:
                    print("ERROR: ", v, " not defined in ", k," : ", expr )
                    nErr += 1
    return nErr

def check_formulas( user_input, response, op_cost=default_operation_costs ):
    Formulas      = getOrMakeFormulas( user_input )
    DOFs          = remove_commens( user_input["DOFs"] );

    flines, names, subexprs = formulasFromResponse(response, DOFs )

    # ------ check defintions
    symbols = getOrMakeSymbols( user_input )
    nErr = check_defined( names, flines, subexprs, symbols )
    if( nErr > 0 ):
        print("ERROR: ", nErr, " variables not defined")
        return nErr

    # ------ estimate performance cost
    ndiv, nmul, nadd, nsub, npow = count_operations( response ); 
    cost = ndiv*op_cost["/"] + nmul*op_cost["*"] + nadd*op_cost["+"] + nsub*op_cost["-"] + npow*op_cost["^"]
    print("Count Operation:\nn(div):",ndiv,"\nn(mul):",nmul,"\nn(add):",nadd,"\nn(sub):",nsub,"\nn(pow):",npow)
    print("Total Computational Cost: ",cost)
    
    #print("flines ", flines )

    # ------ check formulas with maxima vs referece

    fname="check_formulas.mac"
    fout = open(fname, "w")
    fout.write( "linel     : 256$\n" )
    fout.write( "display2d : false$\n")
    for f in Formulas:
        fout.write(f+"$\n")
    for s in subexprs:  
        s=s[:]+'$'
        fout.write(s+"\n")
    for k in names:
        k_ = k + "_"
        v  = flines[k]
        v=v[:-1]+'$'
        fout.write( k_+" : "+v+"\n")
    #fout.write('print("##########");\n')
    for k in names:
        k_ = k + "_"
        fout.write("ratsimp( expand( %s ) - expand( %s ) );\n" %(k,k_) )
    fout.close()

    code = read_file(fname)
    out = ma.run_maxima(code)

    nErr = 0
    lines = out.splitlines()
    if( len(lines) != len(names) ): 
        print("ERROR: Maxima ouput ", len(lines), " lines, but we expect ", len(names), " expresions" )
        print("ERROR: Maxima ouput ", out )
        return nErr
    
    for i,name in enumerate( names ):
        l = lines[i].strip()
        if l != "0":
            k = name
            v = flines[k]
            print(  "Error_"+name+"   :  "+ v )
            
            code=""   
            for s in subexprs:  code += s[:]+"$\n"
            code += ( "ratsimp(%s);" %(v[:-1]) ) 
            #print(">>>",code,"<<<") 
            out=ma.run_maxima(code)
            print(  "expands to  :  ", out )

            print("\n\n>>>\n",code,"\n<<<\n\n") 

            #print(  "Error "+name+"   expands to  "+  )
            #print(  "Error "+name+"  not matching original formula  "+  )
            nErr += 1
    if nErr>0:
        print("check_formulas() FAIL: ", nErr, " out of ", len(names), " expressions has non-zero error with respect to reference !!! ")
    else:
        print("check_formulas() PASS: all of ", len(names) ,"expressions matched. ")
    return nErr



#out = ma.get_derivs( Eformula, DOFs+params )



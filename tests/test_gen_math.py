import sys
sys.path.append("../")
#import LMagent as lm
import pyCruncher.Maxima as ma


'''

Strategies for generating math expression examples
1. Sum of product of low-degree polynomials
  * train see simple expressions like (a+b)^2 in complex polynomials
    * complete the square  (a*x)^2 + 2*a*b*x + b*b
    * difference of squares a^2 - b^2
  * train find polynominals algebraically solvable by substitution (e.g. ((x^4)^2-2)^3=16 )
  * decompose sum of fractions (e.g. (x^2+1)/(x^2-1) + 2 )
2. Subsitution of variables in expressions
    1. Consider algebraic forms of common shapes (e.g. sphere, cylinder, cone, paraboloide, hyperboloide, torus etc.)
       * find intersection of two shapes (e.g. sphere and cylinder)
          * do it in rotated coordinats (one shape is rotated with respect to another)





'''

def power_binary_expansion( base, pmax ):    
    lines=[]
    xo=base
    for i in range(1,pmax):
        x2 =  base+str(2**i)
        lines.append( x2+" : "+xo+"*"+xo )
        xo=x2
    #print(lines)
    return lines

def make_expresion( base, pows, muls ):
    terms = []
    for i,e in enumerate(pows):
        be = bin(e)[2:][::-1]
        if be.count('1')<=1: continue
        l = ""
        prev=False
        if len(muls[i])>0:
            l = muls[i]
            prev=True
        for j in range(len(be)):
            if be[j]=='1':
                if prev: l+="*"
                l+=base+str(2**j)
                prev=True
        terms.append( l )
    return terms

def make_LJ_like( sname, subs, expnames, pows, muls ):
    lines = [ sname+" : "+subs ]
    # ---- generate powers
    es   = list( {item for lst in pows for item in lst } )
    bes  = [ bin(e)[2:][::-1] for e in es ]
    pmax = max( [ len(be) for be in bes ] )
    lines += power_binary_expansion( sname, pmax )
    # ---- generate expresions 
    for i,expname in enumerate( expnames ):
        l=expname+" : "
        lst = pows[i]
        terms = make_expresion( sname, lst, muls[i] )
        l+= "+".join(terms)
        lines.append( l )
    return lines

def sum_terms( terms, coefs, e ):
    n = len(terms)
    ts = [ str(coefs[i])+"*"+str(terms[i]) for i in range(n) ]
    s = "+".join(ts)
    if e!=1: s = "("+s+")^"+str(e)
    return s  


def derivs_by_terms( Eterms, preterms, var='x' ):
    pre_code=[ t for t in preterms ]
    for i in range( len(Eterms) ):
        Eterm = Eterms[i]
        print("######## ", Eterm  )
        code =  [] 
        code += pre_code
        code.append( "E : "+Eterm )
        #code.append( "F : "+Fterms[i]+";" )
        code.append( f"F : diff( E, {var} )" )
        #code.append( "E_: ratsimp( E );" )
        #code.append( "F_: ratsimp( F );" )
        code.append( "F_E: ratsimp( F/E );" )
        scode = "$\n".join(code)
        print( scode )
        print("======== ", Eterm  )
        out =  ma.run_maxima(scode)
        print( out )


#power_binary_expansion( "x", [13,11,7,4,3] )
#power_binary_expansion( "u",  )

# lines = ["ir : 1/r"]
# lines += make_LJ_like( "u", "r0*ir", ["E","dE_dr"], [[6,12],[6,12]], [["e0","-2*e0"],["-12*e0","12*e0"]] )
# for line in lines: print(line)


#derivs_by_terms( ["e0*u2*u4","-2*e0*u4*u8"], ["u2 : u*u", "u4 : u2*u2", "u8 : u4*u4" ], var='u' )

l = sum_terms( ["a","b"], [2,3], 2 ) +"+"+ sum_terms( ["a","b"], [1,-1], 3 ) ; print( "answer   : ", l )
out =  ma.run_maxima( "expand("+l+");" )                                     ; print( "quastion : ", out )


exit()

answer='''
ir  : 1/r$
ir2 : ir*ir$
u2  : r0*r0*ir2$
u6  : u2*u2*u2$
expr1: e0*( u6*u6 - 2*u6 - Kcoul*Q*ir )$
'''

code=answer+"expand( expr1 );"

question = ma.run_maxima(code)
print(question)
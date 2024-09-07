

import subprocess
import sys
sys.path.append('../python')
import Maxima as ma



Eformula=" A/r^12 - B/r^6 + Q/r"
DOFs=["r"]
params=["A","B","Q"]

Eformula=" E0*( (R0/r)^12 - 2*(R0/r)^6 ) + Q/r  "
DOFs=["r"]
params=["E0","R0","Q"]

out = ma.get_derivs( Eformula, DOFs+params )

#out = ma.label_maxima_output( out, ["E"]+ DOFs+params )

print( out ) 



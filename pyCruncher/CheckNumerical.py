import numpy as np
import  time

def getNumDerivs( xs, Es ):
    F = ( Es[2:] - Es[:-2] ) / ( 2*xs[2:] - xs[:-2] )
    return F

def getNumDerivsPerp( xs, Es, dx ):
    F = ( Es[2:] - Es[:-2] ) / ( 2*xs[2:] - xs[:-2] )
    return F

def checkDerivs( func, dofs0, ts, idx=0, params ):
    nps   = len(ts)
    nDOFs = len(dofs0)
    xs = np.zeros( (nps, nDOFs) )
    xs[:,:]   = dofs0[ None, :]   # default values of the DOFs
    xs[:,idx] = ts                # scan of DOFs[idx]
    FEs = func( xs, params )
    Fidx = FEs[idx]




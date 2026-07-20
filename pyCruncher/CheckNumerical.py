"""
Numerical derivative sanity checks — finite-difference verification of forces.

Simple NumPy helpers to compute numerical derivatives of energy arrays and
compare them against analytical forces. Intentionally minimal: no SymPy,
no Maxima, just finite differences.

Non-obvious things:
- `getNumDerivs()` uses the central difference formula (E[i+2]-E[i-2])/(2*dx)
  which is O(h²) accurate but needs at least 3 points.
- `checkDerivs()` scans along one degree of freedom while keeping others
  fixed, then compares the numerical force against the analytical one.
- This module has a syntax error in `checkDerivs` (missing default for
  `params`) — it's experimental/incomplete code.
"""

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




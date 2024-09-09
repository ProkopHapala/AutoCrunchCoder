
# **Generating python interface**

You should generate the python interface to this C/C++ sampling function so that we can test it using python.

#### Python/ctypes side of interface template

```python

# void {function_name}( int nps, int nDOF, double* ps, double* Es, double* Fs, double* params )
lib.{function_name}.argtypes = [c_int,c_int,array2d,array1d,array2d,array1d]
lib.{function_name}.restype  = c_double
def {function_name}(ps,params,Es=None,Fs=None):
    nps,nDOFs = ps.shape
    if Fs is None: Fs = np.zeros((nps,ndofs))
    if Es is None: Es = np.zeros(nps)
    lib.{function_name}(ps,Es,Fs,params)
    return Es, Fs
```

Assume that ctypes is already loaded and aliases for numpy array types are already defined as follows:

```python
from   ctypes import c_int, c_double, c_bool, c_float, c_char_p, c_bool, c_void_p, c_char_p
import ctypes
import os
import sys
import subprocess
import numpy as np

c_double_p = ctypes.POINTER(c_double)
c_float_p  = ctypes.POINTER(c_float)
c_int_p    = ctypes.POINTER(c_int)
c_bool_p   = ctypes.POINTER(c_bool)

array1d  = np.ctypeslib.ndpointer(dtype=np.double, ndim=1, flags='CONTIGUOUS')
array2d  = np.ctypeslib.ndpointer(dtype=np.double, ndim=2, flags='CONTIGUOUS')
array3d  = np.ctypeslib.ndpointer(dtype=np.double, ndim=3, flags='CONTIGUOUS')
array1i  = np.ctypeslib.ndpointer(dtype=np.int32,  ndim=1, flags='CONTIGUOUS')
array2i  = np.ctypeslib.ndpointer(dtype=np.int32,  ndim=2, flags='CONTIGUOUS')


```
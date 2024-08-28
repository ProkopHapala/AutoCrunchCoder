


from   ctypes import c_int, c_double, c_bool, c_float, c_char_p, c_bool, c_void_p, c_char_p
import ctypes
import os
import sys
import subprocess
import numpy as np

array1ui = np.ctypeslib.ndpointer(dtype=np.uint32, ndim=1, flags='CONTIGUOUS')
array1i  = np.ctypeslib.ndpointer(dtype=np.int32,  ndim=1, flags='CONTIGUOUS')
array2i  = np.ctypeslib.ndpointer(dtype=np.int32,  ndim=2, flags='CONTIGUOUS')
array1d  = np.ctypeslib.ndpointer(dtype=np.double, ndim=1, flags='CONTIGUOUS')
array2d  = np.ctypeslib.ndpointer(dtype=np.double, ndim=2, flags='CONTIGUOUS')
array3d  = np.ctypeslib.ndpointer(dtype=np.double, ndim=3, flags='CONTIGUOUS')

c_double_p = ctypes.POINTER(c_double)
c_float_p  = ctypes.POINTER(c_float)
c_int_p    = ctypes.POINTER(c_int)
c_bool_p   = ctypes.POINTER(c_bool)


# Define the filenames
name="nbody"
#cpp_file = "nbody.cpp"
#asm_file_unoptimized   = "nbody_unoptimized.s"
#asm_file_optimized     = "nbody_optimized.s"
#shared_lib_unoptimized = "nbody_unoptimized.so"
#shared_lib_optimized   = "nbody_optimized.so"


#subprocess.run(f"g++ -O0    -fPIC -S -fverbose-asm -shared {cpp_file} -o {asm_file_unoptimized}", shell=True) # Compile to unoptimized assembly with comments
#subprocess.run(f"g++ -Ofast -fPIC -S -fverbose-asm -shared {cpp_file} -o {asm_file_optimized}", shell=True) # Compile to optimized assembly with comments
#subprocess.run(f"g++ -O0    -fPIC                  -shared {cpp_file} -o {shared_lib_unoptimized}", shell=True) # Compile to unoptimized shared library
#subprocess.run(f"g++ -Ofast -fPIC                  -shared {cpp_file} -o {shared_lib_optimized}", shell=True)  # Compile to optimized shared library

subprocess.run(f"g++ -O0    -fPIC -S -fverbose-asm -shared {name} -o {name}_O0.so",  shell=True) # Compile to unoptimized assembly with comments
subprocess.run(f"g++ -Ofast -fPIC -S -fverbose-asm -shared {name} -o {name}_opt.so", shell=True) # Compile to optimized assembly with comments
subprocess.run(f"g++ -O0    -fPIC                  -shared {name} -o {name}_O0.so",  shell=True) # Compile to unoptimized shared library
subprocess.run(f"g++ -Ofast -fPIC                  -shared {name} -o {name}_opt.so", shell=True) # Compile to optimized shared library

lib = ctypes.CDLL(os.path.abspath("{name}_opt.so"))    # Load the optimized shared library using ctypes

lib.nbody_coulomb_c.argtypes = [c_int,array2d,array2d,array2d]
lib.nbody_coulomb_c.restype  = c_double
def nbody_coulomb(pos,params,forces=None):
    n = len(pos)
    if forces is None:forces = np.zeros((n,3))
    E= lib.nbody_coulomb_c(pos,params,forces)
    return E, forces

nb = 100
pos    = np.random.rand(nb,3)
params = np.random.rand(nb,4)
E, forces = nbody_coulomb(pos,params)

print("E = ",           E )
print("forces = ", forces )
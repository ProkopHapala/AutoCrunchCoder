import pyopencl as cl
import numpy as np

'''
export PYOPENCL_CTX='1'; python test_pyOpenCL.py
'''


# Initialize OpenCL context and queue
context = cl.create_some_context()
queue = cl.CommandQueue(context)

# Read and compile the OpenCL program
with open("nbody.cl", "r") as f:
    kernel_source = f.read()

program = cl.Program(context, kernel_source).build()

# Initialize input data
n = 3  # Number of particles
workgroup_size = 32  
n_glob = n

if n_glob % workgroup_size != 0:
    n_glob = (n_glob // workgroup_size + 1) * workgroup_size

pos = np.array([[0.0, 0.0, 0.0,0.0],  # Particle 1
                [1.0, 0.0, 0.0,0.0],  # Particle 2
                [0.0, 1.0, 0.0,0.0],], # Particle 3
               dtype=np.float32)

params = np.array([[ 0.0, 0.0, 1.0, 0.0],  # Particle 1
                   [ 0.0, 0.0, 1.0, 0.0],  # Particle 2
                   [ 0.0, 0.0, 1.0, 0.0],], # Particle 3
                  dtype=np.float32)

fe_out = np.zeros( (n,4), dtype=np.float32)

# Create buffers
mf = cl.mem_flags
pos_buf    = cl.Buffer(context, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=pos)
params_buf = cl.Buffer(context, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=params)
fe_buf     = cl.Buffer(context, mf.WRITE_ONLY, fe_out.nbytes)

# ------ Kernel Simple ---------

program.nbody_coulomb(queue, (n,), None, np.int32(n), pos_buf, params_buf, fe_buf )   # Set kernel arguments and execute
cl.enqueue_copy(queue, fe_out, fe_buf).wait()    # Copy results from the device
print("FEout:"       ); print(fe_out.reshape((n, 4)))

# ------ Kernel Local Memory ---------

kernel = program.nbody_coulomb_local
kernel.set_args(np.int32(n), pos_buf, params_buf, fe_buf)
cl.enqueue_nd_range_kernel(queue, kernel, (n_glob,), (workgroup_size,)).wait()    # Execute the kernel
cl.enqueue_copy(queue, fe_out, fe_buf).wait()                                # Copy results from the device

print("FEout:"       ); print(fe_out.reshape((n, 4)))  # Print results

import pycuda.autoinit
import pycuda.driver as drv
import numpy as np
from pycuda.compiler import SourceModule

# load the CUDA code from a file ./nbody.cu
cuda_code = open("./nbody.cu", "r").read()

# Compile the CUDA kernel
mod = SourceModule(cuda_code)

# Get the kernel function
nbody_coulomb = mod.get_function("nbody_coulomb")

# Initialize input data
n = 3  # Number of particles
block_size = 32  # Must match BLOCK_SIZE in the kernel
grid_size = (n + block_size - 1) // block_size

# Adjust the number of particles to a multiple of block_size
if n % block_size != 0:
    n_adjusted = (n // block_size + 1) * block_size
else:
    n_adjusted = n

# Initialize pos, params, and fe_out arrays
pos    = np.zeros((n_adjusted, 4), dtype=np.float32)
params = np.zeros((n_adjusted, 4), dtype=np.float32)
fe_out = np.zeros((n_adjusted, 4), dtype=np.float32)

# Initialize actual particle data (only the first n particles)
pos[:n] = np.array([
    [0.0, 0.0, 0.0, 0.0],  # Particle 1
    [1.0, 0.0, 0.0, 0.0],  # Particle 2
    [0.0, 1.0, 0.0, 0.0],  # Particle 3
    # ... add more particles ...
])

params[:n] = np.array([
    [1.0, 0.0, 1.0, 1.0],  # Particle 1
    [1.0, 0.0, 1.0, 1.0],  # Particle 2
    [1.0, 0.0, 1.0, 1.0],  # Particle 3
    # ... add more particles ...
])

# Allocate device memory and copy data to the device
pos_gpu = drv.mem_alloc(pos.nbytes)
params_gpu = drv.mem_alloc(params.nbytes)
fe_out_gpu = drv.mem_alloc(fe_out.nbytes)

drv.memcpy_htod(pos_gpu, pos)
drv.memcpy_htod(params_gpu, params)

# Calculate shared memory size needed
shared_mem_size = 2 * block_size * 4 * np.dtype(np.float32).itemsize  # 2 arrays of float4

# Execute the kernel
nbody_coulomb(
    np.int32(n), pos_gpu, params_gpu, fe_out_gpu,
    block=(block_size, 1, 1), grid=(grid_size, 1),
    shared=shared_mem_size
)

# Copy the result back to the host
drv.memcpy_dtoh(fe_out, fe_out_gpu)

# Print the results for the first n particles
print("Forces:")
print(fe_out[:n])

#!/usr/bin/env python3

"""
Example demonstrating N-body simulation using CUDA.
This example shows how to:
1. Load and compile CUDA kernels
2. Set up particle data and GPU memory
3. Execute N-body force calculations on GPU
4. Handle shared memory and block/grid organization
"""

import numpy as np
from pyCruncher2.scientific.gpu.cuda import compile_cuda_kernel, allocate_and_copy

def setup_particle_data(n_particles: int, block_size: int) -> tuple[np.ndarray, np.ndarray]:
    """Set up initial particle positions and parameters."""
    # Adjust particle count to block size
    n_adjusted = ((n_particles + block_size - 1) // block_size) * block_size
    
    # Initialize arrays with adjusted size
    pos = np.zeros((n_adjusted, 4), dtype=np.float32)
    params = np.zeros((n_adjusted, 4), dtype=np.float32)
    
    # Set actual particle data
    pos[:n_particles] = np.array([
        [0.0, 0.0, 0.0, 0.0],  # Particle 1 at origin
        [1.0, 0.0, 0.0, 0.0],  # Particle 2 at (1,0,0)
        [0.0, 1.0, 0.0, 0.0],  # Particle 3 at (0,1,0)
    ])
    
    # Set particle parameters (charge, mass, etc.)
    params[:n_particles] = np.array([
        [1.0, 0.0, 1.0, 1.0],  # Particle 1 parameters
        [1.0, 0.0, 1.0, 1.0],  # Particle 2 parameters
        [1.0, 0.0, 1.0, 1.0],  # Particle 3 parameters
    ])
    
    return pos, params

def main():
    # Configuration
    n_particles = 3
    block_size = 32  # Must match BLOCK_SIZE in CUDA kernel
    
    # Set up particle data
    pos, params = setup_particle_data(n_particles, block_size)
    fe_out = np.zeros_like(pos)
    
    # Compile CUDA kernel
    kernel = compile_cuda_kernel("nbody.cu", "nbody_coulomb")
    
    # Calculate grid dimensions
    grid_size = (n_particles + block_size - 1) // block_size
    
    # Allocate GPU memory and copy data
    pos_gpu, params_gpu, fe_out_gpu = allocate_and_copy([pos, params, fe_out])
    
    # Calculate shared memory size
    shared_mem_size = 2 * block_size * 4 * np.dtype(np.float32).itemsize
    
    # Execute kernel
    kernel(
        np.int32(n_particles),
        pos_gpu,
        params_gpu,
        fe_out_gpu,
        block=(block_size, 1, 1),
        grid=(grid_size, 1),
        shared=shared_mem_size
    )
    
    # Copy results back to host
    fe_out_gpu.get(ary=fe_out)
    
    # Print results
    print("\n=== N-body Simulation Results ===")
    print(f"Number of particles: {n_particles}")
    print("\nParticle positions:")
    print(pos[:n_particles])
    print("\nComputed forces:")
    print(fe_out[:n_particles])

if __name__ == "__main__":
    main()

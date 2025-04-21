#!/usr/bin/env python3

"""
Example demonstrating N-body simulation using OpenCL.
This example shows how to:
1. Set up OpenCL context and compile kernels
2. Use both global and local memory implementations
3. Handle workgroups and memory buffers
4. Compare performance between different implementations
"""

import numpy as np
from pyCruncher2.scientific.gpu.opencl import (
    setup_opencl_context,
    compile_opencl_kernel,
    create_buffer,
    execute_kernel
)

def setup_particle_data(n_particles: int, workgroup_size: int) -> tuple[np.ndarray, np.ndarray]:
    """Set up initial particle positions and parameters."""
    # Adjust particle count to workgroup size
    n_adjusted = ((n_particles + workgroup_size - 1) // workgroup_size) * workgroup_size
    
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
        [0.0, 0.0, 1.0, 0.0],  # Particle 1 parameters
        [0.0, 0.0, 1.0, 0.0],  # Particle 2 parameters
        [0.0, 0.0, 1.0, 0.0],  # Particle 3 parameters
    ])
    
    return pos, params

def run_nbody_simulation(kernel_name: str, n_particles: int, pos_buf, params_buf, fe_buf,
                        context, queue, program, workgroup_size: int = None):
    """Run N-body simulation with specified kernel."""
    print(f"\n=== Running {kernel_name} ===")
    
    # Initialize output array
    fe_out = np.zeros((n_particles, 4), dtype=np.float32)
    
    # Execute kernel
    if workgroup_size is None:
        # Simple global memory version
        program.nbody_coulomb(queue, (n_particles,), None,
                            np.int32(n_particles), pos_buf, params_buf, fe_buf)
    else:
        # Local memory version
        n_glob = ((n_particles + workgroup_size - 1) // workgroup_size) * workgroup_size
        kernel = program.nbody_coulomb_local
        kernel.set_args(np.int32(n_particles), pos_buf, params_buf, fe_buf)
        cl.enqueue_nd_range_kernel(queue, kernel, (n_glob,), (workgroup_size,)).wait()
    
    # Copy results back
    cl.enqueue_copy(queue, fe_out, fe_buf).wait()
    
    print("Computed forces:")
    print(fe_out)
    
    return fe_out

def main():
    # Configuration
    n_particles = 3
    workgroup_size = 32
    
    # Set up OpenCL
    context, queue = setup_opencl_context()
    program = compile_opencl_kernel(context, "nbody.cl")
    
    # Set up particle data
    pos, params = setup_particle_data(n_particles, workgroup_size)
    
    # Create OpenCL buffers
    pos_buf = create_buffer(context, pos, read_only=True)
    params_buf = create_buffer(context, params, read_only=True)
    fe_buf = create_buffer(context, np.zeros_like(pos), write_only=True)
    
    # Run simulations with different kernels
    fe_global = run_nbody_simulation(
        "Global Memory Kernel",
        n_particles,
        pos_buf,
        params_buf,
        fe_buf,
        context,
        queue,
        program
    )
    
    fe_local = run_nbody_simulation(
        "Local Memory Kernel",
        n_particles,
        pos_buf,
        params_buf,
        fe_buf,
        context,
        queue,
        program,
        workgroup_size
    )
    
    # Compare results
    print("\n=== Results Comparison ===")
    print("Maximum difference between implementations:",
          np.max(np.abs(fe_global - fe_local)))

if __name__ == "__main__":
    main()

// nbody_coulomb.cu

#define COULOMB_CONST 14.3996448915
#define BLOCK_SIZE 32

__global__ void nbody_coulomb(
    int n, 
    const float4* pos, 
    const float4* params, 
    float4* fe_out
) {
    int gid = blockIdx.x * blockDim.x + threadIdx.x;

    if (gid >= n) return;  // Early exit if gid is out of bounds

    extern __shared__ float4 shared_mem[];
    float4* local_pos = (float4*)shared_mem;
    float4* local_params = (float4*)&shared_mem[blockDim.x];

    float3 pi   = make_float3(pos[gid].x, pos[gid].y, pos[gid].z);
    float4 pari = params[gid];
    float4 fe   = make_float4(0.0f, 0.0f, 0.0f, 0.0f);

    // Loop over all blocks
    for (int wg = 0; wg < n; wg += blockDim.x) {
        int local_idx = wg + threadIdx.x;

        // Load data into shared memory if within bounds
        if (local_idx < n) {
            local_pos[threadIdx.x] = pos[local_idx];
            local_params[threadIdx.x] = params[local_idx];
        }

        // Synchronize to ensure all shared memory is populated
        __syncthreads();

        // Compute interactions with particles in the shared memory
        for (int j = 0; j < blockDim.x; j++) {
            int global_j = wg + j;

            if (global_j >= n || gid == global_j) continue;  // Skip out-of-bounds and self-interaction

            float3 pj   = make_float3(local_pos[j].x, local_pos[j].y, local_pos[j].z);
            float4 parj = local_params[j];

            float3 d  = make_float3(pj.x - pi.x, pj.y - pi.y, pj.z - pi.z);
            float ir2 = dot(d, d) + 1e-32f;
            float ir  = sqrtf(ir2);
            float qq  = pari.z * parj.z;
            float E   = COULOMB_CONST * qq * ir;

            fe.x += d.x * (E * ir2);
            fe.y += d.y * (E * ir2);
            fe.z += d.z * (E * ir2);
            fe.w += E;
        }

        // Synchronize before the next iteration
        __syncthreads();
    }

    // Write the computed force to global memory
    fe_out[gid] = fe;
}

// nbody_coulomb.cl

#define COULOMB_CONST 14.3996448915  
#define WORKGROUP_SIZE 32

__kernel void nbody_coulomb(
    const int n, 
    __global const float4* pos, 
    __global const float4* params, 
    __global       float4* fe_out
) {
    int i = get_global_id(0);
    
    float3 pi   = pos[i].xyz;
    float4 pari = params[i];
    float4 fe   = (float4)(0.0f, 0.0f, 0.0f, 0.0f);
    
    for (int j = 0; j < n; j++) {
        if (i == j) continue;
        
        float3 pj   = pos[j].xyz;
        float4 parj = params[i];
        
        float3 d  = pj - pi;
        float ir2 = dot(d, d) + 1e-32;
        float ir  = sqrt(ir2);
        float qq  = pari.z * parj.z;
        float E   = COULOMB_CONST * qq * ir;
        
        fe += (float4)(d * (E * ir2), E);
    }
    fe_out[i] = fe;
}

__kernel void nbody_coulomb_local(
    const int n, 
    __global const float4* pos, 
    __global const float4* params, 
    __global       float4* fe_out
) {
    int gid = get_global_id(0);
    int lid = get_local_id(0);
    int group_size = get_local_size(0);

    if (gid >= n) return;  // Early exit if gid is out of bounds

    __local float4 local_pos[WORKGROUP_SIZE];
    __local float4 local_params[WORKGROUP_SIZE];

    float3 pi   = pos[gid].xyz;
    float4 pari = params[gid];
    float4 fe   = (float4)(0.0f, 0.0f, 0.0f, 0.0f);

    // Loop over all workgroups
    for (int wg = 0; wg < n; wg += group_size) {
        int local_idx = wg + lid;

        // Load data into local memory if within bounds
        if (local_idx < n) {
            local_pos[lid] = pos[local_idx];
            local_params[lid] = params[local_idx];
        }

        // Synchronize to ensure all local memory is populated
        barrier(CLK_LOCAL_MEM_FENCE);

        // Compute interactions with particles in the local memory
        for (int j = 0; j < group_size; j++) {
            int global_j = wg + j;

            if (global_j >= n || gid == global_j) continue;  // Skip out-of-bounds and self-interaction

            float3 pj   = local_pos[j].xyz;
            float4 parj = local_params[j];

            float3 d  = pj - pi;
            float ir2 = dot(d, d) + 1e-32;
            float ir  = sqrt(ir2);
            float qq  = pari.z * parj.z;
            float E   = COULOMB_CONST * qq * ir;

            fe += (float4)(d * (E * ir2), E);
        }

        // Synchronize before the next iteration
        barrier(CLK_LOCAL_MEM_FENCE);
    }

    // Write the computed force to global memory
    fe_out[gid] = fe;
}

/*
__kernel void nbody_coulomb_local(
    const int n, 
    __global const float4* pos, 
    __global const float4* params, 
    __global       float4* fe_out
) {
    int gid = get_global_id(0);
    int lid = get_local_id(0);
    int group_size = get_local_size(0);

    __local float4 local_pos[WORKGROUP_SIZE];
    __local float4 local_params[WORKGROUP_SIZE];

    float3 pi   = pos[gid].xyz;
    float4 pari = params[gid];
    float4 fe   = (float4)(0.0f, 0.0f, 0.0f, 0.0f);

    // Loop over all workgroups
    for (int wg = 0; wg < n; wg += group_size) {
        int local_idx = wg + lid;

        // Load data into local memory
        if (local_idx < n) {
            local_pos[lid] = pos[local_idx];
            local_params[lid] = params[local_idx];
        }

        // Synchronize to ensure all local memory is populated
        barrier(CLK_LOCAL_MEM_FENCE);

        // Compute interactions with particles in the local memory
        for (int j = 0; j < group_size && wg + j < n; j++) {
            if (gid == wg + j) continue;

            float3 pj   = local_pos[j].xyz;
            float4 parj = local_params[j];

            float3 d  = pj - pi;
            float ir2 = dot(d, d) + 1e-32;
            float ir  = sqrt(ir2);
            float qq  = pari.z * parj.z;
            float E   = COULOMB_CONST * qq * ir;

            fe += (float4)(d * (E * ir2), E);
        }

        // Synchronize before the next iteration
        barrier(CLK_LOCAL_MEM_FENCE);
    }

    // Write the computed force to global memory
    fe_out[gid] = fe;
}
*/
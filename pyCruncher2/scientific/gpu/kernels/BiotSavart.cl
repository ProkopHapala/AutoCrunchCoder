// BiotSavart.cl - accumulate magnetic field B at sampling points from discrete current elements
// The per-element contribution is dB = K * I * ( dl x r ) / |r|^3, with r = r_sample - r_src

// Constants
#define MU0_4PI 1.0e-7f   // mu0/(4*pi) in SI units

// Some helpers in Forces.cl reference COULOMB_CONST; provide a benign default to compile standalone
#ifndef COULOMB_CONST
#define COULOMB_CONST 1.0f
#endif

// We will inject helper functions (e.g., getBiotSavart_dB) from Forces.cl via preprocessing
//<<<file Forces

// Default macro to compute and accumulate dB; can be overridden via preprocessing
// Usage context variables available: dp (float3), dl (float3), I (float), K (float), Bacc (float3)
#ifndef GET_DB_EXPR
#define GET_DB_EXPR \
    { float4 dB4 = getBiotSavart_dB(dp, dl, I, K); Bacc += (float3)(dB4.x, dB4.y, dB4.z); }
#endif

__kernel void accumulateB(
    __global const float4* src_pos,   // [M] source element positions (xyz), w unused
    __global const float4* src_dl,    // [M] source differential vectors (xyz), w unused
    __global const float*  src_I,     // [M] current magnitude per element (can be uniform)
    const int M,                      // number of source elements
    __global const float4* sample_pos,// [N] sampling point positions (xyz)
    const int N,                      // number of sampling points
    const float K,                    // prefactor (e.g., MU0_4PI)
    __global float4* out_B            // [N] output B field per sample (xyz), w reserved
){
    const int j = get_global_id(0);
    if (j >= N) return;

    const float3 rj = (float3)(sample_pos[j].x, sample_pos[j].y, sample_pos[j].z);
    float3 Bacc = (float3)(0.f,0.f,0.f);

    // Simple global-memory loop over elements (can be optimized with tiling later)
    for (int i=0; i<M; i++){
        const float3 ri  = (float3)(src_pos[i].x, src_pos[i].y, src_pos[i].z);
        const float3 dli = (float3)(src_dl[i].x,  src_dl[i].y,  src_dl[i].z);
        const float  Ii  = src_I[i];
        const float3 dp  = rj - ri;                   // vector from element to sample
        const float3 dl  = dli;                        // element vector
        const float  I   = Ii;                         // current magnitude
        // Allow specialization via macro
        GET_DB_EXPR
    }

    out_B[j] = (float4)(Bacc.x, Bacc.y, Bacc.z, 0.f);
}

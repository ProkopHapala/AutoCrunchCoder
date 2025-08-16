// NumIntegral.cl - Generic accumulation kernel specialized via macro substitution
// This kernel sums pairwise contributions from sources to samples.
// Available context in GET_PAIR_EXPR:
//   dp    : float3 = src_pos[i].xyz - sample_pos[j].xyz    (source - sample)
//   dl    : float3 = src_vec[i].xyz                         (per-source vector)
//   I     : float  = src_f[i]                               (per-source scalar)
//   par   : float4 = src_par[i]                             (per-source parameters)
//   REQH0 : float4 (uniform)                                (global parameters)
//   ffpar : float8 (uniform)                                (global parameters)
//   K     : float  (uniform)                                (global scalar constant)
//   contrib : float4 (must be assigned by macro)            (xyz vector + w scalar)
// The kernel will accumulate 'contrib' into the output per sample.

// Provide benign default for constants referenced by helpers from Forces.cl
#ifndef COULOMB_CONST
#define COULOMB_CONST 1.0f
#endif

// Inject helper library
//<<<file Forces

// Default macro produces zero contribution; user should override with custom code
#ifndef GET_PAIR_EXPR
#define GET_PAIR_EXPR \
    { contrib = (float4)(0.f,0.f,0.f,0.f); }
#endif

__kernel void accumulatePairs(
    __global const float4* src_pos,     // [M] source positions (xyz)
    __global const float4* src_vec,     // [M] source vectors   (xyz) e.g., dl
    __global const float*  src_f,       // [M] source scalars   e.g., current
    __global const float4* src_par,     // [M] source params    e.g., REQH per atom
    const int              M,           // number of sources
    __global const float4* sample_pos,  // [N] sample positions (xyz)
    const int              N,           // number of samples
    const float4           REQH0,       // uniform parameter vector
    const float8           ffpar,       // uniform parameter vector
    const float            K,           // uniform scalar constant
    __global float4*       out_sum      // [N] accumulated result per sample
){
    const int j = get_global_id(0);
    if(j>=N) return;

    const float3 pj = (float3)(sample_pos[j].x, sample_pos[j].y, sample_pos[j].z);
    float4 SUM = (float4)(0.f,0.f,0.f,0.f);

    for(int i=0; i<M; i++){
        const float3 si  = (float3)(src_pos[i].x, src_pos[i].y, src_pos[i].z);
        const float3 dl  = (float3)(src_vec[i].x, src_vec[i].y, src_vec[i].z);
        const float  I   = src_f[i];
        const float4 par = src_par[i];
        const float3 dp  = si - pj;          // source - sample (matches nonbond usage)
        float4 contrib;                      // to be set by macro
        //<<<GET_PAIR_EXPR
        SUM += contrib;
    }
    out_sum[j] = SUM;
}

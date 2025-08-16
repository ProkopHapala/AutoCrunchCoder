# NumIntegrationCL: A Macro-Specialized GPU Integral Framework

This document describes the generalized OpenCL-based numerical integration framework built around a single kernel template specialized at build time via macro injection. It explains the design philosophy, current implementation, usage, developer notes, and a forward-looking plan to integrate with Computer Algebra Systems (CAS) for analytical integrals. It also outlines applications across physics and engineering.


## Goals
- **Unify kernels**: Avoid copy-paste of many similar OpenCL kernels by using a single generic template that is specialized via macros.
- **Rapid experimentation**: Allow researchers to switch integrands (physics formulas) without touching kernel control-flow or buffer plumbing.
- **Performance-friendly**: Keep a clear path to GPU optimizations (tiling, PBC, vectorization) while retaining flexibility.
- **Reusability**: Reuse helper functions in `Forces.cl` and existing infrastructure in `OpenCLBase.py`.


## Philosophy
- **Single generic kernel, many integrands**: Implement one kernel (`accumulatePairs`) that loops over source→sample pairs and accumulates a contribution `contrib`. The integrand is injected via a compile-time macro (`GET_PAIR_EXPR`).
- **Conventions, not ad hoc**: Standardize memory layout (e.g., float4 alignment), parameter passing (`REQH0`, `ffpar`, `K`), and naming. This lets different integrands share the same driver code.
- **Fail loudly, debug easily**: Macro injection is explicit; if something does not compile, the preprocessed source is straightforward to inspect.
- **Incremental optimization**: Start with a simple global-memory loop and keep the door open for later shared-memory tiling, PBC images, and batching.


## What is implemented now
- Kernel template `accumulatePairs` in `pyCruncher2/scientific/gpu/kernels/NumIntegral.cl` with a hook `//<<<GET_PAIR_EXPR`.
- Helper library `pyCruncher2/scientific/gpu/kernels/Forces.cl` is injected via `//<<<file Forces` so all helper functions are available to macros.
- Python driver and demo `pyCruncher2/scientific/gpu/test_num_integral_cl.py` showing two examples:
  - **Biot–Savart** magnetic field accumulation with `getBiotSavart_dB()`.
  - **Morse non-bonded** potential accumulation using `getMorse` and its polynomial variants.
- Reuse of `OpenCLBase.py` preprocessing (file/macro substitution), buffer management, and kernel argument generation.
- Plotting of results (|B| for Biot–Savart, energy for Morse) for quick inspection.


## Architecture and Data Conventions
- File: `pyCruncher2/scientific/gpu/kernels/NumIntegral.cl`
  - Kernel: `__kernel void accumulatePairs(...)`
  - Buffers:
    - `src_pos[M]`  float4 (xyz, w unused)
    - `src_vec[M]`  float4 (xyz, e.g., dl)
    - `src_f[M]`    float  (scalar per source, e.g., current I)
    - `src_par[M]`  float4 (per-source params; e.g., per-atom REQH)
    - `sample_pos[N]` float4 (xyz)
    - `out_sum[N]`  float4 (xyz contribution + w scalar, integrand decides)
  - Uniforms: `REQH0` (float4), `ffpar` (float8), `K` (float)
  - Pair loop context available to the macro (`GET_PAIR_EXPR`):
    - `dp`   = `src_pos[i].xyz - sample_pos[j].xyz` (source - sample)
    - `dl`   = `src_vec[i].xyz`
    - `I`    = `src_f[i]`
    - `par`  = `src_par[i]`
    - `REQH0`, `ffpar`, `K`
    - You must assign `float4 contrib` inside the macro.

- Preprocessing: `pyCruncher2/scientific/gpu/OpenCLBase.py`
  - Replaces `//<<<file Forces` with the contents of `Forces.cl`.
  - Replaces any line starting with `//<<<GET_PAIR_EXPR` with the provided macro string.

- Helpers: `pyCruncher2/scientific/gpu/kernels/Forces.cl`
  - Contains vector math and physics utility functions, e.g., `getBiotSavart_dB`, `getMorse`, `getMorse_lin5`, `getMorse_lin9`, `getMorse_lin17`, Coulomb/LJ helpers, etc.


## Using the Framework
### Quick start (end-to-end demo)
- Run the generic tests and plots:
```bash
python -u -m pyCruncher2.scientific.gpu.test_num_integral_cl | tee OUT-generic-integral
```

### Specialize Biot–Savart
- Macro in `test_num_integral_cl.py`:
```c
// dp is source - sample here -> use -dp to match Forces.cl convention (r = sample - source)
contrib = getBiotSavart_dB(-dp, dl, I, K);
```
- Output: `out_sum[j].xyz` accumulates B, `.w` unused (0).

### Specialize Morse (non-bonded)
- Macro in `test_num_integral_cl.py` builds `REQH` by combining per-source `par` with uniform `REQH0` then calls the chosen approximation:
```c
{ float4 REQH=par; REQH.x+=REQH0.x; REQH.yzw*=REQH0.yzw; contrib = getMorse(dp, REQH.x, REQH.y, ffpar.x); }
```
- Output: `out_sum[j].xyz` force-like vector, `out_sum[j].w` energy-like scalar (depends on the integrand function semantics).

### Adding a New Integrand
1. Identify or implement a helper in `Forces.cl` (or inline directly in the macro if small).
2. Define `GET_PAIR_EXPR` macro string in Python with these rules:
   - You have access to `dp`, `dl`, `I`, `par`, `REQH0`, `ffpar`, `K`.
   - Compute and assign `float4 contrib`.
3. Build and run via `NumIntegralSim.build_program(macros={ 'GET_PAIR_EXPR': your_macro })` and `run_accumulate(...)`.

### Data Preparation Tips
- Use float4-aligned arrays for positions/results to match OpenCL alignment. In Python, the helper `to_f4()` in `test_num_integral_cl.py` handles (n,3) or (n,4) inputs.
- Uniforms:
  - `REQH0` packs global 4 parameters to be combined per-pair as you see fit inside the macro.
  - `ffpar` packs up to 8 scalars for global tuning of the integrand.
  - `K` is a single scalar, e.g., `MU0_4PI` for Biot–Savart.

## Developer Notes
- **dp direction**: In `NumIntegral.cl`, `dp = src - sample`. Some formulas use `r = sample - source`; just flip sign in the macro (`-dp`).
- **Macro style**: Keep the macro a single OpenCL statement or a braced block. Ensure `contrib` is assigned unconditionally.
- **Build errors**: If compilation fails, `OpenCLBase.build_program()` can print the preprocessed source for debugging.
- **Performance**: Current implementation uses a simple global loop. For large `M,N`, add tiling and local memory, modeled e.g. on `scanNonBond2` in `pyCruncher2/scientific/gpu/kernels/Molecular.cl`.
- **Plotting**: The generic demo plots `|B|` and Morse energy to quickly sanity-check results.
- **Compatibility**: `pyopencl.array.vec` is deprecated; consider migrating to `pyopencl.cltypes` for uniform vectors in future refactors.

## Outlook: CAS Integration (Maxima, SymPy)
We aim to connect this framework with CAS tools to:
- **Derive closed-form integrals** for canonical geometries, then compare them against numerical accumulation for validation/benchmarking.
- **Auto-generate macro code** from symbolic expressions for specialized integrands.

### Planned workflow
1. **Define geometry & integrand** in Python.
2. **CAS back-end** (Maxima/SymPy) computes analytical expressions (e.g., fields/potentials due to rings, line segments, layers).
3. **Code generation**: Convert symbolic expressions to OpenCL-compatible code snippets.
4. **Inject** these snippets as `GET_PAIR_EXPR` macros for fast evaluation or as reference/validation curves.

### First analytical targets
- Electromagnetism & Vortex methods:
  - Magnetic field for a circular current loop (on/off axis), finite line segment, and half-infinite line.
  - Potential-flow analogues using Biot–Savart to compute induced velocity from vortex filaments.
- Electrostatics & dipole layers:
  - Electric field/potential above an infinite/half-plane of dipoles, 2D layers, or 1D dipole lines.
- FEM-related kernels:
  - Closed-form integrals of simple basis functions over segments/triangles/tetrahedra for assembling stiffness/mass matrices.
- Materials & acoustics:
  - Green’s function integrals for layered media approximations.

### Integration details
- **SymPy**: Derive expressions symbolically, simplify, and export C/OpenCL code (`sympy.printing.ccode`) with manual tweaks for OpenCL types.
- **Maxima**: Use `.mac` scripts in `Maxima/` and `Maxima/wxMaxima/` to derive results; export to a simple text format; write a small parser to turn them into macro strings.
- **Validation**: Compare analytical expressions from CAS to numerical accumulation results (`NumIntegral.cl`) over scan lines or grids. In the limit of small integration step size, the two should agree (up to machine precision).
   * maybe we need to use double precision in some case, but that is not efficient on GPU. We keep it for later.

## How to Contribute New Integrands
1. Add/verify helper in `Forces.cl` or write a compact inline macro.
2. Craft a `GET_PAIR_EXPR` that assigns `contrib`.
3. Write a small driver similar to `test_num_integral_cl.py` to prepare buffers and invoke `accumulatePairs`.
4. Add plots and test cases that compare to analytical or known numerical results.

## References in Repository
- Kernel template: `pyCruncher2/scientific/gpu/kernels/NumIntegral.cl`
- Helpers: `pyCruncher2/scientific/gpu/kernels/Forces.cl`
- Generic demo: `pyCruncher2/scientific/gpu/test_num_integral_cl.py`
- Supporting infra: `pyCruncher2/scientific/gpu/OpenCLBase.py`
- Related examples: `pyCruncher2/scientific/gpu/run_biot_savart.py`, `pyCruncher2/scientific/gpu/run_scanNonBond.py`
- Maxima assets: `Maxima/`, `Maxima/wxMaxima/`

## Running the Demo
```bash
python -u -m pyCruncher2.scientific.gpu.test_num_integral_cl | tee OUT-generic-integral
```

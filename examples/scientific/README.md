# examples/scientific

End-to-end scientific computing examples: from symbolic math derivation to GPU kernel execution.

## Files

- `maxima_derivatives.py` — Compute symbolic derivatives using the Maxima CAS wrapper (`get_derivs()` for energy and force expressions).
- `opencl_nbody.py` — OpenCL N-body simulation using `OpenCLBase` for device selection and kernel loading.
- `cuda_nbody.py` — CUDA N-body simulation using PyCUDA `SourceModule` for runtime kernel compilation.
- `slater_orbital_integration.py` — Numerical integration of Slater-type orbitals — a common task in computational chemistry.

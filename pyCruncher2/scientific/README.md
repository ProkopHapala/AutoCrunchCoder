# pyCruncher2/scientific

Scientific computing helpers: symbolic math (Maxima CAS), GPU kernels (OpenCL/CUDA), periodic table data, and shared plotting utilities. These are the reorganized counterparts of `pyCruncher/Maxima.py`, `pyCruncher/code_derivs.py`, `pyCruncher/tools.py`, and the GPU/element code.

## Files

- `elements.py` — Flat list of element tuples indexed by constants (`index_Z`, `index_Rcov`, `index_Rvdw`, `index_color`, `index_val_elec`, `index_mass`). SSOT for element properties — no class, just data. Used by the molecule renderer and plotting helpers for consistent atom coloring.
- `plotUtils.py` — `plotEF()` 2×1 subplot for energy/force validation; `numDeriv()` from arrays; element colors from `elements.py`. Keeps plotting separate from computation (SoC).

## Subdirectories

- `cas/` — Maxima CAS wrapper, code-derivs glue, and callable math tools.
- `gpu/` — OpenCL base class, utility functions, standalone smoke tests, and example GPU kernels.

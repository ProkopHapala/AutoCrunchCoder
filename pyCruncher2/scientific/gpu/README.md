# pyCruncher2/scientific/gpu

GPU and high-performance numerical computing helpers. OpenCL is the primary backend; CUDA is supported via PyCUDA for NVIDIA-only scenarios.

## Files

- `OpenCLBase.py` — `select_device()` prefers NVIDIA GPUs (PoCL/CPU timings must not be reported as GPU); `OpenCLBase` class manages context, queue, and a named buffer dict; `load_program()` compiles `.cl` files and extracts kernel headers via regex.
- `clUtils.py` — Flat helper functions (not a class): `bytePerFloat=4` for memory calculation; `FFT=None` lazy-init; rounding global work sizes to local-size multiples.
- `opencl.py` — Standalone OpenCL smoke test: `PYOPENCL_CTX` env selects device; `sys.path.append('../')` for in-dir execution.
- `cuda.py` — Standalone CUDA smoke test: `pycuda.autoinit` default context; `SourceModule` runtime compilation (no nvcc); reads `./nbody.cu`.
- `run_biot_savart.py` — Biot-Savart magnetic field integration on GPU.
- `run_scanNonBond.py` — Non-bonded interaction scan on GPU.
- `test_num_integral_cl.py` — Numerical integration test on OpenCL.
- `kernels/` — `.cl` kernel source files.

See `doc/OpenCLBase.md` and `docs/NumIntegrationCL.md` for details.

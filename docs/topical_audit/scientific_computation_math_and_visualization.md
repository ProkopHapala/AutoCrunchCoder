# 4. Scientific Computation, Math & Visualization

## What this topic does

Symbolic math derivations, high-performance numeric kernels, and a web-based 3D molecule viewer. This is the execution side of the repo: the LLM agents generate ideas, and these files turn them into force-field evaluators and simulation kernels.

## Main challenges and how they are solved

- **Turning equations into correct code**: Maxima derives energy/force expressions; `pyCruncher/code_derivs.py` checks the generated code against the original formula and counts arithmetic cost.
- **Fast numeric kernels on CPU and GPU**: header-only `Vec3`/`Vec4` classes, inline force-field functions, and `OpenCLBase` for quick OpenCL experiments.
- **Exploring results**: `molecule_renderer/` gives an immediate 3D view of atomic configurations and bonds using Three.js.

## Core files and their essence

### `pyCruncher/Maxima.py` and `pyCruncher2/scientific/cas/maxima.py`

Thin Python wrappers around the Maxima CAS.

- `run_maxima(code)` — send a batch of Maxima commands to a subprocess, turn off 2D display, and return stdout.
- `get_derivs(Eformula, DOFs)` — compute energy `E` and all `dE_<var>` derivatives for a list of degrees of freedom.
- `run_maxima_script(script_content, timeout)` — robust `subprocess.run` wrapper with timeout.
- `label_maxima_output()` — pair raw Maxima output lines with user labels.

### `pyCruncher/code_derivs.py`

Glue symbolic math to LLM-generated code.

- `makeFormulas()` / `getOrMakeFormulas()` — compute or re-use `E` and `dE_` formulas from `Maxima.get_derivs()`.
- `makePrompt_understand()` / `makePrompt_code_first()` / `makePrompt_simplify()` — fill prompt templates under `prompts/ImplementPotential/`.
- `formulasFromResponse()` — parse an LLM response that claims to contain `E: ...` and `dE_x: ...`.
- `check_formulas()` — generate a Maxima verification script that expands and compares the generated expressions with the reference expressions; reports the first non-zero difference.
- `count_operations()` — crude FLOP estimate (div/mul/add/sub/pow) for generated expressions.

### `pyCruncher/tools.py`

Math tools that the LLM agents can call.

- `symbolic_derivative()`, `compute_integral()`, `compute_numerical_derivative()`, `check_numerical_vs_analytical_derivative()` — exact vs numerical checks using Maxima + SymPy + NumPy.
- `compute_expression_steps()` — evaluate a sequence of named math expressions.

### `cpp/Vec3.h`

Header-only 3D vector class.

- `Vec3T<T>` — union of `x/y/z`, `a/b/c`, and `array[3]`.
- Swizzles (`xzy()`, `yxz()`, ...), component-wise `set()`, `get()`, `add()`, `mul()`, `div()`, operators `+`, `-`, `*`, `/`.
- `dot()`, `norm2()`, `norm()`, `normalize()`, `normalized()`, `cross()`.
- Typedefs `Vec3i`, `Vec3f`, `Vec3d`, `Vec3b` and constants `Vec3dZero`, `Vec3dOne`, `Vec3dX`, etc.

### `cpp/ForceFields.cpp`

Inline force-field evaluators and parameter-derivatives.

- `getCoulomb()`, `_getCoulomb()` — Coulomb energy and force on a `Vec3d` displacement, plus variational derivative w.r.t. `qq`.
- `getLJ()`, `_getLJ()` — Lennard-Jones energy/force with `E0` and `R0` parameters.
- `getLJQ()`, `_getLJQ()` — combined LJ + Coulomb energy/force.
- `varCoulomb()`, `varLJ()`, `varLJQ()` — compute derivatives of energy w.r.t. fitting parameters, useful for force-field parameter optimization.

### `pyCruncher2/scientific/gpu/OpenCLBase.py`

OpenCL orchestration.

- `select_device()` / `print_devices()` — choose an NVIDIA (or fallback) OpenCL device.
- `OpenCLBase` — context, command queue, buffer dictionary, and program loader.
- `load_program()` — compile an OpenCL `.cl` source file and optionally extract kernel signatures.
- `extract_kernel_headers()` — regex-based kernel header extraction for quick inspection.

### Other GPU/CUDA helpers

- `pyCruncher2/scientific/gpu/clUtils.py` — OpenCL utility functions.
- `pyCruncher2/scientific/gpu/opencl.py` / `cuda.py` — runner wrappers.
- `pyCruncher2/scientific/gpu/run_biot_savart.py`, `run_scanNonBond.py`, `test_num_integral_cl.py` — example numeric integration tasks on the GPU.
- `pyCruncher2/scientific/gpu/kernels/` — `.cl` kernel source files.

### `molecule_renderer/moleculeRenderer.js`

Web-based 3D renderer using Three.js.

- `MoleculeRenderer` — takes a `Molecule` object and a Three.js scene.
- `renderMolecule()` — creates sphere meshes for atoms and cylinder meshes for bonds, positioning/rotating bonds from the two atom vectors.

### Supporting files

- `molecule.js` — `Molecule` class with atom symbols, positions, and bond generation.
- `sceneSetup.js` — camera, lights, renderer setup.
- `selectionManager.js` — click/selection handling.
- `server.py` — tiny Python HTTP static server to open `index.html`.
- `pyCruncher2/scientific/elements.py` — periodic table / element data.
- `pyCruncher2/scientific/plotUtils.py` — shared plotting helpers.
- `Maxima/my_functions.mac` / `test_maxima.mac` — reusable Maxima script definitions.

### Tests and examples

- `examples/scientific/maxima_derivatives.py`, `slater_orbital_integration.py`, `opencl_nbody.py`, `cuda_nbody.py` — topic-specific examples.
- `tests/test_maxima_derivs.py`, `test_pymaxima.py`, `test_pyCUDA.py`, `test_pyOpenCL.py`, `test_coder_forcefield*.py` — quick tests.
- `tests/Cpp_Train/CodeExamples/` — header-only C++ snippets used as training/reference material.
- `doc/MaximaTutorial.md`, `doc/OpenCLBase.md`, `docs/NumIntegrationCL.md` — reference docs.

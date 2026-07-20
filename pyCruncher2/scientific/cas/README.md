# pyCruncher2/scientific/cas

Computer Algebra System integration — Maxima subprocess wrapper, code-derivs glue, and callable math tools. These are reorganized versions of `pyCruncher/Maxima.py`, `pyCruncher/code_derivs.py`, and `pyCruncher/tools.py`.

## Files

- `__init__.py` — Package marker (empty).
- `maxima.py` — Subprocess wrapper: `display2d:false` for machine-parseable output; `$` = silent, `;` = print; `get_derivs(E, DOFs)` computes E + all partial derivatives in one batch call.
- `code_derivs.py` — Glue between Maxima and LLM-generated force-field code: `check_formulas()` generates a Maxima diff script (zero difference = correct); `count_operations()` crude FLOP estimate; fills `prompts/ImplementPotential/` templates.
- `maxima_tools.py` — Callable math tools for LLM agents: `symbolic_derivative()` (Maxima), `compute_integral()`, `compute_numerical_derivative()` (NumPy), `check_numerical_vs_analytical_derivative()` (SymPy vs finite-diff cross-validation).

See `doc/MaximaTutorial.md` for Maxima usage and `docs/topical_audit/04_scientific_computation_math_and_visualization.md` for the full topic.

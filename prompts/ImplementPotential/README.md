# prompts/ImplementPotential

Prompt templates for the force-field code generation pipeline. The workflow: Maxima derives energy and force expressions → `code_derivs.py` fills these templates → LLM generates C++ code → `check_formulas()` verifies correctness against Maxima reference.

## Files

**Agent personas:**
- `coder_system_prompt.md` — System prompt for the code-generation agent (writes C++ force-field code).
- `matematician_system_prompt.md` — System prompt for the symbolic-math assistant (derives/simplifies expressions).

**Code generation:**
- `code_first.md` — Initial code-generation prompt (first attempt).
- `code_cpp.md` / `code_cpp_gpt.md` — C++ implementation prompts (different model variants).
- `code_interface_cpp.md` / `code_interface_ctypes.md` — Interface-generation prompts (C++ header + ctypes binding).

**Error handling:**
- `code_incorect_result.md` — Prompt for handling incorrect numerical outputs (formula mismatch).
- `code_not_compile.md` — Prompt for fixing compilation errors.

**Optimization:**
- `code_optimize.md` — Optimization prompt (reduce FLOP count).
- `simplify.md` / `simplify2.md` — Equation simplification prompts (algebraic optimization).
- `substitution.md` — Variable substitution prompt (intermediate variables for readability/performance).

**Understanding:**
- `understand.md` — Concept-explanation prompt (asks the model to explain the physics/math).
- `System_bak.md` — Backup system prompt notes.

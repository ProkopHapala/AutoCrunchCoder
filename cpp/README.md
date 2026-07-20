# cpp

Header-only C++ vector math and inline force-field evaluators for scientific computing. Designed for `Vec3d` (double precision). All functions inline for zero-overhead abstraction. Used by the force-field code generation pipeline and compiled to shared libraries via `pyCruncher/compile_utils.py`.

## Files

- `Vec3.h` — `Vec3T<T>` union (`x/y/z` = `a/b/c` = `array[3]`); swizzles (`xzy()`, `yxz()`...); `dot()`, `cross()`, `norm()`, `normalize()`; typedefs `Vec3i/f/d/b`; constants `Vec3dZero/One/X/Y/Z`.
- `Vec4.h` — 4D counterpart: homogeneous coordinates, quaternions.
- `Vec2.h` — 2D counterpart: 2D geometry, texture coords.
- `ForceFields.cpp` — `getCoulomb()/_getCoulomb()` energy+force+variational derivative w.r.t. `qq`; `getLJ()/_getLJ()` with `E0`/`R0` params; `getLJQ()` combined; `varCoulomb()/varLJ()/varLJQ()` for parameter optimization.

See `docs/topical_audit/04_scientific_computation_math_and_visualization.md` for the full topic.

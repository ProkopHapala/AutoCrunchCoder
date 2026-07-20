# Maxima

Maxima CAS script files — reusable function definitions and test scripts for symbolic mathematics. These scripts are loaded by `pyCruncher/Maxima.py` or `pyCruncher2/scientific/cas/maxima.py` via subprocess calls.

## Files

- `my_functions.mac` — Custom Maxima function definitions (energy expressions, force derivations, simplification rules) used by the code-derivs pipeline.
- `test_maxima.mac` — Test/validation script to verify Maxima is working correctly and functions produce expected output.

See `doc/MaximaTutorial.md` for Maxima usage and `pyCruncher/Maxima.py` for the Python integration layer.

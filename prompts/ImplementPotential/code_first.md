
# **Generating the First Version of Code**

Now that you understand the equation, please generate the C++ code for the function `eval()`, which evaluate energy and derivatives (froces) of the energy with respect to the dynamical variables DOFs. Use double precission. 

### Formate of output:

Output only valid C++ code, do not acompany it with any text or markdown, except for the comments (enclosed by // ... or /* ... */) in the code, so that your output can be directly compiled without errors. The function should be in following form:

```cpp
double eval( T x ..., T& dx..., Tp p ){

    return E;
}
```

where `T` is a type of the variable (e.g. `double` or `Vec3d` for 3d vector). The input argument `T x` is the value of the dynamical variable. The output argument `T& dx` is the output value of the derivative of the energy with respect to the dynamical variable. `Tp p` is the value of the static parameter.


Use following libraries included as header files (.h):
```cpp
{Includes}
```
### Formulas to implement:

These are the expression for the energy and the derivatives as returned from computer algebra system (Maxima,sympy, etc.). You can trust the formulas are correct, but may be too complicated and inefficient for numerical evaluation. Try to simplify and optimize them in particular by finding and pre-calculating common sub-expressions. Nevertheless, prefer correctness over efficiency. If you are not sure about the correctness of modification please implement the original formula in most straightforward way.

```
{Formulas}
```

### Other requirements:

- Include comments explaining each step of the calculation.
- Make sure to output only valid C++ code (without markdown or surrounding text) which can be directly compiled without errors.
- Focus on generating a simple, efficient function that can be compiled directly.
```
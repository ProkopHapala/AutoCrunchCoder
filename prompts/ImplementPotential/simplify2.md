# **Simplify and Optimize the Expression**

Below are the mathematical formulas for evaluating the energy and its derivatives with respect to the dynamical variables (DOFs):

```Maxima
{Formulas}
```

These formulas were obtained from the computer algebra system Maxima, and we assume they are correct. However, they are not optimized for numerical evaluation. Your task is to simplify the expressions and optimize them for numerical computation, focusing especially on pre-calculating common sub-expressions. The goal is to minimize the total number of operations.

When optimizing, consider that the most costly operations are functions like `sin`, `cos`, `exp`, `log`, `sqrt`, and `atan` and `^` try to use them in minimum amount. Division (`/`) is also quite expensive, whereas multiplication (`*`), addition (`+`), and subtraction (`-`) are relatively cheap.

#### Tips for optimizing the expression:

- Powers with integer exponents, such as `x^6`, should be expressed as multiplications to minimize costly `^` operations. For example: 
  ```Maxima
  x2: x*x; 
  x6: x2*x2*x2;
  ```
- Pre-calculate fractions where possible. For example, replace 
  ```Maxima
  expr: (a/b) + (a/b)^2 + (a/b)^4
  ``` 
  with 
  ```
  ab: a/b; 
  ab2: ab*ab; 
  expr: ab + ab2 + ab2*ab;
  ```
- To minimize number of divisions we try to pre-calculate inverse and its powers. For example: `1/x`. For example,
  ```Maxima
  expr: 1/x + 1/x^2 + 1/x^3
  ```
  can be efficiently evaluated as
  ```
  inv_x = 1/x; 
  inv_x2: inv_x*inv_x; 
  expr: inv_x + inv_x2 + inv_x2*inv_x;
  ```
- Find and pre-calculate common sub-expressions and store them in temporary local variables. For example:
  ```Maxima
  expr: (x^2 - y^2) * (x^2 + y^2) + 1/(x^2 - y^2);
  ```
  can be optimized as:
  ```Maxima
  x2: x*x; y2: y*y; 
  x2y2: x2 - y2; 
  expr: (x2 + y2) * x2y2 + 1/x2y2;
  ```
- For evaluating polynomials, use Horner's method. For example:
  ```Maxima
  expr: 5*x^3 + 2*x^2 - 3*x + 4;
  ```
  can be rewritten as:
  ```Maxima
  expr: 4 + x*(-3 + x*(2 + x*5));
  ```


#### Example:

Consider the following expression and its derivatives:
```Maxima
E       : (3*(sj^2 + si^2)) / (2*si^2*sj^2) - (6*(sj^2 + si^2) - 4*r^2) / (sj^2 + si^2)^2;
dE_si   : (-3*sj^6 + 3*si^4*sj^2 - 9*si^2*sj^4 + 9*si^6 - 16*r^2*si^4) / (si^3*(sj^2 + si^2)^3);
dE_sj   : (-3*si^6 + 3*si^2*sj^4 - 9*si^4*sj^2 + 9*sj^6 - 16*r^2*sj^4) / (sj^3*(sj^2 + si^2)^3);
dE_r    : (8*r) / (sj^2 + si^2)^2;
```

This can be simplified and optimized by pre-calculating common sub-expressions:

```Maxima
/* pre-calculate sub-expressions */
r2           : r*r;
si2          : si*si; 
sj2          : sj*sj; 
si2sj2       : si2 + sj2;
inv_si       : 1/si;
inv_sj       : 1/sj; 
inv_si2      : inv_si*inv_si; 
inv_sj2      : inv_sj*inv_sj;
inv_si2sj2   : 1/si2sj2;
inv_sisi2sj2 : inv_si*inv_si2sj2;

/* final formulas and the derivative */
E            : (3/2)*si2sj2*inv_si2*inv_sj2 - (6*si2sj2 - 4*r2)*inv_si2sj2*inv_si2sj2;
dE_si        : (-3*(sj2 - si2)*(si2 + sj2)*(sj2 + 3*si2) - 16*r2*si2*si2) * inv_sisi2sj2*inv_sisi2sj2*inv_sisi2sj2;
dE_sj        : (-3*(si2 - sj2)*(si2 + sj2)*(si2 + 3*sj2) - 16*r2*sj2*sj2) * inv_sisi2sj2*inv_sisi2sj2*inv_sisi2sj2;
dE_r         : 8*r*inv_si2sj2*inv_si2sj2;
```

## Task:

Using the instructions and the example above, simplify and optimize the following expression and its derivatives by finding and pre-calculating common sub-expressions:

```Maxima
{Formulas}
```

#### Output Format:

- Ensure the output is valid Maxima code without any accompanying text or markdown. The output should be directly executable in Maxima.
- Use `:` for assignments (e.g., `expr: 5*x + 1/x + 1.25;`).
- NEVER include any comments, text or markdown formatting in the output !!!
- use concise names for sub-expression.
- The final formulas should have the energy denoted by `E:` followed by the derivatives, where each derivative is denoted as `dE_*:`, with `*` being the name of the dynamical variable (DOF), such as `dE_si:` for the derivative with respect to `si` and `dE_r:` for the derivative with respect to `r`.
- Each expression should be a single-line assignment. Do not break lines in the middle of the expression, even if it is long.

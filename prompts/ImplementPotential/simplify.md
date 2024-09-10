# **Simplify and optimize the expression**

Here is the mathematical formula for evaluation of the energy and its derivatives with respect to dynamical variables (DOFs): 
```Maxima
{Formulas}
```

The formulas were obtained from computer algebra system (Maxima, sympy) and we can assume that they are correct. However they are not optimized for numerical evaluation. Try to simplify and optimize the expression for numerical evaluation.

#### Some tips how simplify and optimized expression:

* Find common sub-expressions and pre-calculate them (store them in temporary local variables). For example `expr: (x^2-y^2)*(x^2+y^2) + 1/(x^2-y^2);` can be optimized by precalcualting sub-expression to `x2:x*x; y2:y*y; x2y2:x2-y2; expr:(x2+y2)*x2y2 + 1/x2y2;`
* Powers with integer exponent such as `x^6` express as multiplication, e.g. `x2:x*x; x6: x2*x2*x2;`
* Division by denominator is often efficient to pre-calculate, especially when it is used multiple times. For exmaple `expr: 1/x + 1/x^2 + 1/x^3` can be efficientlu evaluated as `inv_x=1/x; inv_x2:inv_x*inv_x; expr: inv_x + inv_x2 + inv_x2*inv_x;`
* For evaluation of polynominals it is offten efficient to use Homer's scheme. For example `expr: 5*x^3 + 2*x^2 -3*x + 4` can be evaluated as `expr: 4 + x*( -3 + x*(2 + x*5));`
* try to find patterns related to known polynominal indetities: 
   * `(x+y)^2     =    x^2 - 2*x*y + y^2`
   * `(x-y)^3     =    x^3 - 3*x^2*y + 3*x*y^2 - y^3`
   * `x^2 - y^2   =   (x-y)*(x+y)`
   * `x^3 - y^3   =   (x-y)*(x^2 + x*y + y^2)`



#### Example:

For example following expression and its derivatives:
```Maxima
E       :   (3*(sj^2+si^2))/(2*si^2*sj^2)-(6*(sj^2+si^2)-4*r^2)/(sj^2+si^2)^2;
dE_si  :   ( -3*sj^6  +  3*si^4*sj^2  -9*si^2*sj^4 + 9*si^6  -16*r^2*si^4 )/(si^3*(sj^2+si^2)^3);
dE_sj  :   ( -3*si^6  +  3*si^2*sj^4  -9*si^4*sj^2 + 9*sj^6  -16*r^2*sj^4 )/(sj^3*(sj^2+si^2)^3);
dE_r   :   (8*r)/(sj^2+si^2)^2;
```

can be simplified and optimized by pre-calculating sub-expressions as follows::

```Maxima
/* pre-calculate sub-expressions */
r2           : r*r;
si2          : si*si; 
sj2          : sj*sj; 
si2sj2       : si2+sj2; 
inv_si2      : 1/si2; 
inv_sj2      : 1/sj2;
inv_si       : 1/si;
inv_sj       : 1/sj; 
inv_si2sj2   : 1/si2sj2;
inv_sisi2sj2 : inv_si*inv_si2sj2;
/* final formulas and the derivative */
E            : (3/2)*si2sj2*inv_si2*inv_sj2 - ( 6*si2sj2-4*r2 )*inv_si2sj2*inv_si2sj2;
dE_si       : ( -3*(sj2-si2)*(si2+sj2)*(sj2+3*si2)  -  16*r2*si2*si2  ) * inv_sisi2sj2*inv_sisi2sj2*inv_sisi2sj2; 
dE_sj       : ( -3*(si2-sj2)*(si2+sj2)*(si2+3*sj2)  -  16*r2*sj2*sj2  ) * inv_sisi2sj2*inv_sisi2sj2*inv_sisi2sj2; 
dE_r        : 8*r*inv_si2sj2*inv_si2sj2; 
```

## Task:

Following the instructions and the example above, simplify and optimize the following expression and its derivatives by finding and pre-calculating common sub-expressions

```Maxima
{Formulas}
```

#### Ouput Format:

* Make sure you generate pure valid Maxima code without any acompanying text of markdown. The output you generate will be directly executed by Maxima, so make sure that it is valid Maxima code. Use `/* ... */` for eventual comments and `:` separator for assignments e.g. `expr: 1/x + 1/x^2 + 1/x^3;`. 
* Final formulas must be in the format that `E:` denotes expression for Energy flollowed by expressions for derivative in form `dE_*` where `*` is the name of the dynamical variable (DOF), for example `dE_si` for derivative with respect to `si` variable, `dE_r` for derivative with respect to `r` variable.
* Each expression with single assignement `:` must be on single line. Do not break lines in the middle of the expression just because it is too long. 
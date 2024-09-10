# Suggest substitutions to optimize the expressions

Your task is to suggest 5 different substitutions that can be used to simplify the following expressions:

```Maxima
{Formulas}
```

The goal is to reduce computational complexity of the evaluation of the expressions. This means to pre-calculate common sub-expressions and reuse them for evaluation of the whole expressions. The evaluation costs are as follows

 * addition `+`, subtraction `-` and multiplication `*` costs 1
 * division `/` cost 3
 * exponentiation `^`, suare root `sqrt` or rising to power `pow` costs 10
 * functions like `sin`, `cos`, `exp`, `log`, `sqrt`, `atan` costs 20

Therefore we should introduce such substitutions that will make sure we evaluate costly operations as few times as possible. In case multiple expressions are provided the substitutions should be suitable to all of them.

## Examples

##### Example 1

Original expression
```Maxima
expr1 : 1/x + 1/x^2 + 1/x^3;
```
Subbsitutions
```Maxima
inv_x : 1/x;
inv_x2 : inv_x*inv_x;
expr1 : inv_x + inv_x2 + inv_x2*inv_x;
```
this reduce evaluation cost from 31 to 7

##### Example 3

Original expression
```Maxima
expr1 : (x^2-y^2)*(x^2+y^2) + 1/(x^2-y^2);
```
Subbsitutions
```Maxima
x2 : x*x; 
y2 : y*y; 
x2y2 : x2-y2; 
expr1 : (x2+y2)*x2y2 + 1/x2y2;
```

##### Example 4

Original expression
```Maxima
expr1 :          exp(-(x/w)^2)^2 -       2*exp(-(x/w)^2)
expr2 : -4*(x/w)*exp(-(x/w)^2)^2 + 4*(x/w)*exp(-(x/w)^2)
```
Subbsitutions
```Maxima
xw : x/w;
exw : exp(-(x/w)^2);
expr1 : exw^2 - 2*exw
expr2 : -4*xw*exw^2 + 4*xw*exw
```

##### Example 2

Original expression
```Maxima
expr1 : a/b + (a/b)^3 + 1/sqrt(a^2+b^2) + ( (a/b)^2 + (b/a)^2 )/sqrt(a^2+b^2)^3;
expr2 : b/a + (b/a)^4 + 1/sqrt(a^2-b^2) + ( (b/a)^2 + (a/b)^2 )/(sqrt(a^2+b^2)^2*sqrt(a^2-b^2));
```
Subbsitutions
```Maxima
fab : a/b;
fba : b/a;
a2 : a*a;
b2 : b*b;
isqrtab : 1/sqrt(a2+b2);
isqrtba : 1/sqrt(a2-b2);
expr1 : fab + fab*fab*fab     + isqrtab + ( fab*fab + fba*fba )*isqrtab*isqrtab*isqrtab;
expr2 : fba + fba*fba*fba*fba + isqrtba + ( fba*fba + fab*fab )*isqrtba*isqrtab*isqrtab;
```

## Task

Using the instructions and the example above, suggest 5 substitutions which allow to pre-calculate costly common sub-expression in following formulas:

```Maxima
{Formulas}
```

#### Output Format

- Ensure the output is valid Maxima code without any accompanying text or markdown. The output should be directly executable in Maxima.
- Use `:` for assignments (e.g., `expr : 5*x^2;`).
- NEVER include any comments, text or markdown formatting in the output !!!
- use concise names for sub-expression.
- The final formulas should have the energy denoted by `E:` followed by the derivatives, where each derivative is denoted as `dE_*:`, with `*` being the name of the dynamical variable (DOF), such as `dE_si:` for the derivative with respect to `si` and `dE_r:` for the derivative with respect to `r`.
- Each expression should be a single-line assignment. Do not break lines in the middle of the expression, even if it is long.

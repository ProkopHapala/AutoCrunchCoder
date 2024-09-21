import subprocess
import re
import numpy as np
from sympy import sympify, lambdify, diff, integrate
from typing import List, Dict, Any, Callable

from .Maxima import run_maxima

def symbolic_derivative( expr: str, var: str, bSimplify=False, bFactor=False, bExpand=False ) -> str:
    """
    Compute analytical derivative with Maxima.
    expr: expression to differentiate
    var: variable to differentiate with respect to
    """
    code = f"diff({expr}, {var})"
    if( bSimplify ): code = f"ratsimp({code})"
    if( bExpand ):   code = f"expand({code})"
    if( bFactor ):   code = f"factor({code})"
    code+=";\n"
    #process = subprocess.Popen(['maxima', '--very-quiet'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    #output, _ = process.communicate(command)
    #output.strip()
    return run_maxima(code)

def compute_numerical_derivative(expr: str, var: str, point: float, h: float = 1e-5) -> float:
    """Compute the numerical derivative of an expression using Maxima."""
    command = f"""
    expr: {expr};
    var: {var};
    point: {point};
    h: {h};
    float((subst({var}=point+h,expr) - subst({var}=point,expr)) / h);
    """
    result = run_maxima(command)
    return float(result.split('\n')[-1])

def compute_expression_steps(steps: List[Dict[str, str]]) -> Dict[str, Any]:
    """Compute an expression composed of a list of steps (evaluation of named sub-expressions)."""
    results = {}
    for step in steps:
        name = step['name']
        expr = step['expression']
        for prev_name, prev_value in results.items():
            expr = expr.replace(prev_name, str(prev_value))
        try:
            results[name] = float(sympify(expr).evalf())
        except:
            results[name] = str(sympify(expr))
    return results

def compute_integral(expr: str, var: str, lower: float, upper: float) -> float:
    """Compute the definite integral of an expression using Maxima."""
    command = f"""
    expr: {expr};
    var: {var};
    integrate(expr, var, {lower}, {upper});
    float(%);
    """
    result = run_maxima(command)
    return float(result.split('\n')[-1])

def check_numerical_vs_analytical_derivative(expr: str, var: str, point: float, h: float = 1e-5, tolerance: float = 1e-6) -> Dict[str, Any]:
    """Check numerical vs analytical derivative using Python and NumPy."""
    # Analytical derivative
    expr_sympy = sympify(expr)
    analytical_derivative = diff(expr_sympy, var)
    analytical_func = lambdify(var, analytical_derivative, 'numpy')
    analytical_result = float(analytical_func(point))

    # Numerical derivative
    expr_func = lambdify(var, expr_sympy, 'numpy')
    numerical_result = (expr_func(point + h) - expr_func(point)) / h

    # Compare results
    difference = abs(analytical_result - numerical_result)
    is_close = difference <= tolerance

    return {
        'analytical_derivative': str(analytical_derivative),
        'analytical_result': analytical_result,
        'numerical_result': numerical_result,
        'difference': difference,
        'is_close': is_close
    }

# Example usage of the tools
if __name__ == "__main__":
    print("Numerical derivative:", compute_numerical_derivative("x^2", "x", 2))

    steps = [
        {"name": "a", "expression": "2 * 3"},
        {"name": "b", "expression": "a + 4"},
        {"name": "c", "expression": "b ^ 2"}
    ]
    print("Expression steps:", compute_expression_steps(steps))

    print("Integral:", compute_integral("x^2", "x", 0, 1))

    print("Numerical vs Analytical derivative:", check_numerical_vs_analytical_derivative("x^3", "x", 2))

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.deepseek_agent import DeepSeekAgent

def test_math_tools():
    agent = DeepSeekAgent("deepseek-coder")

    # Test numerical derivative
    expr = "x^2"
    var = "x"
    point = 2
    result = agent.numerical_derivative(expr, var, point)
    print(f"Numerical derivative of {expr} at x = {point}: {result}")

    # Test expression steps
    steps = [
        {"name": "a", "expression": "2 * 3"},
        {"name": "b", "expression": "a + 4"},
        {"name": "c", "expression": "b ^ 2"}
    ]
    result = agent.evaluate_expression_steps(steps)
    print("\nExpression steps result:")
    print(result)

    # Test integral
    expr = "x^2"
    var = "x"
    lower = 0
    upper = 1
    result = agent.compute_integral(expr, var, lower, upper)
    print(f"\nIntegral of {expr} from {lower} to {upper}: {result}")

    # Test derivative comparison
    expr = "x^3"
    var = "x"
    point = 2
    result = agent.compare_derivatives(expr, var, point)
    print("\nDerivative comparison result:")
    print(result)

if __name__ == "__main__":
    test_math_tools()

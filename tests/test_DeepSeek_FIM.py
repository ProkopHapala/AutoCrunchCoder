import unittest
from deepseek_agent import DeepSeekAgent

class TestDeepSeekFIM(unittest.TestCase):
    def setUp(self):
        self.agent = DeepSeekAgent("deepseek-chat")

    def test_fim_completion(self):
        prefix = "def fibonacci(n):"
        suffix = "    return fib(n-1) + fib(n-2)"
        result = self.agent.fim_completion(prefix, suffix)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

        # Check if the result contains typical elements of a Fibonacci function
        self.assertIn("if", result.lower())
        self.assertIn("return", result.lower())

    def test_fim_completion_empty_suffix(self):
        prefix = "The capital of France is"
        result = self.agent.fim_completion(prefix)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        self.assertIn("Paris", result)

if __name__ == '__main__':
    unittest.main()

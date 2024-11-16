import unittest
import os
import shutil

import sys
sys.path.append("../")
from pyCruncher.dependency_graph_tree_sitter import DependencyGraphTreeSitter

class TestDependencyGraphTreeSitter(unittest.TestCase):
    def setUp(self):
        """Create test files with sample code"""
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Sample C++ code with classes, namespaces and function calls
        self.cpp_code = """
        namespace math {
            int add(int a, int b) {
                return a + b;
            }
            
            namespace advanced {
                int multiply(int a, int b) {
                    return a * math::add(a, b);
                }
                
                class Calculator {
                public:
                    static int compute(int x, int y) {
                        return math::add(x, math::advanced::multiply(x, y));
                    }
                    
                    int apply(int x, int y) {
                        return compute(x, y);
                    }
                };
            }
        }

        namespace utils {
            class Helper {
            public:
                static int process(int x) {
                    return x * 2;
                }
            };
        }

        int calculate(int x) {
            return utils::Helper::process(x);
        }

        int processNumbers(int a, int b) {
            return math::add(a, b);
        }

        int main() {
            int x = 5, y = 3;
            processNumbers(x, y);
            math::add(x, y);
            math::advanced::multiply(x, y);
            math::advanced::Calculator calc;
            calc.compute(x, y);
            calc.apply(x, y);
            return 0;
        }
        """
        
        # Write test files
        self.cpp_file = os.path.join(self.test_dir, 'test.cpp')
        with open(self.cpp_file, 'w') as f:
            f.write(self.cpp_code)

    def test_cpp_basic(self):
        """Test basic C++ function detection"""
        processor = DependencyGraphTreeSitter()
        processor.parse_file(self.cpp_file)
        
        print("\n=== Testing Basic C++ Function Detection ===")
        
        # Test namespace function detection
        print("\nTesting namespace functions:")
        print(f"Available functions: {list(processor.functions.keys())}")
        if 'math::add' in processor.functions:
            print("SUCCESS: Found math::add function")
        else:
            print("FAILURE: Could not find math::add function")
        
        if 'math::advanced::multiply' in processor.functions:
            print("SUCCESS: Found math::advanced::multiply function")
        else:
            print("FAILURE: Could not find math::advanced::multiply function")
        
        # Test class methods
        print("\nTesting class methods:")
        if 'math::advanced::Calculator::compute' in processor.functions:
            print("SUCCESS: Found Calculator::compute method")
        else:
            print("FAILURE: Could not find Calculator::compute method")
            
        if 'math::advanced::Calculator::apply' in processor.functions:
            print("SUCCESS: Found Calculator::apply method")
        else:
            print("FAILURE: Could not find Calculator::apply method")
        
        # Test class detection
        print("\nTesting class detection:")
        print(f"Available classes: {list(processor.classes.keys())}")
        if 'math::advanced::Calculator' in processor.classes:
            print("SUCCESS: Found Calculator class")
        else:
            print("FAILURE: Could not find Calculator class")
            
        if 'utils::Helper' in processor.classes:
            print("SUCCESS: Found Helper class")
        else:
            print("FAILURE: Could not find Helper class")
        
        # Now run the actual assertions
        self.assertTrue('math::add' in processor.functions, "math::add function not found")
        self.assertTrue('math::advanced::multiply' in processor.functions, "math::advanced::multiply function not found")
        self.assertTrue('math::advanced::Calculator::compute' in processor.functions, "Calculator::compute method not found")
        self.assertTrue('math::advanced::Calculator::apply' in processor.functions, "Calculator::apply method not found")
        self.assertTrue('math::advanced::Calculator' in processor.classes, "Calculator class not found")
        self.assertTrue('utils::Helper' in processor.classes, "Helper class not found")

    def test_cpp_namespaces(self):
        """Test C++ namespace handling"""
        processor = DependencyGraphTreeSitter()
        processor.parse_file(self.cpp_file)
        
        print("\n=== Testing C++ Namespace Handling ===")
        
        # Test namespace structure
        print("\nTesting namespace structure:")
        if 'math::add' in processor.functions:
            add_func = processor.functions['math::add']
            print(f"Found math::add with namespace: {add_func.namespace}")
            if add_func.namespace == 'math':
                print("SUCCESS: Correct namespace for math::add")
            else:
                print(f"FAILURE: Wrong namespace for math::add: {add_func.namespace}")
        else:
            print("FAILURE: Could not find math::add function")
        
        if 'math::advanced::multiply' in processor.functions:
            multiply_func = processor.functions['math::advanced::multiply']
            print(f"Found math::advanced::multiply with namespace: {multiply_func.namespace}")
            if multiply_func.namespace == 'math::advanced':
                print("SUCCESS: Correct namespace for math::advanced::multiply")
            else:
                print(f"FAILURE: Wrong namespace for math::advanced::multiply: {multiply_func.namespace}")
        else:
            print("FAILURE: Could not find math::advanced::multiply function")
        
        # Now run the actual assertions
        add_func = processor.functions['math::add']
        self.assertEqual(add_func.namespace, 'math', "Wrong namespace for math::add")
        
        multiply_func = processor.functions['math::advanced::multiply']
        self.assertEqual(multiply_func.namespace, 'math::advanced', "Wrong namespace for math::advanced::multiply")

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

if __name__ == '__main__':
    unittest.main()

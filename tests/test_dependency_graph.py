import os
import sys
import unittest
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyCruncher.ctags_dependency import DependencyProcessor

class TestDependencyGraph(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create test files
        self.create_test_files()
        
        # Run ctags on test files
        self.tags_file = os.path.join(self.test_dir, "tags.json")
        from pyCruncher.ctags import run_ctags
        run_ctags(self.tags_file, self.test_dir)
        
    def create_test_files(self):
        # Test Python file
        python_content = """
class Calculator:
    def __init__(self):
        self.value = 0
        
    def add(self, x):
        self.value += x
        return self.value
        
    def multiply(self, x):
        self.value = self.add(0)  # Reset value
        for _ in range(x):
            self.add(self.value)
        return self.value

def process_numbers(numbers):
    calc = Calculator()
    result = 0
    for num in numbers:
        if num % 2 == 0:
            result = calc.multiply(num)
        else:
            result = calc.add(num)
    return result

def main():
    numbers = [1, 2, 3, 4]
    result = process_numbers(numbers)
    print(f"Result: {result}")

if __name__ == '__main__':
    main()
"""
        with open(os.path.join(self.test_dir, "calculator.py"), "w") as f:
            f.write(python_content)

        # Test C++ file
        cpp_content = """
class MathUtils {
public:
    MathUtils() : value(0) {}
    
    double add(double x) {
        value += x;
        return value;
    }
    
    double multiply(double x) {
        value = add(0);  // Reset value
        for(int i = 0; i < x; i++) {
            add(value);
        }
        return value;
    }
    
private:
    double value;
};

double processNumbers(const std::vector<double>& numbers) {
    MathUtils calc;
    double result = 0;
    for(const auto& num : numbers) {
        if(static_cast<int>(num) % 2 == 0) {
            result = calc.multiply(num);
        } else {
            result = calc.add(num);
        }
    }
    return result;
}

int main() {
    std::vector<double> numbers = {1.0, 2.0, 3.0, 4.0};
    double result = processNumbers(numbers);
    std::cout << "Result: " << result << std::endl;
    return 0;
}
"""
        with open(os.path.join(self.test_dir, "calculator.cpp"), "w") as f:
            f.write(cpp_content)

        # Test C++ file with namespaces and edge cases
        cpp_content = """
namespace math {
    double add(double x, double y) {
        return x + y;
    }
    
    namespace advanced {
        double multiply(double x, double y) {
            return x * y;
        }
        
        class Calculator {
        public:
            Calculator() : value(0) {}
            
            double compute(double x, double y) {
                // Test calling function from parent namespace
                value = math::add(x, y);
                // Test calling function from same namespace
                value = multiply(value, 2.0);
                return value;
            }
            
            // Test function pointer and complex expressions
            double apply(double (*func)(double, double), double x, double y) {
                value = func(x, y);
                return value;
            }
            
        private:
            double value;
        };
    }
}

namespace utils {
    class Helper {
    public:
        static double process(double x, double y) {
            math::advanced::Calculator calc;
            // Test nested namespace function call
            double result = math::advanced::multiply(x, y);
            // Test method call on object
            result = calc.compute(result, 2.0);
            return result;
        }
    };
}

// Test global namespace function
double calculate(double x, double y) {
    utils::Helper helper;
    // Test static method call
    return utils::Helper::process(x, y);
}

int main() {
    math::advanced::Calculator calc;
    double result = 0.0;
    
    // Test direct function calls
    result = math::add(1.0, 2.0);
    result = math::advanced::multiply(result, 3.0);
    
    // Test method calls
    result = calc.compute(result, 4.0);
    
    // Test function pointer
    result = calc.apply(math::add, result, 5.0);
    
    // Test through helper
    result = calculate(result, 6.0);
    
    return 0;
}
"""
        with open(os.path.join(self.test_dir, "advanced_calculator.cpp"), "w") as f:
            f.write(cpp_content)

    def test_python_dependencies(self):
        processor = DependencyProcessor()
        processor.process_ctags_with_deps(self.tags_file, self.test_dir)
        processor.load_file_contents(self.test_dir)
        processor.analyze_dependencies()
        
        # Test function relationships
        calc_funcs = {f for f in processor.functions.keys() if 'Calculator' in f}
        self.assertTrue('Calculator.add' in calc_funcs)
        self.assertTrue('Calculator.multiply' in calc_funcs)
        
        # Test method dependencies
        multiply_func = processor.functions['Calculator.multiply']
        self.assertTrue('Calculator.add' in multiply_func.calls)
        
        # Test function dependencies
        process_func = processor.functions['process_numbers']
        self.assertTrue('Calculator.multiply' in process_func.calls)
        self.assertTrue('Calculator.add' in process_func.calls)
        
        main_func = processor.functions['main']
        self.assertTrue('process_numbers' in main_func.calls)

    def test_cpp_dependencies(self):
        processor = DependencyProcessor()
        processor.process_ctags_with_deps(self.tags_file, self.test_dir)
        processor.load_file_contents(self.test_dir)
        processor.analyze_dependencies()
        
        # Test class methods
        math_funcs = set(processor.functions.keys())
        self.assertTrue('MathUtils::add' in math_funcs)
        self.assertTrue('MathUtils::multiply' in math_funcs)
        print("SUCCESS: Basic C++ function detection")
        
        # Test method calls
        multiply_func = processor.functions['MathUtils::multiply']
        self.assertTrue('MathUtils::add' in multiply_func.calls)
        print("SUCCESS: C++ method call detection")
        
        process_func = processor.functions['processNumbers']
        self.assertTrue('MathUtils::add' in process_func.calls)
        print("SUCCESS: C++ function call detection")
        
        main_func = processor.functions['main']
        self.assertTrue('processNumbers' in main_func.calls)
        print("SUCCESS: C++ main function dependencies")

    def test_namespace_resolution(self):
        processor = DependencyProcessor()
        processor.process_ctags_with_deps(self.tags_file, self.test_dir)
        processor.load_file_contents(self.test_dir)
        
        # Test namespace structure
        self.assertTrue('math::add' in processor.functions)
        self.assertTrue('math::advanced::multiply' in processor.functions)
        self.assertTrue('math::advanced::Calculator::compute' in processor.functions)
        print("SUCCESS: C++ namespace resolution")
        
        # Test class in namespace
        self.assertTrue('math::advanced::Calculator' in processor.classes)
        self.assertTrue('utils::Helper' in processor.classes)
        print("SUCCESS: C++ class in namespace detection")

    def test_function_calls(self):
        processor = DependencyProcessor()
        processor.process_ctags_with_deps(self.tags_file, self.test_dir)
        processor.load_file_contents(self.test_dir)
        processor.analyze_dependencies(check_call_syntax=True)
        
        # Test nested namespace function calls
        compute_func = processor.functions['math::advanced::Calculator::compute']
        self.assertTrue('math::add' in compute_func.calls)
        self.assertTrue('math::advanced::multiply' in compute_func.calls)
        print("SUCCESS: Nested namespace function calls")
        
        # Test method calls
        main_func = processor.functions['main']
        self.assertTrue('math::add' in main_func.calls)
        self.assertTrue('math::advanced::multiply' in main_func.calls)
        self.assertTrue('math::advanced::Calculator::compute' in main_func.calls)
        self.assertTrue('math::advanced::Calculator::apply' in main_func.calls)
        print("SUCCESS: Complex method calls")
        
        # Test static method calls
        calc_func = processor.functions['calculate']
        self.assertTrue('utils::Helper::process' in calc_func.calls)
        print("SUCCESS: Static method calls")

    def test_call_syntax_detection(self):
        processor = DependencyProcessor()
        processor.process_ctags_with_deps(self.tags_file, self.test_dir)
        processor.load_file_contents(self.test_dir)
        
        # Test with call syntax checking disabled
        processor.analyze_dependencies(check_call_syntax=False)
        main_func = processor.functions['main']
        initial_calls = set(main_func.calls)
        print("SUCCESS: Basic identifier detection")
        
        # Test with call syntax checking enabled
        processor.analyze_dependencies(check_call_syntax=True)
        filtered_calls = set(main_func.calls)
        
        # Should have fewer calls with syntax checking
        self.assertTrue(len(filtered_calls) <= len(initial_calls))
        print("SUCCESS: Call syntax filtering")
        
        # But should still find actual function calls
        self.assertTrue('math::add' in filtered_calls)
        self.assertTrue('math::advanced::multiply' in filtered_calls)
        print("SUCCESS: Function call detection with parentheses")

    def tearDown(self):
        # Clean up test files
        # import shutil
        # shutil.rmtree(self.test_dir)
        pass

if __name__ == '__main__':
    unittest.main()

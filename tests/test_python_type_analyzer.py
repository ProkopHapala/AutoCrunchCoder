import os
import pytest
from tree_sitter import Language, Parser
from pathlib import Path
from pyCruncher.python_type_analyzer import TypeCollector, TypeRegistry, ClassInfo, MethodInfo, FunctionCall

# Configuration
BUILD_PATH = 'tests/build/my-languages.so'
VENDOR_PYTHON_PATH = '/home/prokophapala/SW/vendor/tree-sitter-python'

def setup_parser():
    """Set up tree-sitter parser for Python"""
    # Build the Python language library if it doesn't exist
    if not os.path.exists(VENDOR_PYTHON_PATH):
        raise FileNotFoundError(f"Missing Tree-sitter grammar at {VENDOR_PYTHON_PATH}. "
                              "Ensure you have cloned it.")
    
    Language.build_library(
        BUILD_PATH,
        [VENDOR_PYTHON_PATH]
    )

    PY_LANGUAGE = Language(BUILD_PATH, 'python')
    parser = Parser()
    parser.set_language(PY_LANGUAGE)
    return parser

class TestTypeCollector:
    @pytest.fixture
    def collector(self):
        parser = setup_parser()
        return TypeCollector(parser)

    def test_basic_function_definition(self, collector):
        code = '''
def hello():
    print("Hello")
    return None
'''
        collector.process_code(code)
        functions = collector.registry.get_scope("").functions
        assert "hello" in functions
        assert functions["hello"].name == "hello"

    def test_basic_class_definition(self, collector):
        code = '''
class MyClass:
    def __init__(self):
        self.x = 0
        
    def method1(self):
        return self.x
'''
        collector.process_code(code)
        class_info = collector.registry.get_type("MyClass")
        assert class_info is not None
        assert class_info.name == "MyClass"
        assert len(class_info.methods) == 2
        method_names = {m.name for m in class_info.methods}
        assert method_names == {"__init__", "method1"}

    def test_function_call_tracking(self, collector):
        code = '''
def helper():
    return 42

def main():
    x = helper()
    print(x)
'''
        collector.process_code(code)
        main_func = collector.registry.get_scope("").functions["main"]
        calls = main_func.calls
        assert len(calls) == 2
        call_names = {call.name for call in calls}
        assert call_names == {"helper", "print"}

    def test_method_call_tracking(self, collector):
        code = '''
class Calculator:
    def add(self, x, y):
        return x + y
        
    def calculate(self):
        result = self.add(1, 2)
        print(result)
'''
        collector.process_code(code)
        class_info = collector.registry.get_type("Calculator")
        calc_method = next(m for m in class_info.methods if m.name == "calculate")
        calls = calc_method.calls
        assert len(calls) == 2
        call_names = {call.name for call in calls}
        assert call_names == {"add", "print"}

    def test_cross_file_dependencies(self, tmp_path):
        # Create helper.py
        helper_path = tmp_path / "helper.py"
        helper_path.write_text('''
class Helper:
    def help_method(self):
        return "helping"
''')

        # Create main.py
        main_path = tmp_path / "main.py"
        main_path.write_text('''
from helper import Helper

def main():
    h = Helper()
    result = h.help_method()
    print(result)
''')

        parser = setup_parser()
        collector = TypeCollector(parser)
        
        # Process both files
        collector.process_file(str(helper_path))
        collector.process_file(str(main_path))

        # Check if Helper class was found
        helper_class = collector.registry.get_type("Helper")
        assert helper_class is not None
        assert helper_class.name == "Helper"

        # Check main function calls
        main_func = collector.registry.get_scope("").functions["main"]
        calls = main_func.calls
        assert len(calls) == 3  # Helper(), help_method(), print()
        call_names = {call.name for call in calls}
        assert call_names == {"Helper", "help_method", "print"}

import pytest
from pathlib import Path
from tree_sitter import Parser
from pyCruncher.python_type_analyzer import TypeCollector

def setup_parser():
    """Set up tree-sitter parser for Python"""
    from tree_sitter import Language
    import os

    BUILD_PATH = 'tests/build/my-languages.so'
    VENDOR_PYTHON_PATH = '/home/prokophapala/SW/vendor/tree-sitter-python'

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

@pytest.fixture
def collector():
    return TypeCollector(setup_parser())

def test_basic_import(collector, tmp_path):
    # Create math_utils.py
    math_utils = tmp_path / "math_utils.py"
    math_utils.write_text('''
def add(x, y):
    return x + y

def multiply(x, y):
    return x * y
''')

    # Create main.py
    main = tmp_path / "main.py"
    main.write_text('''
import math_utils

def calculate():
    result = math_utils.add(2, 3)
    return result
''')

    # Process both files
    collector.process_file(str(math_utils))
    collector.process_file(str(main))

    # Check if imports are tracked
    imports = collector.registry.get_imports("main.py")
    assert imports is not None
    assert "math_utils" in imports

    # Check if function call is resolved
    func_info = collector.registry.get_function("calculate")
    assert func_info is not None
    assert len(func_info.calls) == 1
    assert func_info.calls[0].name == "add"
    assert func_info.calls[0].object == "math_utils"

def test_from_import(collector, tmp_path):
    # Create helpers.py
    helpers = tmp_path / "helpers.py"
    helpers.write_text('''
def helper1():
    return "help1"

def helper2():
    return "help2"
''')

    # Create main.py
    main = tmp_path / "main.py"
    main.write_text('''
from helpers import helper1, helper2

def use_helpers():
    a = helper1()
    b = helper2()
    return a + b
''')

    # Process both files
    collector.process_file(str(helpers))
    collector.process_file(str(main))

    # Check if imports are tracked
    imports = collector.registry.get_imports("main.py")
    assert imports is not None
    assert "helper1" in imports
    assert "helper2" in imports

    # Check if function calls are resolved
    func_info = collector.registry.get_function("use_helpers")
    assert func_info is not None
    assert len(func_info.calls) == 2
    assert any(call.name == "helper1" for call in func_info.calls)
    assert any(call.name == "helper2" for call in func_info.calls)

def test_aliased_import(collector, tmp_path):
    # Create data_utils.py
    data_utils = tmp_path / "data_utils.py"
    data_utils.write_text('''
def process_data(data):
    return data.upper()
''')

    # Create main.py
    main = tmp_path / "main.py"
    main.write_text('''
import data_utils as du

def handle_data(text):
    return du.process_data(text)
''')

    # Process both files
    collector.process_file(str(data_utils))
    collector.process_file(str(main))

    # Check if imports are tracked with alias
    imports = collector.registry.get_imports("main.py")
    assert imports is not None
    assert "data_utils" in imports
    assert imports["data_utils"] == "du"  # Check alias

    # Check if function call through alias is resolved
    func_info = collector.registry.get_function("handle_data")
    assert func_info is not None
    assert len(func_info.calls) == 1
    assert func_info.calls[0].name == "process_data"
    assert func_info.calls[0].object == "du"

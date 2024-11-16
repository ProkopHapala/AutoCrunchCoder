# C++ Dependency Graph Analyzer

A comprehensive tool for analyzing function and class dependencies across C++ codebases using tree-sitter parsing.

## Overview

The C++ Dependency Graph Analyzer is a Python-based tool that performs static code analysis on C++ codebases. It uses tree-sitter for robust parsing and can:

1. Track file-level dependencies through `#include` statements
2. Extract function and class definitions with full context
3. Maintain namespace and class hierarchies
4. Support static methods and nested namespaces

## Installation

### Prerequisites

- Python 3.10 or higher
- tree-sitter library with C++ grammar

### Setup

1. Install required Python packages:
```bash
pip install tree-sitter
```

2. Clone and build the C++ grammar:
```bash
git clone https://github.com/tree-sitter/tree-sitter-cpp
cd tree-sitter-cpp
make
```

## Usage

### Basic Usage

```python
from pyCruncher.dependency_graph_tree_sitter import DependencyGraphTreeSitter

# Initialize the analyzer
analyzer = DependencyGraphTreeSitter()

# Parse a file and its dependencies
analyzer.parse_file_with_deps("path/to/your/file.cpp", "path/to/project/root")

# Access parsed information
for func_name, func_info in analyzer.functions.items():
    print(f"Function: {func_name}")
    print(f"  File: {func_info.file_path}")
    print(f"  Namespace: {func_info.namespace}")
    print(f"  Class: {func_info.class_name}")

for class_name, class_info in analyzer.classes.items():
    print(f"Class: {class_name}")
    print(f"  Methods: {len(class_info.methods)}")
```

### Advanced Usage

#### Finding File Dependencies

```python
# Get all dependencies of a file
deps = analyzer.find_dependencies("path/to/file.cpp", "project/root")
print(f"Found {len(deps)} dependencies")
```

#### Parsing Multiple Files

```python
# Parse an entire directory
analyzer.parse_directory("/path/to/src", file_pattern=".cpp")
```

## Architecture

### Core Components

1. **DependencyGraphTreeSitter**
   - Main class that orchestrates parsing and analysis
   - Maintains dictionaries of functions, classes, and files

2. **Data Classes**
   - `FunctionInfo`: Stores function metadata
   - `ClassInfo`: Stores class metadata
   - `FileInfo`: Stores file metadata

### Key Features

#### File Dependency Resolution

The analyzer uses a multi-step approach to find include files:
1. Checks relative to source file
2. Checks relative to project root
3. Checks common include directories (include, src, common, libs)

#### Code Analysis

Extracts detailed information about:
- Function definitions (including static methods)
- Class definitions
- Namespace hierarchies
- File dependencies

## Implementation Details

### Function Processing

The `_process_function` method:
1. Identifies function declarators
2. Extracts function names
3. Detects static methods
4. Builds qualified names with namespace and class context
5. Creates `FunctionInfo` objects

### Class Processing

The `_process_class` method:
1. Identifies class specifiers
2. Extracts class names
3. Builds qualified names with namespace context
4. Creates `ClassInfo` objects

### Dependency Resolution

The `find_dependencies` method:
1. Recursively processes `#include` statements
2. Resolves include paths
3. Maintains a visited set to prevent cycles
4. Returns a complete set of dependencies

## Future Improvements

### 1. Function Call Analysis

**Priority: High**
- Implement `analyze_dependencies()` method
- Track function calls within function bodies
- Build call graphs
- Consider:
  * Function overloading
  * Template instantiation
  * Virtual function calls

### 2. C++ Feature Support

**Priority: Medium**
- Add support for:
  * Templates
  * Operator overloading
  * Friend functions
  * Using declarations
  * Aliases

### 3. Performance Optimization

**Priority: Medium**
- Implement parallel processing for large codebases
- Add caching for parsed files
- Consider incremental parsing
- Optimize memory usage for large projects

### 4. Visualization

**Priority: Low**
- Add graph visualization using libraries like:
  * Graphviz
  * D3.js
  * NetworkX
- Consider:
  * Interactive visualization
  * Filtering options
  * Different view modes (call graph, include graph)

### 5. Multi-Language Support

**Priority: Low**
- Extend to other languages:
  * Python
  * Java
  * JavaScript
- Abstract language-specific parsing

## Known Limitations

1. **Parsing**
   - Limited support for complex C++ features
   - No preprocessing support
   - Template instantiation not tracked

2. **Dependencies**
   - System includes not processed
   - Conditional includes not evaluated
   - Macro-based includes not supported

3. **Analysis**
   - No function call tracking yet
   - Limited support for templates
   - No cross-translation unit analysis

## Contributing

### Adding New Features

1. Fork the repository
2. Create a feature branch
3. Add tests in `tests/`
4. Implement the feature
5. Run the test suite
6. Submit a pull request

### Testing

Run the test suite:
```bash
PYTHONPATH=/path/to/project python3 -m pytest tests/
```

## License

[Insert License Information]

## Contact

[Insert Contact Information]

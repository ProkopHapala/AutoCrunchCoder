# Python Type Analyzer: Design Principles

## Overview
The Python Type Analyzer is a static code analysis tool that builds a comprehensive dependency graph of Python codebases without executing the code. It focuses on tracking class hierarchies, method calls, and type relationships across multiple files.

## Core Principles

### 1. Two-Pass Analysis
The analyzer uses a two-pass approach:
- First Pass: Collects basic structure (classes, methods, imports)
- Second Pass: Resolves relationships (inheritance, method calls)

This approach ensures that all type information is available when resolving dependencies.

### 2. Import Resolution
- Maintains a per-file import registry
- Tracks both direct imports (`import x`) and from-imports (`from x import y`)
- Resolves aliases and qualified names
- Maps imported symbols to their original definitions

### 3. Type Information Collection
- Builds a hierarchical representation of the codebase
- Tracks class definitions and their locations
- Maintains inheritance relationships
- Records method definitions and calls

### 4. Scope Management
- Each entity (class, method) maintains its own scope
- Scopes are hierarchical (global -> class -> method)
- Import resolution considers the appropriate scope

### 5. Tree-sitter Integration
- Uses tree-sitter for robust AST parsing
- Custom queries extract relevant nodes
- Avoids syntax errors through AST-based analysis

## Key Features

1. **Class Hierarchy Tracking**
   - Records base classes for each class
   - Handles multi-level inheritance
   - Resolves imported base classes

2. **Method Call Analysis**
   - Tracks method calls within classes
   - Records caller-callee relationships
   - Maintains call locations for debugging

3. **Import Management**
   - Per-file import registry
   - Resolution of aliased imports
   - Support for relative imports

4. **Location Tracking**
   - Records precise file locations
   - Maintains source ranges for all entities
   - Enables accurate debugging and navigation

## Design Philosophy
- Static analysis over runtime execution
- Accuracy over performance
- Comprehensive over minimal
- Maintainable over complex

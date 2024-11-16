import os
from dataclasses import dataclass, field
from typing import List, Dict, Set
from .tree_sitter_utils import get_parser, get_node_text, get_qualified_name, visit_tree

@dataclass
class FunctionInfo:
    """Information about a function/method"""
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    file_path: str
    class_name: str = None
    namespace: str = None
    is_method: bool = False
    is_static: bool = False
    calls: Set[str] = field(default_factory=set)
    body: str = None

class ClassInfo:
    """Information about a class"""
    def __init__(self, name: str, qualified_name: str, file_path: str, start_line: int, end_line: int, body: str, namespace: str = None):
        self.name = name
        self.qualified_name = qualified_name
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.body = body
        self.namespace = namespace
        self.methods = []
        self.fields = []

@dataclass
class FileInfo:
    """Information about a source file"""
    path: str
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    content: bytes = None

class DependencyGraphTreeSitter:
    def __init__(self):
        self.functions: Dict[str, FunctionInfo] = {}
        self.classes: Dict[str, ClassInfo] = {}
        self.files: Dict[str, FileInfo] = {}
        self.cpp_parser = None
        self.python_parser = None
        
    def initialize_parser(self, language):
        """Initialize parser for the specified language"""
        if language.lower() == "cpp":
            if not self.cpp_parser:
                self.cpp_parser = get_parser("cpp")
            return self.cpp_parser
        elif language.lower() == "python":
            if not self.python_parser:
                self.python_parser = get_parser("python")
            return self.python_parser
        else:
            raise ValueError(f"Unsupported language: {language}")

    def parse_file(self, file_path: str):
        """Parse a single source file"""
        # Determine language from file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.cpp', '.hpp', '.h', '.cc']:
            parser = self.initialize_parser("cpp")
        elif ext in ['.py']:
            parser = self.initialize_parser("python")
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Parse the file
        tree = parser.parse(content)
        
        # Create file info
        file_info = FileInfo(path=file_path, content=content)
        self.files[file_path] = file_info
        
        # Process the syntax tree
        self._process_tree(tree.root_node, content, file_path)
        
        return tree

    def parse_directory(self, dir_path: str, file_pattern: str = None):
        """Parse all matching files in a directory"""
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file_pattern and not file.endswith(file_pattern):
                    continue
                file_path = os.path.join(root, file)
                try:
                    self.parse_file(file_path)
                except Exception as e:
                    print(f"Error parsing {file_path}: {str(e)}")

    def _process_tree(self, node, content: bytes, file_path: str):
        """Process the syntax tree to extract functions, classes, and dependencies"""
        def process_node(node):
            if node.type == 'function_definition':
                self._process_function(node, content, file_path)
            elif node.type == 'class_specifier':  # C++ class node type
                self._process_class(node, content, file_path)
            
        visit_tree(node, process_node)

    def _process_function(self, node, content: bytes, file_path: str):
        """Extract information about a function definition"""
        # Get the function declarator
        declarator = next((child for child in node.children if child.type == 'function_declarator'), None)
        if not declarator:
            return
        
        # Get the function name
        name_node = None
        for child in declarator.children:
            if child.type in ['identifier', 'field_identifier']:  
                name_node = child
                break
            elif child.type == 'qualified_identifier':
                # Handle qualified names (e.g., namespace::function)
                for subchild in child.children:
                    if subchild.type in ['identifier', 'field_identifier']:  
                        name_node = subchild
                        break
        
        if name_node:
            name = get_node_text(name_node, content)
            
            # Check if the function is static
            is_static = False
            for child in node.children:
                if child.type == 'storage_class_specifier':
                    specifier_text = get_node_text(child, content)
                    if specifier_text == 'static':
                        is_static = True
                        break
            
            # Extract namespace and class info
            namespace = None
            class_name = None
            
            # Walk up the tree to find namespace and class
            current = node.parent
            namespace_parts = []
            while current:
                if current.type == 'namespace_definition':
                    for child in current.children:
                        if child.type == 'namespace_identifier':
                            ns_name = get_node_text(child, content)
                            namespace_parts.insert(0, ns_name)
                            break
                elif current.type == 'class_specifier':
                    for child in current.children:
                        if child.type == 'type_identifier':
                            class_name = get_node_text(child, content)
                            break
                current = current.parent
            
            if namespace_parts:
                namespace = '::'.join(namespace_parts)
            
            # Build qualified name
            qualified_parts = []
            if namespace:
                qualified_parts.append(namespace)
            if class_name:
                qualified_parts.append(class_name)
            qualified_parts.append(name)
            qualified_name = '::'.join(qualified_parts)
            
            func_info = FunctionInfo(
                name=name,
                qualified_name=qualified_name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                file_path=file_path,
                body=get_node_text(node, content),
                namespace=namespace,
                class_name=class_name,
                is_method=bool(class_name),
                is_static=is_static
            )
            
            self.functions[qualified_name] = func_info
            self.files[file_path].functions.append(qualified_name)

    def _process_class(self, node, content: bytes, file_path: str):
        """Extract information about a class definition"""
        name_node = next((child for child in node.children if child.type == 'type_identifier'), None)
        if name_node:
            name = get_node_text(name_node, content)
            
            # Extract namespace info
            namespace = None
            
            # Walk up the tree to find namespace
            current = node.parent
            namespace_parts = []
            while current:
                if current.type == 'namespace_definition':
                    for child in current.children:
                        if child.type == 'namespace_identifier':
                            ns_name = get_node_text(child, content)
                            namespace_parts.insert(0, ns_name)
                            break
                current = current.parent
            
            if namespace_parts:
                namespace = '::'.join(namespace_parts)
            
            # Build qualified name
            qualified_parts = []
            if namespace:
                qualified_parts.append(namespace)
            qualified_parts.append(name)
            qualified_name = '::'.join(qualified_parts)
            
            class_info = ClassInfo(
                name=name,
                qualified_name=qualified_name,
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                body=get_node_text(node, content),
                namespace=namespace
            )
            
            self.classes[qualified_name] = class_info
            self.files[file_path].classes.append(qualified_name)

    def _process_function_calls(self, node, content: bytes, current_function: FunctionInfo):
        """Process function calls within a function body"""
        def process_node(node):
            # Check for function calls
            if node.type == 'call_expression':
                # Get the function name being called
                function_name = None
                if node.children:
                    # First child is typically the function identifier
                    func_node = node.children[0]
                    
                    # Handle different types of function calls
                    if func_node.type == 'identifier':
                        # Simple function call
                        function_name = get_node_text(func_node, content)
                    elif func_node.type == 'field_expression':
                        # Method call (obj.method())
                        for child in func_node.children:
                            if child.type == 'field_identifier':
                                function_name = get_node_text(child, content)
                                break
                    elif func_node.type == 'qualified_identifier':
                        # Namespace qualified call (ns::func())
                        function_name = get_node_text(func_node, content)
                    
                    if function_name:
                        # Try to find the fully qualified name
                        qualified_name = None
                        
                        # Check if it's a class method
                        if current_function.class_name:
                            # First check in the same class
                            class_qualified = f"{current_function.class_name}::{function_name}"
                            if class_qualified in self.functions:
                                qualified_name = class_qualified
                        
                        # Check in the same namespace
                        if not qualified_name and current_function.namespace:
                            ns_qualified = f"{current_function.namespace}::{function_name}"
                            if ns_qualified in self.functions:
                                qualified_name = ns_qualified
                        
                        # Use global scope if not found
                        if not qualified_name:
                            # Look for exact match in functions
                            for func_qualified_name in self.functions:
                                if func_qualified_name.endswith(f"::{function_name}"):
                                    qualified_name = func_qualified_name
                                    break
                            
                            # If still not found, store the unqualified name
                            if not qualified_name:
                                qualified_name = function_name
                        
                        current_function.calls.add(qualified_name)
        
        visit_tree(node, process_node)

    def analyze_dependencies(self):
        """Analyze function bodies to find dependencies"""
        for func_name, func_info in self.functions.items():
            if func_info.body:
                # Parse the function body
                tree = self.cpp_parser.parse(func_info.body.encode())
                self._process_function_calls(tree.root_node, func_info.body.encode(), func_info)

    def find_include_file(self, include_path: str, source_file: str, project_root: str) -> str:
        """Find the full path of an included file"""
        # If it's a system include (e.g., <vector>), skip it
        if include_path.startswith('<'):
            return None
            
        # Remove quotes if present
        include_path = include_path.strip('"')
        
        # Try relative to the source file first
        source_dir = os.path.dirname(source_file)
        full_path = os.path.normpath(os.path.join(source_dir, include_path))
        if os.path.exists(full_path):
            return full_path
            
        # Try relative to project root
        full_path = os.path.normpath(os.path.join(project_root, include_path))
        if os.path.exists(full_path):
            return full_path
            
        # Try common include directories relative to project root
        common_include_dirs = ['include', 'src', 'common', 'libs']
        for include_dir in common_include_dirs:
            full_path = os.path.normpath(os.path.join(project_root, include_dir, include_path))
            if os.path.exists(full_path):
                return full_path
                
        return None

    def get_includes_from_file(self, file_path: str) -> list:
        """Extract #include statements from a file"""
        includes = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#include'):
                        # Extract the include path
                        include_path = line.split('#include', 1)[1].strip()
                        includes.append(include_path)
        except Exception as e:
            print(f"Error reading includes from {file_path}: {e}")
        return includes

    def find_dependencies(self, file_path: str, project_root: str, visited=None) -> set:
        """Recursively find all dependencies of a file"""
        if visited is None:
            visited = set()
            
        if file_path in visited:
            return visited
            
        visited.add(file_path)
        includes = self.get_includes_from_file(file_path)
        
        for include in includes:
            dep_path = self.find_include_file(include, file_path, project_root)
            if dep_path and dep_path not in visited:
                self.find_dependencies(dep_path, project_root, visited)
                
        return visited

    def parse_file_with_deps(self, file_path: str, project_root: str):
        """Parse a file and all its dependencies"""
        # First find all dependencies
        all_files = self.find_dependencies(file_path, project_root)
        
        # Then parse each file
        for dep_file in all_files:
            self.parse_file(dep_file)

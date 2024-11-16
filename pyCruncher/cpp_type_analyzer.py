import os
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
from tree_sitter import Parser, Node

# Debug logging setup
DEBUG_LEVEL = 0  # 0=INFO, 1=DEBUG, 2=TRACE
def setup_logging(level: int):
    if level == 0:
        logging.basicConfig(level=logging.INFO)
    elif level == 1:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.DEBUG)  # Python doesn't have TRACE, we'll use custom logging

def debug(msg: str, level: int = 1):
    """Debug print with level"""
    if level <= DEBUG_LEVEL:
        if level == 1:
            logging.debug(msg)
        else:
            logging.debug(f"TRACE: {msg}")

# Set initial logging
setup_logging(DEBUG_LEVEL)

class ScopeType(Enum):
    GLOBAL = auto()
    NAMESPACE = auto()
    CLASS = auto()
    FUNCTION = auto()
    BLOCK = auto()

class AccessSpecifier(Enum):
    PUBLIC = auto()
    PRIVATE = auto()
    PROTECTED = auto()

class TypeType(Enum):
    CLASS = auto()

@dataclass
class FileInfo:
    """Information about a source file"""
    path: str
    includes: List[str] = field(default_factory=list)
    scope: Optional['Scope'] = None

    def add_include(self, include_path: str):
        """Add an include path"""
        if include_path not in self.includes:
            self.includes.append(include_path)

@dataclass
class Location:
    """Source code location information"""
    file_path: str
    start_point: tuple[int, int]  # (line, column)
    end_point: tuple[int, int]    # (line, column)

    @property
    def start(self) -> tuple[int, int]:
        return self.start_point

    @property
    def end(self) -> tuple[int, int]:
        return self.end_point

    @property
    def start_line(self) -> int:
        return self.start_point[0]

    @property
    def end_line(self) -> int:
        return self.end_point[0]

    @property
    def start_column(self) -> int:
        return self.start_point[1]

    @property
    def end_column(self) -> int:
        return self.end_point[1]

@dataclass
class ParameterInfo:
    """Represents a function parameter"""
    name: str
    type_name: str
    default_value: Optional[str] = None
    location: Optional[Location] = None

@dataclass
class FunctionCall:
    """Represents a function call in the code"""
    name: str
    object_name: Optional[str] = None
    location: Optional[Location] = None
    resolved_file: Optional[str] = None
    caller: Optional['MethodInfo'] = None
    is_constructor: bool = False
    is_static: bool = False
    template_args: List[str] = field(default_factory=list)
    resolved_method: Optional['MethodInfo'] = None
    arguments: List[str] = field(default_factory=list)
    resolved_parameters: List[ParameterInfo] = field(default_factory=list)
    scope: Optional['Scope'] = None

@dataclass
class FunctionInfo:
    """Information about a function"""
    name: str
    return_type: str
    scope: Optional[str] = None

@dataclass
class Scope:
    """Represents a scope in the code"""
    type: ScopeType
    name: str
    parent: Optional['Scope'] = None
    children: List['Scope'] = field(default_factory=list)
    scopes: List['Scope'] = field(default_factory=list)
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    location: Optional[Location] = None

    @property
    def full_name(self) -> str:
        """Get the fully qualified name of this scope"""
        if not self.name:
            return ""
        # Skip file scopes when building the name
        if self.type == ScopeType.GLOBAL:
            return ""
        if self.parent:
            parent_name = self.parent.full_name
            if parent_name:
                return f"{parent_name}::{self.name}"
        return self.name

    def get_full_name(self) -> str:
        """Get the fully qualified name (for backward compatibility)"""
        return self.full_name

@dataclass
class MethodInfo:
    """Information about a method"""
    name: str
    return_type: str
    access: AccessSpecifier = AccessSpecifier.PUBLIC
    parameters: List[ParameterInfo] = field(default_factory=list)
    calls: List[FunctionCall] = field(default_factory=list)
    location: Optional[Location] = None
    scope: Optional[Scope] = None
    parent_class: Optional['ClassInfo'] = None

    @property
    def full_name(self) -> str:
        """Get the fully qualified name of this method"""
        if self.scope:
            return f"{self.scope.full_name}::{self.name}"
        return self.name

@dataclass
class VariableInfo:
    """Information about a variable"""
    name: str
    type_name: str
    access: AccessSpecifier
    location: Optional[Location] = None
    scope: Optional[Scope] = None

@dataclass
class TypeInfo:
    """Base class for type information"""
    name: str
    type_type: TypeType
    scope: Optional[Scope] = None
    location: Optional[Location] = None
    fields: List[VariableInfo] = field(default_factory=list)
    methods: List[MethodInfo] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)

    def full_name(self) -> str:
        """Get the fully qualified name of this type"""
        if not self.scope:
            return self.name
        scope_name = self.scope.full_name
        if scope_name:
            return f"{scope_name}::{self.name}"
        return self.name

@dataclass
class NamespaceInfo(TypeInfo):
    """Information about a C++ namespace"""
    pass

@dataclass
class ClassInfo(TypeInfo):
    """Information about a C++ class"""
    access_specifier: AccessSpecifier = AccessSpecifier.PRIVATE

class TypeRegistry:
    """Registry of all types and scopes"""
    def __init__(self):
        self.types: Dict[str, TypeInfo] = {}
        self.scope_stack: List[Scope] = []
        self.current_scope: Optional[Scope] = None
        self.files: Dict[str, FileInfo] = {}

    def add_type(self, type_info: TypeInfo):
        """Add a type to the registry"""
        name = type_info.full_name()
        debug(f"Adding type to registry: {name} (scope: {type_info.scope.full_name if type_info.scope else 'None'})", 1)
        self.types[name] = type_info

    def get_type(self, name: str) -> Optional[TypeInfo]:
        """Get a type by name"""
        debug(f"Getting type from registry: {name}", 1)
        debug(f"Available types: {list(self.types.keys())}", 2)

        # Try exact match first
        if name in self.types:
            return self.types[name]

        # Try searching all types for a match on the base name or namespace-qualified name
        for type_name, type_info in self.types.items():
            # Match on base name
            if type_info.name == name:
                return type_info
            
            # Match on namespace-qualified name
            # Strip off file name prefix and compare
            type_parts = type_name.split("::")
            if len(type_parts) > 2:  # Has file prefix
                type_name_without_file = "::".join(type_parts[1:])
                if type_name_without_file == name:
                    return type_info

        return None

    def get_scope(self, name: str) -> Optional[Scope]:
        """Get a scope by name"""
        debug(f"Getting scope: {name}", 1)
        debug(f"Current scope stack: {[s.name for s in self.scope_stack]}", 2)
        
        # First check if it's the current scope
        if self.current_scope and self.current_scope.name == name:
            debug(f"Found in current scope", 2)
            return self.current_scope
        
        # Then check all scopes in the stack
        for scope in reversed(self.scope_stack):
            if scope.name == name:
                debug(f"Found in scope stack", 2)
                return scope
            
            # Check nested scopes
            for child_scope in scope.scopes:
                if child_scope.name == name:
                    debug(f"Found in nested scopes", 2)
                    return child_scope
        
        debug(f"Scope not found", 2)
        return None

    def enter_scope(self, scope: Scope):
        """Enter a new scope"""
        debug(f"Entering scope: {scope.name} (type: {scope.type})", 1)
        self.scope_stack.append(scope)
        self.current_scope = scope
        return scope

    def exit_scope(self):
        """Exit the current scope"""
        if self.scope_stack:
            exiting_scope = self.scope_stack[-1]
            debug(f"Exiting scope: {exiting_scope.name}", 1)
            self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1] if self.scope_stack else None
            debug(f"New current scope: {self.current_scope.name if self.current_scope else 'None'}", 2)

    def add_file(self, file_path: str) -> FileInfo:
        """Add a file to the registry"""
        if file_path not in self.files:
            self.files[file_path] = FileInfo(path=file_path)
        return self.files[file_path]

    def get_file(self, file_path: str) -> Optional[FileInfo]:
        """Get a file by path"""
        return self.files.get(file_path)

    def process_file(self, file_path: str, content: str):
        """Process a file and track includes"""
        file_info = self.add_file(file_path)
        
        # Create a global scope for this file if it doesn't exist
        if not file_info.scope:
            file_info.scope = Scope(type=ScopeType.GLOBAL, name=os.path.basename(file_path))
            self.scope_stack = [file_info.scope]
            self.current_scope = file_info.scope

class TypeCollector:
    """Collect type information from source files"""
    def __init__(self, parser: Parser, verbosity: int = 0):
        self.registry = TypeRegistry()
        self._classes: List[ClassInfo] = []
        self.parser = parser
        global DEBUG_LEVEL
        DEBUG_LEVEL = verbosity
        setup_logging(DEBUG_LEVEL)
        debug("TypeCollector initialized", 1)

    def process_code(self, code: str):
        """Process C++ code directly"""
        debug("Processing code string", 1)
        tree = self.parser.parse(bytes(code, "utf8"))
        self.process_node(tree.root_node, code, "<string>")

    def process_file(self, file_path: str):
        """Process a C++ source file"""
        debug(f"Processing file: {file_path}", 1)
        
        # Read the file content
        with open(file_path, 'r') as f:
            content = f.read()
        debug("File content read", 2)

        # Initialize file tracking
        file_info = self.registry.add_file(file_path)
        file_scope = Scope(type=ScopeType.GLOBAL, name=os.path.basename(file_path))
        file_info.scope = file_scope
        
        # Set up initial scope
        self.registry.scope_stack = [file_scope]
        self.registry.current_scope = file_scope
        
        # Parse and process the file
        tree = self.parser.parse(bytes(content, "utf8"))
        debug("File parsed", 2)
        self.process_node(tree.root_node, content, file_path)

    def process_node(self, node: Node, content: str, file_path: str):
        """Process a node in the AST"""
        if not node:
            return

        debug(f"Processing node: {node.type}", 2)

        # Process node based on type
        if node.type == "class_specifier":
            debug("Found class_specifier", 1)
            self._process_class(node, content, file_path)
        elif node.type == "namespace_definition":
            debug("Found namespace_definition", 1)
            self._process_namespace(node, content, file_path)
        elif node.type == "function_definition":
            debug("Found function_definition", 1)
            self._process_function(node, content, file_path)
        elif node.type == "preproc_include":
            debug("Found preproc_include", 1)
            self._process_include(node, content, file_path)
        
        # Process children recursively
        for child in node.children:
            if child.type == "comment":
                continue
            self.process_node(child, content, file_path)

    def _process_include(self, node: Node, content: str, file_path: str):
        """Process an include directive"""
        path_node = node.child_by_field_name("path")
        if not path_node:
            return

        include_path = self._get_node_text(path_node, content)
        if not include_path:
            return

        # Remove quotes from path
        include_path = include_path.strip('"<>')
        
        # Try to find the header file relative to the current file
        current_dir = os.path.dirname(file_path)
        header_path = os.path.join(current_dir, include_path)
        
        # Track the include in the current file
        current_file = self.registry.get_file(file_path)
        if current_file:
            current_file.add_include(include_path)
        
        if os.path.exists(header_path):
            logging.info(f"Processing included header: {header_path}")
            self.process_file(header_path)

    def _process_namespace(self, node: Node, content: str, file_path: str):
        """Process a namespace definition"""
        # Get namespace name
        namespace_name = None
        for child in node.children:
            if child.type == "namespace_identifier":
                namespace_name = child.text.decode('utf-8')
                break

        if not namespace_name:
            return

        debug(f"Processing namespace: {namespace_name}", 1)

        # Create namespace scope
        namespace_scope = Scope(
            type=ScopeType.NAMESPACE,
            name=namespace_name,
            parent=self.registry.current_scope
        )
        debug(f"Added to parent scope: {self.registry.current_scope.name if self.registry.current_scope else 'None'}", 2)

        # Add to parent's scopes and enter the new scope
        if self.registry.current_scope:
            self.registry.current_scope.scopes.append(namespace_scope)
        self.registry.enter_scope(namespace_scope)

        # Process the namespace body
        declaration_list = node.child_by_field_name("body")
        if declaration_list:
            self.process_node(declaration_list, content, file_path)

        # Exit the namespace scope
        self.registry.exit_scope()

    def _process_class(self, node: Node, content: str, file_path: str):
        """Process a class definition"""
        # Get class name
        class_name = None
        for child in node.children:
            if child.type == "type_identifier":
                class_name = child.text.decode('utf-8')
                break

        if not class_name:
            return

        debug(f"Processing class: {class_name}", 1)

        # Create class scope
        class_scope = Scope(
            type=ScopeType.CLASS,
            name=class_name,
            parent=self.registry.current_scope
        )

        # Create class info
        class_info = ClassInfo(
            name=class_name,
            type_type=TypeType.CLASS,
            scope=self.registry.current_scope
        )

        # Add to registry
        debug(f"Adding type to registry: {class_info.full_name()} (scope: {class_info.scope.full_name if class_info.scope else 'None'})", 1)
        self.registry.add_type(class_info)

        # Add to parent's scopes and enter the new scope
        if self.registry.current_scope:
            self.registry.current_scope.scopes.append(class_scope)
            debug(f"Added to parent scope: {self.registry.current_scope.name}", 2)

        self.registry.enter_scope(class_scope)

        # Process class body
        declaration_list = node.child_by_field_name("body")
        if declaration_list:
            self.process_node(declaration_list, content, file_path)

        # Exit class scope
        self.registry.exit_scope()

    def _process_declaration(self, node: Node, content: str, file_path: str, parent_class: ClassInfo):
        """Process a declaration in a class"""
        if node.type == "field_declaration":
            self._process_field(node, content, file_path, parent_class)
        elif node.type == "function_definition":
            self._process_method(node, content, file_path, parent_class)

    def _process_method(self, node: Node, content: str, file_path: str, parent_class: ClassInfo):
        """Process a method definition"""
        # Get method name and return type
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return
        
        name_node = declarator.child_by_field_name("declarator")
        if not name_node:
            return
        
        method_name = self._get_node_text(name_node, content)
        if not method_name:
            return

        # Get return type
        type_node = node.child_by_field_name("type")
        return_type = self._get_node_text(type_node, content) if type_node else "void"

        logging.debug(f"Processing method: {method_name}")
        
        # Create method info
        method_info = MethodInfo(
            name=method_name,
            return_type=return_type,
            parent_class=parent_class,
            scope=self.registry.current_scope,
            location=self._get_location(node, file_path)
        )

        # Process method body for function calls
        body_node = node.child_by_field_name("body")
        if body_node:
            self._process_method_body(body_node, content, file_path, method_info)

        # Add method to class
        parent_class.methods.append(method_info)

    def _process_field(self, node: Node, content: str, file_path: str, parent_class: ClassInfo):
        """Process a field declaration in a class"""
        # Get field name and type
        type_node = node.child_by_field_name("type")
        declarator = node.child_by_field_name("declarator")
        if not type_node or not declarator:
            return

        field_type = self._get_node_text(type_node, content)
        field_name = self._get_node_text(declarator, content)
        if not field_type or not field_name:
            return

        debug(f"Processing field: {field_name} (type: {field_type})", 1)

        # Create field info
        field_info = VariableInfo(
            name=field_name,
            type_name=field_type,
            scope=self.registry.current_scope,
            location=self._get_location(node, file_path),
            access=parent_class.access_specifier  # Add access specifier from parent class
        )

        # Add field to class
        parent_class.fields.append(field_info)
        debug(f"Added field to class {parent_class.name}", 2)

    def _process_function(self, node: Node, content: str, file_path: str):
        """Process a function definition"""
        # Get function name
        function_name = None
        function_declarator = node.child_by_field_name("declarator")
        if function_declarator:
            function_name = function_declarator.text.decode('utf-8')

        if not function_name:
            return

        # Get return type
        return_type = None
        type_node = node.child_by_field_name("type")
        if type_node:
            return_type = type_node.text.decode('utf-8')

        # Create function info
        debug(f"Processing function: {function_name} (return type: {return_type})", 1)
        function_info = FunctionInfo(
            name=function_name,
            return_type=return_type,
            scope=self.registry.current_scope.name if self.registry.current_scope else None
        )

        # Add function to current scope
        if self.registry.current_scope:
            self.registry.current_scope.functions[function_name] = function_info

    def _get_node_text(self, node: Node, content: str) -> str:
        """Get the text of a node"""
        if node:
            text = content[node.start_byte:node.end_byte].strip()
            # Remove parentheses and parameters for function names
            if node.type == "function_declarator":
                text = text.split('(')[0]
            return text
        return ""

    def _process_call_expression(self, node: Node, content: str, file_path: str, method_info: Optional[MethodInfo] = None):
        """Process a function or method call"""
        if not method_info:
            return

        # Handle constructor calls (new expressions)
        if node.type == "new_expression":
            type_node = node.child_by_field_name("type")
            if type_node:
                type_name = self._get_node_text(type_node, content)
                if type_name:
                    call_info = FunctionCall(
                        name=type_name,
                        is_constructor=True,
                        location=self._get_location(node, file_path)
                    )
                    method_info.calls.append(call_info)
                    logging.debug(f"Found constructor call: {type_name}")
            return

        # Handle normal function/method calls
        function_node = node.child_by_field_name("function")
        if not function_node:
            return

        # Get function name
        function_name = self._get_node_text(function_node, content)
        if not function_name:
            return

        # Create call info
        call_info = FunctionCall(
            name=function_name,
            is_constructor=False,
            location=self._get_location(node, file_path)
        )

        # Process arguments
        arguments_node = node.child_by_field_name("arguments")
        if arguments_node:
            for arg_node in arguments_node.children:
                if arg_node.type != "," and arg_node.type != "(":
                    arg_text = self._get_node_text(arg_node, content)
                    if arg_text:
                        call_info.arguments.append(arg_text)

        method_info.calls.append(call_info)
        logging.debug(f"Found function call: {function_name}")

    def _process_method_body(self, node: Node, content: str, file_path: str, method_info: MethodInfo):
        """Process a method body to find function calls"""
        if not node:
            return

        # Process call expressions
        if node.type == "call_expression" or node.type == "new_expression":
            self._process_call_expression(node, content, file_path, method_info)

        # Process children recursively
        for child in node.children:
            if child.type == "comment":
                continue
            self._process_method_body(child, content, file_path, method_info)

    def _get_location(self, node: Node, file_path: str = "<unknown>") -> Location:
        """Get the location of a node"""
        return Location(
            file_path=file_path,
            start_point=node.start_point,
            end_point=node.end_point
        )

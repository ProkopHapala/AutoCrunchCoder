import os
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
from tree_sitter import Parser, Node

# Debug logging setup
DEBUG_LEVEL = 2  # 0=INFO, 1=DEBUG, 2=TRACE
def setup_logging(level: int):
    if level == 0:
        logging.basicConfig(level=logging.INFO)
    elif level == 1:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.DEBUG)

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
    CLASS = auto()
    FUNCTION = auto()
    METHOD = auto()

@dataclass
class Location:
    """Source code location information"""
    file_path: str
    start_point: tuple[int, int]
    end_point: tuple[int, int]

    def start_line(self): return self.start_point[0]
    def end_line(self): return self.end_point[0]
    def start_column(self): return self.start_point[1]
    def end_column(self): return self.end_point[1]

@dataclass
class FunctionCall:
    """Represents a function call in the code"""
    name: str
    object: Optional[str] = None
    location: Optional[Location] = None
    resolved_file: Optional[str] = None
    arguments: List[str] = field(default_factory=list)
    is_constructor: bool = False
    caller: Optional['MethodInfo'] = None
    scope: Optional['Scope'] = None

@dataclass
class Scope:
    """Represents a scope in the code"""
    type: ScopeType
    name: str
    parent: Optional['Scope'] = None
    children: List['Scope'] = field(default_factory=list)
    functions: Dict[str, 'FunctionInfo'] = field(default_factory=dict)
    location: Optional[Location] = None
    calls: List[FunctionCall] = field(default_factory=list)

    def full_name(self) -> str:
        """Get the fully qualified name of this scope"""
        if self.parent and self.parent.name:
            return f"{self.parent.full_name()}.{self.name}"
        return self.name

@dataclass
class FunctionInfo:
    """Information about a function"""
    name: str
    scope: Optional[Scope] = None
    location: Optional[Location] = None
    calls: List[FunctionCall] = field(default_factory=list)

    def full_name(self) -> str:
        if self.scope:
            return f"{self.scope.full_name()}.{self.name}"
        return self.name

@dataclass
class MethodInfo(FunctionInfo):
    """Information about a method"""
    parent_class: Optional['ClassInfo'] = None

@dataclass
class ClassInfo:
    """Information about a class"""
    name: str
    scope: Optional[Scope] = None
    location: Optional[Location] = None
    methods: List[MethodInfo] = field(default_factory=list)
    fields: Set[str] = field(default_factory=set)

    def full_name(self) -> str:
        if self.scope:
            return f"{self.scope.full_name()}.{self.name}"
        return self.name

class TypeRegistry:
    """Registry of all types and scopes"""
    def __init__(self):
        self.types: Dict[str, ClassInfo] = {}
        self.scope_stack: List[Scope] = []
        self.current_scope: Optional[Scope] = None
        self.files: Dict[str, str] = {}  # file_path -> module_name mapping

    def add_type(self, type_info: ClassInfo):
        """Add a type to the registry"""
        debug(f"Adding type {type_info.name} with full name {type_info.full_name()}", 2)
        self.types[type_info.name] = type_info  # Use simple name as key

    def get_type(self, name: str) -> Optional[ClassInfo]:
        """Get a type by name"""
        debug(f"Getting type {name}", 2)
        return self.types.get(name)  # Use simple name as key

    def get_scope(self, name: str) -> Optional[Scope]:
        """Get a scope by name"""
        if not name:
            return self.scope_stack[0] if self.scope_stack else None
        for scope in reversed(self.scope_stack):
            if scope.full_name() == name:
                return scope
        return None

    def enter_scope(self, scope: Scope):
        """Enter a new scope"""
        if self.current_scope:
            scope.parent = self.current_scope
            self.current_scope.children.append(scope)
        self.scope_stack.append(scope)
        self.current_scope = scope

    def exit_scope(self):
        """Exit the current scope"""
        if self.scope_stack:
            self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1] if self.scope_stack else None

class TypeCollector:
    """Collect type information from Python source files"""
    def __init__(self, parser: Parser, verbosity: int = 0):
        self.registry = TypeRegistry()
        self.parser = parser
        global DEBUG_LEVEL
        DEBUG_LEVEL = verbosity
        setup_logging(DEBUG_LEVEL)
        
        # Initialize global scope
        global_scope = Scope(type=ScopeType.GLOBAL, name="")
        self.registry.enter_scope(global_scope)

    def process_code(self, code: str, file_path: str = "<string>"):
        """Process Python code directly"""
        tree = self.parser.parse(bytes(code, "utf8"))
        self._process_node(tree.root_node, code, file_path)

    def process_file(self, file_path: str):
        """Process a Python source file"""
        with open(file_path, 'r') as f:
            content = f.read()
        self.process_code(content, file_path)

    def _process_node(self, node: Node, content: str, file_path: str):
        """Process a node in the AST"""
        debug(f"Processing node type: {node.type}", 2)
        
        if node.type == "module":
            for child in node.children:
                self._process_node(child, content, file_path)
        
        elif node.type == "class_definition":
            self._process_class(node, content, file_path)
            # Process class body recursively
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._process_node(child, content, file_path)
        
        elif node.type == "function_definition":
            if isinstance(self.registry.current_scope, Scope) and self.registry.current_scope.type == ScopeType.CLASS:
                # Skip processing as method - it will be handled by _process_class
                return
            self._process_function(node, content, file_path)

    def _process_class(self, node: Node, content: str, file_path: str):
        """Process a class definition"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        class_name = self._get_node_text(name_node, content)
        location = self._get_location(node, file_path)
        
        class_info = ClassInfo(
            name=class_name,
            scope=self.registry.current_scope,
            location=location,
            methods=[],  # Initialize empty methods list
            fields=set()  # Initialize empty fields set
        )
        
        # Create and enter class scope
        class_scope = Scope(
            type=ScopeType.CLASS,
            name=class_name,
            location=location
        )
        self.registry.enter_scope(class_scope)
        
        # Process class body
        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                if child.type == "function_definition":
                    self._process_method(child, content, file_path, class_info)
                elif child.type == "expression_statement":
                    # Handle potential field assignments
                    self._process_class_field(child, content, class_info)
        
        self.registry.exit_scope()
        self.registry.add_type(class_info)

    def _process_function(self, node: Node, content: str, file_path: str):
        """Process a function definition"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        func_name = self._get_node_text(name_node, content)
        location = self._get_location(node, file_path)
        
        func_info = FunctionInfo(
            name=func_name,
            scope=self.registry.current_scope,
            location=location
        )
        
        # Create and enter function scope
        func_scope = Scope(
            type=ScopeType.FUNCTION,
            name=func_name,
            location=location
        )
        self.registry.enter_scope(func_scope)
        
        # Process function body for calls
        body = node.child_by_field_name("body")
        if body:
            self._process_function_body(body, content, file_path, func_info)
        
        self.registry.exit_scope()
        
        # Add function to current scope
        if self.registry.current_scope:
            self.registry.current_scope.functions[func_name] = func_info

    def _process_method(self, node: Node, content: str, file_path: str, class_info: ClassInfo):
        """Process a method definition"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        method_name = self._get_node_text(name_node, content)
        location = self._get_location(node, file_path)
        
        method_info = MethodInfo(
            name=method_name,
            scope=self.registry.current_scope,
            location=location,
            parent_class=class_info
        )
        
        # Create and enter method scope
        method_scope = Scope(
            type=ScopeType.METHOD,
            name=method_name,
            location=location
        )
        self.registry.enter_scope(method_scope)
        
        # Process method body for calls
        body = node.child_by_field_name("body")
        if body:
            self._process_function_body(body, content, file_path, method_info)
        
        self.registry.exit_scope()
        
        # Add method to class
        class_info.methods.append(method_info)

    def _process_function_body(self, node: Node, content: str, file_path: str, func_info: FunctionInfo):
        """Process a function/method body to find function calls"""
        def visit_node(node):
            if node.type == "call":
                self._process_call(node, content, file_path, func_info)
            for child in node.children:
                visit_node(child)
        
        visit_node(node)

    def _process_call(self, node: Node, content: str, file_path: str, func_info: FunctionInfo):
        """Process a function call"""
        function = node.child_by_field_name("function")
        if not function:
            return

        # Handle method calls (e.g., obj.method())
        if function.type == "attribute":
            obj = function.child_by_field_name("object")
            attr = function.child_by_field_name("attribute")
            if obj and attr:
                call = FunctionCall(
                    name=self._get_node_text(attr, content),
                    object=self._get_node_text(obj, content),
                    location=self._get_location(node, file_path),
                    caller=func_info
                )
                func_info.calls.append(call)
        # Handle direct function calls
        else:
            call = FunctionCall(
                name=self._get_node_text(function, content),
                location=self._get_location(node, file_path),
                caller=func_info,
                is_constructor=function.type == "identifier" and function.text.decode('utf8')[0].isupper()
            )
            func_info.calls.append(call)

    def _process_class_field(self, node: Node, content: str, class_info: ClassInfo):
        """Process potential class field assignments"""
        # Look for self.field = value pattern
        if node.type == "expression_statement":
            expr = node.child_by_field_name("expression")
            if expr and expr.type == "assignment":
                left = expr.child_by_field_name("left")
                if left and left.type == "attribute":
                    obj = left.child_by_field_name("object")
                    if obj and obj.type == "identifier" and self._get_node_text(obj, content) == "self":
                        field = left.child_by_field_name("attribute")
                        if field:
                            field_name = self._get_node_text(field, content)
                            debug(f"Found class field: {field_name}", 2)
                            class_info.fields.add(field_name)

    def _get_node_text(self, node: Node, content: str) -> str:
        """Get the text of a node"""
        return content[node.start_byte:node.end_byte]

    def _get_location(self, node: Node, file_path: str = "<unknown>") -> Location:
        """Get the location of a node"""
        return Location(
            file_path=file_path,
            start_point=node.start_point,
            end_point=node.end_point
        )

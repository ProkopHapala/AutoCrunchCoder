from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union
import os
from tree_sitter import Parser, Node

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
class FunctionCall:
    """Represents a function call in the code"""
    name: str
    object_name: Optional[str] = None
    location: Optional[Location] = None
    resolved_file: Optional[str] = None  # Path to the file containing the called function

@dataclass
class Scope:
    """Represents a scope in the code"""
    type: ScopeType
    name: str
    parent: Optional['Scope'] = None
    children: List['Scope'] = field(default_factory=list)
    location: Optional[Location] = None

    @property
    def full_name(self) -> str:
        """Get the fully qualified name of this scope"""
        if not self.name:
            return ""
        if self.parent and self.parent.name:
            return f"{self.parent.full_name}::{self.name}"
        return self.name

    def get_full_name(self) -> str:
        """Get the fully qualified name (for backward compatibility)"""
        return self.full_name

@dataclass
class MethodInfo:
    """Information about a method"""
    name: str
    return_type: str
    access: AccessSpecifier
    parameters: List[str]
    location: Optional[Location] = None
    scope: Optional[Scope] = None
    calls: List[FunctionCall] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Get the fully qualified name of this method"""
        if self.scope:
            return f"{self.scope.full_name}::{self.name}"
        return self.name

@dataclass
class ParameterInfo:
    """Information about a function parameter"""
    name: str
    type_name: str
    default_value: Optional[str] = None

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
    scope: Optional[Scope] = None
    location: Optional[Location] = None

    @property
    def full_name(self) -> str:
        """Get the fully qualified name of this type"""
        if self.scope and self.scope.name:
            return f"{self.scope.full_name}::{self.name}"
        return f"::{self.name}"  # Global scope

@dataclass
class ClassInfo(TypeInfo):
    """Information about a C++ class"""
    base_classes: List[str] = field(default_factory=list)
    methods: List[MethodInfo] = field(default_factory=list)
    fields: List[VariableInfo] = field(default_factory=list)
    access_specifier: AccessSpecifier = AccessSpecifier.PRIVATE

class TypeRegistry:
    """Registry of all types and scopes"""
    def __init__(self):
        self.types: Dict[str, TypeInfo] = {}
        self.files: Dict[str, FileInfo] = {}
        self.global_scope = Scope(ScopeType.GLOBAL, "", None)
        self.current_scope = self.global_scope
        self.current_file = None

        # Initialize basic types
        self._init_basic_types()

    def _init_basic_types(self):
        """Initialize basic C++ types"""
        basic_types = [
            "void", "bool", "char", "int", "float", "double",
            "int8_t", "uint8_t", "int16_t", "uint16_t",
            "int32_t", "uint32_t", "int64_t", "uint64_t"
        ]
        for type_name in basic_types:
            type_info = TypeInfo(type_name, self.global_scope)
            self.types[type_name] = type_info

    def add_type(self, type_info: TypeInfo):
        """Add a type to the registry"""
        if not type_info.scope:
            type_info.scope = self.current_scope

        if isinstance(type_info, FileInfo):
            self.files[type_info.path] = type_info
            return

        # Get fully qualified name
        full_name = type_info.full_name
        if full_name:
            self.types[full_name] = type_info
            # Also add with simple name for lookup without scope
            self.types[type_info.name] = type_info

    def get_type(self, name: str) -> Optional[TypeInfo]:
        """Get a type by name"""
        # Try exact match first
        if name in self.types:
            return self.types[name]

        # Try with current scope
        if self.current_scope and self.current_scope.full_name:
            scoped_name = f"{self.current_scope.full_name}::{name}"
            if scoped_name in self.types:
                return self.types[scoped_name]

        # Try in parent scopes
        scope = self.current_scope
        while scope and scope.parent:
            scope = scope.parent
            if scope.full_name:
                scoped_name = f"{scope.full_name}::{name}"
                if scoped_name in self.types:
                    return self.types[scoped_name]

        return None

    def get_scope(self, name: str) -> Optional[Scope]:
        """Get a scope by name"""
        parts = name.split("::")
        current = self.global_scope
        for part in parts:
            found = False
            for child in current.children:
                if child.name == part:
                    current = child
                    found = True
                    break
            if not found:
                return None
        return current

    def enter_scope(self, type: ScopeType, name: str) -> Scope:
        """Enter a new scope"""
        scope = Scope(type, name, self.current_scope)
        self.current_scope.children.append(scope)
        self.current_scope = scope
        return scope

    def exit_scope(self):
        """Exit the current scope"""
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def enter_file(self, file_path: str):
        """Enter a file scope"""
        self.current_file = file_path
        self.current_scope = self.global_scope

    def exit_file(self):
        """Exit file scope"""
        self.current_file = None
        self.current_scope = self.global_scope

    def add_file(self, file_info: FileInfo):
        """Add a file to the registry"""
        self.files[file_info.path] = file_info

class TypeCollector:
    """Collect type information from source files"""
    def __init__(self, parser: Parser, verbosity: int = 0):
        self.parser = parser
        self.registry = TypeRegistry()
        self.verbosity = verbosity

    def _debug(self, level: int, msg: str):
        """Print debug message if verbosity level is high enough"""
        if self.verbosity >= level:
            indent = "  " * (level - 1) if level > 0 else ""
            print(f"{indent}[TypeCollector] {msg}")

    def _adjust_point(self, point: tuple) -> tuple:
        """Adjust a point tuple to be 1-based line numbers"""
        return (point[0] + 1, point[1])

    def process_file(self, file_path: str):
        """Process a file and collect type information"""
        if not os.path.exists(file_path):
            return

        with open(file_path, 'r') as f:
            content = f.read()

        self._debug(1, f"Processing file: {file_path}")
        
        # Create file info
        file_info = FileInfo(file_path)
        self.registry.add_file(file_info)

        # Parse the file
        tree = self.parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node

        # Process the AST
        self.registry.enter_file(file_path)
        try:
            self.process_node(root_node, content, file_path)
        finally:
            self.registry.exit_file()

        # Resolve cross-file dependencies
        for include_path in file_info.includes:
            if not os.path.exists(include_path):
                continue
            self.process_file(include_path)

    def process_node(self, node: Node, content: str, file_path: str):
        """Process a node in the AST"""
        # Process includes first
        if node.type == "preproc_include":
            header = node.child_by_field_name("path")
            if header:
                header_path = self._get_node_text(header, content).strip('"<>')
                if file_path in self.registry.files:
                    # Convert relative path to absolute
                    if not os.path.isabs(header_path):
                        header_path = os.path.abspath(os.path.join(os.path.dirname(file_path), header_path))
                    self.registry.files[file_path].add_include(header_path)

        # Process other nodes
        if node.type == "namespace_definition":
            self._process_namespace(node, content, file_path)
        elif node.type == "class_specifier":
            self._process_class(node, content, file_path)
        elif node.type == "function_definition":
            self._process_function_definition(node, content, file_path)

        # Process children
        for child in node.children:
            if child.type == "comment":
                continue
            self.process_node(child, content, file_path)

    def _process_class(self, node: Node, content: str, file_path: str):
        """Process a class definition"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self._get_node_text(name_node, content)
        if not name:
            return

        self._debug(1, f"Processing class at {node.start_point}")

        # Create class info
        class_info = ClassInfo(
            name=name,
            scope=self.registry.current_scope,
            location=Location(
                file_path=file_path,
                start_point=self._adjust_point(node.start_point),
                end_point=self._adjust_point(node.end_point)
            )
        )

        # Process base classes
        self._debug(2, f"Class node type: {node.type}")
        self._debug(2, f"Class node text: {content[node.start_byte:node.end_byte]}")
        self._debug(2, "Class node children:")
        base_clause = None
        for child in node.children:
            self._debug(2, f"  Child type: {child.type} text: {content[child.start_byte:child.end_byte]}")
            if child.type == "base_class_clause":
                base_clause = child
                break

        if base_clause:
            self._debug(2, f"Processing base clause: {base_clause.type}")
            self._debug(2, f"Base clause text: {content[base_clause.start_byte:base_clause.end_byte]}")
            for child in base_clause.children:
                self._debug(2, f"Base clause child: {child.type} text: {content[child.start_byte:child.end_byte]}")
                if child.type == "type_identifier":
                    base_name = self._get_node_text(child, content)
                    if base_name:
                        self._debug(2, f"Found base class: {base_name}")
                        class_info.base_classes.append(base_name)

        # Create and enter class scope
        scope = self.registry.enter_scope(ScopeType.CLASS, name)
        scope.location = Location(
            file_path=file_path,
            start_point=self._adjust_point(node.start_point),
            end_point=self._adjust_point(node.end_point)
        )

        # Process class body
        body_node = node.child_by_field_name("body")
        if body_node:
            self._debug(2, f"Processing class body at {body_node.start_point}")
            self._process_class_body(body_node, content, file_path, class_info)

        self.registry.exit_scope()
        self.registry.add_type(class_info)

    def _process_namespace(self, node: Node, content: str, file_path: str):
        """Process a namespace definition"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self._get_node_text(name_node, content)
        if not name:
            return

        # Create and enter namespace scope
        scope = self.registry.enter_scope(ScopeType.NAMESPACE, name)
        scope.location = Location(
            file_path=file_path,
            start_point=self._adjust_point(node.start_point),
            end_point=self._adjust_point(node.end_point)
        )

        self._debug(1, f"Processing namespace: {name}")
        self._debug(2, f"  Entered namespace scope: {scope.full_name}")

        # Process namespace body
        body_node = node.child_by_field_name("body")
        if body_node:
            self._debug(2, "  Processing namespace body")
            self.process_node(body_node, content, file_path)

        self._debug(2, "  Exited namespace scope")
        self.registry.exit_scope()

    def _process_class_body(self, node: Node, content: str, file_path: str, class_info: ClassInfo):
        """Process a class body"""
        current_access = AccessSpecifier.PRIVATE  # Default access in C++

        for child in node.children:
            if child.type == "access_specifier":
                access_text = self._get_node_text(child, content).upper()
                if access_text == "PUBLIC":
                    current_access = AccessSpecifier.PUBLIC
                elif access_text == "PROTECTED":
                    current_access = AccessSpecifier.PROTECTED
                elif access_text == "PRIVATE":
                    current_access = AccessSpecifier.PRIVATE
            elif child.type == "field_declaration":
                self._process_field_declaration(child, content, file_path, class_info, current_access)
            elif child.type == "function_definition":
                self._process_method_definition(child, content, file_path, class_info, current_access)

    def _process_field_declaration(self, node: Node, content: str, file_path: str, class_info: ClassInfo, access: AccessSpecifier):
        """Process a field declaration within a class"""
        if node.type == "function_definition":
            declarator = node.child_by_field_name("declarator")
            type_node = node.child_by_field_name("type")
        else:
            declarator = node.child_by_field_name("declarator")
            type_node = node.child_by_field_name("type")

        if not declarator:
            return

        # For function definitions, get the name without parameters
        if node.type == "function_definition":
            name_node = declarator.child_by_field_name("declarator")
            if not name_node:
                return
            name = self._get_node_text(name_node, content).split('(')[0]
        else:
            name = self._get_node_text(declarator, content)

        if not name:
            return

        if node.type == "function_definition":
            method_info = MethodInfo(
                name=name,
                return_type=self._get_node_text(type_node, content) if type_node else "",
                access=access,
                parameters=[],  # TODO: Process parameters
                location=Location(file_path=file_path, start_point=node.start_point, end_point=node.end_point),
                scope=self.registry.current_scope
            )
            class_info.methods.append(method_info)
            
            # Process function body for calls
            body_node = node.child_by_field_name("body")
            if body_node:
                self._process_function_body(body_node, content, file_path, method_info)
        else:
            var_info = VariableInfo(
                name=name,
                type_name=self._get_node_text(type_node, content) if type_node else "",
                access=access,
                location=Location(file_path=file_path, start_point=node.start_point, end_point=node.end_point),
                scope=self.registry.current_scope
            )
            class_info.fields.append(var_info)

    def _process_function_body(self, node: Node, content: str, file_path: str, method_info: MethodInfo):
        """Process a function body for calls"""
        for child in node.children:
            if child.type == "call_expression":
                function_node = child.child_by_field_name("function")
                if function_node:
                    name = self._get_node_text(function_node, content)
                    call_info = FunctionCall(
                        name=name,
                        location=Location(file_path=file_path, start_point=child.start_point, end_point=child.end_point)
                    )
                    method_info.calls.append(call_info)
            else:
                self._process_function_body(child, content, file_path, method_info)

    def _process_function_definition(self, node: Node, content: str, file_path: str):
        """Process a free function definition"""
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return

        name_node = declarator.child_by_field_name("declarator")
        if not name_node:
            return

        function_name = content[name_node.start_byte:name_node.end_byte]
        return_type_node = node.child_by_field_name("type")
        return_type = content[return_type_node.start_byte:return_type_node.end_byte] if return_type_node else "void"

        function_info = MethodInfo(
            name=function_name,
            return_type=return_type,
            access=AccessSpecifier.PUBLIC,
            parameters=[],  # TODO: Process parameters
            location=Location(file_path=file_path, start_point=node.start_point, end_point=node.end_point),
            scope=self.registry.current_scope
        )

        # Process function body for calls
        body_node = node.child_by_field_name("body")
        if body_node:
            method_info = MethodInfo(
                name=function_name,
                return_type=return_type,
                access=AccessSpecifier.PUBLIC,
                parameters=[],  # TODO: Process parameters
                location=Location(file_path=file_path, start_point=node.start_point, end_point=node.end_point),
                scope=self.registry.current_scope
            )
            self._process_method_body(body_node, content, file_path, method_info)
            function_info.parameters = method_info.parameters

        self.registry.add_type(function_info)

    def _process_method_definition(self, node: Node, content: str, file_path: str, class_info: ClassInfo, access: AccessSpecifier):
        """Process a method definition within a class"""
        # Get method name
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return

        name_node = declarator.child_by_field_name("declarator")
        if not name_node:
            return

        name = self._get_node_text(name_node, content)
        if not name:
            return

        # Get return type
        type_node = node.child_by_field_name("type")
        return_type = self._get_node_text(type_node, content) if type_node else "void"

        # Create method info
        method_info = MethodInfo(
            name=name,
            return_type=return_type,
            access=access,
            parameters=[],  # TODO: Process parameters
            location=Location(file_path=file_path, start_point=node.start_point, end_point=node.end_point),
            scope=self.registry.current_scope
        )

        # Process method body for function calls
        body_node = node.child_by_field_name("body")
        if body_node:
            self._process_method_body(body_node, content, file_path, method_info)

        class_info.methods.append(method_info)

    def _process_method_body(self, node: Node, content: str, file_path: str, method_info: MethodInfo):
        """Process a method body for function calls"""
        for child in node.children:
            if child.type == "call_expression":
                self._process_call_expression(child, content, file_path, method_info)
            else:
                self._process_method_body(child, content, file_path, method_info)

    def _process_call_expression(self, node: Node, content: str, file_path: str, method_info: MethodInfo):
        """Process a function call expression"""
        function_node = node.child_by_field_name("function")
        if not function_node:
            return

        # Handle method calls (obj.method())
        if function_node.type == "field_expression":
            object_node = function_node.child_by_field_name("argument")
            field_node = function_node.child_by_field_name("field")
            if object_node and field_node:
                object_name = content[object_node.start_byte:object_node.end_byte]
                method_name = content[field_node.start_byte:field_node.end_byte]
                call_info = FunctionCall(
                    name=method_name,
                    object_name=object_name,
                    location=Location(file_path=file_path, start_point=node.start_point, end_point=node.end_point)
                )
                method_info.calls.append(call_info)
        # Handle free function calls
        else:
            function_name = content[function_node.start_byte:function_node.end_byte]
            call_info = FunctionCall(
                name=function_name,
                location=Location(file_path=file_path, start_point=node.start_point, end_point=node.end_point)
            )
            method_info.calls.append(call_info)

    def _get_node_text(self, node: Node, content: str) -> str:
        """Get the text of a node"""
        if node:
            text = content[node.start_byte:node.end_byte].strip()
            # Remove parentheses and parameters for function names
            if node.type == "function_declarator":
                text = text.split('(')[0]
            return text
        return ""

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
    object: Optional[str] = None
    location: Optional[Location] = None
    resolved_file: Optional[str] = None
    template_args: List[str] = field(default_factory=list)
    arguments: List[str] = field(default_factory=list)
    is_constructor: bool = False
    is_static: bool = False
    caller: Optional['MethodInfo'] = None
    resolved_method: Optional['MethodInfo'] = None
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
    is_virtual: bool = False
    is_override: bool = False

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

class ClassInfo(TypeInfo, Scope):
    """Information about a class"""
    def __init__(self, name: str, type_type: TypeType, scope: Optional[Scope] = None, location: Optional[Location] = None):
        TypeInfo.__init__(self, name=name, type_type=type_type, scope=scope)
        Scope.__init__(self, type=ScopeType.CLASS, name=name, parent=scope, location=location)
        self.fields: List[VariableInfo] = []
        self.methods: List[MethodInfo] = []
        self.base_classes: List[str] = []
        self.access_specifier = AccessSpecifier.PRIVATE

    def full_name(self) -> str:
        """Get the fully qualified name of the class"""
        if self.parent:
            return f"{self.parent.get_full_name()}::{self.name}"
        return self.name

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

    @property
    def classes(self) -> List[ClassInfo]:
        """Get all classes that have been collected"""
        return self._classes

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
        
        # Convert relative path to absolute path based on current file's directory
        if not os.path.isabs(include_path):
            current_dir = os.path.dirname(os.path.abspath(file_path))
            include_path = os.path.normpath(os.path.join(current_dir, include_path))
        
        # Add the include to the current file's info
        file_info = self.registry.get_file(file_path)
        if file_info:
            file_info.add_include(include_path)
            debug(f"Added include {include_path} to {file_path}", 2)

        if os.path.exists(include_path):
            logging.info(f"Processing included header: {include_path}")
            self.process_file(include_path)

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
        namespace_scope.location = self._get_location(node, file_path)
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
        debug(f"Processing class node: {node.type}", 2)
        
        # Get class name
        class_name = None
        for child in node.children:
            if child.type == "type_identifier":
                class_name = self._get_node_text(child, content)
                break
        
        if not class_name:
            debug("No class name found", 1)
            return

        # Create class info
        class_info = ClassInfo(
            name=class_name,
            type_type=TypeType.CLASS,
            scope=self.registry.current_scope,
            location=self._get_location(node, file_path)
        )
        
        # Process base classes
        base_clause = next((child for child in node.children if child.type == "base_class_clause"), None)
        if base_clause:
            for child in base_clause.children:
                if child.type == "type_identifier":
                    base_class = self._get_node_text(child, content)
                    class_info.base_classes.append(base_class)

        # Add to registry and enter scope
        self.registry.add_type(class_info)
        self.registry.enter_scope(class_info)
        self._classes.append(class_info)  # Add to classes list

        # Process class body
        body = next((child for child in node.children if child.type == "field_declaration_list"), None)
        if body:
            for child in body.children:
                if child.type in ["field_declaration", "function_definition"]:
                    self._process_declaration(child, content, file_path, class_info)
                elif child.type == "access_specifier":
                    specifier = self._get_node_text(child, content).upper()
                    class_info.access_specifier = AccessSpecifier[specifier]

        # Exit scope
        self.registry.exit_scope()

    def _process_declaration(self, node: Node, content: str, file_path: str, parent_class: Optional[ClassInfo] = None):
        """Process a field or method declaration"""
        # Check if this is a method declaration
        if node.type == "function_definition":
            debug("Found function_definition", 1)
            
            # Get method name
            declarator = node.child_by_field_name("declarator")
            if not declarator:
                return
                
            method_name = self._get_node_text(declarator, content)
            if not method_name:
                return

            # Get return type
            type_node = node.child_by_field_name("type")
            return_type = self._get_node_text(type_node, content) if type_node else "void"

            # Create method info
            debug(f"Processing method: {method_name} (return type: {return_type})", 1)
            method_info = MethodInfo(
                name=method_name,
                return_type=return_type,
                access=AccessSpecifier.PUBLIC,  # Will be updated by access specifier
                parent_class=parent_class,
            )

            # Check if method is virtual
            for child in node.children:
                debug(f"Checking child node: {child.type} text: {child.text.decode('utf-8')}", 2)
                if child.type == "virtual":
                    debug("Method {method_name} is virtual", 2)
                    method_info.is_virtual = True
                elif child.type == "function_declarator":
                    # Check for override specifier in function_declarator
                    for subchild in child.children:
                        if subchild.type == "virtual_specifier" and subchild.text.decode('utf-8') == "override":
                            debug(f"Method {method_name} is override", 2)
                            method_info.is_override = True

            if parent_class:
                debug(f"Added method {method_name} to class {parent_class.name} (virtual={method_info.is_virtual}, override={method_info.is_override})", 2)
                parent_class.methods.append(method_info)

                # Process method body to find function calls
                body_node = node.child_by_field_name("body")
                if body_node:
                    debug(f"Processing method body for {method_name}", 2)
                    self._process_method_body(body_node, content, file_path, method_info)

        elif node.type == "field_declaration":
            self._process_field(node, content, file_path, parent_class)

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
        return_type = self._get_node_text(type_node, content) if type_node else "void"

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

    def _extract_node_text(self, node: Node, content: str) -> Optional[str]:
        """Extract and validate text from a node.
        
        Args:
            node: The AST node to extract text from
            content: The original source code content
            
        Returns:
            The extracted text or None if the node is invalid
        """
        if not node:
            return None
        return self._get_node_text(node, content)

    def _process_call_expression(self, node: Node, content: str, file_path: str, method_info: Optional[MethodInfo] = None):
        """Process a call expression node to extract function call information"""
        if not node:
            return

        debug(f"\nProcessing call expression: {content[node.start_byte:node.end_byte]}", 1)
        debug(f"Node type: {node.type}", 1)

        # Initialize call info with default values
        call_info = FunctionCall(
            name="",
            location=self._get_location(node, file_path)
        )

        # Get function node and argument list
        function_node = node.child_by_field_name("function")
        argument_list = node.child_by_field_name("arguments")
        template_arguments = node.child_by_field_name("template_arguments")

        if not function_node:
            return

        debug(f"Function node type: {function_node.type}", 1)
        debug(f"Function node text: {content[function_node.start_byte:function_node.end_byte]}", 1)

        # Process template arguments if present
        if template_arguments:
            debug(f"Processing template arguments: {content[template_arguments.start_byte:template_arguments.end_byte]}", 1)
            call_info.template_args = self._process_template_arguments(template_arguments, content)

        # Process argument list if present
        if argument_list:
            call_info.arguments = self._process_argument_list(argument_list, content)

        # Process function node based on its type
        if function_node.type == "field_expression":
            # Method call on an object (e.g., obj.method())
            object_node = function_node.child_by_field_name("argument")
            field_node = function_node.child_by_field_name("field")

            if field_node:
                debug(f"Field node type: {field_node.type}", 1)
                debug(f"Field node text: {content[field_node.start_byte:field_node.end_byte]}", 1)

                # Check for template arguments in the field node
                field_template_args = field_node.child_by_field_name("template_arguments")
                if field_template_args:
                    debug(f"Field template arguments: {content[field_template_args.start_byte:field_template_args.end_byte]}", 1)
                    call_info.template_args = self._process_template_arguments(field_template_args, content)

                # Extract method name
                name_node = field_node
                if field_node.type == "template_function":
                    name_node = field_node.child_by_field_name("name")
                raw_method_name = self._get_node_text(name_node, content)
                debug(f"Raw method name before cleaning: {raw_method_name}", 1)  # Added debug statement
                if raw_method_name:
                    call_info.name = self._clean_method_name(raw_method_name)

            if object_node:
                object_text = self._get_node_text(object_node, content)
                if object_text:
                    call_info.object = object_text

        elif function_node.type == "scoped_identifier":
            # Static method call (e.g., Class::method())
            call_info.is_static = True
            debug(f"Processing scoped identifier: {content[function_node.start_byte:function_node.end_byte]}", 1)
            
            # Get the full identifier text and clean it
            raw_method_name = content[function_node.start_byte:function_node.end_byte].strip()
            debug(f"Raw method name before cleaning: {raw_method_name}", 1)  # Added debug statement
            call_info.name = self._clean_method_name(raw_method_name)
            debug(f"Cleaned method name: {call_info.name}", 1)

            # Double check the name is actually clean
            if '::' in call_info.name:
                debug("WARNING: Name still contains scope resolution after cleaning!", 1)

        elif function_node.type == "identifier":
            # Direct function call (e.g., function())
            raw_method_name = self._get_node_text(function_node, content)
            debug(f"Raw method name before cleaning: {raw_method_name}", 1)  # Added debug statement
            if raw_method_name:
                call_info.name = self._clean_method_name(raw_method_name)
                debug(f"Identifier method name: {call_info.name}", 1)

        elif function_node.type == "template_function":
            # Template function call (e.g., function<T>())
            debug(f"Template function node: {content[function_node.start_byte:function_node.end_byte]}", 1)

            name_node = function_node.child_by_field_name("name")
            if name_node:
                raw_method_name = self._get_node_text(name_node, content)
                if raw_method_name:
                    call_info.name = self._clean_method_name(raw_method_name)

            # Process template arguments from the template_function node
            template_args = function_node.child_by_field_name("template_arguments")
            if template_args:
                debug(f"Template arguments: {content[template_args.start_byte:template_args.end_byte]}", 1)
                call_info.template_args = self._process_template_arguments(template_args, content)

        # Process constructor call
        if function_node.type == "type_identifier":
            type_name = self._get_node_text(function_node, content)
            if type_name:
                call_info.name = type_name
                call_info.is_constructor = True
                # Process constructor arguments
                if argument_list:
                    call_info.arguments = self._process_argument_list(argument_list, content)
                if method_info:
                    method_info.calls.append(call_info)
                debug(f"Found constructor call: {type_name} with args: {call_info.arguments}", 2)
            return

        if method_info and call_info.name:
            debug(f"Adding call to method {method_info.name}: {call_info.name} (object: {call_info.object}, args: {call_info.arguments}, template_args: {call_info.template_args}, is_static: {call_info.is_static})", 1)
            method_info.calls.append(call_info)

    def _clean_method_name(self, method_name: str) -> str:
        """Clean a method name by removing template arguments and scope resolution.
        
        Args:
            method_name: Raw method name that may include template args or scope
            
        Returns:
            Clean method name without template args or scope
        """
        debug(f"CLEAN_METHOD_NAME CALLED with: {method_name}", 1)
        # Remove template arguments if present
        if '<' in method_name:
            debug(f"Removing template arguments from: {method_name}", 1)
            method_name = method_name.split('<')[0]
            debug(f"After template removal: {method_name}", 1)
        
        # Remove scope resolution if present
        if '::' in method_name:
            debug(f"Removing scope resolution from: {method_name}", 1)
            method_name = method_name.split('::')[-1]
            debug(f"After scope removal: {method_name}", 1)
            
        debug(f"Final cleaned name: {method_name}", 1)
        return method_name

    def _get_node_text(self, node: Node, content: str) -> str:
        """Get the text of a node"""
        if node:
            debug(f"Getting text for node type: {node.type}", 1)
            text = content[node.start_byte:node.end_byte].strip()
            debug(f"Raw text: {text}", 1)

            # Remove parentheses and parameters for function names
            if node.type == "function_declarator":
                text = text.split('(')[0]
                debug(f"After function declarator processing: {text}", 1)
            # For scoped identifiers, get only the name part
            elif node.type == "scoped_identifier":
                debug("Processing scoped identifier", 1)
                text = self._clean_method_name(text)
                debug(f"After cleaning scoped identifier: {text}", 1)
            debug(f"Final text: {text}", 1)
            return text
        return ""

    def _get_location(self, node: Node, file_path: str = "<unknown>") -> Location:
        """Get the location of a node"""
        return Location(
            file_path=file_path,
            start_point=(node.start_point[0] + 1, node.start_point[1]),
            end_point=(node.end_point[0] + 1, node.end_point[1])
        )

    def _process_template_arguments(self, node: Node, content: str) -> List[str]:
        """Process template arguments"""
        template_args = []
        for child in node.children:
            if child.type not in ["<", ">", ",", "template_argument_list"]:
                arg_text = self._get_node_text(child, content)
                if arg_text:
                    template_args.append(arg_text)
        return template_args

    def _process_argument_list(self, node: Node, content: str) -> List[str]:
        """Process argument list"""
        arguments = []
        for child in node.children:
            if child.type not in ["(", ")", ",", "argument_list"]:
                arg_text = self._get_node_text(child, content)
                if arg_text:
                    arguments.append(arg_text)
        return arguments

    def _process_method_body(self, node: Node, content: str, file_path: str, method_info: MethodInfo):
        """Process a method body to find function calls"""
        if not node:
            return

        debug(f"\nProcessing method body node type: {node.type} text: {content[node.start_byte:node.end_byte]}", 1)
        debug(f"Node structure:", 1)
        for child in node.children:
            debug(f"  Child type: {child.type}", 1)
            debug(f"  Child text: {content[child.start_byte:child.end_byte]}", 1)
            if child.type == "comment":
                continue
            if child.type == "call_expression":
                debug(f"Found call_expression in method body: {content[child.start_byte:child.end_byte]}", 1)
                # Check if this is a scoped static method call
                function_node = child.child_by_field_name("function")
                if function_node and "::" in content[function_node.start_byte:function_node.end_byte]:
                    debug(f"Found scoped static method call: {content[function_node.start_byte:function_node.end_byte]}", 1)
                    # Get the scoped name parts
                    scoped_name = content[function_node.start_byte:function_node.end_byte]
                    
                    call_info = FunctionCall(
                        name=scoped_name,
                        is_static=True,
                        location=self._get_location(child, file_path)
                    )
                    
                    # Add arguments if present
                    argument_list = child.child_by_field_name("arguments")
                    if argument_list:
                        for arg_node in argument_list.children:
                            if arg_node.type not in ["(", ")", ",", "argument_list"]:
                                arg_text = self._get_node_text(arg_node, content)
                                if arg_text:
                                    call_info.arguments.append(arg_text)
                                    debug(f"Added argument to static call: {arg_text}", 1)

                    method_info.calls.append(call_info)
                    debug(f"Added static method call: {call_info.name} (args: {call_info.arguments})", 1)
                else:
                    self._process_call_expression(child, content, file_path, method_info)
            elif child.type == "declaration":
                debug(f"Found declaration in method body: {content[child.start_byte:child.end_byte]}", 1)
                # Handle constructor calls in declarations
                type_node = child.child_by_field_name("type")
                init_declarator = next((child for child in node.children if child.type == "init_declarator"), None)
                if type_node:
                    type_name = self._get_node_text(type_node, content)
                    if type_name:
                        # Strip template parameters from type name
                        base_type = type_name.split('<')[0]
                        call_info = FunctionCall(
                            name=base_type,
                            is_constructor=True,
                            location=self._get_location(node, file_path)
                        )
                        
                        # If there's an init_declarator with argument list, add the arguments
                        if init_declarator:
                            argument_list = next((child for child in init_declarator.children if child.type == "argument_list"), None)
                            if argument_list:
                                for arg_node in argument_list.children:
                                    if arg_node.type not in ["(", ")", ",", "argument_list"]:
                                        arg_text = self._get_node_text(arg_node, content)
                                        if arg_text:
                                            call_info.arguments.append(arg_text)
                        
                        method_info.calls.append(call_info)
                        debug(f"Found constructor call: {base_type} with args: {call_info.arguments}", 1)
            elif child.type == "template_function":
                debug(f"Found template_function in method body: {content[child.start_byte:child.end_byte]}", 1)
                # Process the template function node
                self._process_call_expression(child, content, file_path, method_info)
            elif child.type == "new_expression":
                debug(f"Found new_expression in method body: {content[child.start_byte:child.end_byte]}", 1)
                self._process_call_expression(child, content, file_path, method_info)
            elif child.type == "field_expression":
                debug(f"Found field_expression in method body: {content[child.start_byte:child.end_byte]}", 1)
                # Check for pointer access
                operator_node = child.child_by_field_name("operator")
                if operator_node and operator_node.text.decode('utf-8') == "->":
                    debug(f"Found pointer access operator ->", 1)
                    field_node = child.child_by_field_name("field")
                    argument_node = child.child_by_field_name("argument")
                    if field_node and argument_node:
                        # Find the call_expression that contains this field_expression
                        parent_call = None
                        current = child
                        while current and current.type != "call_expression":
                            current = current.parent
                        if current and current.type == "call_expression":
                            parent_call = current

                        call_info = FunctionCall(
                            name=self._get_node_text(field_node, content),
                            object=self._get_node_text(argument_node, content) + "->",
                            location=self._get_location(child, file_path)
                        )

                        # Add arguments from the parent call_expression
                        if parent_call:
                            argument_list = parent_call.child_by_field_name("arguments")
                            if argument_list:
                                for arg_node in argument_list.children:
                                    if arg_node.type not in ["(", ")", ",", "argument_list"]:
                                        arg_text = self._get_node_text(arg_node, content)
                                        if arg_text:
                                            call_info.arguments.append(arg_text)
                                            debug(f"Added argument to pointer call: {arg_text}", 1)

                        method_info.calls.append(call_info)
                        debug(f"Added pointer method call: {call_info.name} (object: {call_info.object}, args: {call_info.arguments})", 1)

        # Recursively process all children
        for child in node.children:
            debug(f"Processing child node type: {child.type} text: {content[child.start_byte:child.end_byte]}", 1)
            self._process_method_body(child, content, file_path, method_info)

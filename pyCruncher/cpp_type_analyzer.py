from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, ForwardRef

class ScopeType(Enum):
    """Type of scope"""
    GLOBAL = "global"
    NAMESPACE = "namespace"
    CLASS = "class"
    FUNCTION = "function"
    BLOCK = "block"

class AccessSpecifier(Enum):
    """Access specifier for class members"""
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"

@dataclass
class Location:
    """Source code location information"""
    file_path: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int

@dataclass
class Scope:
    """Represents a scope in the code"""
    type: ScopeType
    name: str
    parent: Optional['Scope'] = None
    children: List['Scope'] = field(default_factory=list)
    location: Optional[Location] = None
    
    def get_full_name(self) -> str:
        """Get fully qualified scope name"""
        if not self.name:
            return ""
        if self.parent and self.parent.name:
            return f"{self.parent.get_full_name()}::{self.name}"
        return self.name

@dataclass
class MethodInfo:
    """Information about a method"""
    name: str
    return_type: str
    scope: Scope
    location: Optional[Location] = None
    access_specifier: Optional[AccessSpecifier] = None
    is_virtual: bool = False
    is_static: bool = False
    is_const: bool = False

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
    scope: Scope
    is_member: bool = False
    is_static: bool = False
    location: Optional[Location] = None
    access_specifier: Optional[AccessSpecifier] = None

@dataclass
class TypeInfo:
    """Base class for type information"""
    name: str
    scope: Scope
    location: Optional[Location] = None

@dataclass
class ClassInfo(TypeInfo):
    """Information about a C++ class"""
    base_classes: List[str] = field(default_factory=list)
    methods: Dict[str, MethodInfo] = field(default_factory=dict)
    variables: Dict[str, VariableInfo] = field(default_factory=dict)
    access_specifier: AccessSpecifier = AccessSpecifier.PRIVATE

class TypeRegistry:
    """Registry of all known types in the codebase"""
    def __init__(self):
        self.types: Dict[str, TypeInfo] = {}
        self.global_scope = Scope(ScopeType.GLOBAL, "")
        self.current_scope = self.global_scope
        
        # Initialize with basic C++ types
        self._init_basic_types()
    
    def _init_basic_types(self):
        """Initialize registry with basic C++ types"""
        basic_types = [
            "void", "bool", "char", "int", "float", "double",
            "size_t", "int8_t", "uint8_t", "int16_t", "uint16_t",
            "int32_t", "uint32_t", "int64_t", "uint64_t"
        ]
        for type_name in basic_types:
            self.add_type(TypeInfo(type_name, self.global_scope))

    def enter_scope(self, type: ScopeType, name: str, location: Optional[Location] = None) -> Scope:
        """Enter a new scope"""
        scope = Scope(type, name, self.current_scope, location=location)
        self.current_scope.children.append(scope)
        self.current_scope = scope
        return scope
    
    def exit_scope(self) -> None:
        """Exit current scope"""
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent
    
    def add_type(self, type_info: TypeInfo) -> None:
        """Add a type to the registry"""
        self.types[type_info.name] = type_info
    
    def get_type(self, name: str) -> Optional[TypeInfo]:
        """Get a type from the registry"""
        return self.types.get(name)

class TypeCollector:
    """Collects type information from C++ source code using tree-sitter"""
    def __init__(self, verbosity: int = 0):
        self.registry = TypeRegistry()
        self.verbosity = verbosity
        self.current_access = AccessSpecifier.PRIVATE
    
    def _debug(self, level: int, msg: str) -> None:
        """Print debug message if verbosity level is high enough"""
        if self.verbosity >= level:
            indent = "  " * (level - 1) if level > 0 else ""
            print(f"{indent}[TypeCollector] {msg}")
    
    def process_node(self, node, content: bytes, file_path: str = "") -> None:
        """Process a tree-sitter node to collect type information"""
        self._debug(3, f"Processing node type: {node.type}")
        if self.verbosity >= 4:
            self._debug(4, f"Node text: {content[node.start_byte:node.end_byte].decode('utf8')}")
            self._debug(4, f"Children types: {[child.type for child in node.children]}")
        
        # Process all nodes recursively
        if node.type == 'translation_unit':
            for child in node.children:
                self.process_node(child, content, file_path)
        elif node.type == 'namespace_definition':
            self._process_namespace(node, content, file_path)
        elif node.type == 'class_specifier':
            self._process_class(node, content, file_path)
        elif node.type == 'function_definition':
            self._process_function(node, content, file_path)
        elif node.type == 'declaration':
            self._process_declaration(node, content, file_path)
    
    def _process_namespace(self, node, content: bytes, file_path: str) -> None:
        """Process a namespace definition"""
        # Find namespace name
        name = None
        for child in node.children:
            if child.type == 'namespace_identifier':
                name = content[child.start_byte:child.end_byte].decode('utf8')
                break
        
        if not name:
            self._debug(1, f"Warning: Found namespace without name. Node types: {[child.type for child in node.children]}")
            return
        
        self._debug(1, f"Processing namespace: {name}")
        
        # Create location info
        location = Location(
            file_path=file_path,
            start_line=node.start_point[0],
            end_line=node.end_point[0],
            start_byte=node.start_byte,
            end_byte=node.end_byte
        )
        
        # Enter namespace scope
        namespace_scope = self.registry.enter_scope(ScopeType.NAMESPACE, name, location)
        self._debug(2, f"Entered namespace scope: {namespace_scope.get_full_name()}")
        
        # Find and process the namespace body
        for child in node.children:
            if child.type == 'declaration_list':
                self._debug(2, "Processing namespace body")
                for decl in child.children:
                    self.process_node(decl, content, file_path)
            elif child.type not in ['namespace', 'namespace_identifier', '{', '}']:
                self.process_node(child, content, file_path)
        
        self.registry.exit_scope()
        self._debug(2, f"Exited namespace scope")
    
    def _process_class(self, node, content: bytes, file_path: str) -> None:
        """Process a class definition"""
        if self.verbosity >= 2:
            print(f"Processing class at {node.start_point}")

        # Get class name from the first identifier child
        name_node = None
        for child in node.children:
            if child.type == "type_identifier":
                name_node = child
                break
        
        if not name_node:
            if self.verbosity >= 1:
                print("Warning: Class without name found")
            return

        class_name = content[name_node.start_byte:name_node.end_byte].decode('utf8')
        location = Location(file_path, node.start_point[0], node.end_point[0],
                          node.start_byte, node.end_byte)

        # Create class info
        class_info = ClassInfo(
            name=class_name,
            scope=self.registry.current_scope,
            location=location
        )

        # Process base classes
        base_clause = None
        for child in node.children:
            if child.type == "base_class_clause":
                base_clause = child
                break
        
        if base_clause:
            self._process_base_classes(base_clause, content, class_info)

        # Enter class scope and process body
        class_scope = self.registry.enter_scope(ScopeType.CLASS, class_name, location)
        
        # Find class body
        body = None
        for child in node.children:
            if child.type == "field_declaration_list":
                body = child
                break
        
        if body:
            self._process_class_body(body, content, class_info)
        
        # Add class to registry and exit scope
        self.registry.add_type(class_info)
        self.registry.exit_scope()

    def _process_base_classes(self, node, content: bytes, class_info: ClassInfo) -> None:
        """Process base class declarations"""
        if self.verbosity >= 2:
            print(f"Processing base classes at {node.start_point}")
        
        for child in node.children:
            if child.type == "type_identifier":
                base_name = content[child.start_byte:child.end_byte].decode('utf8')
                class_info.base_classes.append(base_name)

    def _process_class_body(self, node, content: bytes, class_info: ClassInfo) -> None:
        """Process class body including methods and variables"""
        if self.verbosity >= 2:
            print(f"Processing class body at {node.start_point}")
            print(f"Node type: {node.type}")
            for child in node.children:
                print(f"Child type: {child.type}")
                for subchild in child.children:
                    print(f"  Subchild type: {subchild.type}")

        current_access = AccessSpecifier.PRIVATE

        def process_field_declaration(field_node, access):
            """Helper to process a field declaration node"""
            if self.verbosity >= 2:
                print(f"Processing field declaration node: {field_node.type}")
                for child in field_node.children:
                    print(f"  Child type: {child.type}")
                    if child.type == "function_declarator":
                        print("    Function declarator children:")
                        for declarator_child in child.children:
                            print(f"      {declarator_child.type}: {content[declarator_child.start_byte:declarator_child.end_byte].decode('utf8')}")

            var_type = None
            # Get type
            for child in field_node.children:
                if child.type == "primitive_type":
                    var_type = content[child.start_byte:child.end_byte].decode('utf8')
                    break

            if not var_type:
                return

            # Check for method or field
            for child in field_node.children:
                if child.type == "function_declarator":
                    # Method declaration
                    # Look for field_identifier in the function_declarator's children
                    for declarator_child in child.children:
                        if declarator_child.type == "field_identifier":
                            method_name = content[declarator_child.start_byte:declarator_child.end_byte].decode('utf8')
                            if self.verbosity >= 2:
                                print(f"Found method: {method_name} with access {access} and type {var_type}")
                            method_info = MethodInfo(
                                name=method_name,
                                return_type=var_type,
                                scope=self.registry.current_scope,
                                access_specifier=access
                            )
                            class_info.methods[method_name] = method_info
                            break
                elif child.type == "field_identifier":
                    # Field declaration
                    var_name = content[child.start_byte:child.end_byte].decode('utf8')
                    if self.verbosity >= 2:
                        print(f"Found field: {var_name} with access {access}")
                    var_info = VariableInfo(
                        name=var_name,
                        type_name=var_type,
                        scope=self.registry.current_scope,
                        is_member=True,
                        access_specifier=access
                    )
                    class_info.variables[var_name] = var_info

        # Process the field declaration list
        for child in node.children:
            if child.type == "access_specifier":
                specifier = content[child.start_byte:child.end_byte].decode('utf8').lower()
                if specifier == "public":
                    current_access = AccessSpecifier.PUBLIC
                elif specifier == "private":
                    current_access = AccessSpecifier.PRIVATE
                elif specifier == "protected":
                    current_access = AccessSpecifier.PROTECTED
            elif child.type == "field_declaration":
                process_field_declaration(child, current_access)
            elif child.type == "field_declaration_list":
                for list_child in child.children:
                    if list_child.type == "field_declaration":
                        process_field_declaration(list_child, current_access)
                    elif list_child.type == "access_specifier":
                        specifier = content[list_child.start_byte:list_child.end_byte].decode('utf8').lower()
                        if specifier == "public":
                            current_access = AccessSpecifier.PUBLIC
                        elif specifier == "private":
                            current_access = AccessSpecifier.PRIVATE
                        elif specifier == "protected":
                            current_access = AccessSpecifier.PROTECTED

    def _process_function(self, node, content: bytes, file_path: str) -> None:
        """Process a function definition"""
        # Implementation will be added in next step
        pass
    
    def _process_declaration(self, node, content: bytes, file_path: str) -> None:
        """Process a variable or type declaration"""
        # Implementation will be added in next step
        pass

import os
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union
from tree_sitter import Parser, Node, Language
from pathlib import Path

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
    fields: List[str] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)

    def add_method(self, method: MethodInfo):
        self.methods.append(method)
        method.parent_class = self

    def add_field(self, field: str):
        if field not in self.fields:
            self.fields.append(field)

    def add_base_class(self, base_class: str):
        if base_class not in self.base_classes:
            self.base_classes.append(base_class)

    def full_name(self) -> str:
        if self.scope:
            return f"{self.scope.full_name()}.{self.name}"
        return self.name

class TypeRegistry:
    """Registry for tracking types and their relationships"""
    def __init__(self):
        self.imports = {}  # filename -> dict of local_name -> module_name or alias
        self.classes = {}  # class_name -> ClassInfo
        self.functions = {}  # module_name.function_name -> FunctionInfo
        self.scopes = {}  # scope_id -> Scope
        self.module_functions = {}  # module_name -> {function_name -> FunctionInfo}

    def add_import(self, file_path: str, module_name: str, alias: str = None):
        """Add an import to the registry"""
        debug(f"Adding import {module_name} (alias: {alias}) to {file_path}", 1)
        filename = os.path.basename(file_path)
        
        if filename not in self.imports:
            self.imports[filename] = {}

        if '.' in module_name:
            # From import: module.item
            base_module, item = module_name.rsplit('.', 1)
            local_name = alias if alias else item
            self.imports[filename][local_name] = item  # Store just the item name
            
            # Also track the base module
            self.imports[filename][base_module] = None
        else:
            # Regular import
            local_name = alias if alias else module_name
            self.imports[filename][local_name] = module_name
            if alias:
                # Store the alias relationship
                self.imports[filename][module_name] = alias

    def get_imports(self, file_name: str) -> Optional[Dict[str, Union[str, None]]]:
        """Get imports for a file, returns dict of local_name -> module_name or alias"""
        filename = os.path.basename(file_name)
        return self.imports.get(filename)

    def resolve_function_call(self, func_name: str, module_name: str = None, file_path: str = None) -> Tuple[Optional[str], Optional[str]]:
        """Resolve a function call to its actual module and function name"""
        if file_path:
            filename = os.path.basename(file_path)
            imports = self.get_imports(filename)
            if imports and func_name in imports:
                module_name = imports[func_name]
                if isinstance(module_name, str):
                    if '.' in module_name:
                        # From import
                        base_module, item = module_name.rsplit('.', 1)
                        return base_module, item
                    else:
                        # Regular import
                        return module_name, func_name
        
        if module_name:
            return module_name, func_name
            
        return None, func_name

    def add_function(self, module_name: str, function_name: str, function_info: 'FunctionInfo'):
        """Add a function to the registry"""
        debug(f"Adding function {module_name}.{function_name} to registry", 1)
        
        # Store with fully qualified name
        full_name = f"{module_name}.{function_name}"
        self.functions[full_name] = function_info
        
        # Store in module functions
        if module_name not in self.module_functions:
            self.module_functions[module_name] = {}
        self.module_functions[module_name][function_name] = function_info

        # Add to global scope
        global_scope = self.get_scope("")
        if global_scope and function_name not in global_scope.functions:
            global_scope.functions[function_name] = function_info
            function_info.scope = global_scope

    def get_function(self, function_name: str, current_module: str = None) -> Optional['FunctionInfo']:
        """Get function information by name"""
        debug(f"Looking up function: {function_name} in module: {current_module}", 1)
        
        # Try fully qualified name first
        if function_name in self.functions:
            return self.functions[function_name]
            
        # Try in module functions
        for module, funcs in self.module_functions.items():
            if function_name in funcs:
                return funcs[function_name]
        
        # Try in global scope
        global_scope = self.get_scope("")
        if global_scope and function_name in global_scope.functions:
            return global_scope.functions[function_name]
        
        return None

    def add_scope(self, scope_id: str, scope: 'Scope'):
        """Add a scope to the registry"""
        debug(f"Adding scope {scope_id} to registry", 1)
        self.scopes[scope_id] = scope

    def get_scope(self, scope_id: str) -> Optional['Scope']:
        """Get scope by id"""
        return self.scopes.get(scope_id)

    def add_class(self, class_name: str, class_info: 'ClassInfo'):
        """Add a class to the registry"""
        debug(f"Adding class {class_name} to registry", 1)
        self.classes[class_name] = class_info
        debug(f"Registry now contains classes: {list(self.classes.keys())}", 1)

    def get_class(self, class_name: str) -> Optional['ClassInfo']:
        """Get class information by name"""
        return self.classes.get(class_name)

    def get_type(self, type_name: str) -> Optional['ClassInfo']:
        """Get type information by name (alias for get_class)"""
        return self.get_class(type_name)

class TypeCollector:
    """Collect type information from Python source files"""
    def __init__(self, parser: Parser, language: Language):
        self.parser = parser
        self.language = language
        self.registry = TypeRegistry()
        global DEBUG_LEVEL
        DEBUG_LEVEL = 0
        setup_logging(DEBUG_LEVEL)
        
        # Initialize global scope
        global_scope = Scope(type=ScopeType.GLOBAL, name="")
        self.registry.add_scope(global_scope.name, global_scope)

    def process_code(self, code: str, file_path: str = "<string>"):
        """Process Python code directly"""
        debug(f"Processing code from {file_path}", 1)
        
        # Parse the code
        tree = self.parser.parse(bytes(code, "utf8"))
        debug(f"Parsed tree: {tree.root_node.sexp()}", 2)

        # Get or create global scope for this file
        global_scope = self.registry.get_scope("")
        if not global_scope:
            global_scope = Scope(type=ScopeType.GLOBAL, name="")
            self.registry.add_scope("", global_scope)

        # First pass: process imports
        for child in tree.root_node.children:
            if child.type == "import_statement":
                self._process_import(child, code, file_path)
            elif child.type == "import_from_statement":
                self._process_from_import(child, code, file_path)

        # Second pass: process functions and classes
        for child in tree.root_node.children:
            if child.type == "function_definition":
                self._process_function(child, code, file_path)
            elif child.type == "class_definition":
                self._process_class(child, code, file_path)

        debug(f"Finished processing code from {file_path}", 1)

    def process_file(self, file_path: str):
        """Process a Python source file"""
        debug(f"Processing file: {file_path}", 1)
        with open(file_path, 'r') as f:
            code = f.read()
            
        tree = self.parser.parse(bytes(code, "utf8"))
        
        # Get just the filename for registry
        filename = Path(file_path).name
        debug(f"Using filename: {filename} for registry", 1)

        # Get or create global scope for this file
        global_scope = self.registry.get_scope("")
        if not global_scope:
            global_scope = Scope(type=ScopeType.GLOBAL, name="")
            self.registry.add_scope("", global_scope)

        # First pass: process imports
        for child in tree.root_node.children:
            if child.type == "import_statement":
                self._process_import(child, code, file_path)
            elif child.type == "import_from_statement":
                self._process_from_import(child, code, file_path)

        # Second pass: process functions and classes
        for child in tree.root_node.children:
            if child.type == "function_definition":
                self._process_function(child, code, file_path)
            elif child.type == "class_definition":
                self._process_class(child, code, file_path)

        debug(f"Finished processing file: {file_path}", 1)

    def _process_node(self, node: Node, content: str, file_path: str):
        """Process a node in the AST"""
        debug(f"Processing node type: {node.type}", 1)
        debug(f"Node structure: {node.sexp()}", 1)
        debug(f"Node text: {self._get_node_text(node, content)}", 1)
        
        if node.type == "module":
            for child in node.children:
                debug(f"Processing module child: {child.type}", 1)
                debug(f"Module child structure: {child.sexp()}", 1)
                debug(f"Module child text: {self._get_node_text(child, content)}", 1)
                self._process_node(child, content, file_path)
        
        elif node.type == "class_definition":
            debug(f"Found class definition in {file_path}", 1)
            debug(f"Class definition structure: {node.sexp()}", 1)
            debug(f"Class definition text: {self._get_node_text(node, content)}", 1)
            self._process_class(node, content, file_path)
            
        elif node.type == "import_statement":
            debug(f"Found import statement in {file_path}: {self._get_node_text(node, content)}", 1)
            self._process_import(node, content, file_path)
            
        elif node.type == "import_from_statement":
            debug(f"Found from import in {file_path}: {self._get_node_text(node, content)}", 1)
            self._process_from_import(node, content, file_path)
            
        elif node.type == "function_definition":
            debug(f"Found function definition in {file_path}: {self._get_node_text(node.child_by_field_name('name'), content)}", 1)
            debug(f"Function definition structure: {node.sexp()}", 1)
            debug(f"Function definition text: {self._get_node_text(node, content)}", 1)
            self._process_function(node, content, file_path)

    def _process_class(self, node: Node, content: str, file_path: str):
        """Process a class definition"""
        # Get class name
        class_name = None
        for child in node.children:
            if child.type == "identifier":
                class_name = self._get_node_text(child, content)
                break

        if not class_name:
            debug(f"Could not find class name in {file_path}", 1)
            return

        debug(f"Processing class: {class_name} in {os.path.basename(file_path)}", 1)

        # Create class info
        class_info = ClassInfo(
            name=class_name,
            location=self._get_location(node, file_path)
        )
        self.registry.add_class(class_name, class_info)

        # Process base classes
        bases_node = None
        for child in node.children:
            if child.type == "argument_list":
                bases_node = child
                break

        if bases_node:
            file_imports = self.registry.get_imports(os.path.basename(file_path)) or {}
            debug(f"Available imports for {os.path.basename(file_path)}: {file_imports}", 1)
            
            for base in bases_node.children:
                if base.type == "identifier":
                    base_name = self._get_node_text(base, content)
                    debug(f"Found base class: {base_name}", 1)
                    
                    # Check if the base class name is an imported name
                    if base_name in file_imports:
                        imported_name = file_imports[base_name]
                        debug(f"Base class {base_name} is imported as {imported_name}", 1)
                        if imported_name is not None:
                            base_name = imported_name.split('.')[-1]
                    
                    debug(f"Final base class name: {base_name}", 1)
                    class_info.add_base_class(base_name)
                elif base.type == "attribute":
                    # Handle module.Class style inheritance
                    base_name = self._get_node_text(base, content)
                    # Extract just the class name from module.Class
                    base_name = base_name.split('.')[-1]
                    class_info.add_base_class(base_name)

        # Process class body
        body_node = None
        for child in node.children:
            if child.type == "block":
                body_node = child
                break

        if body_node:
            for child in body_node.children:
                if child.type == "function_definition":
                    self._process_method(child, content, class_info, file_path)
                elif child.type == "expression_statement":
                    # This could be a field assignment
                    assignment = child.children[0] if child.children else None
                    if assignment and assignment.type == "assignment":
                        left = assignment.children[0] if assignment.children else None
                        if left and left.type == "identifier":
                            field_name = self._get_node_text(left, content)
                            class_info.add_field(field_name)

    def _process_method(self, node: Node, content: str, class_info: ClassInfo, file_path: str):
        """Process a method definition"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        method_name = self._get_node_text(name_node, content)
        debug(f"Processing method {method_name} in class {class_info.name}", 1)

        # Create method info
        method_info = MethodInfo(
            name=method_name,
            parent_class=class_info
        )

        # Process method body for function calls
        body = node.child_by_field_name("body")
        if body:
            debug(f"Processing body of method {method_name}", 1)
            
            # Use tree-sitter query to find all call expressions
            query_str = """
            (call
              function: (_) @func
              arguments: (argument_list) @args)
            """
            query = self.language.query(query_str)
            captures = query.captures(body)
            
            for capture in captures:
                node, capture_name = capture
                if capture_name == "func":
                    debug(f"Found function call node: {node.type}", 1)
                    debug(f"Function call text: {self._get_node_text(node, content)}", 1)
                    
                    if node.type == "attribute":
                        # This is a method call (obj.method())
                        value_node = node.child_by_field_name("object")
                        attr_node = node.child_by_field_name("attribute")
                        if value_node and attr_node:
                            obj_name = self._get_node_text(value_node, content)
                            method_name = self._get_node_text(attr_node, content)
                            debug(f"Found method call: {obj_name}.{method_name}", 1)
                            
                            call = FunctionCall(
                                name=method_name,
                                object=obj_name,
                                location=self._get_location(node.parent, file_path),
                                caller=method_info
                            )
                            method_info.calls.append(call)
                    else:
                        # This is a regular function call
                        func_name = self._get_node_text(node, content)
                        debug(f"Found function call: {func_name}", 1)
                        
                        # Check if function is imported
                        filename = os.path.basename(file_path)
                        imports = self.registry.get_imports(filename)
                        if imports and func_name in imports:
                            # Get the actual function name from the import
                            actual_func_name = imports[func_name]
                            if actual_func_name:
                                func_name = actual_func_name
                                debug(f"Found imported function {func_name}", 1)
                        
                        call = FunctionCall(
                            name=func_name,
                            location=self._get_location(node.parent, file_path),
                            caller=method_info
                        )
                        method_info.calls.append(call)

        class_info.methods.append(method_info)

    def _process_function(self, node: Node, content: str, file_path: str):
        """Process a function definition node"""
        debug(f"Processing function node: {node.sexp()}", 1)
        
        # Get function name
        name_node = node.child_by_field_name("name")
        if name_node:
            func_name = content[name_node.start_byte:name_node.end_byte]
            debug(f"Found function name: {func_name}", 1)

            # Get current module name from file path
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            debug(f"Module name: {module_name}", 1)

            # Get global scope
            global_scope = self.registry.get_scope("")
            if not global_scope:
                global_scope = Scope(type=ScopeType.GLOBAL, name="")
                self.registry.add_scope("", global_scope)

            # Create function info
            location = self._get_location(node, file_path)
            func_info = FunctionInfo(
                name=func_name,
                scope=global_scope,
                location=location
            )
            
            # Add to global scope first
            global_scope.functions[func_name] = func_info

            # Process function body for calls
            body = node.child_by_field_name("body")
            if body:
                # Use tree-sitter query to find all call expressions
                query_str = """
                (call
                  function: (_) @func
                  arguments: (argument_list) @args)
                """
                query = self.language.query(query_str)
                captures = query.captures(body)
                
                for capture in captures:
                    node, capture_name = capture
                    if capture_name == "func":
                        debug(f"Found function call node: {node.type}", 1)
                        debug(f"Function call text: {self._get_node_text(node, content)}", 1)
                        
                        if node.type == "attribute":
                            # This is a method call (obj.method())
                            value_node = node.child_by_field_name("object")
                            attr_node = node.child_by_field_name("attribute")
                            if value_node and attr_node:
                                obj_name = self._get_node_text(value_node, content)
                                method_name = self._get_node_text(attr_node, content)
                                debug(f"Found method call: {obj_name}.{method_name}", 1)
                                
                                # Resolve the actual module and function name
                                module, func = self.registry.resolve_function_call(obj_name, None, file_path)
                                
                                call = FunctionCall(
                                    name=method_name,
                                    object=obj_name,
                                    location=self._get_location(node.parent, file_path),
                                    caller=func_info
                                )
                                func_info.calls.append(call)
                        else:
                            # This is a regular function call
                            func_name = self._get_node_text(node, content)
                            debug(f"Found function call: {func_name}", 1)
                            
                            # Resolve the actual module and function name
                            module, func = self.registry.resolve_function_call(func_name, module_name, file_path)
                            
                            call = FunctionCall(
                                name=func,
                                object=module,
                                location=self._get_location(node.parent, file_path),
                                caller=func_info
                            )
                            func_info.calls.append(call)

            # Add function to registry with module name
            self.registry.add_function(module_name, func_name, func_info)

    def _process_from_import(self, node: Node, content: str, file_path: str):
        """Process a from import statement"""
        debug(f"Processing from import statement: {self._get_node_text(node, content)}", 2)
        
        # Get just the filename for registry
        filename = Path(file_path).name
        debug(f"Using filename: {filename} for registry", 1)
        
        # Get module name
        module_node = node.child_by_field_name("module_name")
        if not module_node:
            debug(f"No module_name found in from import", 1)
            return
        
        module_name = self._get_node_text(module_node, content)
        debug(f"Found module name: {module_name}", 2)
        
        # Get global scope
        global_scope = self.registry.get_scope("")
        if not global_scope:
            debug(f"No global scope found for {filename}", 1)
            return
        
        # Process imported names
        for import_node in node.children:
            if import_node.type == "aliased_import":
                # Handle "from module import name as alias"
                name_node = import_node.child_by_field_name("name")
                alias_node = import_node.child_by_field_name("alias")
                if name_node:
                    name = self._get_node_text(name_node, content)
                    alias = self._get_node_text(alias_node, content) if alias_node else None
                    debug(f"Found aliased from import {name} as {alias} from {module_name}", 1)
                    # Register the import with module prefix
                    self.registry.add_import(filename, f"{module_name}.{name}", alias or name)
            elif import_node.type == "identifier":
                # Handle "from module import name"
                name = self._get_node_text(import_node, content)
                debug(f"Found from import {name} from {module_name}", 1)
                # Register the import with module prefix
                self.registry.add_import(filename, f"{module_name}.{name}", name)
            elif import_node.type == "dotted_name":
                # Handle "from module import submodule"
                name = self._get_node_text(import_node, content)
                debug(f"Found from import {name} from {module_name}", 1)
                # Register the import with module prefix
                self.registry.add_import(filename, f"{module_name}.{name}", name)

    def _process_import(self, node: Node, content: str, file_path: str):
        """Process an import statement"""
        debug(f"Processing import statement: {self._get_node_text(node, content)}", 2)
        
        # Get just the filename for registry
        filename = Path(file_path).name
        debug(f"Using filename: {filename} for registry", 1)
        
        # Find all import names (handles multiple imports in one statement)
        for import_node in node.children:
            if import_node.type == "aliased_import":
                # Handle "import module as alias"
                name_node = import_node.child_by_field_name("name")
                alias_node = import_node.child_by_field_name("alias")
                if name_node:
                    module_name = self._get_node_text(name_node, content)
                    alias = self._get_node_text(alias_node, content) if alias_node else None
                    debug(f"Found aliased import {module_name} as {alias}", 1)
                    self.registry.add_import(filename, module_name, alias)
            elif import_node.type == "dotted_name":
                # Handle "import module"
                module_name = self._get_node_text(import_node, content)
                alias = None
                
                # Check for "as alias" after the dotted name
                next_node = import_node.next_sibling
                if next_node and next_node.type == "as":
                    alias_node = next_node.next_sibling
                    if alias_node and alias_node.type == "identifier":
                        alias = self._get_node_text(alias_node, content)
                
                debug(f"Found import {module_name} with alias {alias}", 1)
                self.registry.add_import(filename, module_name, alias)

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

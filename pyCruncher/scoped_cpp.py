import re
import sys

# Pre-compile patterns as before
COMMENT_PATTERN     = re.compile(r'//.*?$|/\*.*?\*/', re.MULTILINE | re.DOTALL)
# Common C++ function modifiers that can appear between ) and { or ;
FUNCTION_MODIFIERS = r'''(?:\s*(?:const|override|final|noexcept|volatile|mutable|throw\s*\([^)]*\)|\[\[.*?\]\]))*'''  # zero or more modifiers

# Function pattern explained:
#  1. ([a-zA-Z0-9_*]+)     - Return type (letters, numbers, underscore, pointer)
#  2. \s+                  - Whitespace between return type and name
#  3. ([a-zA-Z0-9_]+)      - Function name
#  4. \s*\(               - Opening parenthesis with optional whitespace
#  5. ([^{}()]*?)          - Function arguments (anything except braces, non-greedy)
#  6. \)                   - Closing parenthesis
#  7. {modifiers}          - Optional function modifiers (const, override, etc)
#  8. \s*[{{;]             - Opening brace or semicolon
FUNCTION_PATTERN = re.compile(
    r'''([a-zA-Z0-9_*]+)\s+([a-zA-Z0-9_]+)\s*\(\s*([^{}()]*?)\)%(modifiers)s\s*[{;]''' % {
        'modifiers': FUNCTION_MODIFIERS
    }, 
    re.VERBOSE | re.MULTILINE | re.DOTALL
)
SCOPE_START_PATTERN = re.compile(r'\b(class|struct|namespace)\s+([a-zA-Z0-9_]+)')

CPP_KEYWORDS = {
    'if', 'else', 'while', 'for', 'switch', 'case', 'return',
    'break', 'continue', 'do', 'sizeof', 'typedef'
}

def is_not_function(return_type, name):
    return (  return_type.strip() in CPP_KEYWORDS 
           or name       .strip() in CPP_KEYWORDS)

class Scope:
    def __init__(self, type_, name, start_pos):
        self.type = type_
        self.name = name
        self.start_pos = start_pos

def print_function_header( fh ):
    if fh['scope']:
        print(f"{fh['return_type']} {fh['scope']}::{fh['name']}({fh['args']})")
    else:
        print(f"{fh['return_type']} {fh['name']}({fh['args']})")

def analyze_scopes_and_functions(content, bPrint=False ):
    # TODO: we should list all function-calls from each function, to be able to reconstruct the call graph ( dependency graph )
    scope_stack = []
    functions = []
    
    pos = 0
    while pos < len(content):
        if content[pos] == '{':
            # Look back to determine scope type
            look_back = content[max(0, pos-100):pos]
            scope_match = SCOPE_START_PATTERN.search(look_back)
            
            if scope_match:
                scope_type, scope_name = scope_match.groups()
                scope = Scope(scope_type, scope_name, pos)
                if bPrint: print( (" "*4*len(scope_stack))+scope.type+" "+scope.name+"{" ) 
            else:
                scope = Scope('block', '', pos)
            
            scope_stack.append(scope)  
        elif content[pos] == '}':
            if scope_stack:
                if bPrint and scope_stack[-1].type != 'block':
                    print( (" "*4*(len(scope_stack)-1))+"}")
                scope_stack.pop()

        # Check for function matches at current position
        func_match = FUNCTION_PATTERN.match(content, pos)
        if func_match:
            return_type, func_name, args = func_match.groups()
            scope_path = '::'.join(s.name for s in scope_stack if s.type in ('class', 'struct', 'namespace') and s.name)
            #full_name = f"{scope_path}::{func_name}" if scope_path else func_name
            if not is_not_function(return_type, func_name):
                #print(f"{scope_path}::{func_name}({args})")
                if bPrint: print( (" "*4*len(scope_stack)) + f"{return_type} {func_name}({args})")
                functions.append({
                    'name': func_name,
                    'return_type': return_type,
                    'args': args,
                    'scope': scope_path
                })
            pos = func_match.end()-1
        else:
            pos += 1
        
        
    return functions

def analyze_scopes_and_variables(content, bPrint=False):
    """
    Analyze the C++ code in 'content' to extract variable declarations that are either class/struct properties or global/namespace variables.
    Local variables inside functions (or any block not associated with class/namespace) are ignored.

    Returns a list of dictionaries with keys: 'name', 'type', and 'scope'.
    """
    variables = []
    scope_stack = []
    pos = 0
    last_pos = 0
    while pos < len(content):
        char = content[pos]
        if char == '{':
            # Look back to see if this brace starts a class/struct/namespace scope
            look_back = content[max(0, pos-100):pos]
            scope_match = SCOPE_START_PATTERN.search(look_back)
            if scope_match:
                scope_type, scope_name = scope_match.groups()
                scope_stack.append({'type': scope_type, 'name': scope_name})
                if bPrint:
                    print("    " * (len(scope_stack)-1) + f"{scope_type} {scope_name} {{")
            else:
                # Treat as a generic block, likely a function body
                scope_stack.append({'type': 'block', 'name': ''})
            pos += 1
            last_pos = pos
            continue
        elif char == '}':
            if scope_stack:
                if bPrint and scope_stack[-1]['type'] != 'block':
                    print("    " * (len(scope_stack)-1) + "}")
                scope_stack.pop()
            pos += 1
            last_pos = pos
            continue
        elif char == ';':
            # Extract statement between last_pos and current pos (inclusive)
            statement = content[last_pos:pos+1].strip()
            # Determine the current scope:
            current_scope = scope_stack[-1]['type'] if scope_stack else 'global'
            # If allowed scope (global or class/struct/namespace), consider it
            if current_scope in ['global', 'class', 'struct', 'namespace']:
                # Heuristic: skip statements with '(' to avoid function calls and other non-declarations
                if '(' not in statement:
                    import re
                    m = re.match(r'^(?P<var_type>[a-zA-Z_][a-zA-Z0-9_:<>\s*&]+?)\s+(?P<var_name>[a-zA-Z_][a-zA-Z0-9_]*)', statement)
                    if m:
                        scope_path = '::'.join(s['name'] for s in scope_stack if s['type'] in ['class','struct','namespace'])
                        variables.append({
                            'name': m.group('var_name'),
                            'type': m.group('var_type').strip(),
                            'scope': scope_path
                        })
                        if bPrint:
                            if scope_path:
                                print(f"{m.group('var_type').strip()} {scope_path}::{m.group('var_name')}")
                            else:
                                print(f"{m.group('var_type').strip()} {m.group('var_name')}")
            pos += 1
            last_pos = pos
            continue
        else:
            pos += 1
    return variables


def print_variable_declaration(var):
    """Print a variable declaration in the format: type scope::name (if scope exists) or type name."""
    if var['scope']:
        print(f"{var['type']} {var['scope']}::{var['name']}")
    else:
        print(f"{var['type']} {var['name']}")


def analyze_inheritance(content, bPrint=False):
    """
    Analyze the C++ code in 'content' to extract parent classes for class and struct definitions.
    Returns a list of dictionaries with keys: 'class' and 'parents' (a list of parent classes).
    """
    inheritances = []
    # Pattern to capture inheritance: e.g. class Derived : public Base, protected Other
    inheritance_pattern = re.compile(r'\b(class|struct)\s+(?P<class_name>[a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?P<parents>[^\{]+)\{', re.MULTILINE)
    for match in inheritance_pattern.finditer(content):
        class_name = match.group('class_name')
        parents_str = match.group('parents').strip()
        # Split by comma and remove access specifiers
        parents = []
        for parent in parents_str.split(','):
            # Remove possible access specifiers (public, protected, private) and extra spaces
            parent_clean = re.sub(r'\b(public|protected|private)\b', '', parent).strip()
            if parent_clean:
                parents.append(parent_clean)
        inheritances.append({
            'class': class_name,
            'parents': parents
        })
        if bPrint:
            print(f"Class {class_name} inherits from: {', '.join(parents)}")
    return inheritances


def analyze_includes(content, bPrint=False):
    """
    Analyze the C++ code in 'content' to extract all #include statements.
    Returns a list of include strings.
    """
    includes = []
    include_pattern = re.compile(r'^\s*#include\s+([<"][^>"]+[>"])', re.MULTILINE)
    for match in include_pattern.finditer(content):
        include_file = match.group(1)
        includes.append(include_file)
        if bPrint:
            print(f"Include: {include_file}")
    return includes


def format_function(func, show_args=True, show_return_type=True, show_scope=True):
    """Format a function entry based on the given options."""
    parts = []
    if show_return_type:
        parts.append(func['return_type'])
    if show_scope and func['scope']:
        parts.append(f"{func['scope']}::")
    parts.append(func['name'])
    if show_args:
        parts.append(f"({func['args']})" if func['args'] else "()")
    return ' '.join(parts)


def format_variable(var, show_type=True, type_after_name=True):
    """Format a variable entry based on the given options."""
    name_part = var['name']
    # Don't include scope for class members - it's already shown in the class section
    if var['scope'] and '::' not in var['scope']:
        name_part = f"{var['scope']}::{name_part}"
    
    if not show_type:
        return f"`{name_part}`"
    elif type_after_name:
        return f"`{name_part}`:`{var['type']}`"
    else:
        return f"`{var['type']} {name_part}`"


def generate_markdown_documentation(file_name, includes, functions, variables, inheritances, saveToFile=None,
                                show_args=True, show_return_type=True, show_scope=True,
                                show_var_type=True, var_type_after_name=True,
                                desc_str="[short description what is the purpose]", 
                                class_desc="[Replace this with: Description what is the purpose of the class, what its role in the bigger context]",
                                file_desc="[Replace this with: Description what is the purpose of this file, what its role in the project]",
                            ):
    """
    Generate markdown documentation from the analysis results.
    Returns a string containing the markdown content.
    
    Args:
        file_name: Name of the file being documented
        file_desc: Brief description of the file's purpose
        includes: List of include statements
        functions: List of function definitions
        variables: List of variable declarations
        inheritances: List of class inheritance information
        show_args: Whether to show function arguments
        show_return_type: Whether to show function return types
        show_scope: Whether to show namespace/class scope
        show_var_type: Whether to show variable types
        var_type_after_name: Whether to show type after variable name (True) or before (False)
    """
    md = []
    
    # File header
    md.append(f"# {file_name}\n")
    md.append(f"\n{file_desc}\n")
    
    # Includes section
    if includes:
        md.append("## Includes\n")
        for inc in includes:
            inc = inc.replace("\"", "`")
            #print(inc)
            md.append(f"- {inc}")
        md.append("\n")

    md.append("---\n")
    
    # Create dictionaries for organizing members by class
    class_members = {}
    free_functions = []
    free_variables = []
    
    # First, initialize class_members from inheritance info
    for inh in inheritances:
        class_name = inh['class']
        if class_name not in class_members:
            class_members[class_name] = {'methods': [], 'properties': [], 'parents': inh['parents']}
    
    # Organize functions by class
    for func in functions:
        if func['scope']:
            parts = func['scope'].split('::')
            class_name = parts[0]
            if class_name not in class_members:
                class_members[class_name] = {'methods': [], 'properties': [], 'parents': []}
            # Remove class name from scope for class methods
            func = func.copy()
            func['scope'] = '::'.join(parts[1:]) if len(parts) > 1 else ''
            class_members[class_name]['methods'].append(func)
        else:
            free_functions.append(func)
    
    # Organize variables by class
    for var in variables:
        if var['scope']:
            parts = var['scope'].split('::')
            class_name = parts[0]
            if class_name not in class_members:
                class_members[class_name] = {'methods': [], 'properties': [], 'parents': []}
            # For nested classes, use the full scope as class name
            if len(parts) > 1:
                class_name = '::'.join(parts[:-1])
                if class_name not in class_members:
                    class_members[class_name] = {'methods': [], 'properties': [], 'parents': []}
            # Remove all class/namespace scopes for properties
            var = var.copy()
            var['scope'] = ''
            class_members[parts[0]]['properties'].append(var)
        else:
            free_variables.append(var)
    
    # Free constants and variables section
    if free_variables:
        md.append("## Free constants and variables\n")
        for var in free_variables:
            md.append(f"- {format_variable(var, show_var_type, var_type_after_name)} - {desc_str}")
        md.append("\n")
    
    # Free functions section
    if free_functions:
        md.append("## Free functions\n")
        for func in free_functions:
            md.append(f"- `{format_function(func, show_args, show_return_type, show_scope)}` - {desc_str}")
        md.append("\n")
    
    # Types section
    if class_members:
        md.append("---\n")
        md.append("## Types (classes and structs)\n")
        for class_name, members in class_members.items():
            md.append(f"### class `{class_name}`\n")
            md.append(f"\n{class_desc}\n")
            
            # Add inheritance information
            if members['parents']:
                md.append("**Inheritance**\n")
                md.append(f"- {', '.join(members['parents'])}\n")
            
            if members['properties']:
                md.append("#### properties\n")
                for var in members['properties']:
                    md.append(f"- {format_variable(var, show_var_type, var_type_after_name)} - {desc_str}")
                md.append("\n")
            
            if members['methods']:
                md.append("#### methods\n")
                for func in members['methods']:
                    md.append(f"- `{format_function(func, show_args, show_return_type, show_scope)}` - {desc_str}")
                md.append("\n")
    
    if saveToFile:
        print( f"generate_markdown_documentation() saving documentation to {saveToFile}" )
        with open(saveToFile, 'w') as f:
            f.write('\n'.join(md))

    return '\n'.join(md)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python function_header_extractor.py <cpp_file>")
        exit()
    with open(sys.argv[1], 'r') as f: content = f.read()
    content   = COMMENT_PATTERN.sub('', content)
    functions = analyze_scopes_and_functions(content, True)
    variables = analyze_scopes_and_variables(content, True)
    inheritances = analyze_inheritance(content, True)
    includes = analyze_includes(content, True)

    print("\n ============ Functions =========== \n")
    for f in functions:
        print_function_header(f)

    print("\n ============ Variables =========== \n")
    for v in variables:
        print_variable_declaration(v)

    print("\n ============ Inheritance =========== \n")
    for inh in inheritances:
        print(f"Class {inh['class']} inherits from: {', '.join(inh['parents'])}")

    print("\n ============ Includes =========== \n")
    for inc in includes:
        print(f"#include {inc}")

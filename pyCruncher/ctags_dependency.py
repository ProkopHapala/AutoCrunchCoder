import re
from collections import defaultdict
import subprocess
import json
import time
#import networkx as nx
import traceback
import os

class_file           = 'tags_classes.log'
method_file          = 'tags_methods.log'
free_function_file   = 'tags_free_functions.log'
global_variable_file = 'tags_global_variables.log'

class FunctionInfo:
    def __init__(self):
        self.name = None          # Function name
        self.start_line = None    # Line where function starts
        self.end_line = None      # Line where function ends
        self.file_path = None     # File containing the function
        self.class_name = None    # Parent class (None for free functions)
        self.namespace = None     # Namespace information
        self.signature = None     # Function signature
        self.body = None          # Function body text
        self.calls = []           # List of functions/methods called
        self.is_method = False    # Whether this is a method
        self.is_static = False    # Whether this is a static method

    def get_qualified_name(self):
        """Get fully qualified name using appropriate separator"""
        parts = []
        if self.namespace:
            parts.append(self.namespace)
        if self.class_name:
            parts.append(self.class_name)
        if self.name:
            parts.append(self.name)
        
        # Use appropriate separator based on language
        if self.file_path.endswith('.py'):
            return '.'.join(parts)
        else:
            return '::'.join(parts)

    def __str__(self):
        return f"{self.name} ({self.file_path}:{self.start_line}-{self.end_line})"

def run_ctags(input_path, output_file):
    """Run ctags on input path and generate JSON output"""
    import subprocess
    
    # Use only supported flags
    cmd = [
        'ctags',
        '-R',
        '--languages=C++,Python',
        '--output-format=json',
        '--fields=+niKe',  # name, line, kind, extras
        '--extras=+q',     # qualified names
        '--excmd=number',
        '-o', output_file,
        input_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"ctags completed successfully, output written to: {output_file}")
            return True
        else:
            print(f"ctags failed with error: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running ctags: {str(e)}")
        return False

def parse_ctags_line(line):
    parts = line.split('\t')
    if len(parts) < 4:
        return None

    tag_name = parts[0]
    file_name = parts[1]
    tag_kind = parts[3].strip()  # Get the type of the tag (e.g., class, function, variable)

    return tag_name, file_name, tag_kind

def print_file_dict(files_dict, end=None):
    for k,v in files_dict.items():
        print("\nfile: ", k)
        print('-- classes')
        for m in v['classes'  ]: print("    ", m, end=end)
        if end is not None: print()
        print('-- functions')
        for f in v['functions']: print("    ", f, end=end)
        if end is not None: print()
        print('-- globals')
        for g in v['globals'  ]: print("    ", g, end=end)
        if end is not None: print()

def print_class_dict(classes_dict, end=None):
    for k,v in classes_dict.items():
        print("\nclass: ", k)
        print("-- Methods:");
        for m in v['methods'   ]: print("   ", m, end=end)
        if end is not None: print()
        print("-- properties:");
        for p in v['properties']: print("   ", p, end=end)
        if end is not None: print()

def process_classes( class_lines, base_path, classes={} ):
    for entry in class_lines:
        #entry = json.loads(line)
        kind = entry.get('kind')
        name = entry.get('name')
        name_ = name.split("::")[-1] 
        path = entry.get('path')
        path_ = path[len(base_path):] 
        scope=entry.get('scope')
        scopeK= entry.get('scopeKind')
        inherits=entry.get('inherits')
        il = entry.get('line')
    
        id = (name_, path_)   # unique identifier
        rec={ "line":il, "kind":kind, "scope":scope, 'scopeKind':scopeK, 'inherits':inherits, "properties":{}, "methods":{} }
        if name_ in classes:
            classes[name_][id] = rec 
        else:
            classes[name_] = {id: rec }
    return classes

def addToClass( name, rec, cls_name, fname, classes, name_spaces, what='properties' ):
    if cls_name in name_spaces:
        print("WARNING: addToClass(",name,") ...  `", cls_name,"` is namespace not class" )
        return
    if cls_name not in classes:
        print("WARNING: addToClass(",name,") ... `", cls_name,"` is not a known classes" )
        return
    cls    = classes[cls_name]
    cls_id = (cls_name, fname )
    if cls_id in cls:
        cls_ = cls[cls_id]
    else:
        cls_id_h = (cls_name, fname.replace('.cpp', '.h'))
        if cls_id_h in cls:
            cls_ = cls[cls_id_h]
        else:
            print("WARNING: addToClass(",name,") ...\n    ", cls_id," not in classes[", cls_name,"]  , keys are:" )
            for k in cls.keys():
                print("    ", k)
            return
    cls_what = cls_[what]   # 'properties' or 'methods'
    cls_what[name] = rec

def printDict(dct, pre=""):
    #print("-----",pre,"printDict")
    ind=pre+"   "
    for k,v in dct.items():
        if isinstance(v, dict):
            print(ind,k, ":")
            printDict(v, ind)
        elif isinstance(v, list) or isinstance(v, set):
            print(ind,k, ":")
            for vv in v:
                print(ind+ind, vv)
        else:
            print(ind, k,":", v )

def process_members( member_lines, base_path, classes, name_spaces, members={} ):
    for entry in member_lines:
        #entry = json.loads(line)
        kind = entry.get('kind')
        name = entry.get('name')
        name_ = name.split("::")[-1] 
        path = entry.get('path')
        path_ = path[len(base_path):] 
        scope=entry.get('scope')
        #scope_=scope.split("::")
        scope_ = None
        for s in scope.split("::"):  # take last non-anonymous scope
            if "__anon" in s: continue
            scope_ = s
        scopeK= entry.get('scopeKind')
        typeref=entry.get('typeref')
        type=typeref.split(":")[-1]
        il = entry.get('line')
        #rec={ 'type':type, "line":il }
        rec=( type, il )
        if (scopeK == 'class' or scopeK == 'struct') and (scope_ is not None):
            try:
                addToClass( name_, rec, scope_, path_, classes, name_spaces )
            except Exception as e:
                printDict( entry )
                print( "excpetion: ", e )
                exit()
    return members

def process_signature(signature):
    cleaned_signature = re.sub(r'[&*]|const', '', signature)             # Remove pointers, references, and 'const'
    cleaned_signature = re.sub(r'\s+', ' ', cleaned_signature.strip())   # Remove extra spaces    
    cleaned_signature = cleaned_signature.strip('()')                    # Remove parentheses from the signature
    params = cleaned_signature.split(',')                                  # Split by comma to get each parameter
    result = []
    for param in params:               # Extract type and name pairs
        parts = param.rsplit(' ', 1)   # Split by last space to separate type and name
        if len(parts) == 2:
            type_, name_ = parts
            result.append((name_.strip(),type_.strip()))
    return result

def process_functions(function_lines, base_path, classes, name_spaces, functions={}):
    
    free_functions = {}

    for entry in function_lines:
        kind = entry.get('kind')
        name = entry.get('name')
        name_ = name.split("::")[-1]
        path = entry.get('path')
        path_ = path[len(base_path):]

        typeref = entry.get('typeref')
        return_type = typeref.split(":")[-1] if typeref else None
        signature = entry.get('signature')

        signature_ = process_signature(signature)

        il = entry.get('line')
        rec = {
            'return_type': return_type,
            'signature': signature_,
            'line': il
        }

        scope = entry.get('scope')

        if scope is not None:   # free function
            scope_ = None
            for s in scope.split("::"):
                if "__anon" in s: continue
                scope_ = s
            scopeK = entry.get('scopeKind')
            
            if (scopeK == 'class' or scopeK == 'struct') and (scope_ is not None):
                try:
                    addToClass(name_, rec, scope_, path_, classes, name_spaces, what='methods')
                except Exception as e:
                    print("")
                    print("Exception in process_functions:")
                    printDict( entry )
                    print(f"Error: {e}")
                    traceback.print_exc()
        else:# Handle free functions
            if name_ not in free_functions:
                free_functions[name_] = {}
            free_functions[name_][path_] = rec
    
    return free_functions

def process_ctags_json(json_file, base_path ):
    #kinds = set()
    kinds = {'class', 'union', 'member', 'macro', 'header', 'variable', 'namespace', 'enum', 'enumerator', 'typedef', 'struct', 'function'}

    #with open(json_file, 'r') as f: lines = [json.loads(line) for line in f if line.startswith('{"_type": "tag"')]  # Filter only relevant tags

    classes={ }

    class_lines    = []
    function_lines = []
    member_lines   = [] 
    name_spaces    = {}
    with open(json_file, 'r') as f:
        for i,line in enumerate(f):
            if line.startswith('{"_type": "tag"'):
                entry = json.loads(line)
                name = entry.get('name')
                if "__anon" in name: continue
                kind = entry.get('kind')
                if kind=='function':
                    function_lines.append(entry)
                elif kind=='member':
                    member_lines.append(entry)
                elif (kind=='class') or (kind=='struct'):
                    class_lines.append(entry)
                elif kind=='namespace':
                    name_spaces[name] = entry

    for k,v in name_spaces.items(): print( "name_space ", k ) 

    classes = process_classes( class_lines, base_path )
    process_members( member_lines, base_path, classes, name_spaces)
    free_functions = process_functions(function_lines, base_path, classes, name_spaces)

    for name,cls in classes.items():
        for id,rec in cls.items():
            print( name, id )
            printDict( rec )
            # for k,v in rec.items():
            #     print( "    ", k,":", v )

    print("kinds: ", kinds)


def process_ctags_json_by_files_2(json_file, base_path):
  """Process ctags JSON file and organize entries by files"""
  files_dict = {}  # Main dictionary organized by files
  name_spaces = {} # Keep track of namespaces
  
  # First pass: collect all entries
  with open(json_file, 'r') as f:
      for line in f:
          if line.startswith('{"_type": "tag"'):
              entry = json.loads(line)
              name = entry.get('name')
              if "__anon" in name: 
                  continue
                  
              kind = entry.get('kind')
              path = entry.get('path')
              rel_path = path[len(base_path):]  # relative path
              
              # Initialize file entry if not exists
              if rel_path not in files_dict:
                  files_dict[rel_path] = {
                      'classes': {},      # classes defined in this file
                      'methods': {},      # methods defined in this file
                      'free_functions': {},  # free functions defined in this file
                      'members': {},         # class members defined in this file
                  }
              
              # Process based on kind
              if kind == 'namespace':
                  name_spaces[name] = entry
                  
              elif kind in ['class', 'struct']:
                  # Process class directly here instead of using process_classes
                  class_info = {
                      'line': entry.get('line'),
                      'kind': kind,
                      'scope': entry.get('scope'),
                      'scopeKind': entry.get('scopeKind'),
                      'inherits': entry.get('inherits'),
                      'properties': {},
                      'methods': {}
                  }
                  # Use the full name (including namespace) as the key
                  files_dict[rel_path]['classes'][name] = class_info
                  
              elif kind == 'function':
                  scope = entry.get('scope')
                  scopeK = entry.get('scopeKind')
                  
                  # Process function info
                  func_info = {
                      'line': entry.get('line'),
                      'signature': process_signature(entry.get('signature', '')),
                      'return_type': entry.get('typeref', '').split(":")[-1] if entry.get('typeref') else None,
                      'name': name
                  }
                  
                  if scope and (scopeK == 'class' or scopeK == 'struct'):
                      # This is a class method
                      files_dict[rel_path]['methods'][f"{scope}::{name}"] = func_info
                  else:
                      # This is a free function
                      files_dict[rel_path]['free_functions'][name] = func_info
                      
              elif kind == 'member':
                  files_dict[rel_path]['members'][name] = {
                      'line': entry.get('line'),
                      'type': entry.get('typeref', '').split(":")[-1] if entry.get('typeref') else None
                  }
  
  return files_dict

def process_ctags_json_by_files(json_file, base_path):
  """Process ctags JSON file and organize entries by files"""
  files_dict = {}  # Main dictionary organized by files
  classes = {}     # Keep track of classes for method association
  name_spaces = {} # Keep track of namespaces
  
  # First pass: collect all entries
  with open(json_file, 'r') as f:
      for line in f:
          if line.startswith('{"_type": "tag"'):
              entry = json.loads(line)
              name = entry.get('name')
              if "__anon" in name: 
                  continue
                  
              kind = entry.get('kind')
              path = entry.get('path')
              rel_path = path[len(base_path):]  # relative path
              
              # Initialize file entry if not exists
              if rel_path not in files_dict:
                  files_dict[rel_path] = {
                      'classes': {},      # classes defined in this file
                      'methods': {},      # methods defined in this file
                      'free_functions': {},  # free functions defined in this file
                      'members': {},         # class members defined in this file
                  }
              
              # Process based on kind
              if kind == 'namespace':
                  name_spaces[name] = entry
                  
              elif kind in ['class', 'struct']:
                  class_lines = []
                  class_lines.append(entry)
                  cls = process_classes(class_lines, base_path, classes)
                  files_dict[rel_path]['classes'][name] = cls[name]
                  
              elif kind == 'function':
                  scope = entry.get('scope')
                  scopeK = entry.get('scopeKind')
                  
                  # Process function info
                  func_info = {
                      'line': entry.get('line'),
                      'signature': process_signature(entry.get('signature', '')),
                      'return_type': entry.get('typeref', '').split(":")[-1] if entry.get('typeref') else None,
                      'name': name
                  }
                  
                  if scope and (scopeK == 'class' or scopeK == 'struct'):
                      # This is a class method
                      files_dict[rel_path]['methods'][f"{scope}::{name}"] = func_info
                  else:
                      # This is a free function
                      files_dict[rel_path]['free_functions'][name] = func_info
                      
              elif kind == 'member':
                  files_dict[rel_path]['members'][name] = {
                      'line': entry.get('line'),
                      'type': entry.get('typeref', '').split(":")[-1] if entry.get('typeref') else None
                  }
  
  return files_dict

def process_ctags_json_claude(json_file, base_path):
    """
    Process ctags JSON file and return two dictionaries:
    1. classes_dict: organized by class names
    2. files_dict: organized by files
    """
    kinds = {'class', 'union', 'member', 'macro', 'header', 'variable', 
            'namespace', 'enum', 'enumerator', 'typedef', 'struct', 'function'}

    classes = {}
    files_dict = {}  # Will store information organized by files
    name_spaces = {}

    class_lines = []
    function_lines = []
    member_lines = []

    # First pass: collect all entries
    with open(json_file, 'r') as f:
        for line in f:
            if line.startswith('{"_type": "tag"'):
                entry = json.loads(line)
                name = entry.get('name')
                if "__anon" in name:
                    continue
                
                kind = entry.get('kind')
                path = entry.get('path')
                rel_path = path[len(base_path):]  # relative path
                
                # Initialize file entry if not exists
                if rel_path not in files_dict:
                    files_dict[rel_path] = {
                        'classes': set(),      # class names defined in this file
                        'methods': {},         # methods defined in this file
                        'free_functions': {},  # free functions defined in this file
                        'members': {},         # class members defined in this file
                    }

                # Collect entries by kind
                if kind == 'function':
                    function_lines.append(entry)
                    # Add to files_dict if it's a free function
                    if not entry.get('scope') or entry.get('scopeKind') not in ['class', 'struct']:
                        files_dict[rel_path]['free_functions'][name] = {
                            'line': entry.get('line'),
                            'signature': process_signature(entry.get('signature', '')),
                            'return_type': entry.get('typeref', '').split(":")[-1] if entry.get('typeref') else None
                        }

                elif kind == 'member':
                    member_lines.append(entry)
                    files_dict[rel_path]['members'][name] = {
                        'line': entry.get('line'),
                        'type': entry.get('typeref', '').split(":")[-1] if entry.get('typeref') else None
                    }

                elif kind in ['class', 'struct']:
                    class_lines.append(entry)
                    files_dict[rel_path]['classes'].add(name)

                elif kind == 'namespace':
                    name_spaces[name] = entry

    # Process classes and their members
    classes = process_classes(class_lines, base_path)
    process_members(member_lines, base_path, classes, name_spaces)
    free_functions = process_functions(function_lines, base_path, classes, name_spaces)

    # Second pass: add methods to files_dict
    for class_name, class_info in classes.items():
        for (_, file_path), class_data in class_info.items():
            if file_path in files_dict:
                # Add methods
                for method_name, method_info in class_data['methods'].items():
                    files_dict[file_path]['methods'][f"{class_name}::{method_name}"] = method_info

    return classes, free_functions, files_dict

def print_files_structure(files_dict):
    """Helper function to print the file-based organization"""
    for file_path, content in files_dict.items():
        print(f"\nFile: {file_path}")
        
        print("  Classes:")
        for class_name in content['classes']:
            print(f"    - {class_name}")
        
        print("  Methods:")
        for method_name, method_info in content['methods'].items():
            print(f"    - {method_name} (line {method_info['line']})")
        
        print("  Free Functions:")
        for func_name, func_info in content['free_functions'].items():
            print(f"    - {func_name} (line {func_info['line']})")
        
        print("  Members:")
        for member_name, member_info in content['members'].items():
            print(f"    - {member_name} (line {member_info['line']})")

class DependencyProcessor:
    def __init__(self):
        self.functions = {}       # Dict of qualified_name -> FunctionInfo
        self.classes = {}         # Dict of class_name -> {methods: {}, properties: {}}
        self.files = {}           # Dict of file_path -> {content, functions: [], classes: []}
        self.namespaces = {}      # Dict of namespace -> {functions: [], classes: []}

    def process_ctags_with_deps(self, json_file, base_path):
        """
        Enhanced version of process_ctags_json that includes function dependencies
        """
        with open(json_file, 'r') as f:
            lines = f.readlines()

        # First pass: collect all classes and function definitions
        for line in lines:
            entry = json.loads(line)
            if entry.get('_type') != 'tag':
                continue
                
            kind = entry.get('kind')
            name = entry.get('name')
            path = entry.get('path')
            path = path[len(base_path):] if path.startswith(base_path) else path
            scope = entry.get('scope', '')
            scope_kind = entry.get('scopeKind', '')
            
            # Build fully qualified name
            qualified_name = name
            if scope:
                if scope_kind == 'namespace':
                    # For functions in namespaces
                    qualified_name = scope + '::' + name
                elif scope_kind == 'class':
                    # For class methods
                    qualified_name = scope + '::' + name
                else:
                    qualified_name = name
            
            if kind == 'class':
                class_info = {
                    'methods': {},
                    'properties': {},
                    'file_path': path,
                    'line': entry.get('line'),
                    'scope': scope,
                    'inherits': entry.get('inherits'),
                }
                self.classes[qualified_name] = class_info
                
                # Add to file tracking
                if path not in self.files:
                    self.files[path] = {'functions': [], 'classes': [], 'content': None}
                self.files[path]['classes'].append(qualified_name)
                
            elif kind in ['function', 'method']:
                func_info = FunctionInfo()
                func_info.name = name
                func_info.start_line = entry.get('line')
                func_info.file_path = path
                func_info.kind = kind
                func_info.signature = entry.get('signature')
                
                if kind == 'method':
                    # For methods, scope should contain the class name
                    func_info.class_name = scope
                else:
                    # For functions in namespaces
                    if scope and scope_kind == 'namespace':
                        func_info.namespace = scope
                    
                self.functions[qualified_name] = func_info
                
                # Add to file tracking
                if path not in self.files:
                    self.files[path] = {'functions': [], 'classes': [], 'content': None}
                self.files[path]['functions'].append(qualified_name)

        return self.functions, self.classes, self.files

    def extract_identifiers(self, code, check_call_syntax=False):
        """
        Extract all identifiers from a piece of code, optionally checking for function call syntax
        """
        import re
        if check_call_syntax:
            # Match function calls with optional namespace/class qualification
            patterns = [
                r'\b([a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*)\s*\(',  # C++ style
                r'\b([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\s*\(',  # Python style
                r'\b((?:[a-zA-Z_]\w*::)*[a-zA-Z_]\w*)\s*\(',  # Nested namespaces
                r'\b((?:[a-zA-Z_]\w*\.)*[a-zA-Z_]\w*)\s*\('   # Nested Python calls
            ]
            identifiers = set()
            for pattern in patterns:
                matches = re.finditer(pattern, code)
                identifiers.update(match.group(1) for match in matches)
            return identifiers
        else:
            # Match any identifier including qualified names
            patterns = [
                r'\b(?:[a-zA-Z_]\w*::)*[a-zA-Z_]\w*\b',  # C++ namespace pattern
                r'\b(?:[a-zA-Z_]\w*\.)*[a-zA-Z_]\w*\b',  # Python/class method pattern
            ]
            identifiers = set()
            for pattern in patterns:
                identifiers.update(re.findall(pattern, code))
            return identifiers

    def analyze_dependencies(self, check_call_syntax=False):
        """
        Analyze function bodies to find potential function calls based on identifiers
        """
        for func_name, func_info in self.functions.items():
            if not func_info.body:
                continue
                
            try:
                # Get all identifiers in function body
                identifiers = self.extract_identifiers(func_info.body, check_call_syntax)
                func_info.calls = []  # Reset calls to avoid duplicates
                
                # Look for direct function calls
                for identifier in identifiers:
                    # Try both separator styles
                    cpp_style = identifier.replace('.', '::')
                    py_style = identifier.replace('::', '.')
                    
                    # Try direct matches
                    if cpp_style in self.functions:
                        func_info.calls.append(cpp_style)
                        continue
                    if py_style in self.functions:
                        func_info.calls.append(py_style)
                        continue
                    
                    # Try with current namespace prefix
                    if func_info.namespace:
                        ns_qualified = f"{func_info.namespace}::{cpp_style}"
                        if ns_qualified in self.functions:
                            func_info.calls.append(ns_qualified)
                            continue
                            
                    # Try with class prefix if this is a method
                    if func_info.class_name:
                        class_qualified = f"{func_info.class_name}::{cpp_style}"
                        if class_qualified in self.functions:
                            func_info.calls.append(class_qualified)
                            continue
                    
                    # Try all classes for method calls
                    for class_name in self.classes:
                        # For unqualified method names
                        if '::' not in cpp_style and '.' not in cpp_style:
                            class_cpp = f"{class_name}::{cpp_style}"
                            class_py = f"{class_name}.{cpp_style}"
                            if class_cpp in self.functions:
                                func_info.calls.append(class_cpp)
                                continue
                            if class_py in self.functions:
                                func_info.calls.append(class_py)
                                continue
                        # For qualified method names (obj.method or obj::method)
                        else:
                            parts = cpp_style.split('::')
                            class_qualified = f"{class_name}::{parts[-1]}"
                            if class_qualified in self.functions:
                                func_info.calls.append(class_qualified)
                                continue
                
                # Handle nested namespace calls
                parts = cpp_style.split('::')
                if len(parts) > 1:
                    # Try all possible namespace combinations
                    for i in range(len(parts)):
                        ns = '::'.join(parts[:i])
                        name = '::'.join(parts[i:])
                        if ns and name:
                            full_name = f"{ns}::{name}"
                            if full_name in self.functions:
                                func_info.calls.append(full_name)
                                break
                    
            except Exception as e:
                print(f"Error analyzing function {func_name}: {str(e)}")

    def find_scope_end(self, lines, start_idx):
        """
        Find the end of a scope (function/method body) by matching brackets
        Returns the line number of the closing bracket
        """
        brace_count = 0
        in_scope = False
        
        for i, line in enumerate(lines[start_idx:], start=start_idx):
            # Skip string literals and comments
            if '/*' in line or '//' in line or '"' in line or "'" in line:
                continue
                
            for char in line:
                if char == '{':
                    brace_count += 1
                    in_scope = True
                elif char == '}':
                    brace_count -= 1
                    
                if in_scope and brace_count == 0:
                    return i
                    
        return len(lines) - 1  # If not found, return last line

    def load_file_contents(self, base_path):
        """
        Load contents of all tracked files and determine function end lines using bracket matching
        """
        for file_path in self.files:
            full_path = os.path.join(base_path, file_path.lstrip('/'))
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                    self.files[file_path]['content'] = content
                    
                    lines = content.split('\n')
                    for func_name, func_info in self.functions.items():
                        if func_info.file_path == file_path:
                            start_idx = func_info.start_line - 1
                            end_idx = self.find_scope_end(lines, start_idx)
                            func_info.end_line = end_idx + 1
                            func_info.body = '\n'.join(lines[start_idx:end_idx+1])
                            
            except Exception as e:
                print(f"Error loading file {file_path}: {str(e)}")

    def print_dependency_graph(self, indent="  "):
        """
        Print the dependency graph in a tree-like format
        """
        def print_deps(func_name, seen=None, level=0):
            if seen is None:
                seen = set()
            
            if func_name in seen:
                print(f"{indent * level}{func_name} (circular ref)")
                return
            
            seen.add(func_name)
            func = self.functions.get(func_name)
            if func:
                print(f"{indent * level}{func_name} ({func.file_path}:{func.start_line})")
                for call in func.calls:
                    print_deps(call, seen.copy(), level + 1)
            seen.remove(func_name)
        
        print("\nFunction Dependency Graph:")
        print("-------------------------")
        # Print dependencies for each root function (functions not called by others)
        called_funcs = {call for func in self.functions.values() for call in func.calls}
        root_funcs = [name for name in self.functions.keys() if name not in called_funcs]
        
        for func_name in sorted(root_funcs):
            print_deps(func_name)

def process_ctags_with_deps(self, json_file, base_path):
    with open(json_file, 'r') as f:
        lines = f.readlines()

    for line in lines:
        entry = json.loads(line)
        if entry.get('_type') != 'tag':
            continue
            
        kind = entry.get('kind')
        name = entry.get('name')
        path = entry.get('path')
        path = path[len(base_path):] if path.startswith(base_path) else path
        scope = entry.get('scope', '')
        scope_kind = entry.get('scopeKind', '')
        
        # Build fully qualified name
        qualified_name = name
        if scope:
            if scope_kind == 'namespace':
                qualified_name = scope + '::' + name
            elif scope_kind == 'class':
                # Use appropriate separator based on file extension
                sep = '.' if path.endswith('.py') else '::'
                qualified_name = scope + sep + name
        
        if kind == 'class':
            class_info = {
                'methods': {},
                'properties': {},
                'file_path': path,
                'line': entry.get('line'),
                'scope': scope,
                'inherits': entry.get('inherits'),
            }
            self.classes[qualified_name] = class_info
            
            if path not in self.files:
                self.files[path] = {'functions': [], 'classes': [], 'content': None}
            self.files[path]['classes'].append(qualified_name)
            
        elif kind in ['function', 'method']:
            func_info = FunctionInfo()
            func_info.name = name
            func_info.start_line = entry.get('line')
            func_info.file_path = path
            func_info.kind = kind
            func_info.signature = entry.get('signature')
            func_info.is_method = (kind == 'method')
            func_info.is_static = bool(entry.get('static'))
            
            # Set scope information
            if scope:
                if scope_kind == 'namespace':
                    func_info.namespace = scope
                elif scope_kind == 'class':
                    func_info.class_name = scope
            
            self.functions[qualified_name] = func_info
            
            if path not in self.files:
                self.files[path] = {'functions': [], 'classes': [], 'content': None}
            self.files[path]['functions'].append(qualified_name)

    return self.functions, self.classes, self.files

def extract_identifiers(self, code, check_call_syntax=False):
    """
    Extract all identifiers from a piece of code, optionally checking for function call syntax
    """
    import re
    if check_call_syntax:
        # Match function calls with optional namespace/class qualification
        patterns = [
            # C++ style calls
            r'\b([a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*)\s*\(',
            r'\b((?:[a-zA-Z_]\w*::)*[a-zA-Z_]\w*)\s*\(',
            # Python style calls
            r'\b([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\s*\(',
            r'\b((?:[a-zA-Z_]\w*\.)*[a-zA-Z_]\w*)\s*\(',
            # Function pointer calls
            r'\b([a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*)\s*\)\s*\(',
        ]
        identifiers = set()
        for pattern in patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                # Get the full match and clean it up
                ident = match.group(1).strip()
                if ident:
                    identifiers.add(ident)
        return identifiers
    else:
        # Match any identifier including qualified names
        patterns = [
            r'\b(?:[a-zA-Z_]\w*::)*[a-zA-Z_]\w*\b',  # C++ style
            r'\b(?:[a-zA-Z_]\w*\.)*[a-zA-Z_]\w*\b',  # Python style
        ]
        identifiers = set()
        for pattern in patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                ident = match.group(0).strip()
                if ident:
                    identifiers.add(ident)
        return identifiers

def analyze_dependencies(self, check_call_syntax=False):
    """
    Analyze function bodies to find potential function calls based on identifiers
    """
    for func_name, func_info in self.functions.items():
        if not func_info.body:
            continue
            
        try:
            # Get all identifiers in function body
            identifiers = self.extract_identifiers(func_info.body, check_call_syntax)
            func_info.calls = []  # Reset calls to avoid duplicates
            
            # Look for direct function calls
            for identifier in identifiers:
                # Try both separator styles
                cpp_style = identifier.replace('.', '::')
                py_style = identifier.replace('::', '.')
                
                # Try direct matches
                if cpp_style in self.functions:
                    func_info.calls.append(cpp_style)
                    continue
                if py_style in self.functions:
                    func_info.calls.append(py_style)
                    continue
                
                # Try with current namespace prefix
                if func_info.namespace:
                    ns_qualified = f"{func_info.namespace}::{cpp_style}"
                    if ns_qualified in self.functions:
                        func_info.calls.append(ns_qualified)
                        continue
                        
                # Try with class prefix if this is a method
                if func_info.class_name:
                    class_qualified = f"{func_info.class_name}::{cpp_style}"
                    if class_qualified in self.functions:
                        func_info.calls.append(class_qualified)
                        continue
                
                # Try all classes for method calls
                for class_name in self.classes:
                    # For unqualified method names
                    if '::' not in cpp_style and '.' not in cpp_style:
                        class_cpp = f"{class_name}::{cpp_style}"
                        class_py = f"{class_name}.{cpp_style}"
                        if class_cpp in self.functions:
                            func_info.calls.append(class_cpp)
                            continue
                        if class_py in self.functions:
                            func_info.calls.append(class_py)
                            continue
                    # For qualified method names (obj.method or obj::method)
                    else:
                        parts = cpp_style.split('::')
                        class_qualified = f"{class_name}::{parts[-1]}"
                        if class_qualified in self.functions:
                            func_info.calls.append(class_qualified)
                            continue
                
                # Handle nested namespace calls
                parts = cpp_style.split('::')
                if len(parts) > 1:
                    # Try all possible namespace combinations
                    for i in range(len(parts)):
                        ns = '::'.join(parts[:i])
                        name = '::'.join(parts[i:])
                        if ns and name:
                            full_name = f"{ns}::{name}"
                            if full_name in self.functions:
                                func_info.calls.append(full_name)
                                break
                
        except Exception as e:
            print(f"Error analyzing function {func_name}: {str(e)}")
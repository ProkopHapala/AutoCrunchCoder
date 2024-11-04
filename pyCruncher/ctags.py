import re
from collections import defaultdict
import subprocess
import json
import time
#import networkx as nx
import traceback

class_file           = 'tags_classes.log'
method_file          = 'tags_methods.log'
free_function_file   = 'tags_free_functions.log'
global_variable_file = 'tags_global_variables.log'

def run_ctags(output_file, path, kinds=None, exclude=None ):
    """
    Run ctags and generate a tags file.
    :param output_file: The output tags file.
    :param kinds: The kinds of tags to generate (e.g., 'c' for classes, 'f' for functions).
    :param path: The path to the source files to be scanned.
    :param exclude: A list of directories to exclude (optional).
    """

    excludes = []
    if exclude:
        excludes = [ "--exclude="+s for s in exclude] # common_resources", "--exclude=Build", ," --exclude=Build-asan --exclude=Build-opt --exclude=Build-dbg

    with open(output_file, 'w') as f: f.write("") # Clear the output file
    #cmd = ['ctags', '-R', "--output-format=json", '--languages=C++', f'--kinds-C++={kinds}'] + excludes +[ "--extra=+fq", '-o', output_file, path]
    #cmd = ['ctags', '-R', "--output-format=json", '--languages=C++']
    #if kinds is not None: cmd.append(  f'--kinds-C++={kinds}' );
    
    cmd = [
        'ctags', '-R',                      # Recursively process files
        #'--languages=C,C++',               # Limit processing to C and C++
        '--languages=C++',                  # Limit processing C++
        '--output-format=json',             # Output the result in JSON format
        '--fields=+cniKSE',                 # Include line number(n), inheritance(i), types(K), and signatures(S), macros(E) (#define)
        '--extras=+qrFS',                   # Include qualified names (for classes, methods, etc.), files reference, scope
        '--excmd=number',                   # only number, no search-pattern
    ]
    
    cmd += excludes +[ '-o', output_file, path]
    
    print("run_ctags"," ".join(cmd))

    try:
        proc = subprocess.run(cmd, check=True)
        print(f"ctags completed successfully, output written to: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error running ctags: {e}")

# Parse a single line from a ctags file
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
                  scope = entry.get('scope')
                  if scope:  # If member has a scope (belongs to a class)
                      member_info = {
                          'line': entry.get('line'),
                          'type': entry.get('typeref', '').split(":")[-1] if entry.get('typeref') else None
                      }
                      # Store with full scoped name
                      files_dict[rel_path]['members'][f"{scope}::{name}"] = member_info
  
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
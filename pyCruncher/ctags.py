import re
from collections import defaultdict
import subprocess
import json
import time
import networkx as nx

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
    # cmd = ['ctags', '-R', "--output-format=json", '--languages=C++']
    # if kinds is not None: cmd.append(  f'--kinds-C++={kinds}' );
    
    
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
    # proc = subprocess.run(cmd, check=True)   # Run the ctags command
    # # print error if any
    # if proc.returncode != 0:
    #     print("Error running ctags:", proc.stderr.decode())

    # Run the ctags command
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
    
        #id = (name, path_)
        #id = (name, scope, scopeK, path_)
        #id = (full_name, path_)
        #id = (name_, path_, il)   # unique identifier
        id = (name_, path_)   # unique identifier
        rec={ "line":il, "kind":kind, "scope":scope, 'scopeKind':scopeK, 'inherits':inherits, "properties":{}, "methods":{} }
        if name_ in classes:
            classes[name_][id] = rec 
            #dup = classes[name_]
            # if id in dup:
            #     print("duplicate class for id= ", id )
            #     print("     old:  ", rec )
            #     print("     new:  ", dup[id] )
            #     print()
        else:
            #if inherits is None: continue
            # print( "class ", id )
            # for k,v in entry.items():
            #     print( "        ", k, v )
            # for k,v in rec.items():
            #     print( "        ", k, v )
            classes[name_] = {id: rec }
        # print( "class: ", name_ )
        # print( "path:  ", path_ )
        # #list all other fields
        # for k,v in entry.items():
        #     print( "        ", k, v )
        #print(f"{entry.get('name')} ({entry.get('kind')}) in {entry.get('file')}")
    return classes

def addToClass( name, rec, cls_name, fname, classes, name_spaces, what='properties' ):
    if cls_name in name_spaces:
        print("WARNING: ", name," :: ", cls_name," is namespace " )
        return
    cls    = classes[cls_name]
    cls_id = (cls_name, fname )
    cls_   = cls[cls_id]
    cls_what = cls_[what]   # 'properties' or 'methods'
    cls_what[name] = rec

def printDict(dct):
    for k,v in dct.items():
        print( "        ", k, v )

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
        # if typeref is None: 
        #     print( "!!!!! member ", name, ": ", typeref,  " in ", scope )
        #     for k,v in entry.items():
        #         print( "        ", k, v )
        #     type = None
        # else:
        type=typeref.split(":")[-1]
        il = entry.get('line')
        #rec={ 'type':type, "line":il }
        rec=( type, il )
        # print( "member ", name, ": ", type,  " :: ", scope_ )
        # for k,v in entry.items():
        #     print( "        ", k, v )
        if (scopeK == 'class' or scopeK == 'struct') and (scope_ is not None):
            try:
                addToClass( name, rec, scope_, path_, classes, name_spaces )
            except Exception as e:
                printDict( entry )
                print( "excpetion: ", e )
                exit()
                
    return members

def process_functions( function_lines, base_path, classes, functions={} ):
    return functions


def process_ctags_json_prokop(json_file, base_path ):
    #kinds = set()
    kinds = {'class', 'union', 'member', 'macro', 'header', 'variable', 'namespace', 'enum', 'enumerator', 'typedef', 'struct', 'function'}

    # with open(json_file, 'r') as f:
    #     for i,line in enumerate(f):
    #         if line.startswith('{"_type": "tag"'):

    #with open(json_file, 'r') as f: lines = [json.loads(line) for line in f if line.startswith('{"_type": "tag"')]  # Filter only relevant tags

    classes={ }
    # with open(json_file, 'r') as f:
    #     for i,line in enumerate(f):
    #         #if line[0]=='{':
    #         if line.startswith('{"_type": "tag"'):

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

    # for line in lines:
    #     #print(i, line)
    #     entry = json.loads(line)
    #     kind = entry.get('kind')
    #     name = entry.get('name')
    #     if "__anon" in name: continue
    #     #kinds.add(entry.get('kind'))
    #     #print(entry.get('kind'))

    #     name_ = name.split("::")[-1] 
    #     path = entry.get('path')
    #     path_ = path[len(base_path):] 
    #     scope=entry.get('scope')
    #     scopeK= entry.get('scopeKind')
    #     inherits=entry.get('inherits')

    #     il = entry.get('line')

    #     full_name = name
    #     if scope is not None:
    #         full_name = scope + "::" + name_

    #     if kind=='function':

    #     if (kind=='class') or (kind=='struct'):
    #         continue

    for name,cls in classes.items():
        for id,rec in cls.items():
            print( name, id )
            for k,v in rec.items():
                print( "    ", k,":", v )

    print("kinds: ", kinds)


def process_ctags_json(json_file):
    """
    Processes the ctags JSON output to generate a structure for files and classes.

    :param json_file: The path to the JSON file generated by ctags.
    :return: Two dictionaries: files_dict and classes_dict.
    """
    # Initialize dictionaries
    files_dict = defaultdict(lambda: {'classes': [], 'functions': [], 'globals': []})
    classes_dict = defaultdict(lambda: {'methods': [], 'properties': []})

    # Load the JSON data
    with open(json_file, 'r') as f:
        data = [json.loads(line) for line in f if line.startswith('{"_type": "tag"')]  # Filter only relevant tags

    # Loop through each entry in the JSON file
    for entry in data:
        file_name = entry.get('path', None)
        tag_name = entry.get('name', None)
        tag_kind = entry.get('kind', None)
        class_name = entry.get('scope', None)  # For methods and properties inside classes

        # Process based on the kind of tag
        if tag_kind == 'class':
            files_dict[file_name]['classes'].append(tag_name)
            classes_dict[tag_name]  # Initialize an entry in classes_dict for the class
        elif tag_kind == 'function':
            if class_name:
                # This is a method inside a class
                classes_dict[class_name]['methods'].append(tag_name)
            else:
                # This is a free function
                files_dict[file_name]['functions'].append(tag_name)
        elif tag_kind == 'variable':
            if class_name:
                # This is a class property
                classes_dict[class_name]['properties'].append(tag_name)
            else:
                # This is a global variable
                files_dict[file_name]['globals'].append(tag_name)

    return files_dict, classes_dict




# def parse_ctags_json(json_file):
#     """
#     Processes the ctags JSON output to generate a structure for files and classes.

#     :param json_file: The path to the JSON file generated by ctags.
#     :return: A dictionary with class details (methods, properties, dependencies).
#     """
#     # Dictionary to store class details
#     class_details = defaultdict(lambda: {
#         'properties': set(),
#         'methods': set(),
#         'dependencies': set()
#     })

#     # Load the JSON data
#     with open(json_file, 'r') as f:
#         data = [json.loads(line) for line in f if line.startswith('{"_type": "tag"')]  # Filter only relevant tags

#     # Loop through each entry in the JSON file
#     for entry in data:
#         tag_name = entry.get('name', None)
#         file_name = entry.get('path', None)
#         tag_kind = entry.get('kind', None)
#         class_name = entry.get('scope', None)  # For methods and properties inside classes
#         tag_type = entry.get('type', None)     # Type for properties or method return type
#         signature = entry.get('signature', None)  # For methods, get the signature
        
#         # If it's a class, store the class and its inheritance relationships
#         if tag_kind == 'class':
#             class_details[tag_name]  # Initialize an entry in class_details for the class
#             if 'inherits' in entry:
#                 for inherited_class in entry['inherits']:
#                     class_details[tag_name]['dependencies'].add(inherited_class)
        
#         # If it's a property (variable) within a class, store it with its type
#         elif tag_kind == 'variable' and class_name:
#             class_details[class_name]['properties'].add((tag_name, tag_type))
#             class_details[class_name]['dependencies'].add(tag_type)  # Dependency on the property's type
        
#         # If it's a method within a class, store the method details
#         elif tag_kind == 'function' and class_name:
#             if signature:
#                 args = tuple( (arg['type'], arg['name']) for arg in signature['arguments'] )  # Method arguments
#             else:
#                 args = tuple()  # No arguments

#             class_details[class_name]['methods'].add((tag_name, tag_type, args))
#             class_details[class_name]['dependencies'].add(tag_type)  # Dependency on the return type
            
#             # Add dependencies on method argument types
#             for arg_type, arg_name in args:
#                 class_details[class_name]['dependencies'].add(arg_type)

#     return class_details

import json
from collections import defaultdict

def parse_ctags_json(json_file):
    """
    Processes the ctags JSON output to generate a structure for classes.
    Each class contains properties, methods, and dependencies on other classes/types.
    
    :param json_file: The path to the JSON file generated by ctags.
    :return: A dictionary with class details (methods, properties, dependencies).
    """
    # Dictionary to store class details
    class_details = defaultdict(lambda: {
        'properties': set(),
        'methods': set(),
        'dependencies': set()
    })

    # Load the JSON data
    with open(json_file, 'r') as f:
        data = [json.loads(line) for line in f if line.startswith('{"_type": "tag"')]

    # Loop through each entry in the JSON file
    for entry in data:
        tag_name = entry.get('name', None)
        file_name = entry.get('path', None)
        tag_kind = entry.get('kind', None)
        class_name = entry.get('scope', None)  # For methods and properties inside classes
        tag_type = entry.get('type', None)     # Type for properties or method return type
        signature = entry.get('signature', None)  # For methods, get the signature

        # If it's a class, store the class and its inheritance relationships
        if tag_kind == 'class':
            class_details[tag_name]  # Initialize an entry in class_details for the class
            if 'inherits' in entry:
                for inherited_class in entry['inherits']:
                    class_details[tag_name]['dependencies'].add(inherited_class)

        # If it's a property (variable) within a class, store it with its type
        elif tag_kind == 'member' and class_name:
            if tag_type:
                class_details[class_name]['properties'].add((tag_name, tag_type))
                class_details[class_name]['dependencies'].add(tag_type)  # Dependency on the property's type
        
        # If it's a method within a class, store the method details
        elif tag_kind == 'function' and class_name:
            if signature:
                # Extract method arguments as a tuple (type, name)
                args = tuple((arg.get('type', 'None'), arg.get('name', 'None')) for arg in signature.get('arguments', []))
            else:
                args = tuple()  # No arguments

            # Store method name, return type, and argument list (converted to tuple)
            return_type = tag_type if tag_type else "None"
            class_details[class_name]['methods'].add((tag_name, return_type, args))
            class_details[class_name]['dependencies'].add(return_type)  # Dependency on the return type
            
            # Add dependencies on method argument types
            for arg_type, arg_name in args:
                class_details[class_name]['dependencies'].add(arg_type)

    return class_details


def display_class_details(class_details):
    """
    Display the structure of class details including properties, methods, and dependencies.
    
    :param class_details: Dictionary containing class details and dependencies.
    """
    for class_name, details in class_details.items():
        print(f"\nClass: {class_name}")
        
        # Display properties
        print("-- Properties:")
        for prop_name, prop_type in details['properties']:
            print(f"   {prop_name}: {prop_type}")
        
        # Display methods
        print("-- Methods:")
        for method_name, return_type, args in details['methods']:
            arg_str = ', '.join([f"{arg_type} {arg_name}" for arg_type, arg_name in args])
            print(f"   {method_name}({arg_str}) -> {return_type}")
        
        # Display dependencies
        print("-- Dependencies:")
        if details['dependencies']:
            for dep in details['dependencies']:
                print(f"   {dep}")
        else:
            print("   None")







# def display_class_details(class_details):
#     """
#     Display the structure of class details including properties, methods, and dependencies.
    
#     :param class_details: Dictionary containing class details and dependencies.
#     """
#     for class_name, details in class_details.items():
#         print(f"\nClass: {class_name}")
        
#         # Display properties
#         print("-- Properties:")
#         for prop_name, prop_type in details['properties']:
#             print(f"   {prop_name}: {prop_type}")
        
#         # Display methods
#         print("-- Methods:")
#         for method_name, return_type, args in details['methods']:
#             arg_str = ', '.join([f"{arg_type} {arg_name}" for arg_type, arg_name in args])
#             print(f"   {method_name}({arg_str}) -> {return_type}")
        
#         # Display dependencies
#         print("-- Dependencies:")
#         for dep in details['dependencies']:
#             print(f"   {dep}")







# General function to parse any ctags file and update dictionaries
def process_ctags_file(file_path, tag_kind_to_key, files_dict, classes_dict=None):
    """
    Parse a ctags file and update the dictionaries based on the tag kind.

    :param file_path: The path to the ctags file.
    :param tag_kind_to_key: A mapping from tag kinds (e.g., 'f', 'v', 'c') to keys in files_dict or classes_dict.
    :param files_dict: The dictionary that holds file-level information.
    :param classes_dict: (Optional) The dictionary that holds class-level information.
    """
    with open(file_path, 'r') as f:
        file_kinds  = tag_kind_to_key['files']
        class_kinds = tag_kind_to_key['classes']
        for line in f:
            parsed = parse_ctags_line(line)
            if parsed:
                tag_name, file_name, tag_kind = parsed

                # For files dictionary
                if tag_kind in tag_kind_to_key['files']:
                    files_dict[file_name][file_kinds[tag_kind]].append(tag_name)

                # For classes dictionary, if applicable
                if classes_dict and tag_kind in tag_kind_to_key['classes']:
                    class_name_match = re.search(r'(\w+)::', tag_name)
                    if class_name_match:
                        class_name = class_name_match.group(1)
                        if class_name in classes_dict:
                            classes_dict[class_name][class_kinds[tag_kind]].append(tag_name)


def generate_ctags_files(src_path, exclude = ['common_resources', 'Build*'] ):
    """ Generate the ctags files for the given source path and exclusions. """
    run_ctags(class_file,           'c', src_path, exclude)
    run_ctags(method_file,          'm', src_path, exclude)
    run_ctags(free_function_file,   'f', src_path, exclude)
    run_ctags(global_variable_file, 'v', src_path, exclude)

#
def construct_dictionaries():
    """ Build the dictionaries from the provided ctags files """
    files_dict   = defaultdict(lambda: {'classes': [], 'free_functions': [], 'global_variables': []})
    classes_dict = defaultdict(lambda: {'methods': [], 'properties': []})
    # Define the mapping for tag kinds to dictionary keys
    tag_kind_to_key = {
        'files': {
            'f': 'free_functions',
            'v': 'global_variables',
            'c': 'classes'
        },
        'classes': {
            'm': 'methods'
        }
    }
    # Process each ctags file
    process_ctags_file(class_file,           tag_kind_to_key, files_dict, classes_dict)
    process_ctags_file(method_file,          tag_kind_to_key, files_dict, classes_dict)
    process_ctags_file(free_function_file,   tag_kind_to_key, files_dict)
    process_ctags_file(global_variable_file, tag_kind_to_key, files_dict)
    return files_dict, classes_dict

def extract_includes(file_path):
    includes = []
    with open(file_path, 'r') as f:
        for line in f:
            match = re.match(r'#include\s+[<"]([^">]+)[">]', line)
            if match:
                includes.append(match.group(1))
    return includes

def process_ctags_json_with_dependencies(json_file):
    class_dependencies = defaultdict(set)
    function_dependencies = defaultdict(set)
    file_dependencies = defaultdict(set)

    with open(json_file, 'r') as f:
        data = [json.loads(line) for line in f if line.startswith('{"_type": "tag"')]

    for tag in data:
        tag_name = tag['name']
        file_name = tag['path']
        tag_kind = tag['kind']
        scope = tag.get('scope', None)

        if tag_kind == 'class' and 'inherits' in tag:
            inherited_class = tag['inherits'][0]
            class_dependencies[tag_name].add(inherited_class)

        elif tag_kind == 'function':
            if scope:
                function_dependencies[f"{scope}::{tag_name}"].add(scope)

        includes = extract_includes(file_name)
        for included_file in includes:
            file_dependencies[file_name].add(included_file)

    return class_dependencies, function_dependencies, file_dependencies


# General function to parse any ctags file and update dictionaries
def process_ctags_file(file_path, tag_kind_to_key, files_dict, classes_dict=None):
    """
    Parse a ctags file and update the dictionaries based on the tag kind.

    :param file_path: The path to the ctags file.
    :param tag_kind_to_key: A mapping from tag kinds (e.g., 'f', 'v', 'c') to keys in files_dict or classes_dict.
    :param files_dict: The dictionary that holds file-level information.
    :param classes_dict: (Optional) The dictionary that holds class-level information.
    """
    with open(file_path, 'r') as f:
        file_kinds  = tag_kind_to_key['files']
        class_kinds = tag_kind_to_key['classes']
        for line in f:
            parsed = parse_ctags_line(line)
            if parsed:
                tag_name, file_name, tag_kind = parsed

                # For files dictionary
                if tag_kind in tag_kind_to_key['files']:
                    files_dict[file_name][file_kinds[tag_kind]].append(tag_name)

                # For classes dictionary, if applicable
                if classes_dict and tag_kind in tag_kind_to_key['classes']:
                    class_name_match = re.search(r'(\w+)::', tag_name)
                    if class_name_match:
                        class_name = class_name_match.group(1)
                        if class_name in classes_dict:
                            classes_dict[class_name][class_kinds[tag_kind]].append(tag_name)

def build_dependency_graph(class_deps, function_deps, file_deps):
    G = nx.DiGraph()

    for cls, deps in class_deps.items():
        for dep in deps:
            G.add_edge(dep, cls, type='class')

    for func, deps in function_deps.items():
        for dep in deps:
            G.add_edge(dep, func, type='function')

    for file, deps in file_deps.items():
        for dep in deps:
            G.add_edge(dep, file, type='file')

    return G

def analyze_dependencies(json_file, output_graph='dependency_graph.png'):
    """
    Analyzes dependencies from a ctags JSON file and generates a dependency graph.

    :param json_file: Path to the JSON file generated by ctags.
    :param output_graph: Path to save the visualized dependency graph.
    :return: Tuple containing the dependency graph, class dependencies, function dependencies,
             file dependencies, files dictionary, and classes dictionary.
    """

    print(f"Starting dependency analysis for {json_file}")
    start_time = time.time()

    print("Processing JSON file to extract dependencies...")
    class_deps, function_deps, file_deps = process_ctags_json_with_dependencies(json_file)
    print(f"Dependency extraction completed in {time.time() - start_time:.2f} seconds")

    print("Building dependency graph...")
    graph_start_time = time.time()
    G = build_dependency_graph(class_deps, function_deps, file_deps)
    print(f"Graph building completed in {time.time() - graph_start_time:.2f} seconds")

    # print(f"Visualizing dependency graph to {output_graph}...")
    # vis_start_time = time.time()
    # visualize_dependency_graph(G, output_graph)
    # print(f"Graph visualization completed in {time.time() - vis_start_time:.2f} seconds")

    print("Processing file and class structures...")
    struct_start_time = time.time()
    files_dict, classes_dict = process_ctags_json(json_file)
    print(f"Structure processing completed in {time.time() - struct_start_time:.2f} seconds")

    total_time = time.time() - start_time
    print(f"Total analysis time: {total_time:.2f} seconds")

    #class_deps, function_deps, file_deps, files_dict, classes_dict

    return G, class_deps, function_deps, file_deps, files_dict, classes_dict

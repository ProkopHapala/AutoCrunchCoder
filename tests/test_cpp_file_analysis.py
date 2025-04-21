import sys
sys.path.append("../")
import pyCruncher.scoped_cpp as scpp

fname = "/home/prokop/git/FireCore/cpp/common/molecular/NBFF.h"


# if len(sys.argv) != 2:
#     print("Usage: python function_header_extractor.py <cpp_file>")
#     exit()
if len(sys.argv) >= 2:
    fname = sys.argv[1]

with open(fname, 'r') as f: content = f.read()
content   = scpp.COMMENT_PATTERN.sub('', content)
#functions = scpp.analyze_scopes_and_functions(content, True)
functions = scpp.analyze_scopes_and_functions(content, False)
variables = scpp.analyze_scopes_and_variables(content, True)
inheritances = scpp.analyze_inheritance(content, True)
includes = scpp.analyze_includes(content, True)
print(f"\n ============ Functions in {fname} \n ")
for f in functions:
    #print()
    #print(f"@ {f['scope']}")
    #print(f"{f['return_type']} {f['name']}({f['args']})")
    #print(f"{f['scope']}::{f['return_type']} {f['name']}({f['args']})")
    scpp.print_function_header( f )

# TODO: we should list all function-calls from each function, to be able to reconstruct the call graph ( dependency graph )
print("\n ============ Variables in {fname} \n ")
for v in variables:
    scpp.print_variable_declaration(v)
print("\n ============ Inheritance =========== \n")
for inh in inheritances:
    print(f"Class {inh['class']} inherits from: {', '.join(inh['parents'])}")
print("\n ============ Includes =========== \n")
for inc in includes:
    print(f"#include {inc}")

#scpp.generate_markdown_documentation( fname.split("/")[-1], includes, functions, variables, inheritances, saveToFile=fname+".md", desc_str ="" )

scpp.generate_markdown_documentation( fname.split("/")[-1], includes, functions, variables, inheritances, saveToFile=fname+".md", desc_str ="",
show_args=False, show_return_type=False, show_scope=False,           show_var_type=False, var_type_after_name=False )
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
print(f"\n ============ Functions in {fname} \n ")
for f in functions:
    #print()
    #print(f"@ {f['scope']}")
    #print(f"{f['return_type']} {f['name']}({f['args']})")
    #print(f"{f['scope']}::{f['return_type']} {f['name']}({f['args']})")
    scpp.print_function_header( f )
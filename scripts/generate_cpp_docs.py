#!/usr/bin/python3

import sys, os
sys.path.append("../")
import pyCruncher.scoped_cpp as scpp
from pyCruncher.AgentOpenAI import AgentOpenAI

def read_file_list(list_file):
    base_dir = os.path.dirname(os.path.abspath(list_file))
    files = []
    with open(list_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Handle both absolute and relative paths
                if not os.path.isabs(line):
                    line = os.path.join(base_dir, line)
                files.append(os.path.abspath(line))
    return files

def process_cpp_file(file_path, output_dir, llm_agent):
    # Read and analyze the C++ file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove comments for analysis
    content_no_comments = scpp.COMMENT_PATTERN.sub('', content)
    
    # Analyze the file
    functions    = scpp.analyze_scopes_and_functions(content_no_comments, False)
    variables    = scpp.analyze_scopes_and_variables(content_no_comments, False)
    inheritances = scpp.analyze_inheritance(content_no_comments, False)
    includes     = scpp.analyze_includes(content_no_comments, False)
    
    # Preserve directory structure in output
    rel_path = os.path.relpath(file_path, start=os.path.commonpath([file_path, output_dir]))
    md_file = os.path.join(output_dir, rel_path + ".md")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(md_file), exist_ok=True)
    
    # Generate markdown template
    scpp.generate_markdown_documentation(
        os.path.basename(file_path), includes, functions, variables, inheritances, saveToFile=md_file,
        show_args=False, show_return_type=False, show_scope=False, 
        show_var_type=True, var_type_after_name=True, desc_str=""
    )
    
    #print("saved to", md_file)
    #return

    # Read the template
    with open(md_file, 'r') as f:
        template = f.read()
    
    # Create prompt for LLM
    prompt = f"""
I will provide you with a C++ source file and a markdown documentation template. Please analyze the code and complete the documentation.

==============================

Source code:
```cpp
{content}
```

==============================

Documentation template:
```markdown
{template}
```

==============================

Please provide the complete markdown documentation with all sections filled in.

1. Adding a clear description of the file's purpose
2. Explaining each function's purpose, parameters, and return values
3. Documenting important variables and their roles
4. Explaining any class inheritance relationships
5. Adding any important implementation details or usage notes

NOTE: Focus on main ideas and big-picture. Explain the purpose and idea behind classes and function in clear and concise manner. Avoid vague phrases and formalities. 
Adjust detail of description appropriately to importance of each class or function. For trivial functions, keep the description very short. For complex and important functions, explain in more detail also internall workings, and the ideas behind their implementation.

"""
    response = llm_agent.query(prompt)
    print("#=============== Response:")
    print(response.content)
    print("#=============== Writing to file:")
    with open(md_file, 'w') as f:
        f.write(response.content)
    print(f"Generated documentation for {file_path}")


# ============= Main =============

# if len(sys.argv) < 3:
#     print("Usage: generate_cpp_docs.py <file_list> <output_dir> [model_name]")
#     sys.exit(1)
# fname = sys.argv[1]
# output_dir = os.path.abspath(sys.argv[2])
# model_name = sys.argv[3] if len(sys.argv) > 3 else "fzu-qwen2_7b_1m"


fname      = "cpp_file_list.txt"
output_dir =  "/home/prokop/git/FireCore/doc/Markdown"
model_name = "fzu-qwen2_7b_1m"


system_prompt = """
You are a technical documentation expert specializing in C++ codebases.
You excel at:
1. Understanding C++ code structure and patterns
2. Writing clear, concise technical documentation
3. Explaining complex functionality in simple terms
4. Identifying and documenting important implementation details
5. Maintaining consistent documentation style
"""

agent = AgentOpenAI(model_name)
agent.set_system_prompt(system_prompt)

# Process each file
file_list = read_file_list(fname)
for file_path in file_list:
    try:
        print(f"Processing {file_path}")
        process_cpp_file(file_path, output_dir, agent)
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
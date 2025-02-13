#!/usr/bin/python3

import sys
sys.path.append("../")
import pyCruncher.scoped_cpp as scpp
from pyCruncher.AgentOpenAI import AgentOpenAI

def read_file_list(list_file):
    with open(list_file, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def process_cpp_file(file_path, llm_agent):
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
    
    # Generate markdown template
    md_file = file_path + ".md"
    scpp.generate_markdown_documentation(
        file_path.split("/")[-1],
        includes, functions, variables, inheritances,
        saveToFile=md_file,
        show_args=True, show_return_type=True, show_scope=True,
        show_var_type=True, var_type_after_name=False,
        desc_str=""
    )
    
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



fname='cpp_file_list.txt'
if len(sys.argv) >= 2:
    fname = sys.argv[1]

# Initialize LLM agent
system_prompt = """
You are a technical documentation expert specializing in C++ codebases.
You excel at:
1. Understanding C++ code structure and patterns
2. Writing clear, concise technical documentation
3. Explaining complex functionality in simple terms
4. Identifying and documenting important implementation details
5. Maintaining consistent documentation style
"""

model_name = "fzu-qwen2_7b_1m"  # Using underscore instead of dots and hyphens

agent = AgentOpenAI(model_name)
agent.set_system_prompt(system_prompt)

# Process each file
file_list = read_file_list(fname)
for file_path in file_list:
    try:
        print(f"Processing {file_path}")
        process_cpp_file(file_path, agent)
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

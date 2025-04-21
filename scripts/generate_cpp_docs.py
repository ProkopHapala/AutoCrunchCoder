#!/usr/bin/python3

import sys, os
sys.path.append("../")
import pyCruncher.scoped_cpp as scpp
from pyCruncher.AgentOpenAI import AgentOpenAI
from pyCruncher.AgentGoogle import AgentGoogle

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

def find_implementation_file(header_path):
    # Get the directory and filename without extension
    dir_path = os.path.dirname(header_path)
    base_name = os.path.splitext(os.path.basename(header_path))[0]
    
    # Check for .cpp and .c files
    for ext in ['.cpp', '.c']:
        impl_path = os.path.join(dir_path, base_name + ext)
        if os.path.exists(impl_path):
            return impl_path
    return None

def process_cpp_file(file_path, output_dir, llm_agent, bSavePrompt=True ):
    # Read the main file (header)
    with open(file_path, 'r') as f:
        header_content = f.read()
    
    # Try to find and read the implementation file
    impl_file = find_implementation_file(file_path)
    impl_content = ""
    if impl_file:
        with open(impl_file, 'r') as f:
            impl_content = f.read()
    
    # Combine content for analysis
    content = header_content
    if impl_content:
        content = header_content + "\n" + impl_content
    
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
    
    # Create backup if existing documentation exists
    existing_doc = ""
    if os.path.exists(md_file):
        # Read existing documentation
        with open(md_file, 'r') as f:
            existing_doc = f.read()
        
        # Create backup with incremental number
        i = 1
        while os.path.exists(f"{md_file}.bak{i}"):
            i += 1
        backup_file = f"{md_file}.bak{i}"
        os.rename(md_file, backup_file)
        print(f"Created backup: {backup_file}")
    
    # Generate new markdown template
    temp_template_file = md_file + ".temp"
    scpp.generate_markdown_documentation(
        os.path.basename(file_path), includes, functions, variables, inheritances, saveToFile=temp_template_file,
        show_args=False, show_return_type=False, show_scope=False, 
        show_var_type=True, var_type_after_name=True, desc_str=""
    )

    #print(" saved template to: " + temp_template_file) 
    #return

    # Read the template
    with open(temp_template_file, 'r') as f:
        template = f.read()
    os.remove(temp_template_file)
    
    # Create prompt for LLM
    prompt = f"""
I will provide you with a C++ header file{' and its implementation file' if impl_content else ''}, a markdown documentation template generated from the current source code, and optionally existing documentation. Please analyze all inputs and generate comprehensive documentation.

---

Source code:

Primary file ({os.path.basename(file_path)}):
```cpp
{header_content}
```

{f'''Implementation file ({os.path.basename(impl_file)}):
```cpp
{impl_content}
```''' if impl_content else ''}

{f'''---

Existing documentation (may contain valuable information but might be outdated):
```markdown
{existing_doc}
```''' if existing_doc else ''}

---

Documentation template (generated from current source code - this reflects the most up-to-date structure):

Make sure that:
1. **You describe all the bullet points ( properties and methods) mentioned in this template, under relevant class section. Do not ommit any.**
2. **You stick to the format specified in this template when describing properties and methods.**. In particular, each property or method should be described in a separate bullet point.

```markdown
{template}
```

---

### Instructions for Documentation Generation:
1. **Follow the provided template** – it reflects the most current code structure and formatting, therefore it should serve as the primary basis for documentation.
2. **Incorporate valuable information from the existing documentation**, if available. However, verify all details against the current source code and ensure consistency with the template’s format.
3. **Clearly describe the purpose of the file** as well as the roles of all classes, functions, and variables.
    * make sure you describe **ALL** properties and methods mentioned in the template, under relevant class section. Do not ommit any.
4. **Document class inheritance relationships**, including how derived classes extend base class functionality.
5. **Explain the purpose of all included headers**, especially non-standard or custom ones.
6. **Keep function descriptions concise**:
   - Summarize each function’s purpose in **one line** (a single bullet point in the list).
   - **Omit argument lists and return types** for brevity.
7. **Highlight non-obvious insights or implementation details**:
   - Extract meaningful insights from the source code or existing documentation.
   - Quote relevant equations in LaTeX notation. This is especially important for functions related to physics and mathematics.
   - Reference external documents, such as scientific articles or webpages, when applicable.
8. **Focus on the big picture and core principles**:
   - Explain the rationale behind classes and functions instead of merely describing them.
   - Adjust the level of detail according to significance:
     - **Trivial functions** should have very brief descriptions.
     - **Complex or critical functions** should include details on their internal logic and implementation principles.
   - Provide **context and interconnections** that are not obvious from function/class names alone—details that would otherwise require reading the implementation.

---

### Objective:
Produce **concise, clear, and structured documentation** that effectively conveys the design, purpose, and insights of the code while maintaining readability and consistency.

Avoid vague wording and unnecessary formalities—focus on delivering practical and insightful explanations.

"""
    if bSavePrompt:
        prompt_file = os.path.join(output_dir, rel_path + ".prompt.md")
        with open(prompt_file, 'w') as f: f.write(prompt)
        #exit(0)

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
#output_dir =  "/home/prokop/git/FireCore/doc/Markdown"
output_dir =  "/home/prokop/git/SimpleSimulationEngine/doc/Markdown"
model_name = "fzu-qwen2_7b_1m"
#model_name = "gemini-flash"


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
#agent = AgentGoogle(model_name)
agent.set_system_prompt(system_prompt)

# Process each file
file_list = read_file_list(fname)
for file_path in file_list:
    try:
        print(f"Processing {file_path}")
        process_cpp_file(file_path, output_dir, agent)
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
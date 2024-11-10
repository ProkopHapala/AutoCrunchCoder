#import os
#from .AgentDeepSeek import AgentDeepSeek

import os
import json
from .AgentDeepSeek import AgentDeepSeek
from . import ctags

def find_function_end(lines, start_line):
    """Find end of function by matching braces"""
    brace_count = 0
    found_opening = False
    for i in range(start_line, len(lines)):
        line = lines[i]
        brace_count += line.count('{') - line.count('}')
        if '{' in line: found_opening = True
        if found_opening and brace_count == 0:
            return i + 1
    return -1  # Function end not found

class CodeDocumenter:
    def __init__(self, context_strategy="whole_file", max_context_size=100000 ):
        self.agent = None
        self.files_dict = None
        self.classes_dict = None
        self.free_functions = None
        #self.setup_agent(agent_type)
        self.bLogPrompts = True
        self.max_context_size = max_context_size
        self.context_strategy = context_strategy

    def setup_agent(self, agent_type="deepseek" ):
        """Setup and verify LLM agent connection"""
        try:
            if agent_type == "deepseek":
                self.agent = AgentDeepSeek(template_name="deepseek-coder", base_url="https://api.deepseek.com/beta" )
                # Test connection with a simple query
                test_response = self.agent.fim_completion(
                    prefix="/// @brief test_connection\n",
                    suffix="void test_connection() {}\n"
                )
                return len(test_response) > 0
            else:
                raise ValueError(f"Unsupported agent type: {agent_type}")
        except Exception as e:
            print(f"Failed to setup agent: {e}")
            return False

    def print_database_stats(self):
        """Print statistics about loaded database"""
        if not self._validate_database():
            print("Database not properly initialized!")
            return

        print("\nDatabase Statistics:")
        print(f"Number of classes: {len(self.classes_dict)}")
        print(f"Number of free functions: {len(self.free_functions)}")
        
        total_methods = sum(len(cls_data[loc]['methods']) 
                        for cls in self.classes_dict.values() 
                        for loc, cls_data in cls.items())
        print(f"Total number of methods: {total_methods}")

    def read_file_content(self, file_path):
        """Read the entire file content"""
        full_path = self.project_path + file_path
        with open(full_path, 'r') as f:
            return f.read()
            
    def read_markdown_docs(self, file_path):
        """Read related markdown documentation if exists"""
        md_path = file_path.replace('.cpp', '.md').replace('.h', '.md')
        if os.path.exists(md_path):
            with open(md_path, 'r') as f:
                return f.read()
        return ""

    def get_function_context(self, file_content, line_number, window=100):
        """Extract relevant context around the function"""
        lines = file_content.split('\n')
        start = max(0, line_number - window)
        end = min(len(lines), line_number + window)
        return '\n'.join(lines[start:end])

    def get_function_context_wholefile(self, file_content, line_number):
        """Get whole file if it fits within context window"""
        if len(file_content) <= self.max_context_size:
            return file_content
        else:
            return self.get_function_context(file_content, line_number)

    def get_function_context_body(self, file_content, line_number):
        """Extract just the function body from header to closing brace"""
        lines = file_content.split('\n')
        start = line_number - 1
        end = find_function_end(lines, start)
        if end == -1:
            # If function end not found, fall back to window method
            return self.get_function_context(file_content, line_number)
        return '\n'.join(lines[start:end])
    
    def prepare_database(self, project_path):
        """Generate and load ctags database"""
        self.project_path=project_path
        tags_file = "tags_all.json"
        ctags.run_ctags(tags_file, project_path)
        
        # Process tags with file-based organization
        #self.files_dict = ctags.process_ctags_json_by_files(tags_file, project_path)
        self.files_dict = ctags.process_ctags_json_by_files_2(tags_file, project_path)
        
        # Validate data
        return self._validate_database()

    def _validate_database(self):
        """Validate that we have proper data structures"""
        return self.files_dict is not None and len(self.files_dict) > 0

    def document_file(self, file_path):
        """Document all functions and methods in a single file"""
        #rel_path = os.path.relpath(file_path)
        if file_path not in self.files_dict:
            print(f"No information found for file: {file_path}")
            return
            
        file_info = self.files_dict[file_path]
        
        # Document free functions
        for func_name, func_info in file_info['free_functions'].items():
            print(f"Documenting free function: {func_name}")
            self.document_function(func_info, file_path)
            
        # Document methods
        for method_name, method_info in file_info['methods'].items():
            print(f"Documenting method: {method_name}")
            self.document_function(method_info, file_path)

    def document_file_diff(self, file_path):
        """Generate documentation for all functions in file and create a unified diff"""
        file_info = self.files_dict[file_path]
        full_path = self.project_path + file_path
        
        # Read original file
        with open(full_path, 'r') as f:
            orig_lines = f.readlines()
        new_lines = orig_lines.copy()
        
        docs = []   # Generate all docstrings first
        processed_methods = set()  # Keep track of processed methods by line number

        method_lines = {(method_info['line'], method_name)  for method_name, method_info in file_info['methods'].items()}  # Create set of method names and their line numbers

        # Document free functions
        for func_name, func_info in file_info['free_functions'].items():
            if (func_info['line'], func_name) not in method_lines:
                print(f"Generating doc for free function: {func_name}")
                doc_string = self.generate_function_doc(func_info, file_path)
                docs.append((func_info['line'], doc_string))
                
        # Document methods
        # for method_name, method_info in file_info['methods'].items():
        #     print(f"Generating doc for method: {method_name}")
        #     doc_string = self.generate_function_doc(method_info, file_path)
        #     docs.append((method_info['line'], doc_string))

        # Document methods
        for method_name, method_info in file_info['methods'].items():
            line_num = method_info['line']
            if line_num not in processed_methods:
                print(f"Generating doc for method: {method_name}")
                doc_string = self.generate_function_doc(method_info, file_path)
                docs.append((line_num, doc_string))
                processed_methods.add(line_num)
        
        docs.sort(reverse=True)        # Sort by line number in reverse order to insert from bottom up
        
        # Insert all docstrings
        for line_num, doc_string in docs:
            # Get proper indentation
            target_line = orig_lines[line_num - 1]
            indent = ' ' * (len(target_line) - len(target_line.lstrip()))
            doc_lines = [f"{indent}{line}\n" for line in doc_string.split('\n')]
            new_lines[line_num - 1:line_num - 1] = doc_lines
        
        diff_file = f"{full_path}.diff"      # Generate diff file name
        
        # Create unified diff
        with open(diff_file, 'w') as f:
            f.write(f"--- {full_path}\n")
            f.write(f"+++ {full_path}\n")
            
            # Generate unified diff format
            from difflib import unified_diff
            diff = unified_diff(orig_lines, new_lines, 
                            fromfile=full_path, 
                            tofile=full_path,
                            lineterm='')
            
            f.writelines('\n'.join(diff))
        
        print(f"Diff file generated: {diff_file}")
        return diff_file

    def log_prompt(self, prefix, suffix, file_path, func_name, scope=""):
        """Write the complete prompt to a debug file for inspection"""
        full_name = f"{scope}::{func_name}" if scope else func_name
        debug_file = f"debug_prompts/{file_path.replace('/', '_')}_{full_name}.md"
        
        os.makedirs(os.path.dirname(debug_file), exist_ok=True)
        
        with open(debug_file, 'w') as f:
            #f.write("# Complete Prompt for DeepSeek FIM\n\n")
            #f.write("## Prefix:\n")
            f.write(prefix)
            f.write("<DeepSeekFIM>")
            #f.write("\n## Suffix:\n")
            f.write(suffix)

    def generate_function_doc(self, function_info, file_path):
        """Generate documentation string for a function without modifying the file"""
        file_content = self.read_file_content(file_path)  # Read the entire file content
        md_content = self.read_markdown_docs(file_path)    # Read related markdown documentation if exists
        # Get function details
        func_name = function_info.get('name', '')
        scope     = function_info.get('scope', '')
        # Get the exact function header
        lines     = file_content.split('\n')
        header    = lines[function_info['line'] - 1].strip()
        full_name = f"{scope}::{func_name}" if scope else func_name    # Construct full qualified name

        #source_code = self.get_function_context(file_content, function_info['line'])

        # Select context based on strategy
        # if self.context_strategy == "whole_file":
        #     source_code = self.get_function_context_wholefile(file_content, function_info['line'])
        # elif self.context_strategy == "body":
        #     source_code = self.get_function_context_body(file_content, function_info['line'])
        # else:  # fallback to window
        #     source_code = self.get_function_context(file_content, function_info['line'])

        source_code_full = self.get_function_context_wholefile(file_content, function_info['line'])

        source_code_body = self.get_function_context_body(file_content, function_info['line'])

        # Create context information and include it in the prefix
        prefix = f"""
Write documentation string for function: `{full_name}` which is used within the following context:  

{md_content}

The source code is following:

```C++
{source_code_full}
```

Try to deduce as much as possible what the function does within context of the provided source code.

Here is once more just the source code of the relevant function:

```C++
{source_code_body}
```

Now fill-in-the-midle a Doxygen compatible documentation string for the give function `{full_name}`. 
Focus on the role (purpose) of the function, what it does, and document the parameters and return value.

/// @brief {full_name}
"""
        suffix = f"{header}"

        if self.bLogPrompts: self.log_prompt(prefix, suffix, file_path, func_name, scope)

        # Generate documentation using FIM with context in prefix
        return self.agent.fim_completion(
            prefix=prefix,
            suffix=suffix,
            max_tokens=200
        )

    def document_function(self, function_info, file_path):
        """Document a single function with full context"""
        doc_string = self.generate_function_doc(function_info, file_path)
        #print( "CodeDocumenter::document_function().doc_string \n", doc_string )
        # Insert documentation into file
        self.insert_documentation(file_path, doc_string, function_info['line'])

    def insert_documentation(self, file_path, doc_string, line_number):
        """Insert documentation into the file above the specified line"""
        full_path = self.project_path + file_path
        with open( full_path, 'r') as f:
            lines = f.readlines()
            
        # Find the correct indentation
        target_line = lines[line_number - 1]
        indentation = len(target_line) - len(target_line.lstrip())
        indent = ' ' * indentation
        
        
        doc_lines = [f"{indent}{line}\n" for line in doc_string.split('\n')]   # Format documentation with proper indentation
        lines[line_number - 1:line_number - 1] = doc_lines                      # Insert documentation
        
        # Create backup
        backup_path = f"{full_path}.bak"
        with open(backup_path, 'w') as f:
            f.writelines(lines)
            
        # Write the modified file
        with open(full_path, 'w') as f:
            f.writelines(lines)

    def process_project(self, project_path, selected_files, tags_file="tags_all.json" , agent_type="deepseek"):
        # 2. Check and prepare database
        if os.path.exists(tags_file):
            print(f"Using existing tags from {tags_file}")
        else:
            print(f"Generating new tags file {tags_file}")
            ctags.run_ctags(tags_file, project_path)
        
        # 3. Load and validate database
        if not self.prepare_database(project_path):
            print("Failed to prepare code database!")
            return False
            
        # 4. Initialize LLM agent
        if not self.setup_agent(agent_type=agent_type):
            print("Failed to initialize LLM agent!")
            return False
        
        # 5. Process selected files
        for file_path in selected_files:
            print(f"\nProcessing file: {file_path}")
            #self.document_file(file_path)
            self.document_file_diff(file_path)
            
        
        return True
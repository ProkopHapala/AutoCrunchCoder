#import os
#from .AgentDeepSeek import AgentDeepSeek

import os
import json
from .AgentDeepSeek import AgentDeepSeek
from . import ctags

class CodeDocumenter:
    def __init__(self, agent_type="deepseek"):
        self.agent = None
        self.files_dict = None
        self.classes_dict = None
        self.free_functions = None
        self.setup_agent(agent_type)

    def setup_agent(self, agent_type):
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

    # def prepare_database(self, project_path):
    #     """Generate and load ctags database"""
    #     try:
    #         # Generate tags
    #         tags_file = "tags_all.json"
    #         ctags.run_ctags(tags_file, project_path)
            
    #         # Process tags
    #         self.classes_dict, self.free_functions = ctags.process_ctags_json_claude(tags_file, project_path)
            
    #         # Validate data
    #         return self._validate_database()
    #     except Exception as e:
    #         print(f"Failed to prepare database: {e}")
    #         return False

    # def _validate_database(self):
    #     """Validate that we have proper data structures"""
    #     if self.classes_dict is None or self.free_functions is None:
    #         return False
    #     return len(self.classes_dict) > 0 or len(self.free_functions) > 0

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

    def prepare_database(self, project_path):
        """Generate and load ctags database"""
        #try:
        # Generate tags
        self.project_path=project_path
        tags_file = "tags_all.json"
        ctags.run_ctags(tags_file, project_path)
        
        # Process tags with file-based organization
        #self.files_dict = ctags.process_ctags_json_by_files(tags_file, project_path)
        self.files_dict = ctags.process_ctags_json_by_files_2(tags_file, project_path)
        
        # Validate data
        return self._validate_database()
        #except Exception as e:
        #    print(f"Failed to prepare database: {e}")
        #    return False

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


    def document_function(self, function_info, file_path):
        """Document a single function with full context"""
        # Read the entire file content
        file_content = self.read_file_content(file_path)
        
        # Read related markdown documentation if exists
        md_content = self.read_markdown_docs(file_path)
        
        # Get function details
        func_name = function_info.get('name', '')
        scope = function_info.get('scope', '')
        
        # Get the exact function header
        lines = file_content.split('\n')
        header = lines[function_info['line'] - 1].strip()
        
        # Construct full qualified name
        full_name = f"{scope}::{func_name}" if scope else func_name
        
        # Create context information and include it in the prefix
        prefix = f"""
// Context from source file:
{self.get_function_context(file_content, function_info['line'])}

// Additional documentation context:
{md_content}

/// @brief {full_name}
"""
        
        suffix = f"/// {header}"
    
        print( "CodeDocumenter::document_function().prefix \n", prefix )
        print( "CodeDocumenter::document_function().suffix \n", suffix )


        # Generate documentation using FIM with context in prefix
        doc_string = self.agent.fim_completion(
            prefix=prefix,
            suffix=suffix,
            max_tokens=200
        )

        print( "CodeDocumenter::document_function().doc_string \n", doc_string )
    
        # Insert documentation into file
        self.insert_documentation(file_path, doc_string, function_info['line'])

#     def document_function(self, function_info, file_path):
#         """Document a single function with full context"""
#         # Read the entire file content
#         file_content = self.read_file_content(file_path)
        
#         # Read related markdown documentation if exists
#         md_content = self.read_markdown_docs(file_path)
        
#         # Get function details
#         func_name = function_info.get('name', '')
#         scope = function_info.get('scope', '')
        
#         # Get the exact function header
#         lines = file_content.split('\n')
#         header = lines[function_info['line'] - 1].strip()
        
#         # Construct full qualified name
#         full_name = f"{scope}::{func_name}" if scope else func_name
        
#         # Create context for LLM
#         context = f"""
# Please document the following function/method:
# {header}

# Context from source file:
# {self.get_function_context(file_content, function_info['line'])}

# Additional documentation context:
# {md_content}
# """
      
#         # Generate documentation using FIM
#         doc = self.agent.fim_completion(
#             prefix=f"/// @brief {full_name}\n",
#             suffix=f"/// {header}",
#             prompt=context
#         )
        
#         # Insert documentation into file
#         self.insert_documentation(file_path, doc, function_info['line'])

    def insert_documentation(self, file_path, doc_string, line_number):
        """Insert documentation into the file above the specified line"""
        full_path = self.project_path + file_path
        with open( full_path, 'r') as f:
            lines = f.readlines()
            
        # Find the correct indentation
        target_line = lines[line_number - 1]
        indentation = len(target_line) - len(target_line.lstrip())
        indent = ' ' * indentation
        
        # Format documentation with proper indentation
        doc_lines = [f"{indent}{line}\n" for line in doc_string.split('\n')]
        
        # Insert documentation
        lines[line_number - 1:line_number - 1] = doc_lines
        
        # Create backup
        backup_path = f"{full_path}.bak"
        with open(backup_path, 'w') as f:
            f.writelines(lines)
            
        # Write the modified file
        with open(full_path, 'w') as f:
            f.writelines(lines)
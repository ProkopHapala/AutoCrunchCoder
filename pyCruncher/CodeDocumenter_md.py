from .AgentDeepSeek import AgentDeepSeek
from .AgentGoogle import AgentGoogle
from . import ctags
import os

class CodeDocumenter_md:
    def __init__(self, max_context_size=100000):
        self.agent = None
        self.files_dict = None
        self.project_path = None
        self.max_context_size = max_context_size
        self.bLogPrompts = True

    def setup_agent(self, agent_type="deepseek-coder" ):
        """Setup LLM agent connection"""
        try:
            if "deepseek" in agent_type:
                self.agent = AgentDeepSeek(template_name="deepseek-coder", base_url="https://api.deepseek.com/beta")        
            elif "gemini" in agent_type:
                self.agent = AgentGoogle("gemini-flash")
            else:
                raise ValueError(f"Unsupported agent type: {agent_type}")
            # test_response = self.agent.query("Test connection")
            # return len(test_response.text) > 0
            return True
        except Exception as e:
            print(f"Failed to setup agent: {e}")
            return False

    def prepare_database(self, project_path):
        """Generate and load ctags database"""
        self.project_path = project_path
        tags_file = "tags_all.json"
        ctags.run_ctags(tags_file, project_path)
        self.files_dict = ctags.process_ctags_json_by_files_2(tags_file, project_path)
        return self._validate_database()

    def _validate_database(self):
        """Validate that we have proper data structures"""
        return self.files_dict is not None and len(self.files_dict) > 0

    def read_file_content(self, file_path):
        """Read the entire file content"""
        full_path = self.project_path + file_path
        with open(full_path, 'r') as f:
            return f.read()

    def generate_markdown_skeleton(self, file_path):
        """Generate markdown template with all components listed"""
        file_info = self.files_dict[file_path]
        
        sections = []
        sections.append(f"# `{os.path.basename(file_path)}`\n")
        
        # Classes section
        if file_info['classes']:
            sections.append("# Classes\n")
            for class_name, class_info in file_info['classes'].items():
                sections.append(f"### `{class_name}`\n")
                sections.append("\n##### Properties\n")
                
                # Get members for this class
                class_members = {name: info for name, info in file_info['members'].items() 
                               if name.startswith(f"{class_name}::")}
                for member_name, member_info in class_members.items():
                    name = member_name.split("::")[-1]
                    sections.append(f"* `{name}`\n")
                
                sections.append("\n##### Methods\n")
                # Get methods for this class
                class_methods = {name: info for name, info in file_info['methods'].items() 
                               if name.startswith(f"{class_name}::")}
                for method_name, method_info in class_methods.items():
                    name = method_name.split("::")[-1]
                    sections.append(f"* `{name}`\n")
                sections.append("\n")
        
        # Free Functions section
        if file_info['free_functions']:
            sections.append("# Free Functions\n")
            for func_name, func_info in file_info['free_functions'].items():
                sections.append(f"* `{func_name}`\n")
            
        return '\n'.join(sections)

    def log_prompt(self, source_code, skeleton, file_path):
        """Write the complete prompt to a debug file for inspection"""
        debug_file = f"debug_prompts/{file_path.replace('/', '_')}_md.txt"
        os.makedirs(os.path.dirname(debug_file), exist_ok=True)
        with open(debug_file, 'w') as f:
            f.write("SOURCE CODE:\n")
            f.write(source_code)
            f.write("\nSKELETON:\n")
            f.write(skeleton)

    def get_all_files(self, project_path, filter="*.*"):
        """Get all files in the project path matching the filter"""
        print( f"CodeDocumenter_md.py::get_all_files() {project_path} filter={filter}" )
        import glob
        import os
        import fnmatch

        def find_files(directory, pattern):
            for root, dirs, files in os.walk(directory):
                for basename in files:
                    if fnmatch.fnmatch(basename, pattern):
                        filename = os.path.join(root, basename)
                        print( f"CodeDocumenter_md.py::get_all_files() add {filename}" )
                        yield filename

        patterns = filter.split(',')
        selected_files = []
        for pattern in patterns:
            pattern = pattern.strip()
            if pattern:
                selected_files.extend(find_files(project_path, pattern))
        
        return selected_files

    def read_example_doc(self, fname="file_documentation_example.md" ):
        """Read the example markdown documentation"""
        # example_path = os.path.join(os.path.dirname(__file__), fname )
        with open(fname, 'r') as f:
            return f.read()

    def generate_markdown_doc(self, file_path, skeleton=None ):
        """Generate complete markdown documentation for a file"""
        source_code = self.read_file_content(file_path)
        if skeleton is None: skeleton = self.generate_markdown_skeleton(file_path)
        out_name    = file_path + '.md'
        example     = self.read_example_doc()
        if self.bLogPrompts:  self.log_prompt(source_code, skeleton, file_path)
        prompt = f"""Given the following C++ source code, create a markdown documentation listing all classes, functions, and their brief descriptions.

The format of the markdown documentation should be as in the following example:
{example}
        
This is the actual source code you should process:
```cpp
{source_code}
```

Fill in descriptions of free functions, classes as well as their properties and methods listed in the following markdown documentation template based on the previous source code.
Keep descriptions concise and focus on the purpose and role of each component. Maintain the exact structure of the template, just add brief descriptions after each item.

{skeleton}
        """

        # Split path into directory and filename, add debug_ prefix and join it back
        debug_file = self.project_path + os.path.join(os.path.dirname(file_path), f"debug_{os.path.basename(file_path)}")
        with open(debug_file, 'w') as f:
            f.write(prompt)
        
        response = self.agent.query(prompt)

        llm_text = self.agent.get_response_text(response)

        # Write markdown output
        md_path = self.project_path + out_name
        with open(md_path, 'w') as f:
            f.write(llm_text)

        return md_path

    def process_project(self, project_path, selected_files=None, agent_type="deepseek", bLLM=True, bSaveSkeleton=False, filter="*.cpp,*.h,*.hpp,*.cc,*.cxx" ):
        """Process selected files in the project"""
        if not self.prepare_database(project_path):
            print("Failed to prepare code database!")
            return False
            
        if not self.setup_agent( agent_type=agent_type ):
            print("Failed to initialize LLM agent!")
            return False
        
        if selected_files is None:
            selected_files = self.get_all_files(project_path, filter)
        
        for file_path in selected_files:
            print(f"\nProcessing file: {file_path}")
            
            skeleton = self.generate_markdown_skeleton(file_path)

            if bSaveSkeleton:
                debug_file = self.project_path + file_path + ".skeleton.md"
                print(f"Documentation skeleton saved to : {debug_file}")
                with open(debug_file, 'w') as f:
                    f.write(skeleton)
            
            if bLLM:
                md_path = self.generate_markdown_doc(file_path, skeleton=skeleton)
                print(f"Generated markdown documentation: {md_path}")
            
        return True

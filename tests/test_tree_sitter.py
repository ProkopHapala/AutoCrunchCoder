from tree_sitter import Language, Parser
import os

# Define paths

'''
How to build tree-sitter-cpp (it is rather complicated, not just `pip install` ):
https://chatgpt.com/share/67367367-1f38-8003-9851-1adf08c15a55
'''

BUILD_PATH = 'build/my-languages.so'
VENDOR_CPP_PATH = '/home/prokophapala/SW/vendor/tree-sitter-cpp'

# Ensure the build directory exists
os.makedirs('build', exist_ok=True)

# Build the C++ language library if it doesn't exist
if not os.path.exists(BUILD_PATH):
    if not os.path.exists(VENDOR_CPP_PATH):
        raise FileNotFoundError(f"Missing Tree-sitter grammar at {VENDOR_CPP_PATH}. "
                                "Ensure you have cloned it.")
    
    Language.build_library(
        BUILD_PATH,
        [VENDOR_CPP_PATH]
    )

LANGUAGE = Language(BUILD_PATH, 'cpp')


def generate_markdown(file_name, classes_dict):
    markdown_output = f"# `{file_name}`\n\n"

    # Header for Classes
    markdown_output += "# Classes\n\n"

    for class_name, class_data in classes_dict.items():
        markdown_output += f"### `{class_name}`\n\n"
        
        # Add Methods
        if class_data['methods']:
            markdown_output += "##### Methods\n\n"
            for method in class_data['methods']:
                markdown_output += f"* `{method}`\n"
            markdown_output += "\n"

        # Add Properties
        if class_data['properties']:
            markdown_output += "##### Properties\n\n"
            for prop in class_data['properties']:
                markdown_output += f"* `{prop}`\n"
            markdown_output += "\n"

    return markdown_output

def parse_cpp_file(file_path):
    parser = Parser()
    parser.set_language(LANGUAGE)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")

    with open(file_path, 'r') as f:
        source_code = f.read()

    tree = parser.parse(bytes(source_code, "utf8"))
    root_node = tree.root_node

    classes_dict = {}

    # Traverse the syntax tree to find classes, methods, and properties
    def traverse(node, parent_class=None):
        if node.type == 'class_specifier':
            class_name = node.child_by_field_name('name')
            if class_name:
                class_name = class_name.text.decode('utf8')
                classes_dict[class_name] = {'methods': [], 'properties': []}
                parent_class = class_name

        elif node.type == 'function_definition' and parent_class:
            method_name = node.child_by_field_name('declarator')
            if method_name:
                method_name = method_name.text.decode('utf8')
                classes_dict[parent_class]['methods'].append(method_name)

        elif node.type == 'field_declaration' and parent_class:
            property_name = node.child_by_field_name('declarator')
            if property_name:
                property_name = property_name.text.decode('utf8')
                classes_dict[parent_class]['properties'].append(property_name)

        for child in node.children:
            traverse(child, parent_class)

    traverse(root_node)
    return classes_dict

def main():
    project_path = os.path.expanduser("~/git/FireCore/cpp")
    selected_files = ["common/molecular/MolWorld_sp3_simple.h"]

    for file_path in selected_files:
        full_path = os.path.join(project_path, file_path)
        try:
            class_info = parse_cpp_file(full_path)
            markdown = generate_markdown(file_path, class_info)
            #save markdown to file
            with open(f"debug_tree_sitter.md", "w") as f: f.write(markdown)

            #print(f"Classes in {file_path}: {class_info}")
        except FileNotFoundError as e:
            print(e)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    main()

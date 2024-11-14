from tree_sitter import Language, Parser
import os
from utils import hello

# Load the C++ language
Language.build_library(
  'build/my-languages.so',
  [
    'vendor/tree-sitter-cpp'
  ]
)

CPP_LANGUAGE = Language('build/my-languages.so', 'cpp')

def parse_cpp_file(file_path):
    parser = Parser()
    parser.set_language(CPP_LANGUAGE)

    with open(file_path, 'r') as f:
        source_code = f.read()

    tree = parser.parse(bytes(source_code, "utf8"))
    root_node = tree.root_node

    classes_dict = {}

    # Traverse the syntax tree to find classes, methods, and properties
    def traverse(node, parent_class=None):
        if node.type == 'class_specifier':
            class_name = node.child_by_field_name('name').text.decode('utf8')
            classes_dict[class_name] = {'methods': [], 'properties': []}
            parent_class = class_name

        elif node.type == 'function_definition' and parent_class:
            method_name = node.child_by_field_name('declarator').text.decode('utf8')
            classes_dict[parent_class]['methods'].append(method_name)

        elif node.type == 'field_declaration' and parent_class:
            property_name = node.child_by_field_name('declarator').text.decode('utf8')
            classes_dict[parent_class]['properties'].append(property_name)

        for child in node.children:
            traverse(child, parent_class)

    traverse(root_node)
    return classes_dict

def main():
    hello()
    project_path = os.path.expanduser("~/git/FireCore/cpp")
    selected_files = ["/common/molecular/MolWorld_sp3_simple.h"]

    for file_path in selected_files:
        full_path = os.path.join(project_path, file_path)
        class_info = parse_cpp_file(full_path)
        print(f"Classes in {file_path}: {class_info}")

if __name__ == "__main__":
    main()

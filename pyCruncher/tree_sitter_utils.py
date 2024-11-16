import tree_sitter
import os

# Define paths
BUILD_PATH = 'build/my-languages.so'
VENDOR_CPP_PATH = '/home/prokophapala/SW/vendor/tree-sitter-cpp'

def get_parser(language):
    """
    Initialize a tree-sitter parser for the specified language
    """
    if language.lower() == "cpp":
        # Ensure the build directory exists
        os.makedirs('build', exist_ok=True)

        # Build the C++ language library if it doesn't exist
        if not os.path.exists(BUILD_PATH):
            if not os.path.exists(VENDOR_CPP_PATH):
                raise FileNotFoundError(f"Missing Tree-sitter grammar at {VENDOR_CPP_PATH}. "
                                     "Ensure you have cloned it.")
            
            tree_sitter.Language.build_library(
                BUILD_PATH,
                [VENDOR_CPP_PATH]
            )

        # Create and return the parser
        parser = tree_sitter.Parser()
        cpp_language = tree_sitter.Language(BUILD_PATH, 'cpp')
        parser.set_language(cpp_language)
        return parser
    else:
        raise ValueError(f"Unsupported language: {language}")

def get_node_text(node, source_bytes):
    """Get text content of a node"""
    return source_bytes[node.start_byte:node.end_byte].decode('utf8')

def get_qualified_name(node, source_bytes):
    """Build qualified name from node chain"""
    parts = []
    current = node
    
    # First, get the immediate identifier
    if current.type == 'identifier':
        parts.insert(0, get_node_text(current, source_bytes))
    
    # Then walk up the tree to build the full qualified name
    current = current.parent
    while current:
        if current.type == 'namespace_definition':
            # Get namespace name
            for child in current.children:
                if child.type == 'identifier':
                    parts.insert(0, get_node_text(child, source_bytes))
                    break
        elif current.type == 'class_specifier':
            # Get class name from the name field
            for child in current.children:
                if child.type == 'name':
                    for subchild in child.children:
                        if subchild.type == 'identifier':
                            parts.insert(0, get_node_text(subchild, source_bytes))
                            break
                    break
        elif current.type == 'field_declaration':
            # This is a class member
            current = current.parent
            if current and current.type == 'class_specifier':
                for child in current.children:
                    if child.type == 'name':
                        for subchild in child.children:
                            if subchild.type == 'identifier':
                                parts.insert(0, get_node_text(subchild, source_bytes))
                                break
                        break
        current = current.parent
    
    return '::'.join(parts) if parts else ''

def visit_tree(node, callback):
    """Visit all nodes in the syntax tree"""
    callback(node)
    for child in node.children:
        visit_tree(child, callback)

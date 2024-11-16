import os
import subprocess

def setup_tree_sitter():
    """Setup tree-sitter and required language parsers"""
    # Create build directory
    os.makedirs('build', exist_ok=True)
    
    # Setup C++ parser
    if not os.path.exists('tree-sitter-cpp'):
        subprocess.run(['git', 'clone', 'https://github.com/tree-sitter/tree-sitter-cpp.git'], check=True)
    
    # Setup Python parser
    if not os.path.exists('tree-sitter-python'):
        subprocess.run(['git', 'clone', 'https://github.com/tree-sitter/tree-sitter-python.git'], check=True)

if __name__ == '__main__':
    setup_tree_sitter()

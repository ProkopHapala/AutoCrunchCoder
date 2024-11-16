import os
import unittest
from pyCruncher.dependency_graph_tree_sitter import DependencyGraphTreeSitter

class TestDependencyGraphTreeSitterDeps(unittest.TestCase):
    def setUp(self):
        self.project_path = os.path.expanduser("~/git/FireCore/cpp")
        self.test_file = os.path.join(self.project_path, "common/molecular/MolWorld_sp3_simple.h")
        self.processor = DependencyGraphTreeSitter()

    def test_find_dependencies(self):
        """Test finding dependencies of a C++ file"""
        # First verify the test file exists
        self.assertTrue(os.path.exists(self.test_file), f"Test file not found: {self.test_file}")
        
        # Find dependencies
        deps = self.processor.find_dependencies(self.test_file, self.project_path)
        
        # Verify we found some dependencies
        self.assertGreater(len(deps), 0, "No dependencies found")
        print(f"\nFound {len(deps)} dependencies:")
        for dep in sorted(deps):
            print(f"  {os.path.relpath(dep, self.project_path)}")

    def test_parse_with_deps(self):
        """Test parsing a file with all its dependencies"""
        # Parse the file and its dependencies
        self.processor.parse_file_with_deps(self.test_file, self.project_path)
        
        # Verify we found some functions and classes
        print("\nFunctions found:")
        for func_name, func_info in self.processor.functions.items():
            print(f"  {func_name}")
            
        print("\nClasses found:")
        for class_name, class_info in self.processor.classes.items():
            print(f"  {class_name}")
        
        self.assertGreater(len(self.processor.functions), 0, "No functions found")
        self.assertGreater(len(self.processor.classes), 0, "No classes found")

if __name__ == '__main__':
    unittest.main()

import unittest
from pyCruncher.cpp_type_analyzer import (
    TypeCollector, TypeRegistry, ScopeType,
    Location, Scope, TypeInfo, MethodInfo, VariableInfo, ClassInfo, AccessSpecifier
)
from pyCruncher.tree_sitter_utils import get_parser

class TestTypeCollector(unittest.TestCase):
    def setUp(self):
        self.collector = TypeCollector(verbosity=2)  # Increased verbosity for debugging
        self.parser = get_parser("cpp")

    def _parse_and_process(self, code: str) -> None:
        """Helper to parse and process C++ code"""
        tree = self.parser.parse(code.encode())
        self.collector.process_node(tree.root_node, code.encode(), "test.cpp")

    def test_basic_types(self):
        """Test that basic C++ types are initialized"""
        registry = TypeRegistry()
        basic_types = ["int", "float", "double", "char", "bool"]
        for type_name in basic_types:
            self.assertIn(type_name, registry.types)

    def test_namespace_processing(self):
        """Test processing of namespace definitions"""
        code = """
        namespace outer {
            namespace inner {
                int x;
            }
        }
        """
        self._parse_and_process(code)
        
        # Check that namespaces were processed
        self.assertIn("outer", [s.name for s in self.collector.registry.global_scope.children])
        outer_scope = next(s for s in self.collector.registry.global_scope.children if s.name == "outer")
        self.assertEqual(outer_scope.type, ScopeType.NAMESPACE)
        
        # Check inner namespace
        self.assertIn("inner", [s.name for s in outer_scope.children])
        inner_scope = next(s for s in outer_scope.children if s.name == "inner")
        self.assertEqual(inner_scope.type, ScopeType.NAMESPACE)

    def test_scope_names(self):
        """Test generation of fully qualified scope names"""
        # Create nested scopes
        registry = TypeRegistry()
        
        # Create namespace scope
        ns_scope = registry.enter_scope(ScopeType.NAMESPACE, "myns")
        self.assertEqual(ns_scope.get_full_name(), "myns")
        
        # Create class scope inside namespace
        class_scope = registry.enter_scope(ScopeType.CLASS, "MyClass")
        self.assertEqual(class_scope.get_full_name(), "myns::MyClass")
        
        # Create function scope inside class
        func_scope = registry.enter_scope(ScopeType.FUNCTION, "method")
        self.assertEqual(func_scope.get_full_name(), "myns::MyClass::method")

    def test_location_tracking(self):
        """Test that source locations are tracked correctly"""
        code = """
        namespace test {
            int x;
        }
        """
        self._parse_and_process(code)
        
        # Find the namespace scope
        test_scope = next(s for s in self.collector.registry.global_scope.children if s.name == "test")
        
        # Check location information
        self.assertEqual(test_scope.location.file_path, "test.cpp")
        self.assertGreater(test_scope.location.end_line, test_scope.location.start_line)
        self.assertGreater(test_scope.location.end_byte, test_scope.location.start_byte)

    def test_type_registry(self):
        """Test TypeRegistry functionality"""
        registry = TypeRegistry()
        
        # Add a custom type
        scope = registry.global_scope
        type_info = TypeInfo("MyClass", scope)
        registry.add_type(type_info)
        
        # Check type retrieval
        self.assertIn("MyClass", registry.types)
        retrieved = registry.get_type("MyClass")
        self.assertEqual(retrieved.name, "MyClass")
        self.assertEqual(retrieved.scope, scope)

    def test_class_processing(self):
        """Test processing of class definitions with inheritance and members"""
        code = """
        class Base {
        public:
            int base_method();
        protected:
            float base_var;
        };
        
        class Derived : public Base {
        private:
            int private_var;
        public:
            void derived_method();
            double public_var;
        };
        """
        self._parse_and_process(code)
        
        # Check Base class
        base = self.collector.registry.get_type("Base")
        self.assertIsNotNone(base)
        self.assertIsInstance(base, ClassInfo)
        
        # Check Base class members
        self.assertIn("base_method", base.methods)
        self.assertEqual(base.methods["base_method"].access_specifier, AccessSpecifier.PUBLIC)
        
        self.assertIn("base_var", base.variables)
        self.assertEqual(base.variables["base_var"].access_specifier, AccessSpecifier.PROTECTED)
        self.assertEqual(base.variables["base_var"].type_name, "float")
        
        # Check Derived class
        derived = self.collector.registry.get_type("Derived")
        self.assertIsNotNone(derived)
        self.assertIsInstance(derived, ClassInfo)
        
        # Check inheritance
        self.assertEqual(derived.base_classes, ["Base"])
        
        # Check Derived class members
        self.assertIn("derived_method", derived.methods)
        self.assertEqual(derived.methods["derived_method"].access_specifier, AccessSpecifier.PUBLIC)
        self.assertEqual(derived.methods["derived_method"].return_type, "void")
        
        self.assertIn("private_var", derived.variables)
        self.assertEqual(derived.variables["private_var"].access_specifier, AccessSpecifier.PRIVATE)
        self.assertEqual(derived.variables["private_var"].type_name, "int")
        
        self.assertIn("public_var", derived.variables)
        self.assertEqual(derived.variables["public_var"].access_specifier, AccessSpecifier.PUBLIC)
        self.assertEqual(derived.variables["public_var"].type_name, "double")

    def test_class_in_namespace(self):
        """Test processing of classes within namespaces"""
        code = """
        namespace outer {
            class MyClass {
            public:
                void method();
            private:
                int var;
            };
        }
        """
        self._parse_and_process(code)
        
        # Check class is in correct namespace
        my_class = self.collector.registry.get_type("MyClass")
        self.assertIsNotNone(my_class)
        self.assertEqual(my_class.scope.get_full_name(), "outer")
        
        # Check class members
        self.assertIn("method", my_class.methods)
        self.assertEqual(my_class.methods["method"].access_specifier, AccessSpecifier.PUBLIC)
        
        self.assertIn("var", my_class.variables)
        self.assertEqual(my_class.variables["var"].access_specifier, AccessSpecifier.PRIVATE)

if __name__ == '__main__':
    unittest.main()

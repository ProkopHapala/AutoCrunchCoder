import unittest
from pyCruncher.cpp_type_analyzer import (
    TypeCollector, TypeRegistry, ScopeType,
    Location, Scope, TypeInfo, MethodInfo, VariableInfo, ClassInfo, AccessSpecifier
)
from pyCruncher.tree_sitter_utils import get_parser
import tempfile
import os

class TestTypeCollector(unittest.TestCase):
    def setUp(self):
        self.parser = get_parser("cpp")
        self.collector = TypeCollector(parser=self.parser, verbosity=2)

    def test_basic_types(self):
        """Test that basic C++ types are initialized"""
        # Create a temporary file with C++ code
        code = """
        class MyClass {
            int x;
            float y;
            char z;
        };
        """
        with tempfile.NamedTemporaryFile(suffix='.cpp', mode='w', delete=False) as f:
            f.write(code)
            f.flush()
            self.collector.process_file(f.name)

        # Check that the class was found
        my_class = self.collector.registry.get_type("MyClass")
        self.assertIsNotNone(my_class)
        self.assertEqual(my_class.name, "MyClass")
        self.assertEqual(len(my_class.fields), 3)

        # Check field types
        field_types = {field.name: field.type_name for field in my_class.fields}
        self.assertEqual(field_types["x"], "int")
        self.assertEqual(field_types["y"], "float")
        self.assertEqual(field_types["z"], "char")

    def test_location_tracking(self):
        """Test that source locations are tracked correctly"""
        code = """
        namespace test {
            class MyClass {
                void method() {}
            };
        }
        """
        with tempfile.NamedTemporaryFile(suffix='.cpp', mode='w', delete=False) as f:
            f.write(code)
            f.flush()
            self.collector.process_file(f.name)

        # Get the namespace scope
        test_scope = self.collector.registry.get_scope("test")
        self.assertIsNotNone(test_scope)
        self.assertEqual(test_scope.location.start[0], 2)

        # Get the class
        my_class = self.collector.registry.get_type("test::MyClass")
        self.assertIsNotNone(my_class)
        self.assertEqual(my_class.location.start[0], 3)

    def test_class_processing(self):
        """Test processing of class definitions with inheritance and members"""
        code = """
        class Base {
        public:
            void base_method() {}
        };

        class Derived : public Base {
        public:
            void derived_method() {}
        private:
            int x;
        };
        """
        with tempfile.NamedTemporaryFile(suffix='.cpp', mode='w', delete=False) as f:
            f.write(code)
            f.flush()
            self.collector.process_file(f.name)

        # Check base class
        base = self.collector.registry.get_type("Base")
        self.assertIsNotNone(base)
        self.assertEqual(base.name, "Base")
        self.assertIn("base_method", [m.name for m in base.methods])

        # Check derived class
        derived = self.collector.registry.get_type("Derived")
        self.assertIsNotNone(derived)
        self.assertEqual(derived.name, "Derived")
        self.assertIn("derived_method", [m.name for m in derived.methods])
        self.assertEqual(len(derived.base_classes), 1)
        self.assertEqual(derived.base_classes[0], "Base")

    def test_namespace_processing(self):
        """Test processing of namespace definitions"""
        code = """
        namespace outer {
            namespace inner {
                class MyClass {};
            }
        }
        """
        with tempfile.NamedTemporaryFile(suffix='.cpp', mode='w', delete=False) as f:
            f.write(code)
            f.flush()
            self.collector.process_file(f.name)

        # Check that the class was found in the correct namespace
        my_class = self.collector.registry.get_type("outer::inner::MyClass")
        self.assertIsNotNone(my_class)
        self.assertEqual(my_class.name, "MyClass")

    def test_scope_names(self):
        """Test generation of fully qualified scope names"""
        code = """
        namespace outer {
            namespace inner {
                class MyClass {};
            }
        }

        namespace inner {
            class AnotherClass {};
        }
        """
        with tempfile.NamedTemporaryFile(suffix='.cpp', mode='w', delete=False) as f:
            f.write(code)
            f.flush()
            self.collector.process_file(f.name)

        # Check scope names
        my_class = self.collector.registry.get_type("outer::inner::MyClass")
        self.assertIsNotNone(my_class)
        self.assertEqual(my_class.scope.get_full_name(), "outer::inner")

        another_class = self.collector.registry.get_type("inner::AnotherClass")
        self.assertIsNotNone(another_class)
        self.assertEqual(another_class.scope.get_full_name(), "inner")

    def test_class_in_namespace(self):
        """Test processing of classes within namespaces"""
        code = """
        namespace outer {
            class MyClass {
                void method() {}
            };
        }
        """
        with tempfile.NamedTemporaryFile(suffix='.cpp', mode='w', delete=False) as f:
            f.write(code)
            f.flush()
            self.collector.process_file(f.name)

        # Check class in namespace
        my_class = self.collector.registry.get_type("outer::MyClass")
        self.assertIsNotNone(my_class)
        self.assertEqual(my_class.scope.get_full_name(), "outer")

    def test_function_calls(self):
        """Test tracking of function calls within methods"""
        code = """
        class Helper {
        public:
            void helper_method() {}
        };

        class MyClass {
        public:
            void method1() {
                Helper h;
                h.helper_method();
            }

            void method2() {
                method1();
            }
        };
        """
        with tempfile.NamedTemporaryFile(suffix='.cpp', mode='w', delete=False) as f:
            f.write(code)
            f.flush()
            self.collector.process_file(f.name)

        # Check class methods
        my_class = self.collector.registry.get_type("MyClass")
        self.assertIsNotNone(my_class)
        self.assertIn("method1", [m.name for m in my_class.methods])
        self.assertIn("method2", [m.name for m in my_class.methods])

        # Check method calls
        method2 = next(m for m in my_class.methods if m.name == "method2")
        self.assertEqual(len(method2.calls), 1)
        self.assertEqual(method2.calls[0].name, "method1")

    def test_cross_file_dependencies(self):
        """Test resolution of dependencies across multiple files"""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create header file
            header_path = os.path.join(tmpdir, "helper.h")
            with open(header_path, 'w') as f:
                f.write("""
                class Helper {
                public:
                    void helper_method() {}
                };
                """)

            # Create implementation file
            impl_path = os.path.join(tmpdir, "main.cpp")
            with open(impl_path, 'w') as f:
                f.write("""
                #include "helper.h"
                class MyClass {
                    Helper h;
                };
                """)

            # Process the implementation file
            self.collector.process_file(impl_path)

            # Check that both classes were found
            helper_class = self.collector.registry.get_type("Helper")
            self.assertIsNotNone(helper_class)
            self.assertEqual(helper_class.name, "Helper")

            my_class = self.collector.registry.get_type("MyClass")
            self.assertIsNotNone(my_class)
            self.assertEqual(my_class.name, "MyClass")

            # Check that the include was tracked
            impl_file_info = self.collector.registry.files[impl_path]
            self.assertIn(header_path, impl_file_info.includes)

if __name__ == '__main__':
    unittest.main()

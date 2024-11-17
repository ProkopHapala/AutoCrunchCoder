import unittest
import tempfile
import logging
from tree_sitter import Language, Parser
from pyCruncher.cpp_type_analyzer import (
    TypeCollector, TypeRegistry, ScopeType,
    Location, Scope, TypeInfo, MethodInfo, VariableInfo, ClassInfo, AccessSpecifier,
    setup_logging
)
from pyCruncher.tree_sitter_utils import get_parser
import os

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)

class TestTypeCollector(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Create a new parser for each test
        Language.build_library(
            'build/my-languages.so',
            [
                'tree-sitter-cpp'
            ]
        )
        CPP_LANGUAGE = Language('build/my-languages.so', 'cpp')
        parser = Parser()
        parser.set_language(CPP_LANGUAGE)
        # Initialize the type collector with high verbosity
        self.collector = TypeCollector(parser, verbosity=3)  # Increase verbosity for debugging

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
        template<typename T>
        class Helper {
        public:
            void helper_method() {}
            static void static_method() {}
            T template_method() {}
        };

        class MyClass {
        public:
            void method1() {
                Helper<int> h;
                h.helper_method();
                h.template_method<float>();
                Helper<int>::static_method();
            }

            void method2() {
                method1();
                Helper<int> h2;
                h2.helper_method().template_method<double>();
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

        # Get method1 and check its calls
        method1 = next(m for m in my_class.methods if m.name == "method1")
        print("\nFound calls in method1:")
        for call in method1.calls:
            print(f"  - {call.name} (object: {call.object}, args: {call.arguments}, template_args: {call.template_args})")
        self.assertEqual(len(method1.calls), 4)  # Constructor + 3 method calls
        
        # Check constructor call
        constructor_call = next(c for c in method1.calls if c.is_constructor)
        self.assertEqual(constructor_call.name, "Helper")
        self.assertTrue(constructor_call.is_constructor)

        # Check method calls
        helper_call = next(c for c in method1.calls if c.name == "helper_method")
        self.assertEqual(helper_call.object, "h")
        
        template_call = next(c for c in method1.calls if c.name == "template_method")
        self.assertEqual(template_call.object, "h")
        self.assertEqual(template_call.template_args, ["float"])

        static_call = next(c for c in method1.calls if c.is_static)
        self.assertEqual(static_call.name, "static_method")
        self.assertTrue(static_call.is_static)

        # Get method2 and check its calls
        method2 = next(m for m in my_class.methods if m.name == "method2")
        self.assertEqual(len(method2.calls), 3)  # method1() + constructor + 2 chained calls

        # Check method calls
        method_call = next(c for c in method2.calls if c.name == "method1")
        self.assertIsNone(method_call.object)  # Local method call has no object

        constructor_call = next(c for c in method2.calls if c.is_constructor)
        self.assertEqual(constructor_call.name, "Helper")
        self.assertTrue(constructor_call.is_constructor)

        chained_call = next(c for c in method2.calls if c.name == "helper_method")
        self.assertEqual(chained_call.object, "h2")

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

    def test_method_resolution(self):
        """Test resolution of method calls and parameter tracking"""
        code = """
        class Helper {
        public:
            Helper(int x) {}
            void helper_method(int x, float y) {}
            static void static_method(const std::string& msg) {}
        };

        class MyClass {
        private:
            Helper* helper;
        public:
            MyClass() : helper(new Helper(42)) {}
            
            void process(int value) {
                helper->helper_method(value, 3.14f);
                Helper::static_method("test");
                Helper h2(123);
                h2.helper_method(456, 7.89f);
            }
        };
        """
        
        self.collector.process_code(code)
        
        my_class = next(c for c in self.collector.classes if c.name == "MyClass")
        process_method = next(m for m in my_class.methods if m.name == "process")
        
        # Check constructor call
        constructor_call = next(c for c in process_method.calls if c.is_constructor)
        self.assertEqual(constructor_call.name, "Helper")
        self.assertEqual(len(constructor_call.arguments), 1)
        self.assertEqual(constructor_call.arguments[0], "123")

        # Check instance method call through pointer
        pointer_call = next(c for c in process_method.calls if "->" in c.object)
        self.assertEqual(pointer_call.name, "helper_method")
        self.assertEqual(pointer_call.object, "helper->")
        self.assertEqual(len(pointer_call.arguments), 2)
        self.assertEqual(pointer_call.arguments[0], "value")
        self.assertEqual(pointer_call.arguments[1], "3.14f")

        # Check static method call
        static_call = next(c for c in process_method.calls if c.is_static)
        self.assertEqual(static_call.name, "static_method")
        self.assertTrue(static_call.is_static)
        self.assertEqual(len(static_call.arguments), 1)
        self.assertEqual(static_call.arguments[0], '"test"')

        # Check instance method call through object
        instance_call = next(c for c in process_method.calls if c.object == "h2")
        self.assertEqual(instance_call.name, "helper_method")
        self.assertEqual(instance_call.object, "h2")
        self.assertEqual(len(instance_call.arguments), 2)
        self.assertEqual(instance_call.arguments[0], "456")
        self.assertEqual(instance_call.arguments[1], "7.89f")

    def test_basic_method_call(self):
        """Test basic method call tracking"""
        code = """
        class Helper {
        public:
            void helper_method() {}
        };
        
        class MyClass {
            void method() {
                Helper h;
                h.helper_method();
            }
        };
        """
        self.collector.process_code(code)
        my_class = self.collector.registry.get_type("MyClass")
        method = next(m for m in my_class.methods if m.name == "method")
        
        # Should have 2 calls: constructor and method
        self.assertEqual(len(method.calls), 2)
        
        # Check constructor call
        constructor_call = next(c for c in method.calls if c.is_constructor)
        self.assertEqual(constructor_call.name, "Helper")
        self.assertTrue(constructor_call.is_constructor)
        
        # Check method call
        method_call = next(c for c in method.calls if not c.is_constructor)
        self.assertEqual(method_call.name, "helper_method")
        self.assertEqual(method_call.object, "h")
        self.assertEqual(method_call.arguments, [])

    def test_template_method_call(self):
        """Test template method call tracking"""
        code = """
        template<typename T>
        class Helper {
        public:
            T template_method() {}
        };
        
        class MyClass {
            void method() {
                Helper<int> h;
                h.template_method<float>();
            }
        };
        """
        self.collector.process_code(code)
        my_class = self.collector.registry.get_type("MyClass")
        method = next(m for m in my_class.methods if m.name == "method")
        
        # Check template method call
        template_call = next(c for c in method.calls if not c.is_constructor)
        self.assertEqual(template_call.name, "template_method")
        self.assertEqual(template_call.object, "h")
        self.assertEqual(template_call.template_args, ["float"])

    def test_static_method_call(self):
        """Test static method call tracking"""
        code = """
        class Helper {
        public:
            static void static_method(const std::string& msg) {}
        };
        
        class MyClass {
            void method() {
                Helper::static_method("test");
            }
        };
        """
        self.collector.process_code(code)
        my_class = self.collector.registry.get_type("MyClass")
        method = next(m for m in my_class.methods if m.name == "method")
        
        # Check static method call
        static_call = next(c for c in method.calls if c.is_static)
        self.assertEqual(static_call.name, "static_method")
        self.assertEqual(static_call.arguments, ["\"test\""])
        self.assertTrue(static_call.is_static)

    def test_pointer_method_call(self):
        """Test method call through pointer"""
        code = """
        class Helper {
        public:
            void helper_method(int x, float y) {}
        };
        
        class MyClass {
            Helper* helper;
            void method() {
                helper->helper_method(42, 3.14f);
            }
        };
        """
        self.collector.process_code(code)
        my_class = self.collector.registry.get_type("MyClass")
        method = next(m for m in my_class.methods if m.name == "method")
        
        # Check pointer method call
        pointer_call = next(c for c in method.calls if "->" in c.object)
        self.assertEqual(pointer_call.name, "helper_method")
        self.assertEqual(pointer_call.object, "helper->")
        self.assertEqual(pointer_call.arguments, ["42", "3.14f"])

    def test_template_method_name_parsing(self):
        """Test parsing template method name without template arguments"""
        code = """
        template<typename T>
        class Helper {
        public:
            T template_method() {}
        };
        
        class MyClass {
            void method() {
                Helper<int> h;
                h.template_method();  // No template args in call
            }
        };
        """
        self.collector.process_code(code)
        my_class = self.collector.registry.get_type("MyClass")
        method = next(m for m in my_class.methods if m.name == "method")
        
        method_call = next(c for c in method.calls if not c.is_constructor)
        self.assertEqual(method_call.name, "template_method")
        self.assertEqual(method_call.template_args, [])

    def test_template_method_with_args_parsing(self):
        """Test parsing template method name with template arguments"""
        code = """
        template<typename T>
        class Helper {
        public:
            template<typename U>
            U template_method() {}
        };
        
        class MyClass {
            void method() {
                Helper<int> h;
                h.template_method<float>();
            }
        };
        """
        self.collector.process_code(code)
        my_class = self.collector.registry.get_type("MyClass")
        method = next(m for m in my_class.methods if m.name == "method")
        
        method_call = next(c for c in method.calls if not c.is_constructor)
        self.assertEqual(method_call.name, "template_method")
        self.assertEqual(method_call.template_args, ["float"])

    def test_static_method_name_parsing(self):
        """Test parsing static method name without class scope"""
        code = """
        class Helper {
        public:
            static void static_method() {}
        };
        
        class MyClass {
            void method() {
                Helper::static_method();
            }
        };
        """
        self.collector.process_code(code)
        my_class = self.collector.registry.get_type("MyClass")
        method = next(m for m in my_class.methods if m.name == "method")
        
        static_call = next(c for c in method.calls if c.is_static)
        self.assertEqual(static_call.name, "static_method")
        self.assertEqual(static_call.class_scope, "Helper")

    def test_static_method_with_namespace_parsing(self):
        """Test parsing static method name with namespace and class scope"""
        code = """
        namespace ns {
            class Helper {
            public:
                static void static_method() {}
            };
        }
        
        class MyClass {
            void method() {
                ns::Helper::static_method();
            }
        };
        """
        self.collector.process_code(code)
        my_class = self.collector.registry.get_type("MyClass")
        method = next(m for m in my_class.methods if m.name == "method")
        
        static_call = next(c for c in method.calls if c.is_static)
        self.assertEqual(static_call.name, "static_method")
        self.assertEqual(static_call.class_scope, "ns::Helper")

    def test_node_text_extraction(self):
        """Test basic node text extraction"""
        code = """
        class MyClass {
            void method() {}
        };
        """
        # Get the AST root node
        tree = self.collector.parser.parse(bytes(code, "utf8"))
        root = tree.root_node
        
        print("\nRoot node type:", root.type)
        for node in root.children:
            print(f"Child node type: {node.type}")
            if node.type == "class_specifier":
                print("\nClass node children:")
                for child in node.children:
                    print(f"  Child type: {child.type}")
                    if hasattr(child, 'text'):
                        print(f"  Child text: {child.text.decode('utf8')}")
        
        # Find the class node
        class_node = None
        for node in root.children:
            if node.type == "class_specifier":
                class_node = node
                break
        
        self.assertIsNotNone(class_node, "Failed to find class node")
        
        # Find the method node in the class body
        method_node = None
        class_body = class_node.child_by_field_name("body")
        if class_body:
            for node in class_body.children:
                print(f"Body child type: {node.type}")
                if node.type == "function_definition":
                    method_node = node
                    break
        
        self.assertIsNotNone(method_node, "Failed to find method node")
        
        # Test node text extraction
        method_name = self.collector._extract_node_text(
            method_node.child_by_field_name("declarator"),
            code
        )
        self.assertEqual(method_name, "method")
        
        # Test with None node
        self.assertIsNone(self.collector._extract_node_text(None, code))

if __name__ == '__main__':
    unittest.main()

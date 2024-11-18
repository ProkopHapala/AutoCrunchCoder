import pytest
from tree_sitter import Language, Parser
from pyCruncher.python_type_analyzer import TypeCollector

@pytest.fixture
def collector():
    # Initialize Tree-sitter parser
    parser = Parser()
    language_path = "/home/prokophapala/SW/vendor/tree-sitter-python"
    build_path = "/home/prokophapala/git/AutoCrunchCoder/tests/build/my-languages.so"
    Language.build_library(build_path, [language_path])
    language = Language(build_path, "python")
    parser.set_language(language)
    
    # Create TypeCollector
    return TypeCollector(parser, language)

def test_agent_hierarchy(collector):
    # Process all Agent-related files
    base_path = "/home/prokophapala/git/AutoCrunchCoder/pyCruncher"
    agent_files = [
        f"{base_path}/Agent.py",
        f"{base_path}/AgentAnthropic.py",
        f"{base_path}/AgentDeepSeek.py",
        f"{base_path}/AgentGoogle.py",
        f"{base_path}/AgentOpenAI.py"
    ]
    
    # Process each file
    for file_path in agent_files:
        collector.process_file(file_path)
    
    # Test imports
    base_imports = collector.registry.get_imports("Agent.py")
    assert base_imports is not None, "Base Agent imports not found"
    
    # Test class hierarchy
    base_agent = collector.registry.get_class("Agent")
    assert base_agent is not None, "Base Agent class not found"
    
    # Test derived classes
    derived_agents = {
        "AgentAnthropic.py": ("AnthropicAgent", "Agent"),
        "AgentDeepSeek.py": ("AgentDeepSeek", "AgentOpenAI"),
        "AgentGoogle.py": ("AgentGoogle", "Agent"),
        "AgentOpenAI.py": ("AgentOpenAI", "Agent")
    }
    
    for file_name, (class_name, parent_class) in derived_agents.items():
        agent_class = collector.registry.get_class(class_name)
        assert agent_class is not None, f"{class_name} class not found in {file_name}"
        # Now that inheritance tracking is implemented, we can test it:
        assert parent_class in agent_class.base_classes, f"{class_name} should inherit from {parent_class}"
    
    # Print class information for manual verification
    print("\nAgent Class Hierarchy Analysis:")
    print_class_info(collector, "Agent")
    for _, class_name in derived_agents.values():
        print_class_info(collector, class_name)

def print_class_info(collector, class_name):
    """Helper function to print class information"""
    print(f"\n{class_name}:")
    class_info = collector.registry.get_class(class_name)
    if class_info:
        method_names = [method.name for method in class_info.methods]
        print(f"  Methods: {', '.join(method_names)}")
        print(f"  Fields: {', '.join(class_info.fields)}")
        if hasattr(class_info, 'base_classes'):
            print(f"  Base Classes: {', '.join(class_info.base_classes)}")
    else:
        print("  Not found in registry")

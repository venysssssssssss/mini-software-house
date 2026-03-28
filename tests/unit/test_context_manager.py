"""Tests for CodeSummarizer — AST extraction of function signatures."""

from src.agents.context_manager import get_code_summary


class TestGetCodeSummary:
    def test_simple_function(self):
        code = "def hello(name):\n    print(name)\n"
        result = get_code_summary(code)
        assert "def hello(name): ..." in result

    def test_class_with_methods(self):
        code = (
            "class Dog:\n"
            "    def __init__(self, name):\n"
            "        self.name = name\n"
            "    def bark(self):\n"
            "        return 'woof'\n"
        )
        result = get_code_summary(code)
        assert "class Dog:" in result
        assert "def __init__(name): ..." in result  # self removed
        assert "def bark(): ..." in result  # self removed

    def test_class_with_base(self):
        code = "class Cat(Animal):\n    pass\n"
        result = get_code_summary(code)
        assert "class Cat(Animal):" in result

    def test_function_with_return_type(self):
        code = "def add(a, b) -> int:\n    return a + b\n"
        result = get_code_summary(code)
        assert "def add(a, b) -> int: ..." in result

    def test_nested_class_indentation(self):
        code = "class Outer:\n    class Inner:\n        def method(self):\n            pass\n"
        result = get_code_summary(code)
        lines = result.strip().split("\n")
        assert lines[0] == "class Outer:"
        assert lines[1] == "    class Inner:"
        assert lines[2] == "        def method(): ..."

    def test_syntax_error_handled(self):
        bad_code = "def broken(:\n"
        result = get_code_summary(bad_code)
        assert "Syntax Error" in result

    def test_empty_code(self):
        result = get_code_summary("")
        assert result == ""

    def test_multiple_functions(self):
        code = "def a(): pass\ndef b(x): pass\ndef c(x, y): pass\n"
        result = get_code_summary(code)
        assert "def a(): ..." in result
        assert "def b(x): ..." in result
        assert "def c(x, y): ..." in result

    def test_self_removed_from_args(self):
        code = "class X:\n    def method(self, arg1, arg2):\n        pass\n"
        result = get_code_summary(code)
        assert "def method(arg1, arg2): ..." in result
        assert "self" not in result

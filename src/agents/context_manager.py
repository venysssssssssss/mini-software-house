import ast


class CodeSummarizer(ast.NodeVisitor):
    """
    Parses Python code and extracts a structural summary (signatures of classes and functions).
    Used to save context window tokens by ignoring function bodies.
    """

    def __init__(self):
        self.summary = []
        self.indent_level = 0

    def visit_ClassDef(self, node):
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        base_str = f"({', '.join(bases)})" if bases else ""
        self.summary.append(f"{'    ' * self.indent_level}class {node.name}{base_str}:")

        self.indent_level += 1
        self.generic_visit(node)
        self.indent_level -= 1

    def visit_FunctionDef(self, node):
        args = [a.arg for a in node.args.args]
        if "self" in args:
            args.remove("self")

        # Add return type hint if present
        ret_annotation = ""
        if node.returns:
            # Simplified handling for simple return types
            if isinstance(node.returns, ast.Name):
                ret_annotation = f" -> {node.returns.id}"
            elif isinstance(node.returns, ast.Constant):
                ret_annotation = f" -> {node.returns.value}"

        indent = "    " * self.indent_level
        sig = f"{indent}def {node.name}({', '.join(args)}){ret_annotation}: ..."
        self.summary.append(sig)
        # Important: We do NOT visit the body of the function to keep it summarized


def _get_code_summary_python(code: str) -> str:
    """Pure-Python AST-based code summarizer."""
    try:
        tree = ast.parse(code)
        summarizer = CodeSummarizer()
        summarizer.visit(tree)
        return "\n".join(summarizer.summary)
    except SyntaxError:
        return "    (Syntax Error in file parsing)"


def get_code_summary(code: str) -> str:
    """Summarize Python code — uses Rust tree-sitter when available, else Python AST.

    Falls back to Python AST if Rust is unavailable or if the code has syntax errors
    (Python's ast module provides better error messages for invalid code).
    """
    # First check for syntax errors with Python's ast — it gives clear diagnostics
    try:
        ast.parse(code)
    except SyntaxError:
        return "    (Syntax Error in file parsing)"

    try:
        from ..utils.performance_bridge import get_rust_ast_parser

        rust_parser = get_rust_ast_parser()
        if rust_parser.available:
            return rust_parser.summarize(code)
    except Exception:
        pass

    return _get_code_summary_python(code)
